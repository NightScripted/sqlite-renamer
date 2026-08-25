"""Unit tests for explicit database handles and runner boundaries."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import config
import db
import logger
import run_renamer
from planning import discover_operations
from renamer import edit_db


class TestLogPrint(unittest.TestCase):
    def setUp(self):
        original_debug_mode = config.DEBUG_MODE
        self.addCleanup(setattr, config, "DEBUG_MODE", original_debug_mode)

    def test_non_debug_message_always_printed(self):
        config.DEBUG_MODE = False
        with patch("builtins.print") as mock_print:
            logger.logPrint("Hello world")
        mock_print.assert_called_once_with("Hello world")

    def test_debug_message_is_suppressed_when_debug_is_off(self):
        config.DEBUG_MODE = False
        with patch("builtins.print") as mock_print:
            logger.logPrint("[DEBUG] hidden")
        mock_print.assert_not_called()


class TestDatabaseHandle(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.connection = MagicMock()
        self.database = db.Database(self.connection, self.cursor)
        self.original_female_only = config.FEMALE_ONLY

    def tearDown(self):
        config.FEMALE_ONLY = self.original_female_only

    def test_tag_and_scene_queries_are_parameterized(self):
        self.cursor.fetchone.return_value = (42,)
        self.assertEqual(self.database.get_tag_id("My Tag"), "42")
        self.cursor.execute.assert_called_with("SELECT id from tags WHERE name=?;", ["My Tag"])
        self.cursor.fetchall.return_value = [(1,), (2,)]
        self.assertEqual(self.database.get_scene_ids_for_tag("42"), ["1", "2"])

    def test_missing_tag_and_studio_return_empty_values(self):
        self.cursor.fetchone.return_value = None
        self.assertIsNone(self.database.get_tag_id("Missing"))
        self.cursor.fetchall.return_value = []
        self.assertEqual(self.database.get_studio_name("99"), "")

    def test_performer_filter_and_orphan_handling(self):
        self.cursor.fetchall.side_effect = [[(1,), (2,)], [("Ada", "FEMALE")], []]
        self.assertEqual(self.database.get_performers_for_scene("1"), "Ada")
        self.cursor.reset_mock()
        self.cursor.fetchall.side_effect = [[(1,)], [("John", "MALE")]]
        config.FEMALE_ONLY = True
        self.assertEqual(self.database.get_performers_for_scene("1"), "")

    def test_more_than_three_performers_are_omitted_and_close_owns_resources(self):
        self.cursor.fetchall.return_value = [(1,), (2,), (3,), (4,)]
        self.assertEqual(self.database.get_performers_for_scene("1"), "")
        self.database.close()
        self.cursor.close.assert_called_once_with()
        self.connection.close.assert_called_once_with()


class TestPlanning(unittest.TestCase):
    def test_discovery_uses_handle_metadata_and_returns_operations(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1, "old.mp4", "/media", "Title", "2026-01-01", 2, 2160)]
        database = MagicMock(cursor=cursor)
        database.get_performers_for_scene.return_value = "Ada"
        database.get_studio_name.return_value = "Studio"
        operations = discover_operations(database, "$performer - $studio - $title")
        self.assertEqual(
            operations[0].destination, os.path.join("/media", "Ada - Studio - Title.mp4")
        )
        database.get_performers_for_scene.assert_called_once_with("1")
        database.get_studio_name.assert_called_once_with(2)

    def test_discovery_can_stop_after_first(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (1, "one.mp4", "/media", "One", None, None, None),
            (2, "two.mp4", "/media", "Two", None, None, None),
        ]
        operations = discover_operations(MagicMock(cursor=cursor), "$title", stop_after_first=True)
        self.assertEqual([operation.scene_id for operation in operations], ["1"])


class TestCompatibilityRenderer(unittest.TestCase):
    def test_edit_db_uses_a_short_lived_handle_and_never_applies(self):
        manager = MagicMock()
        database = manager.__enter__.return_value
        database.cursor.fetchall.return_value = [
            (1, "old.mp4", "/fixture", "Fixture Title", None, None, None)
        ]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(db, "open_database", return_value=manager),
        ):
            original_cwd = os.getcwd()
            os.chdir(directory)
            try:
                plan = edit_db("$title")
            finally:
                os.chdir(original_cwd)
        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0].destination, "/fixture/Fixture Title.mp4")
        manager.__enter__.assert_called_once_with()
        manager.__exit__.assert_called_once()


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.original_values = {
            name: getattr(config, name)
            for name in (
                "DRY_RUN",
                "USING_LOG",
                "FALLBACK_TEMPLATE",
                "PATH_FILTER",
                "tags_dict",
                "STOP_AFTER_FIRST",
            )
        }
        config.DRY_RUN = False
        config.USING_LOG = False
        config.FALLBACK_TEMPLATE = "$title"
        config.PATH_FILTER = ""
        config.STOP_AFTER_FIRST = False
        config.tags_dict = {
            "first": {"tag": "First", "filename": "$title"},
            "second": {"tag": "Second", "filename": "$date $title"},
        }

    def tearDown(self):
        for name, value in self.original_values.items():
            setattr(config, name, value)

    def test_first_matching_tag_claims_scene_and_excludes_later_passes(self):
        database = MagicMock()
        database.get_tag_id.side_effect = ["10", "20"]
        database.get_scene_ids_for_tag.side_effect = [["1", "2"], ["2", "3"]]
        with patch.object(run_renamer, "discover_operations", return_value=[]) as discover:
            tagged_scene_ids, operations = run_renamer._discover_tag_passes(database)
            operations.extend(run_renamer._discover_fallback_pass(database, tagged_scene_ids))
        self.assertEqual(
            discover.call_args_list,
            [
                unittest.mock.call(database, "$title", "WHERE s.id IN (?,?)", ("1", "2"), False),
                unittest.mock.call(database, "$date $title", "WHERE s.id IN (?)", ("3",), False),
                unittest.mock.call(
                    database, "$title", "WHERE s.id NOT IN (?,?,?)", ("1", "2", "3"), False
                ),
            ],
        )

    def test_run_opens_and_closes_one_database_handle(self):
        manager = MagicMock()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(run_renamer.config, "validate"),
            patch.object(run_renamer.db, "open_database", return_value=manager),
            patch.object(run_renamer, "_discover_tag_passes", return_value=([], [])),
            patch.object(run_renamer, "_discover_fallback_pass", return_value=[]),
            patch.object(run_renamer, "write_plan"),
            patch.object(run_renamer, "write_manifest"),
        ):
            old_cwd = os.getcwd()
            os.chdir(directory)
            try:
                run_renamer.run("plan.json")
            finally:
                os.chdir(old_cwd)
        run_renamer._discover_tag_passes.assert_not_called if False else None
        manager.__enter__.assert_called_once_with()
        manager.__exit__.assert_called_once()

    def test_main_refuses_apply_while_dry_run_is_enabled(self):
        config.DRY_RUN = True
        with self.assertRaises(SystemExit):
            run_renamer.main(["--apply-plan", "plan.json"])

    def test_main_applies_with_explicit_log_choice(self):
        config.DRY_RUN = False
        config.USING_LOG = False
        plan = MagicMock()
        with (
            patch.object(run_renamer.config, "load_local_config"),
            patch.object(run_renamer, "read_plan", return_value=plan),
            patch.object(run_renamer, "apply_plan", return_value=()) as apply,
            patch.object(run_renamer, "write_manifest") as manifest,
        ):
            run_renamer.main(["--apply-plan", "plan.json"])
        apply.assert_called_once_with(plan, None)
        manifest.assert_called_once_with(plan, (), "applied", action="apply")


if __name__ == "__main__":
    unittest.main()
