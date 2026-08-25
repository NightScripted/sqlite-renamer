"""Database-backed discovery of immutable rename operations."""

from __future__ import annotations

import os
import re

from db import Database
from rename_plan import RenameOperation, sanitize_filename
from renamer import makeFilename


SCENE_QUERY = """
SELECT s.id,f.basename,d.path,s.title,s.date,s.studio_id,vf.height
FROM scenes AS s
LEFT JOIN scenes_files AS sf ON s.id = sf.scene_id
LEFT JOIN files AS f ON sf.file_id = f.id
LEFT JOIN folders AS d ON f.parent_folder_id = d.id
LEFT JOIN video_files AS vf ON f.id = vf.file_id
"""


def _height_label(height: object) -> str:
    """Normalize a raw video height to the filename-template label."""
    value = "" if height is None else str(height)
    return {"2160": "4k", "4320": "8k"}.get(value, "{}p".format(value) if value else "")


def discover_operations(
    database: Database,
    template: str,
    optional_query: str = "",
    params: tuple = (),
    stop_after_first: bool = False,
) -> list[RenameOperation]:
    """Query *database* and return candidates without touching the filesystem."""
    database.cursor.execute(f"{SCENE_QUERY} {optional_query};", params)
    operations: list[RenameOperation] = []
    for row in database.cursor.fetchall():
        scene_id, basename, directory, title, date, studio_id, height = row
        source = os.path.join(str(directory), str(basename))
        extension = os.path.splitext(str(basename))[1]
        scene_info = {
            "title": re.sub(re.escape(extension) + "$", "", title or ""),
            "date": date or "",
            "performer": database.get_performers_for_scene(str(scene_id))
            if "$performer" in template
            else "",
            "studio": database.get_studio_name(studio_id)
            if "$studio" in template and studio_id is not None
            else "",
            "height": _height_label(height),
        }
        stem = makeFilename(scene_info, template)
        if not stem or not stem.strip(".") or not any(char.isalnum() for char in stem):
            operation = RenameOperation(
                str(scene_id), source, source, "filename template produced no usable name"
            )
        else:
            try:
                filename = sanitize_filename(stem + extension)
                operation = RenameOperation(
                    str(scene_id), source, os.path.join(str(directory), filename)
                )
            except ValueError as error:
                operation = RenameOperation(str(scene_id), source, source, str(error))
        operations.append(operation)
        if stop_after_first:
            break
    return operations
