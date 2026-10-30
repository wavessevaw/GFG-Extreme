"""Protect the original Linux observation archive against accidental replacement."""
import hashlib
from pathlib import Path
import unittest
import zipfile


ARCHIVE = Path(__file__).resolve().parents[1] / "docs/baseline-3.2.2/linux-evidence.zip"
SHA256 = "fdaf15b068cdc110ee3b44c4b4151eef416d02d9d57852fd069727a72f1b1ab2"


class BaselineEvidenceTest(unittest.TestCase):
    def test_original_archive_digest_and_contents(self):
        self.assertEqual(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), SHA256)
        with zipfile.ZipFile(ARCHIVE) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {
                "SANDBOX_REPORT.md", "environment.txt", "frontend-build.log",
                "frontend-smoke.log", "sandbox.json", "sandbox.log", "stress.json",
                "stress.log", "unit.log",
            })
            environment = archive.read("environment.txt").decode("utf-8")
            self.assertIn("92b557f678d118ae97948673c26e2498b7a28467", environment)


    def test_original_gsf_archive_digest_and_contents(self):
        archive_path = ARCHIVE.with_name("gsf-model-engine.zip")
        expected = "5a6ad32dc546ac5d42d28f49a7ea476758ac45632178f1ef6c270b24077daef5"
        self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(), expected)
        with zipfile.ZipFile(archive_path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {"engine.json", "scenarios.json"})

if __name__ == "__main__":
    unittest.main()
