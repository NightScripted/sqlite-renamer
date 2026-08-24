import argparse
import os

import config
import db
import logger
from planning import discover_operations
from execution import apply_plan
from rename_plan import create_plan, read_plan, render_plan, validate_plan, write_plan
from run_manifest import write_manifest


PLAN_FILE = "renamer_plan.json"


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
) -> tuple[list[str], list]:
    """Discover operations for the scenes uniquely claimed by one tag."""
    tag_id = database.get_tag_id(dict_section.get("tag", ""))
    if tag_id is None:
        return [], []

    matching_scene_ids = database.get_scene_ids_for_tag(tag_id)
    if not matching_scene_ids:
        return [], []

    scene_ids = _claim_new_scene_ids(matching_scene_ids, claimed_scene_ids)
    if not scene_ids:
        return [], []

    query, params = _build_scene_query(scene_ids, "IN")
    operations = discover_operations(
        database, dict_section.get("filename", ""), query, params, config.STOP_AFTER_FIRST
    )
    logger.logPrint("====================")
    return scene_ids, operations


def _discover_tag_passes(database: db.Database) -> tuple[list[str], list]:
    """Discover tag operations in first-match order and return claimed IDs."""
    tagged_scene_ids = []
    operations = []
    claimed_scene_ids: set[str] = set()
    for dict_section in config.tags_dict.values():
        scene_ids, tag_operations = _discover_tag_pass(database, dict_section, claimed_scene_ids)
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


def run(plan_path: str = PLAN_FILE) -> None:
    """Create one validated plan, then render or apply that exact plan."""
    config.validate()
    logger.logPrint("Database Path: {}".format(config.DB_PATH))
    _clear_dry_run_log()

    with db.open_database() as database:
        tagged_scene_ids, operations = _discover_tag_passes(database)
        operations.extend(_discover_fallback_pass(database, tagged_scene_ids))
    plan = create_plan(operations)
    issues = validate_plan(plan)
    write_plan(plan, plan_path)
    rendered = render_plan(plan, issues)
    with open("renamer_dryrun.txt", "w", encoding="utf-8") as dry_run_log:
        dry_run_log.write(rendered)
    logger.logPrint(rendered.rstrip())
    logger.logPrint("[PLAN] Wrote {}".format(plan_path))
    if not config.DRY_RUN:
        manifest = write_manifest(plan, issues, "blocked" if issues else "planned")
        logger.logPrint("[MANIFEST] Wrote {}".format(manifest))
    # Planning never mutates files. A reviewed persisted plan requires the
    # explicit --apply-plan command and DRY_RUN=False configuration.
    return


def main(argv: list[str] | None = None) -> None:
    """Load configuration and either create a plan or apply a saved plan."""
    parser = argparse.ArgumentParser(description="Safely plan or apply Stash file renames.")
    parser.add_argument("--config", help="path to a private Python configuration file")
    parser.add_argument("--apply-plan", metavar="PATH", help="apply a saved, digest-verified plan")
    parser.add_argument(
        "--plan-file", default=PLAN_FILE, help="destination for a newly discovered plan"
    )
    args = parser.parse_args(argv)
    try:
        config.load_local_config(args.config)
        if args.apply_plan:
            if config.DRY_RUN:
                parser.error("refusing to apply a plan while DRY_RUN is enabled")
            plan = read_plan(args.apply_plan)
            issues = apply_plan(plan, "rename_log.txt" if config.USING_LOG else None)
            write_manifest(plan, issues, "failed" if issues else "applied")
            if issues:
                parser.error("plan is blocked or changed; regenerate and review it")
            return
        run(args.plan_file)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
