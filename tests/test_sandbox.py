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
        """Even points only (user, 2026-10-29 13:06): S = refresh / cap whole vblanks, S a
        multiple of N; x2@22.5 at 90 Hz is sent as 22."""
        from gfg_plugin import honest
        L = honest.ladder
        self.assertEqual(honest.even_points(90), [(22, 2), (30, 3), (45, 2)])
        self.assertEqual(honest.even_points(60), [(20, 3), (30, 2)])
        self.assertEqual(honest.even_points(120), [(20, 3), (30, 2), (40, 3), (60, 2)])
        self.assertEqual(L("balanced", 90), [(22, 2), (30, 3), (45, 2)])
        self.assertEqual(L("autopilot", 90), [(22, 2), (30, 3), (45, 2)])
        self.assertEqual([L("quality", 90, fg=f) for f in ("x2", "x3")], [[(22, 2), (45, 2)], [(30, 3)]])
        self.assertEqual([L("battery", 90, fg=f) for f in ("auto", "x2", "x3")], [[(22, 2), (30, 3)], [(22, 2)], [(30, 3)]])
        self.assertEqual([L("battery", 60, fg=f) for f in ("auto", "x2", "x3")], [[(20, 3), (30, 2)], [(30, 2)], [(20, 3)]])
        self.assertEqual(L("balanced", 90, light=True), [(22, 2), (45, 2)])
        self.assertEqual((honest.shown_cap(22, 90), honest.shown_cap(30, 90), honest.shown_cap(45, 90)), (22.5, 30.0, 45.0))
        for obj in ("autopilot", "balanced", "quality", "battery"):
            for hz in (60, 90, 120):
                for fg in ("auto", "x2", "x3"):
                    for b, n in L(obj, hz, fg=fg):
                        s_ = round(hz / b)
                        self.assertTrue(2 <= n <= 3 and s_ % n == 0 and hz / s_ >= 20, (obj, hz, fg, b, n))

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
        # Even points: a 42 fps game cannot hold 45, so x3@30 in every mode (Autopilot too, strict).
        for obj, want in (("autopilot", "x3@30"), ("balanced", "x3@30"), ("quality", "x3@30"),
                          ("battery", "x3@30")):
            res = replay.replay(rows, strict=True, gen_cost=0.08, objective=obj)
            top, pairs = self._main(res)
            self.assertEqual(top, want, (obj, pairs))
            self.assertFalse(any(k.startswith("fill") for k in pairs), (obj, pairs))
        # Under 30: the next even point, x2@22.5 (45 on screen), not an uneven cap.
        top, pairs = self._main(replay.replay(self._rows(27.0), strict=True, gen_cost=0.08, objective="balanced"))
        self.assertEqual(top, "x2@22.5", pairs)
        # Without the engine's strict status the 3.3.2 requests stand (fill to the refresh).
        top, pairs = self._main(replay.replay(rows, gen_cost=0.08, objective="balanced"))
        self.assertTrue(top.startswith("fill"), pairs)

    def test_fixed_choice_in_every_mode(self):
        """Fixed x2 in Battery at 90 Hz: x2@22.5 (sent 22, 45 on screen); fixed x3: 30."""
        from sandbox.run import make_rig, play
        from sandbox.vdeck import VGame
        for obj, fg, want in (("battery", "x2", ("2", "22")), ("quality", "x3", ("3", "30")),
                              ("balanced", "x3", ("3", "30"))):
            rig = make_rig(VGame("g", 60.0), objective=obj, fg=fg)
            rig.engine.strict = True
            play(rig, 200)
            self.assertEqual((rig.engine.vars["kfg_multiplier"], rig.engine.vars["kfg_base_fps"]), want, (obj, fg))
            self.assertEqual(rig.engine.vars["kfg_strict"], "1")

    def test_balanced_power_target(self):
        res = replay.replay(self._rows(60.0), strict=True, gen_cost=0.08, objective="balanced")
        self.assertLessEqual(res["all"]["tdp_w"], 12.1)

    def test_clean_cadence_is_even(self):
        for real, want in ((60.0, "x2@45"), (42.0, "x3@30"), (27.0, "x2@22.5")):
            res = replay.replay(self._rows(real), strict=True, gen_cost=0.08, objective="balanced")
            self.assertEqual(self._main(res)[0], want)
            self.assertGreater(res["all"]["even_pct"], 90.0, (real, res["all"]["even_pct"]))


if __name__ == "__main__":
    unittest.main()
