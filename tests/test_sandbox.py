import json
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401

from sandbox import replay, run


class SandboxTest(unittest.TestCase):
    """Every virtual-Deck scenario must pass (model results; see docs/SANDBOX_REPORT.md)."""

    def test_all_scenarios(self):
        results = run.run_all()
        failed = {n: [c for c in r["checks"] if not c["ok"]] for n, r in results.items() if not r["pass"]}
        self.assertEqual(failed, {})
        self.assertGreaterEqual(len(results), 20)



class ReplayTest(unittest.TestCase):
    """The telemetry replay runs on a recorded-looking session (synthetic, no player data)."""

    def test_replay_counts(self):
        with tempfile.TemporaryDirectory() as d:
            rows = []
            for k in range(400):
                heavy = 150 <= k < 250
                rows.append({"t": 1000.0 + k, "app": 4242, "hz": 90, "ceiling": 15.0, "objective": "autopilot",
                             "ac": False, "bat": 70.0, "tdp": 12.0, "real": 30.0 if heavy else 45.0,
                             "fps": 90.0, "mult": 1, "gpu": 99.0 if heavy else 80.0, "cpu": 50.0,
                             "draw": 11.0, "temp": 70.0})
            (Path(d) / "samples.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
            loaded = replay.load_samples([d])
            self.assertEqual(len(loaded), 400)
            res = replay.replay(loaded)
        self.assertEqual(res["sessions"], 1)
        a = res["all"]
        self.assertAlmostEqual(a["hours"], 400 / 3600, places=2)
        for key in ("tdp_writes_h", "policy_changes_h", "point_changes_h", "short_pct", "real_fps", "draw_w"):
            self.assertIn(key, a)
        self.assertGreater(a["real_fps"], 20.0)
        self.assertTrue(set(a["points_pct"]) <= {"24", "30", "35", "40", "45"})


if __name__ == "__main__":
    unittest.main()
