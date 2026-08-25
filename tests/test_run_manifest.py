import json
import os
import tempfile
import unittest
from unittest.mock import patch

from execution import apply_plan
from rename_plan import RenameOperation, create_plan
from run_manifest import (
    MANIFEST_VERSION,
    configuration_digest,
    read_manifest,
    resume_manifest,
    start_manifest,
    write_manifest,
)


class TestRunManifest(unittest.TestCase):
    def test_manifest_is_versioned_complete_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = create_plan((RenameOperation("1", "old.mp4", "new.mp4"),))
            path = write_manifest(plan, (), "planned", directory)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], MANIFEST_VERSION)
            self.assertTrue(payload["complete"])
            self.assertEqual(payload["plan_digest"], plan.digest)
            self.assertEqual(payload["operations"][0]["result"], "planned")
            self.assertFalse(list(path.parent.glob("*.tmp")))
            manifest = read_manifest(path)
            self.assertEqual(manifest.action, "plan")
            self.assertIsNone(manifest.operations[0].sha256)

    def test_interrupted_apply_checkpoints_and_resumes_remaining_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            first_source = os.path.join(directory, "first-old.mp4")
            first_destination = os.path.join(directory, "first-new.mp4")
            second_source = os.path.join(directory, "second-old.mp4")
            second_destination = os.path.join(directory, "second-new.mp4")
            for path, contents in ((first_source, b"first"), (second_source, b"second")):
                with open(path, "wb") as source_file:
                    source_file.write(contents)
            plan = create_plan(
                (
                    RenameOperation("1", first_source, first_destination),
                    RenameOperation("2", second_source, second_destination),
                )
            )
            expected_configuration = configuration_digest({"FALLBACK_TEMPLATE": "$title"})
            recorder = start_manifest(plan, directory, configuration=expected_configuration)
            real_link = os.link
            calls = 0

            def interrupt_second_claim(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise KeyboardInterrupt()
                return real_link(source, destination)

            with patch("execution.os.link", side_effect=interrupt_second_claim):
                with self.assertRaises(KeyboardInterrupt):
                    apply_plan(plan, progress=recorder.record)
            recorder.interrupt(KeyboardInterrupt())

            interrupted = read_manifest(recorder.path, allow_incomplete=True)
            self.assertFalse(interrupted.complete)
            self.assertEqual(interrupted.state, "interrupted")
            self.assertEqual(interrupted.configuration_digest, expected_configuration)
            self.assertEqual(
                [operation.result for operation in interrupted.operations], ["applied", "pending"]
            )

            resumed_recorder, resumed_plan, issues = resume_manifest(recorder.path)
            self.assertEqual(issues, ())
            self.assertEqual([operation.scene_id for operation in resumed_plan.operations], ["2"])
            self.assertEqual(apply_plan(resumed_plan, progress=resumed_recorder.record), ())
            resumed_recorder.finalize("applied")

            completed = read_manifest(recorder.path)
            self.assertEqual(completed.state, "applied")
            self.assertTrue(completed.complete)
            self.assertEqual(
                [operation.result for operation in completed.operations], ["applied", "applied"]
            )

    def test_resume_refuses_a_changed_pending_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "old.mp4")
            destination = os.path.join(directory, "new.mp4")
            with open(source, "wb") as source_file:
                source_file.write(b"original")
            plan = create_plan((RenameOperation("1", source, destination),))
            recorder = start_manifest(plan, directory)
            recorder.interrupt(RuntimeError("simulated interruption"))
            with open(source, "wb") as source_file:
                source_file.write(b"changed")

            _, _, issues = resume_manifest(recorder.path)
            self.assertEqual({issue.code for issue in issues}, {"resume_changed_pending_source"})

    def test_failed_apply_rollbacks_remain_resumable(self):
        with tempfile.TemporaryDirectory() as directory:
            first_source = os.path.join(directory, "first-old.mp4")
            first_destination = os.path.join(directory, "first-new.mp4")
            second_source = os.path.join(directory, "second-old.mp4")
            second_destination = os.path.join(directory, "second-new.mp4")
            for path in (first_source, second_source):
                with open(path, "wb") as source_file:
                    source_file.write(path.encode("utf-8"))
            plan = create_plan(
                (
                    RenameOperation("1", first_source, first_destination),
                    RenameOperation("2", second_source, second_destination),
                )
            )
            recorder = start_manifest(plan, directory)
            real_link = os.link
            calls = 0

            def fail_second_claim(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated failure")
                return real_link(source, destination)

            with patch("execution.os.link", side_effect=fail_second_claim):
                issues = apply_plan(plan, progress=recorder.record)
            recorder.fail(issues)

            failed = read_manifest(recorder.path, allow_incomplete=True)
            self.assertFalse(failed.complete)
            self.assertEqual(failed.state, "failed")
            self.assertEqual(
                [operation.result for operation in failed.operations], ["rolled_back", "failed"]
            )
            self.assertEqual(failed.operations[1].execution_error, "simulated failure")

            resumed_recorder, resumed_plan, resume_issues = resume_manifest(recorder.path)
            self.assertEqual(resume_issues, ())
            self.assertEqual(
                [operation.scene_id for operation in resumed_plan.operations], ["1", "2"]
            )
            self.assertEqual(apply_plan(resumed_plan, progress=resumed_recorder.record), ())
            resumed_recorder.finalize("applied")

            completed = read_manifest(recorder.path)
            self.assertTrue(completed.complete)
            self.assertEqual(completed.state, "applied")
            self.assertEqual(
                [operation.result for operation in completed.operations], ["applied", "applied"]
            )
