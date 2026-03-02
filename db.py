import sqlite3
import sys

import config
import logger

_connection = None
cursor = None


def connect() -> None:
    """Open the SQLite connection and set the module-level ``cursor``.

    Logs a FATAL message and exits if the connection fails.
    """
    global _connection, cursor
    try:
        _connection = sqlite3.connect(config.DB_PATH)
        cursor = _connection.cursor()
        logger.logPrint("Python successfully connected to SQLite\n")
    except sqlite3.Error as error:
        logger.logPrint("FATAL SQLITE Error: {}".format(error))
        sys.exit(1)


def close() -> None:
    """Close the cursor and the database connection."""
    global _connection, cursor
    if cursor:
        cursor.close()
    if _connection:
        _connection.close()
    logger.logPrint("The SQLite connection is closed")


def gettingTagsID(name):
    """Return the tag ID for *name* as a string, or ``None`` if the tag is not found.

    Args:
        name (str): Exact tag name to look up in the ``tags`` table.

    Returns:
        str | None: Tag ID string, or ``None`` on no match or lookup error.
    """
    cursor.execute("SELECT id from tags WHERE name=?;", [name])
    result = cursor.fetchone()
    try:
        id = str(result[0])
        logger.logPrint("[Tag] [{}] {}".format(id, name))
    except (TypeError, IndexError) as e:
        id = None
        logger.logPrint("[Tag] Error when trying to get:{} ({})".format(name, e))
    return id


def get_SceneID_fromTags(id):
    """Return a comma-separated string of scene IDs that carry the given tag.

    Args:
        id (str): Tag ID to look up in ``scenes_tags``.

    Returns:
        str: Comma-separated scene IDs (e.g. ``"1,2,3"``), or ``""`` if none.
    """
    cursor.execute("SELECT scene_id from scenes_tags WHERE tag_id=?;", [id])
    record = cursor.fetchall()
    logger.logPrint("There is {} scene(s) with the tag_id {}".format(len(record), id))
    array_ID = []
    for row in record:
        array_ID.append(row[0])
    scene_id_list = ",".join(map(str, array_ID))
    return scene_id_list


def get_Perf_fromSceneID(id_scene):
    """Return a space-trimmed string of performer names for a scene.

    Returns ``""`` if the scene has more than 3 performers. When
    ``config.FEMALE_ONLY`` is ``True``, only performers whose gender is
    ``"FEMALE"`` are included. Orphaned performer IDs (no matching row in
    ``performers``) are silently skipped.

    Args:
        id_scene (str): Scene ID to query.

    Returns:
        str: Space-separated performer names, or ``""`` if none qualify.
    """
    perf_list = ""
    cursor.execute(
        "SELECT performer_id from performers_scenes WHERE scene_id=?;", [id_scene]
    )
    record = cursor.fetchall()
    if len(record) > 3:
        logger.logPrint("More than 3 performers.")
    else:
        perfcount = 0
        for row in record:
            perf_id = str(row[0])
            cursor.execute("SELECT name,gender from performers WHERE id=?;", [perf_id])
            perf = cursor.fetchall()
            if not perf:
                continue
            if config.FEMALE_ONLY:
                # Only take female gender
                if str(perf[0][1]) == "FEMALE":
                    perf_list += str(perf[0][0]) + " "
                    perfcount += 1
                else:
                    continue
            else:
                perf_list += str(perf[0][0]) + " "
                perfcount += 1
    perf_list = perf_list.strip()
    return perf_list


def get_Studio_fromID(id):
    """Return the studio name for *id*, or ``""`` if the studio is not found.

    Args:
        id (str | int): Studio ID to look up in the ``studios`` table.

    Returns:
        str: Studio name, or ``""`` on no match.
    """
    cursor.execute("SELECT name from studios WHERE id=?;", [id])
    record = cursor.fetchall()
    if not record:
        return ""
    studio_name = str(record[0][0])
    return studio_name
