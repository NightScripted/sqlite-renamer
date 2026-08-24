"""
Tests for makeFilename() in renamer.py.
"""

import unittest

from renamer import makeFilename

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

    def test_missing_middle_variable_collapses_repeated_separators(self):
        info = {**FULL_INFO, "performer": None}
        result = makeFilename(info, "$date - $performer - $title")
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

    def test_no_variable_tokens(self):
        result = makeFilename(FULL_INFO, "hardcoded_name")
        self.assertEqual(result, "hardcoded_name")

    def test_empty_string_title_treated_as_missing(self):
        info = {**FULL_INFO, "title": ""}
        result = makeFilename(info, "$date $title")
        self.assertEqual(result, "2016-12-29")

    def test_string_none_value_passes_through(self):
        # makeFilename does not filter the string "None"; that is edit_db's responsibility
        info = {**FULL_INFO, "title": "None"}
        result = makeFilename(info, "$title")
        self.assertEqual(result, "None")

    def test_variable_token_in_field_value_not_expanded(self):
        # $performer inside a field value is not re-expanded; makeFilename is not recursive
        info = {**FULL_INFO, "title": "The $performer Show"}
        result = makeFilename(info, "$title")
        self.assertEqual(result, "The $performer Show")


if __name__ == "__main__":
    unittest.main()
