"""Create, preview, apply, and undo safe persisted rename plans."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path

import config
import db
import logger
from planning import discover_operations
from execution import apply_plan
from rename_plan import (
    PlanIssue,
    RenamePlan,
    create_plan,
    read_plan,
    render_plan,
    validate_plan,
    write_plan,
)
from run_manifest import (
    configuration_digest,
    read_manifest,
    resume_manifest,
    start_manifest,
    write_manifest,
)
from undo import create_undo_plan


PLAN_FILE = "renamer_plan.json"


def _current_configuration_digest() -> str:
    """Hash the active private settings for manifest audit without storing their values."""
    return configuration_digest(
        {
            "DB_PATH": config.DB_PATH,
            "USING_LOG": config.USING_LOG,
            "FEMALE_ONLY": config.FEMALE_ONLY,
            "STOP_AFTER_FIRST": config.STOP_AFTER_FIRST,
            "tags_dict": config.tags_dict,
            "PATH_FILTER": config.PATH_FILTER,
            "FALLBACK_TEMPLATE": config.FALLBACK_TEMPLATE,
        }
    )


def _apply_with_manifest(
    plan: RenamePlan,
    *,
    action: str = "apply",
    parent_run_id: str | None = None,
) -> tuple[tuple[PlanIssue, ...], Path]:
    """Apply one validated plan with an atomic checkpoint before and after each mutation."""
    configuration = _current_configuration_digest()
    issues = validate_plan(plan)
    if issues:
        manifest = write_manifest(
            plan,
            issues,
            "blocked",
            action=action,
            parent_run_id=parent_run_id,
            configuration=configuration,
        )
        return issues, manifest
    recorder = start_manifest(
        plan,
        action=action,
        parent_run_id=parent_run_id,
        configuration=configuration,
    )
    try:
        issues = apply_plan(
            plan,
            "rename_log.txt" if config.USING_LOG else None,
            recorder.record,
        )
    except BaseException as error:
        recorder.interrupt(error)
        raise
    if issues and action == "apply":
        recorder.fail(issues)
    else:
        recorder.finalize("failed" if issues else "undone" if action == "undo" else "applied")
    return issues, recorder.path


@dataclass(frozen=True)
class TagPassSummary:
    """Outcome of one configured tag rule during operation discovery."""

    name: str
    status: str
    matching_scene_count: int
    claimed_scene_count: int
    operation_count: int


def _clear_dry_run_log() -> None:
    """Clear the prior dry-run log when dry-run mode is enabled."""
    if not config.DRY_RUN:
        return

    try:
        os.remove("renamer_dryrun.txt")
    except FileNotFoundError:
        pass
    except OSError as error:
        logger.logPrint("[Warn] Could not remove renamer_dryrun.txt: {}".format(error))
    logger.logPrint("[DRY_RUN] DRY-RUN Enabled")


def _build_scene_query(scene_ids: list[str], operator: str) -> tuple[str, tuple[str, ...]]:
    """Build a parameterized scene-ID query, optionally constrained by path."""
    placeholders = ",".join("?" for _ in scene_ids)
    query = "WHERE s.id {} ({})".format(operator, placeholders)
    params = tuple(scene_ids)
    if config.PATH_FILTER:
        return "{} AND d.path LIKE ?".format(query), params + (config.PATH_FILTER,)
    return query, params


def _claim_new_scene_ids(scene_ids: list[str], claimed_scene_ids: set[str]) -> list[str]:
    """Return unclaimed scene IDs and reserve them for this tag pass."""
    new_scene_ids = []
    for scene_id in scene_ids:
        if scene_id and scene_id not in claimed_scene_ids:
            new_scene_ids.append(scene_id)
            claimed_scene_ids.add(scene_id)
    return new_scene_ids


def _discover_tag_pass(
    database: db.Database,
    dict_section: dict[str, str],
    claimed_scene_ids: set[str],
    summaries: list[TagPassSummary] | None = None,
) -> tuple[list[str], list]:
    """Discover operations for the scenes uniquely claimed by one tag."""
    tag_name = dict_section["tag"]
    tag_id = database.get_tag_id(tag_name)
    if tag_id is None:
        if summaries is not None:
            summaries.append(TagPassSummary(tag_name, "missing", 0, 0, 0))
        return [], []

    matching_scene_ids = database.get_scene_ids_for_tag(tag_id)
    if not matching_scene_ids:
        if summaries is not None:
            summaries.append(TagPassSummary(tag_name, "empty", 0, 0, 0))
        return [], []

    scene_ids = _claim_new_scene_ids(matching_scene_ids, claimed_scene_ids)
    if not scene_ids:
        if summaries is not None:
            summaries.append(
                TagPassSummary(tag_name, "claimed_by_earlier_rule", len(matching_scene_ids), 0, 0)
            )
        return [], []

    query, params = _build_scene_query(scene_ids, "IN")
    operations = discover_operations(
        database, dict_section.get("filename", ""), query, params, config.STOP_AFTER_FIRST
    )
    logger.logPrint("====================")
    if summaries is not None:
        summaries.append(
            TagPassSummary(
                tag_name, "selected", len(matching_scene_ids), len(scene_ids), len(operations)
            )
        )
    return scene_ids, operations


def _discover_tag_passes(
    database: db.Database, summaries: list[TagPassSummary] | None = None
) -> tuple[list[str], list]:
    """Discover tag operations in first-match order and return claimed IDs."""
    tagged_scene_ids = []
    operations = []
    claimed_scene_ids: set[str] = set()
    for dict_section in config.tags_dict.values():
        scene_ids, tag_operations = _discover_tag_pass(
            database, dict_section, claimed_scene_ids, summaries
        )
        tagged_scene_ids.extend(scene_ids)
        operations.extend(tag_operations)
    return tagged_scene_ids, operations


def _discover_fallback_pass(database: db.Database, tagged_scene_ids: list[str]) -> list:
    """Discover fallback operations for scenes not claimed by a tag."""
    if not config.FALLBACK_TEMPLATE:
        return []

    if tagged_scene_ids:
        query, params = _build_scene_query(tagged_scene_ids, "NOT IN")
        operations = discover_operations(
            database, config.FALLBACK_TEMPLATE, query, params, config.STOP_AFTER_FIRST
        )
    elif config.PATH_FILTER:
        operations = discover_operations(
            database,
            config.FALLBACK_TEMPLATE,
            "WHERE d.path LIKE ?",
            (config.PATH_FILTER,),
            config.STOP_AFTER_FIRST,
        )
    else:
        operations = discover_operations(
            database, config.FALLBACK_TEMPLATE, stop_after_first=config.STOP_AFTER_FIRST
        )
    logger.logPrint("====================")
    return operations


def render_configuration_summary(
    tag_summaries: list[TagPassSummary], fallback_operation_count: int
) -> str:
    """Render configuration and configured-tag outcomes without changing the plan."""
    fallback_state = "enabled" if config.FALLBACK_TEMPLATE else "disabled"
    path_filter_state = "enabled" if config.PATH_FILTER else "disabled"
    stop_state = "enabled" if config.STOP_AFTER_FIRST else "disabled"
    lines = [
        "CONFIGURATION SUMMARY",
        "=====================",
        "Mode: {}".format("dry run" if config.DRY_RUN else "plan only; apply is explicit"),
        "Tag rules: {}; fallback: {}; path filter: {}; stop after first: {}".format(
            len(tag_summaries), fallback_state, path_filter_state, stop_state
        ),
    ]
    if tag_summaries:
        status_counts: dict[str, int] = {}
        for summary in tag_summaries:
            status_counts[summary.status] = status_counts.get(summary.status, 0) + 1
        lines.append(
            "Tag outcomes: {}".format(
                ", ".join(
                    "{} {}".format(count, status.replace("_", " "))
                    for status, count in sorted(status_counts.items())
                )
            )
        )
        for summary in tag_summaries:
            if summary.status == "missing":
                lines.append("MISSING TAG: {}".format(summary.name))
            elif summary.status == "empty":
                lines.append("EMPTY TAG: {}".format(summary.name))
            elif summary.status == "claimed_by_earlier_rule":
                lines.append(
                    "SHADOWED TAG: {} ({} matching scene(s) claimed by earlier rule)".format(
                        summary.name, summary.matching_scene_count
                    )
                )
            else:
                lines.append(
                    "TAG: {} ({} matching, {} claimed, {} operation(s))".format(
                        summary.name,
                        summary.matching_scene_count,
                        summary.claimed_scene_count,
                        summary.operation_count,
                    )
                )
    lines.append("Fallback: {} operation(s) ({})".format(fallback_operation_count, fallback_state))
    return "\n".join(lines) + "\n"


def run(plan_path: str = PLAN_FILE) -> None:
    """Create one validated persisted plan and its review report without applying it."""
    config.validate()
    logger.logPrint("Database Path: {}".format(config.DB_PATH))
    _clear_dry_run_log()

    tag_summaries: list[TagPassSummary] = []
    with db.open_database() as database:
        tagged_scene_ids, operations = _discover_tag_passes(database, tag_summaries)
        fallback_operations = _discover_fallback_pass(database, tagged_scene_ids)
        operations.extend(fallback_operations)
    plan = create_plan(operations)
    issues = validate_plan(plan)
    write_plan(plan, plan_path)
    rendered = "{}\n{}".format(
        render_configuration_summary(tag_summaries, len(fallback_operations)),
        render_plan(plan, issues),
    )
    with open("renamer_dryrun.txt", "w", encoding="utf-8") as dry_run_log:
        dry_run_log.write(rendered)
    logger.logPrint(rendered.rstrip())
    logger.logPrint("[PLAN] Wrote {}".format(plan_path))
    if not config.DRY_RUN:
        manifest = write_manifest(
            plan,
            issues,
            "blocked" if issues else "planned",
            configuration=_current_configuration_digest(),
        )
        logger.logPrint("[MANIFEST] Wrote {}".format(manifest))
    # Planning never mutates files. A reviewed persisted plan requires the
    # explicit --apply-plan command and DRY_RUN=False configuration.
    return


def main(argv: list[str] | None = None) -> None:
    """Load configuration and either create a plan or apply a saved plan."""
    parser = argparse.ArgumentParser(description="Safely plan or apply Stash file renames.")
    parser.add_argument("--config", help="path to a private Python configuration file")
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--apply-plan", metavar="PATH", help="apply a saved, digest-verified plan"
    )
    action_group.add_argument(
        "--undo-manifest",
        metavar="PATH",
        help="undo one completed v2/v3 apply manifest after hash precondition checks",
    )
    action_group.add_argument(
        "--resume-manifest",
        metavar="PATH",
        help="reconcile and resume one interrupted v3 apply manifest",
    )
    action_group.add_argument(
        "--preview-plan",
        metavar="PATH",
        help="revalidate and display a saved plan without applying it",
    )
    parser.add_argument(
        "--plan-file", default=PLAN_FILE, help="destination for a newly discovered plan"
    )
    args = parser.parse_args(argv)
    try:
        if args.preview_plan:
            plan = read_plan(args.preview_plan)
            logger.logPrint(render_plan(plan, validate_plan(plan)).rstrip())
            return
        config.load_local_config(args.config)
        if args.apply_plan:
            if config.DRY_RUN:
                parser.error("refusing to apply a plan while DRY_RUN is enabled")
            plan = read_plan(args.apply_plan)
            issues, manifest_path = _apply_with_manifest(plan)
            logger.logPrint("[MANIFEST] Wrote {}".format(manifest_path))
            if issues:
                parser.error("plan is blocked or changed; regenerate and review it")
            return
        if args.resume_manifest:
            if config.DRY_RUN:
                parser.error("refusing to resume a manifest while DRY_RUN is enabled")
            recorder, plan, issues = resume_manifest(args.resume_manifest)
            if issues:
                parser.error("resume is blocked by manifest or filesystem preconditions")
            try:
                issues = apply_plan(
                    plan,
                    "rename_log.txt" if config.USING_LOG else None,
                    recorder.record,
                )
            except BaseException as error:
                recorder.interrupt(error)
                raise
            if issues:
                recorder.fail(issues)
            else:
                recorder.finalize("applied")
            logger.logPrint("[MANIFEST] Updated {}".format(recorder.path))
            if issues:
                parser.error("resumed plan is blocked or changed; inspect its manifest")
            return
        if args.undo_manifest:
            if config.DRY_RUN:
                parser.error("refusing to undo a manifest while DRY_RUN is enabled")
            manifest = read_manifest(args.undo_manifest)
            plan, issues = create_undo_plan(manifest)
            if not issues:
                issues, undo_record = _apply_with_manifest(
                    plan, action="undo", parent_run_id=manifest.run_id
                )
            else:
                undo_record = write_manifest(
                    plan,
                    issues,
                    "blocked",
                    action="undo",
                    parent_run_id=manifest.run_id,
                    configuration=_current_configuration_digest(),
                )
            logger.logPrint("[MANIFEST] Wrote {}".format(undo_record))
            if issues:
                parser.error("undo is blocked by manifest or filesystem preconditions")
            return
        run(args.plan_file)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
