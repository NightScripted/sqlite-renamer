"""Versioned, digest-verified records for plan, apply, undo, and recovery runs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from rename_plan import (
    PlanIssue,
    RenameOperation,
    RenamePlan,
    create_plan,
    plan_digest,
    validate_plan,
)

MANIFEST_VERSION = 3
SUPPORTED_MANIFEST_VERSIONS = {2, MANIFEST_VERSION}
MANIFEST_STATES = {"planned", "running", "applied", "blocked", "failed", "undone", "interrupted"}
MANIFEST_ACTIONS = {"plan", "apply", "undo"}


@dataclass(frozen=True)
class ManifestOperation:
    """One persisted operation result with pre- and post-operation hashes."""

    scene_id: str
    source: str
    destination: str
    error: str | None
    result: str
    sha256: str | None
    source_sha256: str | None = None


@dataclass(frozen=True)
class RunManifest:
    """A digest-verified run record, including incomplete apply checkpoints."""

    version: int
    run_id: str
    created_at: str
    updated_at: str
    completed_at: str | None
    plan_digest: str
    configuration_digest: str | None
    action: str
    state: str
    complete: bool
    parent_run_id: str | None
    error: str | None
    operations: tuple[ManifestOperation, ...]


def _timestamp() -> str:
    """Return a UTC timestamp suitable for a persisted manifest."""
    return datetime.now(UTC).isoformat()


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest for a regular file without loading it all at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration_digest(configuration: Mapping[str, object]) -> str:
    """Return a stable digest of a private configuration snapshot without storing it."""
    payload = json.dumps(configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _manifest_payload(manifest: RunManifest) -> dict[str, object]:
    """Convert a manifest record to the v3 JSON representation."""
    return {
        "version": manifest.version,
        "run_id": manifest.run_id,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
        "completed_at": manifest.completed_at,
        "plan_digest": manifest.plan_digest,
        "configuration_digest": manifest.configuration_digest,
        "action": manifest.action,
        "state": manifest.state,
        "complete": manifest.complete,
        "parent_run_id": manifest.parent_run_id,
        "error": manifest.error,
        "operations": [
            {
                "scene_id": operation.scene_id,
                "source": operation.source,
                "destination": operation.destination,
                "error": operation.error,
                "result": operation.result,
                "sha256": operation.sha256,
                "source_sha256": operation.source_sha256,
            }
            for operation in manifest.operations
        ],
    }


def _write_record(path: Path, manifest: RunManifest) -> None:
    """Atomically replace one manifest record without exposing a partial JSON file."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(_manifest_payload(manifest), indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _manifest_operations(
    plan: RenamePlan, issues: tuple[PlanIssue, ...], state: str
) -> tuple[ManifestOperation, ...]:
    """Create immutable operation records for a completed planning-style manifest."""
    issue_keys = {(issue.scene_id, issue.destination): issue.code for issue in issues}
    return tuple(
        ManifestOperation(
            operation.scene_id,
            operation.source,
            operation.destination,
            operation.error,
            issue_keys.get(
                (operation.scene_id, operation.destination),
                "noop" if operation.source == operation.destination else state,
            ),
            file_sha256(operation.destination)
            if operation.source != operation.destination and state in {"applied", "undone"}
            else None,
        )
        for operation in plan.operations
    )


def _new_manifest(
    plan: RenamePlan,
    operations: tuple[ManifestOperation, ...],
    state: str,
    *,
    action: str,
    configuration: str | None,
    parent_run_id: str | None,
    complete: bool,
    error: str | None = None,
) -> RunManifest:
    """Build one validated in-memory v3 record."""
    if state not in MANIFEST_STATES:
        raise ValueError("unsupported manifest state: {}".format(state))
    if action not in MANIFEST_ACTIONS:
        raise ValueError("unsupported manifest action: {}".format(action))
    if action == "undo" and not parent_run_id:
        raise ValueError("undo manifests require a parent run ID")
    now = _timestamp()
    return RunManifest(
        MANIFEST_VERSION,
        str(uuid4()),
        now,
        now,
        now if complete else None,
        plan.digest,
        configuration,
        action,
        state,
        complete,
        parent_run_id,
        error,
        operations,
    )


