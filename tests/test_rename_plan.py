"""Safety tests for persisted rename plans and Windows normalization."""
import os
import tempfile
import unittest

from rename_plan import (
    RenameOperation,
    apply_plan,
    create_plan,
    read_plan,
    sanitize_filename,
    validate_plan,
    write_plan,
)


class TestFilenameSanitization(unittest.TestCase):

    def test_strips_control_characters_and_trailing_dot_space(self):
        self.assertEqual(sanitize_filename("Title\x00 .mp4. "), "Title .mp4")

    def test_rejects_reserved_windows_names_with_extensions(self):
        for name in ("CON.mp4", "nul", "COM1.txt", "LPT9 "):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    sanitize_filename(name)


class TestRenamePlan(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.tempdir.name, "old.mp4")
        self.destination = os.path.join(self.tempdir.name, "new.mp4")
        with open(self.source, "w", encoding="utf-8") as source_file:
            source_file.write("test")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_missing_source_and_occupied_destination_block_a_plan(self):
        with open(self.destination, "w", encoding="utf-8") as destination_file:
            destination_file.write("occupied")
        plan = create_plan((RenameOperation("1", self.source, self.destination), RenameOperation("2", "missing.mp4", "other.mp4")))
        codes = {issue.code for issue in validate_plan(plan)}
        self.assertEqual(codes, {"occupied_destination", "missing_source"})

    def test_normalized_duplicate_destinations_block_a_plan(self):
        other_source = os.path.join(self.tempdir.name, "other.mp4")
        with open(other_source, "w", encoding="utf-8") as other_file:
            other_file.write("test")
        plan = create_plan((
            RenameOperation("1", self.source, self.destination),
            RenameOperation("2", other_source, os.path.join(self.tempdir.name, "NEW.mp4")),
        ))
        self.assertIn("duplicate_destination", {issue.code for issue in validate_plan(plan)})

    def test_write_read_and_apply_require_an_unchanged_valid_plan(self):
        plan = create_plan((RenameOperation("1", self.source, self.destination),))
        plan_path = os.path.join(self.tempdir.name, "plan.json")
        write_plan(plan, plan_path)
        loaded = read_plan(plan_path)
        self.assertEqual(loaded.digest, plan.digest)
        self.assertEqual(apply_plan(loaded), ())
        self.assertTrue(os.path.exists(self.destination))

    def test_destination_outside_source_directory_is_blocked(self):
        plan = create_plan((RenameOperation("1", self.source, os.path.join(self.tempdir.name, "..", "outside.mp4")),))
        self.assertIn("outside_source_directory", {issue.code for issue in validate_plan(plan)})


if __name__ == "__main__":
    unittest.main()
