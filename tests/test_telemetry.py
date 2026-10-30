import json
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401

from gfg_plugin.telemetry import Telemetry
from sandbox import run
from sandbox.vdeck import VGame


class TelemetrySampleTest(unittest.TestCase):
    def test_standard_sample_has_every_live_value(self):
        with tempfile.TemporaryDirectory() as d:
            rig = run.make_rig(VGame("game", 40.0), objective="balanced")
            rig.service.telemetry = Telemetry(Path(d))
            run.play(rig, 30)
            rig.service.telemetry.flush()  # samples are written in batches
            lines = (Path(d) / "samples.jsonl").read_text().splitlines()
            self.assertGreaterEqual(len(lines), 20)
            row = json.loads(lines[-1])
            for key in ("fps", "real", "pace", "point", "mult", "cap", "hz", "tdp", "draw", "ceiling", "temp",
                        "cpu", "gpu", "gpu_mhz", "fan", "bat", "ac", "hours", "cpu_cap_khz", "gpu_limit_mhz"):
                self.assertIn(key, row)
            for key in ("fps", "tdp", "temp", "cpu", "gpu", "bat"):
                self.assertIsNotNone(row[key], key)


if __name__ == "__main__":
    unittest.main()


class TelemetryBatchTest(unittest.TestCase):
    def test_samples_are_batched_and_flushed(self):
        with tempfile.TemporaryDirectory() as d:
            t = Telemetry(Path(d))
            for i in range(5):
                t.sample({"i": i})
            self.assertFalse((Path(d) / "samples.jsonl").exists())
            t.session({"end": 1})  # a session line writes the queued samples first
            self.assertEqual(len((Path(d) / "samples.jsonl").read_text().splitlines()), 5)
            t.sample({"i": 5})
            self.assertEqual(len(t.files()), 2)  # listing for the report flushes too
            self.assertEqual(len((Path(d) / "samples.jsonl").read_text().splitlines()), 6)