class ManifestRecorder:
    """Atomically checkpoint one running apply or undo operation sequence."""

    def __init__(self, path: Path, manifest: RunManifest) -> None:
        """Bind an in-memory running manifest to its atomic on-disk record."""
        self.path = path
        self.manifest = manifest

    def _persist(
        self,
        *,
        state: str | None = None,
        complete: bool | None = None,
        error: str | None = None,
        update_error: bool = False,
        operations: tuple[ManifestOperation, ...] | None = None,
    ) -> None:
        """Persist a replacement record with an updated timestamp."""
        now = _timestamp()
        resulting_complete = self.manifest.complete if complete is None else complete
        self.manifest = replace(
            self.manifest,
            updated_at=now,
            completed_at=now if resulting_complete else None,
            state=self.manifest.state if state is None else state,
            complete=resulting_complete,
            error=error if update_error else self.manifest.error,
            operations=self.manifest.operations if operations is None else operations,
        )
        _write_record(self.path, self.manifest)

    def record(self, operation: RenameOperation, result: str, error: str | None = None) -> None:
        """Checkpoint the latest outcome for one operation after filesystem work."""
        completed_result = (
            "undone" if self.manifest.action == "undo" and result == "applied" else result
        )
        updated_operations = []
        found = False
        for recorded in self.manifest.operations:
            if (recorded.scene_id, recorded.destination) == (
                operation.scene_id,
                operation.destination,
            ):
                completed_target = (
                    operation.destination if completed_result in {"applied", "undone"} else None
                )
                updated_operations.append(
                    replace(
                        recorded,
                        result=completed_result,
                        error=error if error is not None else recorded.error,
                        sha256=file_sha256(completed_target) if completed_target else None,
                    )
                )
                found = True
            else:
                updated_operations.append(recorded)
        if not found:
            raise ValueError("operation is not part of this manifest")
        self._persist(operations=tuple(updated_operations))

    def begin_resume(self) -> None:
        """Mark an incomplete apply record as actively resuming after reconciliation."""
        self._persist(state="running", complete=False, error=None, update_error=True)

    def finalize(self, state: str, error: str | None = None) -> None:
        """Persist a completed, terminal operation outcome."""
        self._persist(state=state, complete=True, error=error, update_error=error is not None)

    def interrupt(self, error: BaseException) -> None:
        """Persist an incomplete checkpoint before propagating an interruption or exception."""
        state = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        self._persist(
            state=state,
            complete=False,
            error="{}: {}".format(type(error).__name__, error),
            update_error=True,
        )


def start_manifest(
    plan: RenamePlan,
    directory: str = "renamer_runs",
    *,
    action: str = "apply",
    configuration: str | None = None,
    parent_run_id: str | None = None,
) -> ManifestRecorder:
    """Write a running v3 checkpoint before the first apply or undo mutation."""
    if action not in {"apply", "undo"}:
        raise ValueError("only apply and undo runs can be started")
    operations = tuple(
        ManifestOperation(
            operation.scene_id,
            operation.source,
            operation.destination,
            operation.error,
            "noop" if operation.source == operation.destination else "pending",
            None,
            file_sha256(operation.source)
            if operation.source != operation.destination and os.path.isfile(operation.source)
            else None,
        )
        for operation in plan.operations
    )
    manifest = _new_manifest(
        plan,
        operations,
        "running",
        action=action,
        configuration=configuration,
        parent_run_id=parent_run_id,
        complete=False,
    )
    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)
    path = directory_path / "{}.json".format(manifest.run_id)
    _write_record(path, manifest)
    return ManifestRecorder(path, manifest)


def write_manifest(
    plan: RenamePlan,
    issues: tuple[PlanIssue, ...],
    state: str,
    directory: str = "renamer_runs",
    *,
    action: str = "plan",
    parent_run_id: str | None = None,
    configuration: str | None = None,
) -> Path:
    """Atomically write a completed digest-linked plan, apply, or undo record."""
    operations = _manifest_operations(plan, issues, state)
    manifest = _new_manifest(
        plan,
        operations,
        state,
        action=action,
        configuration=configuration,
        parent_run_id=parent_run_id,
        complete=True,
    )
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / "{}.json".format(manifest.run_id)
    _write_record(target, manifest)
    return target


