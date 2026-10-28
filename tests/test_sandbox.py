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


class HonestTest(unittest.TestCase):
    """Honest multipliers: xN draws exactly N-1 generated frames, x3 at most, the panel's refresh
    is kept and only Autopilot aims at 90 on screen."""

    def test_ladders(self):
        from gfg_plugin import honest
        self.assertEqual(honest.ladder("autopilot", 90), [(27, 3), (30, 3), (32, 2), (35, 2), (40, 2), (42, 2), (45, 2)])
        self.assertEqual(honest.ladder("balanced", 90), [(30, 3), (35, 2), (40, 2), (45, 2)])
        self.assertEqual(honest.ladder("quality", 90), [(45, 2)])
        self.assertEqual(honest.ladder("battery", 90), [(30, 3)])
        self.assertEqual(honest.ladder("autopilot", 90, light=True), [(45, 2)])
        self.assertEqual(honest.ladder("balanced", 60, dock=True), [(20, 3), (25, 2), (30, 2)])
        self.assertEqual((honest.cap(2, 90), honest.cap(3, 90), honest.cap(2, 60)), (45, 30, 30))
        bal = honest.ladder("balanced", 90)
        self.assertEqual([honest.n_for(bal, b) for b in (24, 30, 33, 35, 45)], [3, 3, 3, 2, 2])
        self.assertEqual(honest.n_for(honest.ladder("quality", 90), 30), 2)
        for obj in ("autopilot", "balanced", "quality", "battery"):
            for hz in (60, 75, 90):
                self.assertTrue(all(2 <= n <= 3 for _, n in honest.ladder(obj, hz)))

    @staticmethod
    def _rows(real):
        return [{"t": 1000.0 + k, "app": 4242, "hz": 90, "ceiling": 15.0, "objective": "autopilot",
                 "ac": False, "bat": 70.0, "tdp": 15.0, "real": real, "fps": real, "mult": 1,
                 "gpu": 99.0, "cpu": 50.0, "draw": 14.0, "temp": 70.0} for k in range(600)]

    def _main(self, res):
        pairs = res["all"]["pairs_pct"]
        return max(pairs, key=pairs.get), pairs

    def test_strict_engine_gets_pairs(self):
        rows = self._rows(42.0)
        for obj, want in (("autopilot", "x2@40"), ("balanced", "x2@40"), ("quality", "x2@45"),
                          ("battery", "x3@30")):
            res = replay.replay(rows, strict=True, gen_cost=0.08, objective=obj)
            top, pairs = self._main(res)
            self.assertEqual(top, want, (obj, pairs))
            self.assertFalse(any(k.startswith("fill") for k in pairs), (obj, pairs))
        # x3 only for a game that cannot hold more than about 30, outside Autopilot too.
        top, pairs = self._main(replay.replay(self._rows(33.0), strict=True, gen_cost=0.08, objective="balanced"))
        self.assertEqual(top, "x3@30", pairs)
        # Without the engine's strict status the 3.3.2 requests stand (fill to the refresh).
        top, pairs = self._main(replay.replay(rows, gen_cost=0.08, objective="balanced"))
        self.assertTrue(top.startswith("fill"), pairs)

    def test_clean_cadence_is_even(self):
        res = replay.replay(self._rows(60.0), strict=True, gen_cost=0.08, objective="balanced")
        self.assertEqual(self._main(res)[0], "x2@45")
        self.assertGreater(res["all"]["even_pct"], 80.0)


if __name__ == "__main__":
    unittest.main()
