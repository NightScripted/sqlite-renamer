"""Pure filename rendering plus a plan-only compatibility entry point."""

from __future__ import annotations

import re


def makeFilename(scene_info, query):
    """Build a filename stem by substituting template variables with scene metadata.

    Available variables are ``$date``, ``$performer``, ``$title``, ``$studio``,
    and ``$height``. Missing variables and their surrounding separators are
    removed before whitespace and empty brackets are normalized.
    """
    new_filename = str(query)
    for variable in ("date", "performer", "title", "studio", "height"):
        token = "${}".format(variable)
        value = scene_info.get(variable)
        if token not in new_filename:
            continue
        if value == "" or value is None:
            new_filename = re.sub(r"\${}\s*".format(variable), "", new_filename)
        else:
            new_filename = new_filename.replace(token, str(value))
    new_filename = re.sub(r"^\s*-\s*", "", new_filename)
    new_filename = re.sub(r"\s*-\s*$", "", new_filename)
    new_filename = re.sub(r"\[\W*]", "", new_filename)
    return re.sub(r"\s{2,}", " ", new_filename).strip()


def edit_db(query_filename, optional_query="", params=()):
    """Render a validated plan using a temporary explicit database handle.

    This compatibility function never applies filesystem changes. New callers
    should use :mod:`run_renamer`, which combines all tag and fallback passes
    in one plan before rendering or applying it.
    """
    import config
    from db import open_database
    from planning import discover_operations
    from rename_plan import create_plan, render_plan, validate_plan

    with open_database() as database:
        operations = discover_operations(
            database,
            query_filename,
            optional_query,
            params,
            config.STOP_AFTER_FIRST,
        )
    plan = create_plan(operations)
    issues = validate_plan(plan)
    with open("renamer_dryrun.txt", "a", encoding="utf-8") as dry_run_log:
        dry_run_log.write(render_plan(plan, issues))
    return plan