def read_manifest(path: str | Path, *, allow_incomplete: bool = False) -> RunManifest:
    """Load a v2/v3 manifest and reject untrusted or incomplete records by default."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = payload.get("version")
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        raise ValueError("unsupported run-manifest version")
    if payload.get("action") not in MANIFEST_ACTIONS:
        raise ValueError("unsupported run-manifest action")
    if payload.get("state") not in MANIFEST_STATES:
        raise ValueError("run-manifest has an unsupported state")
    complete = payload.get("complete")
    if not isinstance(complete, bool):
        raise ValueError("run-manifest completion state is invalid")
    if not allow_incomplete and not complete:
        raise ValueError("run-manifest is incomplete")
    operations = tuple(
        ManifestOperation(
            operation["scene_id"],
            operation["source"],
            operation["destination"],
            operation.get("error"),
            operation["result"],
            operation.get("sha256"),
            operation.get("source_sha256"),
        )
        for operation in payload.get("operations", [])
    )
    plan_operations = tuple(
        RenameOperation(
            operation.scene_id, operation.source, operation.destination, operation.error
        )
        for operation in operations
    )
    if plan_digest(plan_operations) != payload.get("plan_digest"):
        raise ValueError("run-manifest digest does not match its operations")
    created_at = payload["created_at"]
    return RunManifest(
        version,
        payload["run_id"],
        created_at,
        payload.get("updated_at", created_at),
        payload.get("completed_at", created_at if complete else None),
        payload["plan_digest"],
        payload.get("configuration_digest"),
        payload["action"],
        payload["state"],
        complete,
        payload.get("parent_run_id"),
        payload.get("error"),
        operations,
    )


def _resume_issue(operation: ManifestOperation, code: str, message: str) -> PlanIssue:
    """Build a consistently attributed resume-safety issue."""
    return PlanIssue(operation.scene_id, operation.source, operation.destination, code, message)


def _verify_applied_operation(operation: ManifestOperation) -> PlanIssue | None:
    """Verify that a checkpointed completed destination is still trustworthy."""
    if not operation.sha256 or not os.path.isfile(operation.destination):
        return _resume_issue(
            operation,
            "resume_missing_applied_destination",
            "recorded applied destination is unavailable for resume verification",
        )
    if file_sha256(operation.destination) != operation.sha256:
        return _resume_issue(
            operation,
            "resume_changed_applied_destination",
            "recorded applied destination SHA-256 has changed",
        )
    return None


def _reconcile_pending_operation(
    recorder: ManifestRecorder, operation: ManifestOperation
) -> tuple[RenameOperation | None, PlanIssue | None]:
    """Return safely pending work or record a verified operation completed before interruption."""
    planned = RenameOperation(
        operation.scene_id, operation.source, operation.destination, operation.error
    )
    if operation.result != "pending" or not operation.source_sha256:
        return None, _resume_issue(
            operation,
            "resume_unknown_operation_state",
            "operation lacks a safely resumable pending state",
        )
    if os.path.isfile(operation.source) and not os.path.exists(operation.destination):
        if file_sha256(operation.source) == operation.source_sha256:
            return planned, None
        return None, _resume_issue(
            operation,
            "resume_changed_pending_source",
            "pending source SHA-256 has changed since the run began",
        )
    if not os.path.exists(operation.source) and os.path.isfile(operation.destination):
        if file_sha256(operation.destination) == operation.source_sha256:
            recorder.record(planned, "applied")
            return None, None
        return None, _resume_issue(
            operation,
            "resume_unverified_destination",
            "destination exists but does not match the recorded source SHA-256",
        )
    return None, _resume_issue(
        operation,
        "resume_conflicting_paths",
        "pending operation paths cannot be reconciled safely",
    )


def resume_manifest(path: str | Path) -> tuple[ManifestRecorder, RenamePlan, tuple[PlanIssue, ...]]:
    """Reconcile a v3 incomplete apply record and return only safely pending work."""
    manifest = read_manifest(path, allow_incomplete=True)
    recorder = ManifestRecorder(Path(path), manifest)
    if (
        manifest.version != MANIFEST_VERSION
        or manifest.action != "apply"
        or manifest.complete
        or manifest.state not in {"running", "interrupted", "failed"}
    ):
        issue = PlanIssue(
            "", "", "", "manifest_not_resumable", "only incomplete v3 apply manifests can resume"
        )
        return recorder, create_plan(()), (issue,)

    issues: list[PlanIssue] = []
    pending_operations: list[RenameOperation] = []
    for operation in manifest.operations:
        if operation.result == "noop":
            continue
        operation_issue: PlanIssue | None = (
            _verify_applied_operation(operation) if operation.result == "applied" else None
        )
        pending_operation: RenameOperation | None = None
        if operation.result != "applied":
            pending_operation, operation_issue = _reconcile_pending_operation(recorder, operation)
        if operation_issue:
            issues.append(operation_issue)
        elif pending_operation:
            pending_operations.append(pending_operation)

    plan = create_plan(pending_operations)
    issues.extend(validate_plan(plan))
    if not issues:
        recorder.begin_resume()
    return recorder, plan, tuple(issues)
