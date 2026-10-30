"""Protect the original Linux observation archive against accidental replacement."""
import hashlib
import json
import math
from pathlib import Path
import unittest
import zipfile


ARCHIVE = Path(__file__).resolve().parents[1] / "docs/baseline-3.2.2/linux-evidence.zip"
SHA256 = "fdaf15b068cdc110ee3b44c4b4151eef416d02d9d57852fd069727a72f1b1ab2"


class BaselineEvidenceTest(unittest.TestCase):
    def test_autopilot_experiment_observations_remain_intact(self):
        path = ARCHIVE.parents[1] / "research/autopilot-floor-2026-10-30.json"
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "6251ca5691fce16c106c31a29ef3ae1732ca177b289a119b4d8a2dedd78e564d")
        cases = json.loads(raw)["cases"]
        self.assertEqual(set(cases), {f"{fps}@{limit}" for fps in (22, 26, 30, 34, 40) for limit in (15, 18)})
        self.assertTrue(all(set(observation) == {"before", "candidate"} for observation in cases.values()))

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

    def test_temporal_observation_archive(self):
        path = ARCHIVE.with_name("gsf-temporal-llvmpipe.zip")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "6f1c14bbd169a37712efa77449b71faecbfb9b3961b9b3160a33b9143d5fb1a0")
        scenes = {"h_turn64": {3}, "h_parallax": {3}, "h_lines_slow": {2, 3}}
        metrics = {"psnr", "psnr_worst", "errgrad", "blk", "badblk_pct", "badblk_max", "temporal", "lineflk", "sharpflk_pct"}
        with zipfile.ZipFile(path) as archive:
            self.assertIsNone(archive.testzip())
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["quality_status"], "UNVERIFIED")
            self.assertEqual(manifest["gsf_commit"], "62621c4f9b60fd3cb95edafb62a1a44a1bb2c21e")
            self.assertEqual(manifest["gamescope_commit"], "aa289ea5977d8b21b92b0f246f0e8f0c225d180f")
            self.assertEqual(set(manifest["evidence"]), set(scenes))
            for scene, modes in scenes.items():
                raw = archive.read(f"{scene}.json")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["evidence"][scene]["sha256"])
                document = json.loads(raw)
                self.assertIn("llvmpipe", document["device"].lower())
                self.assertEqual(document["size"], [1280, 800])
                self.assertEqual(len(document["hard"]), len(modes))
                self.assertEqual({row["mode"] for row in document["hard"]}, modes)
                for row in document["hard"]:
                    self.assertEqual(row["scene"], scene)
                    for name in metrics:
                        self.assertTrue(math.isfinite(row[name]), (scene, name))

if __name__ == "__main__":
    unittest.main()
