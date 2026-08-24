"""Versioned, atomically written records for plan and apply runs."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from rename_plan import RenamePlan, PlanIssue

MANIFEST_VERSION = 1


def write_manifest(plan: RenamePlan, issues: tuple[PlanIssue, ...], state: str, directory: str = "renamer_runs") -> Path:
    """Write one self-contained run record without exposing partial JSON."""
    run_id = str(uuid4())
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    issue_keys = {(issue.scene_id, issue.destination): issue.code for issue in issues}
    operations = [
        {
            "scene_id": operation.scene_id,
            "source": operation.source,
            "destination": operation.destination,
            "result": issue_keys.get((operation.scene_id, operation.destination), "noop" if operation.source == operation.destination else state),
        }
        for operation in plan.operations
    ]
    payload = {
        "version": MANIFEST_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "plan_digest": plan.digest,
        "state": state,
        "complete": state in {"planned", "applied", "blocked", "failed"},
        "operations": operations,
    }
    target = target_directory / f"{run_id}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target
