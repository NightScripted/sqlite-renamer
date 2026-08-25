"""Read-only SQLite access behind an explicit, short-lived handle."""

from __future__ import annotations

import pathlib
import sqlite3
import sys
from typing import Self

import config
import logger


class Database:
    """Own a read-only Stash SQLite connection and its query helpers."""

    def __init__(self, connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
        """Store an open read-only SQLite connection and its cursor."""
        self._connection = connection
        self.cursor = cursor

    @classmethod
    def open(cls, database_path: str | None = None) -> Self:
        """Open *database_path* read-only, logging and exiting on SQLite errors."""
        try:
            path = pathlib.Path(database_path or config.DB_PATH).resolve()
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            logger.logPrint("Python successfully connected to SQLite\n")
            return cls(connection, connection.cursor())
        except sqlite3.Error as error:
            logger.logPrint("FATAL SQLITE Error: {}".format(error))
            sys.exit(1)

    def close(self) -> None:
        """Close database resources owned by this handle."""
        self.cursor.close()
        self._connection.close()
        logger.logPrint("The SQLite connection is closed")

    def __enter__(self) -> Self:
        """Return this handle for use in a context manager."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Close the handle when its context manager exits."""
        self.close()

    def get_tag_id(self, name: str) -> str | None:
        """Return the exact tag ID for *name*, or ``None`` when absent."""
        self.cursor.execute("SELECT id from tags WHERE name=?;", [name])
        result = self.cursor.fetchone()
        try:
            tag_id = str(result[0])
            logger.logPrint("[Tag] [{}] {}".format(tag_id, name))
        except (TypeError, IndexError) as error:
            tag_id = None
            logger.logPrint("[Tag] Error when trying to get:{} ({})".format(name, error))
        return tag_id

    def get_scene_ids_for_tag(self, tag_id: str) -> list[str]:
        """Return the scene IDs carrying *tag_id* in database order."""
        self.cursor.execute("SELECT scene_id from scenes_tags WHERE tag_id=?;", [tag_id])
        records = self.cursor.fetchall()
        logger.logPrint("There is {} scene(s) with the tag_id {}".format(len(records), tag_id))
        return [str(row[0]) for row in records]

    def get_performers_for_scene(self, scene_id: str) -> str:
        """Return qualifying performer names for a scene, or ``""`` when omitted."""
        self.cursor.execute(
            "SELECT performer_id from performers_scenes WHERE scene_id=?;", [scene_id]
        )
        records = self.cursor.fetchall()
        if len(records) > 3:
            logger.logPrint("More than 3 performers.")
            return ""
        performers = []
        for row in records:
            self.cursor.execute("SELECT name,gender from performers WHERE id=?;", [str(row[0])])
            performer = self.cursor.fetchall()
            if not performer:
                continue
            name, gender = performer[0]
            if config.FEMALE_ONLY and str(gender) != "FEMALE":
                continue
            performers.append(str(name))
        return " ".join(performers)

    def get_studio_name(self, studio_id: str | int) -> str:
        """Return the studio name for *studio_id*, or ``""`` when absent."""
        self.cursor.execute("SELECT name from studios WHERE id=?;", [studio_id])
        record = self.cursor.fetchall()
        return str(record[0][0]) if record else ""


def open_database(database_path: str | None = None) -> Database:
    """Open a read-only database handle for one planning operation."""
    return Database.open(database_path)
