"""Filesystem execution for a reviewed, validated rename plan."""

from __future__ import annotations

import os
from collections.abc import Callable

from rename_plan import PlanIssue, RenameOperation, RenamePlan, plan_digest, validate_plan

ProgressCallback = Callable[[RenameOperation, str, str | None], None]


def apply_plan(
    plan: RenamePlan,
    rename_log_path: str | os.PathLike[str] | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[PlanIssue, ...]:
    """Revalidate, apply no-replace moves, and checkpoint progress when requested."""
    if plan_digest(plan.operations) != plan.digest:
        raise ValueError("rename-plan changed after validation")
    issues = validate_plan(plan)
    if issues:
        return issues
    completed: list[RenameOperation] = []
    for operation in plan.operations:
        if operation.source == operation.destination:
            continue
        try:
            os.link(operation.source, operation.destination)
            os.unlink(operation.source)
            completed.append(operation)
            if progress:
                progress(operation, "applied", None)
        except OSError as error:
            if progress:
                progress(operation, "failed", str(error))
            for completed_operation in reversed(completed):
                try:
                    os.link(completed_operation.destination, completed_operation.source)
                    os.unlink(completed_operation.destination)
                    if progress:
                        progress(completed_operation, "rolled_back", None)
                except OSError as rollback_error:
                    if progress:
                        progress(completed_operation, "rollback_failed", str(rollback_error))
            return (
                PlanIssue(
                    operation.scene_id,
                    operation.source,
                    operation.destination,
                    "apply_failed",
                    str(error),
                ),
            )
    if rename_log_path and completed:
        with open(rename_log_path, "a", encoding="utf-8") as rename_log:
            for operation in completed:
                rename_log.write(
                    "{}|{}|{}\n".format(operation.scene_id, operation.source, operation.destination)
                )
    return ()
