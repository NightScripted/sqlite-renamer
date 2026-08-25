"""Tests for private configuration loading and clear validation failures."""

import os
import tempfile
import unittest

import config


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.original_db_path = config.DB_PATH
        self.original_tags = config.tags_dict

    def tearDown(self):
        config.DB_PATH = self.original_db_path
        config.tags_dict = self.original_tags

    def test_missing_database_path_fails_clearly(self):
        config.DB_PATH = ""
        with self.assertRaisesRegex(ValueError, "DB_PATH is required"):
            config.validate()

    def test_explicit_config_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stash.sqlite")
            with open(database_path, "w", encoding="utf-8") as database_file:
                database_file.write("")
            config_path = os.path.join(directory, "local.py")
            with open(config_path, "w", encoding="utf-8") as local_file:
                local_file.write("DB_PATH = {!r}\ntags_dict = {{}}\n".format(database_path))
            config.load_local_config(config_path)
            self.assertEqual(config.DB_PATH, database_path)
            config.validate()

    def test_invalid_tag_rule_fails_before_database_access(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "stash.sqlite")
            with open(database_path, "w", encoding="utf-8") as database_file:
                database_file.write("")
            config.DB_PATH = database_path
            config.tags_dict = {"invalid": {"tag": "Configured tag", "filename": ""}}
            with self.assertRaisesRegex(ValueError, "requires a non-empty 'filename' value"):
                config.validate()


if __name__ == "__main__":
    unittest.main()
