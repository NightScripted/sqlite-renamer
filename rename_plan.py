"""Immutable rename planning, validation, rendering, and application."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable


PLAN_VERSION = 1
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    *(f"COM{number}" for number in "¹²³"),
    *(f"LPT{number}" for number in "¹²³"),
}
INVALID_FILENAME_CHARS = re.compile(r'[\\/:"*?<>|#,\x00-\x1f]+')


@dataclass(frozen=True)
class RenameOperation:
    """One proposed rename, including a template-rendering error when present."""

    scene_id: str
    source: str
    destination: str
    error: str | None = None


@dataclass(frozen=True)
class PlanIssue:
    """A non-mutating safety finding associated with one planned operation."""

    scene_id: str
    source: str
    destination: str
    code: str
    message: str


@dataclass(frozen=True)
class RenamePlan:
    """An immutable, digest-protected set of proposed rename operations."""

    version: int
    created_at: str
    operations: tuple[RenameOperation, ...]
    digest: str


def sanitize_filename(filename: str) -> str:
    """Return a Windows-safe filename component or raise ``ValueError``.

    The existing punctuation policy also strips ``#`` and ``,``. Control
    characters plus leading/trailing ASCII spaces and trailing periods are
    removed. Reserved Windows basenames are rejected rather than silently
    renamed to an unrelated file.
    """
    cleaned = INVALID_FILENAME_CHARS.sub("", filename).lstrip(" ").rstrip(". ")
    if not cleaned or not any(character.isalnum() for character in cleaned):
        raise ValueError("filename is empty after Windows normalization")
    stem = cleaned.split(".", 1)[0].rstrip(" ").upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise ValueError("filename uses reserved Windows basename: {}".format(stem))
    return cleaned


def _canonical_operations(operations: Iterable[RenameOperation]) -> list[dict[str, str | None]]:
    """Convert operations to the stable JSON-compatible structure used for hashing."""
    return [asdict(operation) for operation in operations]


def plan_digest(operations: Iterable[RenameOperation]) -> str:
    """Return the stable SHA-256 digest for a sequence of operations."""
    payload = json.dumps(_canonical_operations(operations), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_plan(operations: Iterable[RenameOperation]) -> RenamePlan:
    """Freeze operations into a timestamped plan with its integrity digest."""
    frozen_operations = tuple(operations)
    return RenamePlan(
        version=PLAN_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        operations=frozen_operations,
        digest=plan_digest(frozen_operations),
    )


def write_plan(plan: RenamePlan, path: str | os.PathLike[str]) -> None:
    """Persist a reviewable plan; its digest covers every operation."""
    payload = {
        "version": plan.version,
        "created_at": plan.created_at,
        "operations": _canonical_operations(plan.operations),
        "digest": plan.digest,
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_plan(path: str | os.PathLike[str]) -> RenamePlan:
    """Read and integrity-check a persisted rename plan."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != PLAN_VERSION:
        raise ValueError("unsupported rename-plan version")
    operations = tuple(RenameOperation(**operation) for operation in payload.get("operations", []))
    plan = RenamePlan(payload["version"], payload["created_at"], operations, payload["digest"])
    if plan_digest(plan.operations) != plan.digest:
        raise ValueError("rename-plan digest does not match its operations")
    return plan


def _normalized_destination(destination: str) -> str:
    """Return the case-insensitive Windows comparison form for a destination."""
    parent, filename = os.path.split(os.path.normpath(destination))
    return os.path.join(parent, filename.lstrip(" ").rstrip(". ")).casefold()


def validate_plan(plan: RenamePlan) -> tuple[PlanIssue, ...]:
    """Validate filesystem and cross-operation safety without modifying files."""
    issues: list[PlanIssue] = []
    destinations: dict[str, RenameOperation] = {}
    for operation in plan.operations:
        if operation.error:
            issues.append(
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "invalid_name",
                    operation.error,
                )
            )
            continue
        if operation.source == operation.destination:
            continue
        source_directory = os.path.abspath(os.path.dirname(operation.source))
        destination_directory = os.path.abspath(os.path.dirname(operation.destination))
        if source_directory != destination_directory:
            issues.append(
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "outside_source_directory",
                    "destination must remain in the source directory",
                )
            )
        if not os.path.isfile(operation.source):
            issues.append(
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "missing_source",
                    "source file does not exist",
                )
            )
        if os.path.exists(operation.destination):
            issues.append(
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "occupied_destination",
                    "destination already exists",
                )
            )
        normalized = _normalized_destination(operation.destination)
        other = destinations.get(normalized)
        if other is not None:
            issues.append(
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "duplicate_destination",
                    "normalizes to the same destination as scene {}".format(other.scene_id),
                )
            )
        else:
            destinations[normalized] = operation
    return tuple(issues)


def render_plan(plan: RenamePlan, issues: Iterable[PlanIssue]) -> str:
    """Render an accessible terminal preview of all operations and blockers."""
    issue_list = tuple(issues)
    issue_map: dict[tuple[str, str], list[PlanIssue]] = {}
    for issue in issue_list:
        issue_map.setdefault((issue.scene_id, issue.destination), []).append(issue)

    status_counts: Counter[str] = Counter()
    blocked_operations: list[tuple[RenameOperation, list[PlanIssue]]] = []
    for operation in plan.operations:
        operation_issues = issue_map.get((operation.scene_id, operation.destination), [])
        if operation_issues:
            status_counts["blocked"] += 1
            blocked_operations.append((operation, operation_issues))
        elif operation.source == operation.destination:
            status_counts["no-op"] += 1
        else:
            status_counts["ready"] += 1

    lines = [
        "RENAME PLAN PREVIEW",
        "===================",
        "Plan: v{}  digest: {}".format(plan.version, plan.digest),
        "Summary: {} ready, {} no-op, {} blocked ({} issue(s))".format(
            status_counts["ready"],
            status_counts["no-op"],
            status_counts["blocked"],
            len(issue_list),
        ),
    ]
    if blocked_operations:
        issue_counts = Counter(issue.code for issue in issue_list)
        lines.extend(["", "CONFLICTS AND BLOCKERS", "---------------------"])
        lines.append(
            "Checks: {}".format(
                ", ".join(
                    "{} ({})".format(code, count) for code, count in sorted(issue_counts.items())
                )
            )
        )
        for operation, operation_issues in blocked_operations:
            codes = ", ".join(issue.code for issue in operation_issues)
            lines.append(
                "BLOCKED [{}] {} -> {}".format(codes, operation.source, operation.destination)
            )
            for issue in operation_issues:
                lines.append("  - {}: {}".format(issue.code, issue.message))

    lines.extend(["", "OPERATIONS", "----------"])
    for operation in plan.operations:
        operation_issues = issue_map.get((operation.scene_id, operation.destination), [])
        if operation_issues:
            codes = ", ".join(issue.code for issue in operation_issues)
            lines.append(
                "BLOCKED [{}] {} -> {}".format(codes, operation.source, operation.destination)
            )
        elif operation.source == operation.destination:
            lines.append("NOOP {}".format(operation.source))
        else:
            lines.append("READY {} -> {}".format(operation.source, operation.destination))
    return "\n".join(lines) + "\n"


def apply_plan(plan: RenamePlan) -> tuple[PlanIssue, ...]:
    """Apply through the isolated executor, retaining the historic API."""
    import config
    from execution import apply_plan as execute_plan

    return execute_plan(plan, "rename_log.txt" if config.USING_LOG else None)
