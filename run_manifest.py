"""Versioned, digest-verified records for plan, apply, and undo runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from rename_plan import PlanIssue, RenameOperation, RenamePlan, plan_digest

MANIFEST_VERSION = 2
COMPLETE_STATES = {"planned", "applied", "blocked", "failed", "undone"}
MANIFEST_ACTIONS = {"plan", "apply", "undo"}


@dataclass(frozen=True)
class ManifestOperation:
    """One persisted operation result with an optional post-operation hash."""

    scene_id: str
    source: str
    destination: str
    error: str | None
    result: str
    sha256: str | None


@dataclass(frozen=True)
class RunManifest:
    """A complete, digest-verified record that may be eligible for undo."""

    version: int
    run_id: str
    created_at: str
    plan_digest: str
    action: str
    state: str
    complete: bool
    parent_run_id: str | None
    operations: tuple[ManifestOperation, ...]


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest for a regular file without loading it all at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    plan: RenamePlan,
    issues: tuple[PlanIssue, ...],
    state: str,
    directory: str = "renamer_runs",
    *,
    action: str = "plan",
    parent_run_id: str | None = None,
) -> Path:
    """Atomically write one digest-linked record, hashing completed targets."""
    if state not in COMPLETE_STATES:
        raise ValueError("unsupported manifest state: {}".format(state))
    if action not in MANIFEST_ACTIONS:
        raise ValueError("unsupported manifest action: {}".format(action))
    if action == "undo" and not parent_run_id:
        raise ValueError("undo manifests require a parent run ID")

    run_id = str(uuid4())
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    issue_keys = {(issue.scene_id, issue.destination): issue.code for issue in issues}
    operations = []
    for operation in plan.operations:
        result = issue_keys.get(
            (operation.scene_id, operation.destination),
            "noop" if operation.source == operation.destination else state,
        )
        completed_target = (
            operation.destination if result == state and state in {"applied", "undone"} else None
        )
        operations.append(
            {
                "scene_id": operation.scene_id,
                "source": operation.source,
                "destination": operation.destination,
                "error": operation.error,
                "result": result,
                "sha256": file_sha256(completed_target) if completed_target else None,
            }
        )
    payload = {
        "version": MANIFEST_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "plan_digest": plan.digest,
        "action": action,
        "state": state,
        "complete": state in COMPLETE_STATES,
        "parent_run_id": parent_run_id,
        "operations": operations,
    }
    target = target_directory / f"{run_id}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def read_manifest(path: str | Path) -> RunManifest:
    """Load a v2 manifest and reject changed operation records before undo."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != MANIFEST_VERSION:
        raise ValueError("unsupported run-manifest version; only v2 manifests support safe undo")
    if payload.get("action") not in MANIFEST_ACTIONS:
        raise ValueError("unsupported run-manifest action")
    if payload.get("state") not in COMPLETE_STATES or not payload.get("complete"):
        raise ValueError("run-manifest is incomplete or has an unsupported state")
    operations = tuple(
        ManifestOperation(**operation) for operation in payload.get("operations", [])
    )
    plan_operations = tuple(
        RenameOperation(
            operation.scene_id, operation.source, operation.destination, operation.error
        )
        for operation in operations
    )
    if plan_digest(plan_operations) != payload.get("plan_digest"):
        raise ValueError("run-manifest digest does not match its operations")
    return RunManifest(
        version=payload["version"],
        run_id=payload["run_id"],
        created_at=payload["created_at"],
        plan_digest=payload["plan_digest"],
        action=payload["action"],
        state=payload["state"],
        complete=payload["complete"],
        parent_run_id=payload.get("parent_run_id"),
        operations=operations,
    )
