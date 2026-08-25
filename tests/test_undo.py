"""Regression tests for hash-preconditioned manifest undo."""

import os
import tempfile
import unittest

from execution import apply_plan
from rename_plan import RenameOperation, create_plan
from run_manifest import write_manifest
from undo import undo_manifest


class TestManifestUndo(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.tempdir.name, "old.mp4")
        self.destination = os.path.join(self.tempdir.name, "new.mp4")
        with open(self.source, "wb") as source_file:
            source_file.write(b"original bytes")
        self.plan = create_plan((RenameOperation("1", self.source, self.destination),))
        self.manifest_directory = os.path.join(self.tempdir.name, "runs")

    def tearDown(self):
        self.tempdir.cleanup()

    def _apply_and_record(self):
        self.assertEqual(apply_plan(self.plan), ())
        return write_manifest(self.plan, (), "applied", self.manifest_directory, action="apply")

    def test_round_trip_restores_the_original_path_and_creates_reverse_plan(self):
        manifest_path = self._apply_and_record()
        manifest, undo_plan, issues = undo_manifest(str(manifest_path))
        self.assertEqual(issues, ())
        self.assertEqual(manifest.state, "applied")
        self.assertEqual(undo_plan.operations[0].source, self.destination)
        self.assertTrue(os.path.exists(self.source))
        self.assertFalse(os.path.exists(self.destination))
        with open(self.source, "rb") as restored_file:
            self.assertEqual(restored_file.read(), b"original bytes")

    def test_changed_destination_blocks_undo_without_mutating_files(self):
        manifest_path = self._apply_and_record()
        with open(self.destination, "wb") as destination_file:
            destination_file.write(b"changed bytes")
        _, _, issues = undo_manifest(str(manifest_path))
        self.assertEqual({issue.code for issue in issues}, {"changed_applied_destination"})
        self.assertFalse(os.path.exists(self.source))
        self.assertTrue(os.path.exists(self.destination))

    def test_occupied_original_path_blocks_undo_without_replacement(self):
        manifest_path = self._apply_and_record()
        with open(self.source, "wb") as source_file:
            source_file.write(b"newer file")
        _, _, issues = undo_manifest(str(manifest_path))
        self.assertEqual({issue.code for issue in issues}, {"occupied_original_source"})
        self.assertTrue(os.path.exists(self.source))
        self.assertTrue(os.path.exists(self.destination))

    def test_non_applied_manifest_cannot_be_undone(self):
        manifest_path = write_manifest(self.plan, (), "planned", self.manifest_directory)
        _, _, issues = undo_manifest(str(manifest_path))
        self.assertEqual({issue.code for issue in issues}, {"not_applied_manifest"})
