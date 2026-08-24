"""Privacy-safe SQLite and temporary-filesystem integration coverage."""
import os
import sqlite3
import tempfile
import unittest

import config
import db
import run_renamer
from rename_plan import read_plan


class TestPlanIntegration(unittest.TestCase):
    """Exercise the supported scene/file join through plan and apply commands."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.original_values = {
            name: getattr(config, name)
            for name in ("DB_PATH", "DRY_RUN", "USING_LOG", "PATH_FILTER", "FALLBACK_TEMPLATE", "tags_dict")
        }
        self.original_cursor = db.cursor
        self.original_connection = db._connection
        self.media_directory = os.path.join(self.tempdir.name, "media")
        os.mkdir(self.media_directory)
        self.database_path = os.path.join(self.tempdir.name, "stash.sqlite")
        self._create_fixture()
        config.DB_PATH = self.database_path
        config.DRY_RUN = True
        config.USING_LOG = False
        config.PATH_FILTER = ""
        config.FALLBACK_TEMPLATE = "$title"
        config.tags_dict = {}

    def tearDown(self):
        db.cursor = self.original_cursor
        db._connection = self.original_connection
        for name, value in self.original_values.items():
            setattr(config, name, value)
        os.chdir(self.original_cwd)
        self.tempdir.cleanup()

    def _create_fixture(self):
        connection = sqlite3.connect(self.database_path)
        connection.executescript(
            """
            CREATE TABLE scenes (id INTEGER PRIMARY KEY, title TEXT, date TEXT, studio_id INTEGER);
            CREATE TABLE folders (id INTEGER PRIMARY KEY, path TEXT);
            CREATE TABLE files (id INTEGER PRIMARY KEY, basename TEXT, parent_folder_id INTEGER);
            CREATE TABLE scenes_files (scene_id INTEGER, file_id INTEGER);
            CREATE TABLE video_files (file_id INTEGER, height INTEGER);
            """
        )
        connection.execute("INSERT INTO scenes VALUES (1, 'Fixture Title', '2026-01-01', NULL)")
        connection.execute("INSERT INTO folders VALUES (1, ?)", (self.media_directory,))
        for file_id, basename, height in ((1, "one.mp4", 1080), (2, "two.mkv", 2160)):
            connection.execute("INSERT INTO files VALUES (?, ?, 1)", (file_id, basename))
            connection.execute("INSERT INTO scenes_files VALUES (1, ?)", (file_id,))
            connection.execute("INSERT INTO video_files VALUES (?, ?)", (file_id, height))
            with open(os.path.join(self.media_directory, basename), "w", encoding="utf-8") as media_file:
                media_file.write("fixture")
        connection.commit()
        connection.close()

    def test_multi_file_scene_uses_one_safe_plan_for_preview_and_apply(self):
        run_renamer.run()
        self.assertTrue(os.path.exists("renamer_plan.json"))
        plan = read_plan("renamer_plan.json")
        self.assertEqual(len(plan.operations), 2)
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "one.mp4")))
        self.assertIn("READY", open("renamer_dryrun.txt", encoding="utf-8").read())

        config.DRY_RUN = False
        run_renamer.main(["--apply-plan", "renamer_plan.json"])
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "Fixture Title.mp4")))
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "Fixture Title.mkv")))


if __name__ == "__main__":
    unittest.main()
