"""Protect the recorded SDR capture manifest without requiring the large archive."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_gsf_reference", ROOT / "tools/verify_gsf_reference.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
MANIFEST = ROOT / "docs/baseline-3.2.2/gsf-sdr-reference-manifest.json"


class ReferenceManifestTest(unittest.TestCase):
    def setUp(self):
        self.raw = MANIFEST.read_bytes()
        self.manifest = json.loads(self.raw)

    def test_original_manifest_identity_and_coverage(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), verify.MANIFEST_SHA256)
        self.assertEqual(len(verify.verify_manifest(self.manifest)), 48)

    def test_missing_or_replaced_frame_is_rejected(self):
        changed = copy.deepcopy(self.manifest)
        del changed["frames"][next(iter(changed["frames"]))]
        with self.assertRaisesRegex(ValueError, "frame list"):
            verify.verify_manifest(changed)
        changed = copy.deepcopy(self.manifest)
        changed["frames"][next(iter(changed["frames"]))] = "not-a-sha256"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify.verify_manifest(changed)

    def test_changed_source_or_mode_is_rejected(self):
        for field, value in (("gsf_commit", "0" * 40), ("size", [640, 400]), ("phases", {})):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.manifest)
                changed[field] = value
                with self.assertRaisesRegex(ValueError, "metadata"):
                    verify.verify_manifest(changed)

    def test_untrusted_archive_is_rejected_before_unzipping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.zip"
            path.write_bytes(b"not the captured archive")
            with self.assertRaisesRegex(ValueError, "archive SHA-256 mismatch"):
                verify.verify_archive(path, MANIFEST)


if __name__ == "__main__":
    unittest.main()
