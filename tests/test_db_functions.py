"""
Tests for all DB-dependent functions and edit_db in Stash_Sqlite_Renamer.py.

The module is loaded once via importlib with a mocked SQLite connection and
mocked progressbar so no real database or installed package is required.
Per-test cursor behaviour is controlled through the shared mock_cursor fixture.
"""
import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Module bootstrap — load once, share across all test classes
# ---------------------------------------------------------------------------

def _load_module():
    """Load Stash_Sqlite_Renamer.py with all side-effects neutralised."""
    script_path = pathlib.Path(__file__).parent.parent / "Stash_Sqlite_Renamer.py"

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None

    with patch("sqlite3.connect", return_value=mock_conn), \
         patch("builtins.input", return_value=""), \
         patch.dict(sys.modules, {"progressbar": MagicMock()}):
        spec = importlib.util.spec_from_file_location("_renamer_db_test", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    return mod, mock_cursor


_mod, _cursor = _load_module()


# ---------------------------------------------------------------------------
# logPrint
# ---------------------------------------------------------------------------

class TestLogPrint(unittest.TestCase):

    def setUp(self):
        _mod.DEBUG_MODE = True

    def tearDown(self):
        _mod.DEBUG_MODE = True

    def test_non_debug_message_always_printed(self):
        _mod.DEBUG_MODE = False
        with patch("builtins.print") as mock_print:
            _mod.logPrint("Hello world")
            mock_print.assert_called_once_with("Hello world")

    def test_debug_message_suppressed_when_debug_off(self):
        _mod.DEBUG_MODE = False
        with patch("builtins.print") as mock_print:
            _mod.logPrint("[DEBUG] verbose info")
            mock_print.assert_not_called()

    def test_debug_message_printed_when_debug_on(self):
        _mod.DEBUG_MODE = True
        with patch("builtins.print") as mock_print:
            _mod.logPrint("[DEBUG] verbose info")
            mock_print.assert_called_once_with("[DEBUG] verbose info")


# ---------------------------------------------------------------------------
# gettingTagsID
# ---------------------------------------------------------------------------

class TestGettingTagsID(unittest.TestCase):

    def setUp(self):
        _cursor.reset_mock()

    def test_tag_found_returns_string_id(self):
        _cursor.fetchone.return_value = (42,)
        result = _mod.gettingTagsID("My Tag")
        self.assertEqual(result, "42")

    def test_tag_not_found_returns_none(self):
        _cursor.fetchone.return_value = None
        result = _mod.gettingTagsID("Missing Tag")
        self.assertIsNone(result)

    def test_executes_correct_query(self):
        _cursor.fetchone.return_value = (1,)
        _mod.gettingTagsID("Test Tag")
        _cursor.execute.assert_called_with(
            "SELECT id from tags WHERE name=?;", ["Test Tag"]
        )


# ---------------------------------------------------------------------------
# get_SceneID_fromTags
# ---------------------------------------------------------------------------

class TestGetSceneIDFromTags(unittest.TestCase):

    def setUp(self):
        _cursor.reset_mock()

    def test_no_scenes_returns_empty_string(self):
        _cursor.fetchall.return_value = []
        result = _mod.get_SceneID_fromTags("1")
        self.assertEqual(result, "")

    def test_single_scene_returns_id(self):
        _cursor.fetchall.return_value = [(101,)]
        result = _mod.get_SceneID_fromTags("1")
        self.assertEqual(result, "101")

    def test_multiple_scenes_returns_csv(self):
        _cursor.fetchall.return_value = [(1,), (2,), (3,)]
        result = _mod.get_SceneID_fromTags("5")
        self.assertEqual(result, "1,2,3")


# ---------------------------------------------------------------------------
# get_Perf_fromSceneID
# ---------------------------------------------------------------------------

class TestGetPerfFromSceneID(unittest.TestCase):

    def setUp(self):
        _cursor.reset_mock()
        _mod.FEMALE_ONLY = False

    def tearDown(self):
        _mod.FEMALE_ONLY = False
        _cursor.fetchall.side_effect = None

    def test_no_performers_returns_empty(self):
        _cursor.fetchall.return_value = []
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "")

    def test_more_than_three_performers_returns_empty(self):
        _cursor.fetchall.return_value = [(1,), (2,), (3,), (4,)]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "")

    def test_single_performer_returned(self):
        _cursor.fetchall.side_effect = [
            [(10,)],                        # performers_scenes query
            [("Eva Lovia", "FEMALE")],      # performers query
        ]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "Eva Lovia")

    def test_two_performers_concatenated(self):
        _cursor.fetchall.side_effect = [
            [(10,), (11,)],
            [("Eva Lovia", "FEMALE")],
            [("Mia Malkova", "FEMALE")],
        ]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertIn("Eva Lovia", result)
        self.assertIn("Mia Malkova", result)

    def test_female_only_includes_female(self):
        _mod.FEMALE_ONLY = True
        _cursor.fetchall.side_effect = [
            [(10,)],
            [("Eva Lovia", "FEMALE")],
        ]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "Eva Lovia")

    def test_female_only_excludes_male(self):
        _mod.FEMALE_ONLY = True
        _cursor.fetchall.side_effect = [
            [(10,)],
            [("John Doe", "MALE")],
        ]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "")

    def test_orphaned_performer_id_skipped(self):
        _cursor.fetchall.side_effect = [
            [(99,)],   # performers_scenes — returns a row
            [],        # performers — no matching record
        ]
        result = _mod.get_Perf_fromSceneID("1")
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# get_Studio_fromID
# ---------------------------------------------------------------------------

