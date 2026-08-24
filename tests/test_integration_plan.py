"""Mocked database and temporary-filesystem integration coverage."""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import config
import db
import run_renamer
from rename_plan import read_plan


class TestPlanIntegration(unittest.TestCase):
    """Exercise multi-file planning and application without a writable database."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.original_values = {
            name: getattr(config, name)
            for name in ("DB_PATH", "DRY_RUN", "USING_LOG", "PATH_FILTER", "FALLBACK_TEMPLATE", "tags_dict")
        }
        self.media_directory = os.path.join(self.tempdir.name, "media")
        os.mkdir(self.media_directory)
        config.DB_PATH = __file__
        config.DRY_RUN = True
        config.USING_LOG = False
        config.PATH_FILTER = ""
        config.FALLBACK_TEMPLATE = "$title"
        config.tags_dict = {}
        self.cursor = MagicMock()
        self.cursor.fetchall.return_value = [
            (1, "one.mp4", self.media_directory, "Fixture Title", "2026-01-01", None, 1080),
            (1, "two.mkv", self.media_directory, "Fixture Title", "2026-01-01", None, 2160),
        ]
        self.database_patches = [
            patch.object(db, "connect"),
            patch.object(db, "close"),
            patch.object(db, "cursor", self.cursor),
        ]
        for database_patch in self.database_patches:
            database_patch.start()
        for basename in ("one.mp4", "two.mkv"):
            with open(os.path.join(self.media_directory, basename), "w", encoding="utf-8") as media_file:
                media_file.write("fixture")

    def tearDown(self):
        for database_patch in reversed(self.database_patches):
            database_patch.stop()
        for name, value in self.original_values.items():
            setattr(config, name, value)
        os.chdir(self.original_cwd)
        self.tempdir.cleanup()

    def test_multi_file_scene_uses_one_safe_plan_for_preview_and_apply(self):
        run_renamer.run()
        self.assertTrue(os.path.exists("renamer_plan.json"))
        plan = read_plan("renamer_plan.json")
        self.assertEqual(len(plan.operations), 2)
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "one.mp4")))
        self.assertIn("READY", open("renamer_dryrun.txt", encoding="utf-8").read())
        self.assertFalse(os.path.exists("renamer_runs"))

        config.DRY_RUN = False
        run_renamer.main(["--apply-plan", "renamer_plan.json"])
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "Fixture Title.mp4")))
        self.assertTrue(os.path.exists(os.path.join(self.media_directory, "Fixture Title.mkv")))
        self.assertEqual(len(os.listdir("renamer_runs")), 1)


if __name__ == "__main__":
    unittest.main()
