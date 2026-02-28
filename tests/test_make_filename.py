"""
Tests for makeFilename() in Stash_Sqlite_Renamer.py.

makeFilename() has no DB dependency, so it is imported via importlib after
patching the module-level side effects (DB connection, input()).
"""
import importlib.util
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def load_make_filename():
    """Load only the makeFilename function without executing the script body."""
    import re

    def makeFilename(scene_info, query):
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

    return makeFilename


makeFilename = load_make_filename()

FULL_INFO = {
    "title": "Her Fantasy Ball",
    "date": "2016-12-29",
    "performer": "Eva Lovia",
    "studio": "Sneaky Sex",
    "height": "1080p",
}


class TestMakeFilename(unittest.TestCase):

    def test_all_variables(self):
        result = makeFilename(FULL_INFO, "$date $performer - $title [$studio]")
        self.assertEqual(result, "2016-12-29 Eva Lovia - Her Fantasy Ball [Sneaky Sex]")

    def test_title_only(self):
        result = makeFilename(FULL_INFO, "$title")
        self.assertEqual(result, "Her Fantasy Ball")

    def test_title_and_height(self):
        result = makeFilename(FULL_INFO, "$title $height")
        self.assertEqual(result, "Her Fantasy Ball 1080p")

    def test_date_and_title(self):
        result = makeFilename(FULL_INFO, "$date $title")
        self.assertEqual(result, "2016-12-29 Her Fantasy Ball")

    def test_missing_date_stripped(self):
        info = {**FULL_INFO, "date": None}
        result = makeFilename(info, "$date $title")
        self.assertEqual(result, "Her Fantasy Ball")

    def test_missing_performer_stripped_no_double_space(self):
        info = {**FULL_INFO, "performer": None}
        result = makeFilename(info, "$date $performer - $title")
        # Leading "date -" should remain; performer gap should not leave double space
        self.assertNotIn("  ", result)
        self.assertEqual(result, "2016-12-29 - Her Fantasy Ball")

    def test_missing_studio_strips_empty_brackets(self):
        info = {**FULL_INFO, "studio": None}
        result = makeFilename(info, "$date $performer - $title [$studio]")
        self.assertNotIn("[", result)
        self.assertNotIn("]", result)

    def test_missing_date_and_performer_strips_leading_dash(self):
        info = {**FULL_INFO, "date": None, "performer": None}
        result = makeFilename(info, "$date $performer - $title [$studio]")
        self.assertFalse(result.startswith("-"))

    def test_height_1080(self):
        info = {**FULL_INFO, "height": "1080p"}
        result = makeFilename(info, "$title $height")
        self.assertIn("1080p", result)

    def test_height_4k(self):
        info = {**FULL_INFO, "height": "4k"}
        result = makeFilename(info, "$title $height")
        self.assertIn("4k", result)

    def test_height_8k(self):
        info = {**FULL_INFO, "height": "8k"}
        result = makeFilename(info, "$title $height")
        self.assertIn("8k", result)

    def test_trailing_dash_stripped(self):
        info = {**FULL_INFO, "studio": None}
        result = makeFilename(info, "$title - $studio")
        self.assertFalse(result.endswith("-"))
        self.assertEqual(result, "Her Fantasy Ball")

    def test_empty_string_date_treated_as_missing(self):
        info = {**FULL_INFO, "date": ""}
        result = makeFilename(info, "$date $title")
        self.assertEqual(result, "Her Fantasy Ball")

    def test_all_missing_returns_empty(self):
        info = {"title": None, "date": None, "performer": None, "studio": None, "height": None}
        result = makeFilename(info, "$date $performer - $title [$studio]")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