class TestGetStudioFromID(unittest.TestCase):

    def setUp(self):
        _cursor.reset_mock()

    def test_studio_found_returns_name(self):
        _cursor.fetchall.return_value = [("Sneaky Sex",)]
        result = _mod.get_Studio_fromID("5")
        self.assertEqual(result, "Sneaky Sex")

    def test_studio_not_found_returns_empty(self):
        _cursor.fetchall.return_value = []
        result = _mod.get_Studio_fromID("999")
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# edit_db
# ---------------------------------------------------------------------------

def _scene_row(scene_id="1", basename="old.mp4", directory="/mock_dir",
               title="My Title", date="2020-01-01", studio_id=None, height="1080"):
    """Return a fake scene row tuple matching the edit_db SELECT columns."""
    return (scene_id, basename, directory, title, date, studio_id, height)


class TestEditDb(unittest.TestCase):

    def setUp(self):
        _cursor.reset_mock()
        _mod.DRY_RUN = True
        _mod.USING_LOG = False
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)

    def tearDown(self):
        _cursor.fetchall.side_effect = None
        _mod.DRY_RUN = True
        _mod.USING_LOG = False
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def test_no_scenes_returns_early_without_error(self):
        _cursor.fetchall.return_value = []
        _mod.edit_db("$title")   # should not raise

    def test_dry_run_writes_proposed_rename(self):
        _mod.DRY_RUN = True
        _cursor.fetchall.side_effect = [
            [_scene_row()],   # main scene query
            [],               # get_Perf_fromSceneID → performers_scenes
            [],               # duplicate check
        ]
        _mod.edit_db("$title")
        self.assertTrue(os.path.exists("renamer_dryrun.txt"))
        with open("renamer_dryrun.txt", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("old.mp4", content)
        self.assertIn("My Title.mp4", content)

    def test_already_correct_name_skipped(self):
        # When current_filename already matches the template output, no rename.
        _cursor.fetchall.side_effect = [
            [_scene_row(basename="My Title.mp4", title="My Title")],
            [],   # performers
            [],   # duplicate check
        ]
        _mod.edit_db("$title")
        # dryrun_log should be empty (nothing to rename)
        if os.path.exists("renamer_dryrun.txt"):
            with open("renamer_dryrun.txt", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content.strip(), "")

    def test_duplicate_detected_writes_duplicate_log(self):
        _cursor.fetchall.side_effect = [
            [_scene_row()],          # main scene query
            [("99",)],               # duplicate check → collision found
        ]
        _mod.edit_db("$title")
        self.assertTrue(os.path.exists("renamer_duplicate.txt"))
        with open("renamer_duplicate.txt", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("old.mp4", content)

    def test_live_rename_calls_os_rename(self):
        _mod.DRY_RUN = False
        _mod.USING_LOG = True
        _cursor.fetchall.side_effect = [
            [_scene_row()],   # main scene query
            [],               # performers
            [],               # duplicate check
        ]
        # isfile: current_path exists, new_path free, new_path exists after rename
        with patch("os.path.isfile", side_effect=[True, False, True]), \
             patch("os.rename") as mock_rename:
            _mod.edit_db("$title")
            mock_rename.assert_called_once()
        self.assertTrue(os.path.exists("rename_log.txt"))

    def test_os_rename_failure_writes_fail_log_and_continues(self):
        _mod.DRY_RUN = False
        _cursor.fetchall.side_effect = [
            [_scene_row()],   # main scene query
            [],               # performers
            [],               # duplicate check
        ]
        with patch("os.path.isfile", side_effect=[True, False]), \
             patch("os.rename", side_effect=OSError("Permission denied")):
            _mod.edit_db("$title")   # must not raise
        self.assertTrue(os.path.exists("renamer_fail.txt"))
        with open("renamer_fail.txt", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("old.mp4", content)

    def test_all_fields_empty_skips_scene(self):
        # All metadata None → makeFilename returns "" → stem validation rejects it.
        # No performer queries or duplicate-check DB calls should occur.
        _cursor.fetchall.side_effect = [
            [_scene_row(title=None, date=None, height=None)],
        ]
        _mod.edit_db("$title")
        # Only one fetchall call: the main scene query.
        # The performer and duplicate-check queries must NOT have run.
        self.assertEqual(_cursor.fetchall.call_count, 1)


if __name__ == "__main__":
    unittest.main()
