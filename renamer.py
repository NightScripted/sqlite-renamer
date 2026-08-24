import os
import re

import progressbar

import config
import db
import logger


def makeFilename(scene_info, query):
    """Build a filename stem by substituting template variables with scene metadata.

    Available variables: ``$date``, ``$performer``, ``$title``, ``$studio``,
    ``$height``. Variables whose values are ``None`` or ``""`` are removed
    along with surrounding separators. Post-processing collapses duplicate
    spaces, strips leading/trailing dashes, removes empty bracket pairs, and
    trims whitespace.

    Args:
        scene_info (dict): Keys ``"date"``, ``"performer"``, ``"title"``,
            ``"studio"``, ``"height"`` mapping to string values or ``None``.
        query (str): Template string, e.g.
            ``"$date $performer - $title [$studio]"``.

    Returns:
        str: Rendered filename stem with no extension and no directory path.

    Example::

        makeFilename({"title": "Her Fantasy Ball", "date": "2016-12-29",
                      "performer": "Eva Lovia", "studio": "Sneaky Sex",
                      "height": "1080p"},
                     "$date $performer - $title [$studio]")
        # → "2016-12-29 Eva Lovia - Her Fantasy Ball [Sneaky Sex]"
    """
    new_filename = str(query)
    if "$date" in new_filename:
        if scene_info.get("date") == "" or scene_info.get("date") is None:
            new_filename = re.sub(r"\$date\s*", "", new_filename)
        else:
            new_filename = new_filename.replace("$date", scene_info["date"])

    if "$performer" in new_filename:
        if scene_info.get("performer") == "" or scene_info.get("performer") is None:
            new_filename = re.sub(r"\$performer\s*", "", new_filename)
        else:
            new_filename = new_filename.replace("$performer", scene_info["performer"])

    if "$title" in new_filename:
        if scene_info.get("title") == "" or scene_info.get("title") is None:
            new_filename = re.sub(r"\$title\s*", "", new_filename)
        else:
            new_filename = new_filename.replace("$title", scene_info["title"])

    if "$studio" in new_filename:
        if scene_info.get("studio") == "" or scene_info.get("studio") is None:
            new_filename = re.sub(r"\$studio\s*", "", new_filename)
        else:
            new_filename = new_filename.replace("$studio", scene_info["studio"])

    if "$height" in new_filename:
        if scene_info.get("height") == "" or scene_info.get("height") is None:
            new_filename = re.sub(r"\$height\s*", "", new_filename)
        else:
            new_filename = new_filename.replace("$height", scene_info["height"])
    new_filename = re.sub(r"^\s*-\s*", "", new_filename)
    new_filename = re.sub(r"\s*-\s*$", "", new_filename)
    new_filename = re.sub(r"\[\W*]", "", new_filename)
    new_filename = re.sub(r"\s{2,}", " ", new_filename)
    new_filename = new_filename.strip()
    return new_filename


