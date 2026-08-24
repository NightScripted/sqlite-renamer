"""Preconditioned reversal of completed rename-run manifests."""

from __future__ import annotations

import os

from execution import apply_plan
from rename_plan import PlanIssue, RenameOperation, RenamePlan, create_plan, validate_plan
from run_manifest import RunManifest, file_sha256, read_manifest


def create_undo_plan(manifest: RunManifest) -> tuple[RenamePlan, tuple[PlanIssue, ...]]:
    """Build a reversible plan only when completed targets still match their hashes."""
    issues: list[PlanIssue] = []
    operations: list[RenameOperation] = []
    if manifest.action != "apply" or manifest.state != "applied":
        issue = PlanIssue(
            "",
            "",
            "",
            "not_applied_manifest",
            "only completed apply manifests can be undone",
        )
        return create_plan(()), (issue,)

    for operation in manifest.operations:
        if operation.result == "noop":
            continue
        reverse = RenameOperation(operation.scene_id, operation.destination, operation.source)
        if operation.result != "applied":
            issues.append(
                PlanIssue(
                    reverse.scene_id,
                    reverse.source,
                    reverse.destination,
                    "operation_not_applied",
                    "manifest does not record this operation as applied",
                )
            )
            continue
        if not operation.sha256:
            issues.append(
                PlanIssue(
                    reverse.scene_id,
                    reverse.source,
                    reverse.destination,
                    "missing_fingerprint",
                    "manifest has no post-apply SHA-256 for this operation",
                )
            )
            continue
        if not os.path.isfile(reverse.source):
            issues.append(
                PlanIssue(
                    reverse.scene_id,
                    reverse.source,
                    reverse.destination,
                    "missing_applied_destination",
                    "applied destination no longer exists as a regular file",
                )
            )
            continue
        if file_sha256(reverse.source) != operation.sha256:
            issues.append(
                PlanIssue(
                    reverse.scene_id,
                    reverse.source,
                    reverse.destination,
                    "changed_applied_destination",
                    "applied destination SHA-256 differs from the completed run",
                )
            )
            continue
        if os.path.exists(reverse.destination):
            issues.append(
                PlanIssue(
                    reverse.scene_id,
                    reverse.source,
                    reverse.destination,
                    "occupied_original_source",
                    "original source path is occupied and will not be replaced",
                )
            )
            continue
        operations.append(reverse)

    plan = create_plan(operations)
    issues.extend(validate_plan(plan))
    return plan, tuple(issues)


def undo_manifest(manifest_path: str) -> tuple[RunManifest, RenamePlan, tuple[PlanIssue, ...]]:
    """Apply a validated reverse plan from one completed manifest, or return blockers."""
    manifest = read_manifest(manifest_path)
    plan, issues = create_undo_plan(manifest)
    if issues:
        return manifest, plan, issues
    return manifest, plan, apply_plan(plan)
