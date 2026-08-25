"""Safety tests for persisted rename plans and Windows normalization."""

import os
import tempfile
import unittest
from unittest.mock import patch

from rename_plan import (
    PlanIssue,
    RenameOperation,
    apply_plan,
    create_plan,
    read_plan,
    render_plan,
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
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.source = os.path.join(self.tempdir.name, "old.mp4")
        self.destination = os.path.join(self.tempdir.name, "new.mp4")
        with open(self.source, "w", encoding="utf-8") as source_file:
            source_file.write("test")

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tempdir.cleanup()

    def test_missing_source_and_occupied_destination_block_a_plan(self):
        with open(self.destination, "w", encoding="utf-8") as destination_file:
            destination_file.write("occupied")
        plan = create_plan(
            (
                RenameOperation("1", self.source, self.destination),
                RenameOperation("2", "missing.mp4", "other.mp4"),
            )
        )
        codes = {issue.code for issue in validate_plan(plan)}
        self.assertEqual(codes, {"occupied_destination", "missing_source"})

    def test_normalized_duplicate_destinations_block_a_plan(self):
        other_source = os.path.join(self.tempdir.name, "other.mp4")
        with open(other_source, "w", encoding="utf-8") as other_file:
            other_file.write("test")
        plan = create_plan(
            (
                RenameOperation("1", self.source, self.destination),
                RenameOperation("2", other_source, os.path.join(self.tempdir.name, "NEW.mp4")),
            )
        )
        self.assertIn("duplicate_destination", {issue.code for issue in validate_plan(plan)})

    def test_write_read_and_apply_require_an_unchanged_valid_plan(self):
        plan = create_plan((RenameOperation("1", self.source, self.destination),))
        plan_path = os.path.join(self.tempdir.name, "plan.json")
        write_plan(plan, plan_path)
        loaded = read_plan(plan_path)
        self.assertEqual(loaded.digest, plan.digest)
        self.assertEqual(apply_plan(loaded), ())
        self.assertTrue(os.path.exists(self.destination))
        with open("rename_log.txt", encoding="utf-8") as rename_log:
            self.assertIn("1|", rename_log.read())

    def test_apply_rolls_back_completed_operations_after_a_failure(self):
        second_source = os.path.join(self.tempdir.name, "second-old.mp4")
        second_destination = os.path.join(self.tempdir.name, "second-new.mp4")
        with open(second_source, "w", encoding="utf-8") as second_file:
            second_file.write("test")
        plan = create_plan(
            (
                RenameOperation("1", self.source, self.destination),
                RenameOperation("2", second_source, second_destination),
            )
        )
        real_link = os.link
        calls = 0

        def fail_second_claim(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated failure")
            return real_link(source, destination)

        with patch("rename_plan.os.link", side_effect=fail_second_claim):
            issues = apply_plan(plan)
        self.assertEqual(issues[0].code, "apply_failed")
        self.assertTrue(os.path.exists(self.source))
        self.assertFalse(os.path.exists(self.destination))

    def test_destination_outside_source_directory_is_blocked(self):
        plan = create_plan(
            (
                RenameOperation(
                    "1", self.source, os.path.join(self.tempdir.name, "..", "outside.mp4")
                ),
            )
        )
        self.assertIn("outside_source_directory", {issue.code for issue in validate_plan(plan)})

    def test_preview_groups_blockers_and_counts_operation_states(self):
        plan = create_plan(
            (
                RenameOperation("1", "ready.mp4", "renamed.mp4"),
                RenameOperation("2", "same.mp4", "same.mp4"),
                RenameOperation("3", "missing.mp4", "blocked.mp4"),
            )
        )
        issue = PlanIssue(
            "3", "missing.mp4", "blocked.mp4", "missing_source", "source file does not exist"
        )
        preview = render_plan(plan, (issue,))
        self.assertIn("RENAME PLAN PREVIEW", preview)
        self.assertIn("Summary: 1 ready, 1 no-op, 1 blocked (1 issue(s))", preview)
        self.assertIn("CONFLICTS AND BLOCKERS", preview)
        self.assertIn("missing_source (1)", preview)
        self.assertIn("  - missing_source: source file does not exist", preview)


if __name__ == "__main__":
    unittest.main()