def _legacy_edit_db(query_filename, optional_query="", params=()):  # pragma: no cover
    """Rename scene files on disk according to a filename template.

    Fetches scenes from the Stash SQLite database (optionally filtered by
    *optional_query*), generates a new filename for each scene using
    :func:`makeFilename`, and either renames the file on disk (live mode) or
    records the proposed rename (dry-run mode).

    Log files appended during the run (all relative to the working directory):

    * ``renamer_duplicate.txt`` — scenes skipped due to a filename collision
      (format: ``scene_id|current_path|new_filename``).
    * ``rename_log.txt`` — successful renames when ``config.USING_LOG`` is ``True``
      (format: ``scene_id|old_path|new_path``).
    * ``renamer_fail.txt`` — OS-level rename failures
      (format: ``old_path -> new_path``).
    * ``renamer_dryrun.txt`` — proposed renames when ``config.DRY_RUN`` is ``True``
      (format: ``old_path -> new_path``).

    Args:
        query_filename (str): Filename template passed to :func:`makeFilename`.
        optional_query (str): Optional SQL ``WHERE`` clause appended to the
            base scene query, e.g. ``"WHERE s.id in (1,2,3)"``. Defaults to
            ``""`` (all scenes).
        params (tuple): Values bound to any ``?`` placeholders in
            *optional_query*. Defaults to ``()`` (no parameters).
    """
    scene_query = """
    SELECT s.id,f.basename,d.path,s.title,s.date,s.studio_id,vf.height
    FROM scenes AS s
    LEFT JOIN scenes_files AS sf ON s.id = sf.scene_id
    LEFT JOIN files AS f ON sf.file_id = f.id
    LEFT JOIN folders AS d ON f.parent_folder_id = d.id
    LEFT JOIN video_files AS vf ON f.id = vf.file_id
    """
    db.cursor.execute(f'{scene_query} {optional_query};', params)
    record = db.cursor.fetchall()
    if len(record) == 0:
        logger.logPrint("[Warn] There is no scene to change with this query")
        return
    logger.logPrint("Scenes numbers: {}".format(len(record)))
    progressbar_Index = 0
    progress = progressbar.ProgressBar(redirect_stdout=True).start(len(record))
    with open("renamer_duplicate.txt", "a", encoding="utf-8") as dup_log, \
         open("rename_log.txt", "a", encoding="utf-8") as rename_log, \
         open("renamer_fail.txt", "a", encoding="utf-8") as fail_log, \
         open("renamer_dryrun.txt", "a", encoding="utf-8") as dryrun_log:
        for row in record:
            progress.update(progressbar_Index + 1)
            progressbar_Index += 1
            scene_ID = str(row[0])
            # Fixing letter (X:Folder -> X:\Folder)
            current_filename = str(row[1])
            current_directory = str(row[2])
            current_path = os.path.join(current_directory, current_filename)
            file_extension = os.path.splitext(current_filename)[1]
            scene_title = row[3] if row[3] is not None else ""
            scene_date = row[4] if row[4] is not None else ""
            scene_Studio_id = str(row[5]) if row[5] is not None else ""
            file_height = str(row[6]) if row[6] is not None else ""
            # By default, title contains extensions.
            scene_title = re.sub(re.escape(file_extension) + "$", "", scene_title)

            performer_name = db.get_Perf_fromSceneID(scene_ID) if "$performer" in query_filename else ""

            studio_name = ""
            if "$studio" in query_filename and scene_Studio_id:
                studio_name = db.get_Studio_fromID(scene_Studio_id)

            if file_height == "4320":
                file_height = "8k"
            else:
                if file_height == "2160":
                    file_height = "4k"
                elif file_height:
                    file_height = "{}p".format(file_height)

            scene_info = {
                "title": scene_title,
                "date": scene_date,
                "performer": performer_name,
                "studio": studio_name,
                "height": file_height,
            }
            logger.logPrint("[DEBUG] Scene information: {}".format(scene_info))
            # Create the new filename
            filename_stem = makeFilename(scene_info, query_filename)
            if not filename_stem or not filename_stem.strip(".") or not any(c.isalnum() for c in filename_stem):
                logger.logPrint("[Error] Information missing for new filename, ID: {}".format(scene_ID))
                continue
            new_filename = filename_stem + file_extension

            # Remove illegal character for Windows ('#' and ',' is not illegal you can remove it)
            new_filename = re.sub(r'[\\/:"*?<>|#,]+', "", new_filename)

            # Replace the old filename by the new in the filepath
            new_path = os.path.join(os.path.dirname(current_path), new_filename)

            if len(new_path) > 240:
                logger.logPrint("[Warn] The Path is too long ({})".format(new_path))
                # We only use the date and title to get a shorter file (eg: 2017-04-27 - Oni Chichi.mp4)
                if scene_info.get("date"):
                    reducePath = (
                        len(
                            current_directory
                            + scene_info["title"]
                            + scene_info["date"]
                            + file_extension
                        )
                        + 3
                    )
                else:
                    reducePath = (
                        len(current_directory + scene_info["title"] + file_extension) + 3
                    )
                if reducePath < 240:
                    if scene_info.get("date"):
                        new_filename = (
                            makeFilename(scene_info, "$date - $title") + file_extension
                        )
                    else:
                        new_filename = makeFilename(scene_info, "$title") + file_extension
                    new_filename = re.sub(r'[\\/:"*?<>|#,]+', "", new_filename)
                    reduced_stem = os.path.splitext(new_filename)[0]
                    if not reduced_stem or not reduced_stem.strip(".") or not any(c.isalnum() for c in reduced_stem):
                        logger.logPrint("[Error] Information missing for new filename, ID: {}".format(scene_ID))
                        continue
                    new_path = os.path.join(os.path.dirname(current_path), new_filename)
                    logger.logPrint("Reduced filename to: {}".format(new_filename))
                else:
                    logger.logPrint(
                        "[Error] Can't manage to reduce the path, ID: {}".format(scene_ID)
                    )
                    continue

            # Looking for duplicate filename in the same directory
            db.cursor.execute(
                "SELECT sf.scene_id FROM scenes_files AS sf"
                " LEFT JOIN files AS f ON sf.file_id = f.id"
                " LEFT JOIN folders AS fd ON f.parent_folder_id = fd.id"
                " WHERE f.basename = ? AND NOT sf.scene_id = ? AND fd.path = ?;",
                [new_filename, scene_ID, current_directory],
            )
            dupl_check = db.cursor.fetchall()
            if len(dupl_check) > 0:
                for dupl_row in dupl_check:
                    logger.logPrint("[Error] Same filename: [{}]".format(dupl_row[0]))
                    print(
                        "{}|{}|{}\n".format(scene_ID, current_path, new_filename),
                        file=dup_log,
                    )
                logger.logPrint("\n")
                continue

            logger.logPrint("[DEBUG] Filename: {} -> {}".format(current_filename, new_filename))
            logger.logPrint("[DEBUG] Path: {} -> {}".format(current_path, new_path))
            if new_path == current_path:
                logger.logPrint("[DEBUG] File already good.\n")
                continue
            else:
                #
                # THIS PART WILL EDIT YOUR DATABASE, FILES (be careful and know what you do)
                #
                # Windows Rename
                if not config.DRY_RUN:
                    if os.path.isfile(current_path):
                        if os.path.isfile(new_path):
                            logger.logPrint("[Error] Destination file already exists on disk: {}".format(new_path))
                            print(
                                "{}|{}|{}\n".format(scene_ID, current_path, new_filename),
                                file=dup_log,
                            )
                            continue
                        try:
                            os.rename(current_path, new_path)
                            if os.path.isfile(new_path):
                                logger.logPrint("[OS] File Renamed! ({})".format(current_filename))
                                if config.USING_LOG:
                                    print(
                                        "{}|{}|{}\n".format(scene_ID, current_path, new_path),
                                        file=rename_log,
                                    )
                            else:
                                logger.logPrint(
                                    "[OS] File failed to rename ? ({})".format(current_filename)
                                )
                                print(
                                    "{} -> {}\n".format(current_path, new_path),
                                    file=fail_log,
                                )
                        except OSError as e:
                            logger.logPrint("[OS] Rename failed ({} -> {}): {}".format(current_path, new_path, e))
                            print(
                                "{} -> {}\n".format(current_path, new_path),
                                file=fail_log,
                            )
                            continue
                    else:
                        logger.logPrint(
                            "[OS] File doesn't exist in your Disk/Drive ({})".format(current_path)
                        )
                else:
                    logger.logPrint("[DRY_RUN][OS] File should be renamed")
                    print(
                        "{} -> {}\n".format(current_path, new_path),
                        file=dryrun_log,
                    )
                logger.logPrint("\n")
            if config.STOP_AFTER_FIRST:
                break
        progress.finish()
    return


def edit_db(query_filename, optional_query="", params=()):
    """Compatibility wrapper that uses the validated plan pipeline.

    New callers should discover all tag and fallback operations together via
    :mod:`run_renamer`; this wrapper keeps the historical function callable
    without bypassing source, destination, or collision validation.
    """
    from planning import discover_operations
    from rename_plan import apply_plan, create_plan, render_plan, validate_plan

    plan = create_plan(discover_operations(query_filename, optional_query, params))
    issues = validate_plan(plan)
    with open("renamer_dryrun.txt", "a", encoding="utf-8") as dry_run_log:
        dry_run_log.write(render_plan(plan, issues))
    if config.DRY_RUN:
        return plan
    if issues:
        return plan
    apply_plan(plan)
    return plan
