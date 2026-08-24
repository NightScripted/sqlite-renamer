import os
import sys

import config
import db
import logger
from renamer import edit_db


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


def _claim_new_scene_ids(scene_ids: str, claimed_scene_ids: set[str]) -> list[str]:
    """Return unclaimed scene IDs and reserve them for this tag pass."""
    new_scene_ids = []
    for scene_id in scene_ids.split(","):
        if scene_id and scene_id not in claimed_scene_ids:
            new_scene_ids.append(scene_id)
            claimed_scene_ids.add(scene_id)
    return new_scene_ids


def _run_tag_pass(dict_section: dict[str, str], claimed_scene_ids: set[str]) -> list[str]:
    """Rename the scenes uniquely claimed by one configured tag."""
    tag_id = db.gettingTagsID(dict_section.get("tag"))
    if tag_id is None:
        return []

    matching_scene_ids = db.get_SceneID_fromTags(tag_id)
    if not matching_scene_ids:
        return []

    scene_ids = _claim_new_scene_ids(matching_scene_ids, claimed_scene_ids)
    if not scene_ids:
        return []

    query, params = _build_scene_query(scene_ids, "IN")
    edit_db(dict_section.get("filename"), query, params)
    logger.logPrint("====================")
    return scene_ids


def _run_tag_passes() -> list[str]:
    """Run configured tag passes in order and return their claimed scene IDs."""
    tagged_scene_ids = []
    claimed_scene_ids = set()
    for dict_section in config.tags_dict.values():
        tagged_scene_ids.extend(_run_tag_pass(dict_section, claimed_scene_ids))
    return tagged_scene_ids


def _run_fallback_pass(tagged_scene_ids: list[str]) -> None:
    """Rename scenes that were not claimed by a configured tag."""
    if not config.FALLBACK_TEMPLATE:
        return

    if tagged_scene_ids:
        query, params = _build_scene_query(tagged_scene_ids, "NOT IN")
        edit_db(config.FALLBACK_TEMPLATE, query, params)
    elif config.PATH_FILTER:
        edit_db(config.FALLBACK_TEMPLATE, "WHERE d.path LIKE ?", (config.PATH_FILTER,))
    else:
        edit_db(config.FALLBACK_TEMPLATE)
    logger.logPrint("====================")


def run() -> None:
    """Run tag passes with first-match precedence, followed by the fallback."""
    logger.logPrint("Database Path: {}".format(config.DB_PATH))
    _clear_dry_run_log()

    db.connect()
    try:
        _run_fallback_pass(_run_tag_passes())
    finally:
        db.close()


def main() -> None:
    """Run the renamer and pause only for interactive command-line use."""
    run()
    if sys.stdin.isatty():
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()
