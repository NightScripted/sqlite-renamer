import json
import tempfile
import unittest

from rename_plan import RenameOperation, create_plan
from run_manifest import MANIFEST_VERSION, read_manifest, write_manifest


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
