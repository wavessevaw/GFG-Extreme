import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sandbox.run import make_rig, play  # noqa: E402
from sandbox.vdeck import VGame, VModel  # noqa: E402


class StablePointTest(unittest.TestCase):
    def test_cooldown_does_not_hide_an_untried_watt(self):
        rig = make_rig(VGame("g", 34.0, seed=1), fg="x3", objective="autopilot",
                       battery=70.0, ambient=30.0, above_x3=True)
        try:
            play(rig, 1200)
            events = [e for e in rig.log if e["src"] == "governor"]
            failed = next(e for e in events if e["kind"] == "governor-floor" and e["tdp"] == 13.0)
            restored = next(e for e in events if e["kind"] == "governor-tdp"
                            and e["t"] >= failed["t"] and e["watts"] == 15.0)
            probes = [e for e in events if e["kind"] == "governor-tdp"
                      and e["t"] > restored["t"] and e["why"] == "window-held"]
            self.assertTrue(probes, "cooldown must not permanently hide the untried 14 W level")
            self.assertGreaterEqual(probes[0]["t"] - restored["t"], 30.0,
                                    "the anti-oscillation cooldown must still be observed")
            self.assertEqual(probes[0]["watts"], 14.0)
            self.assertTrue(rig.service.governor.stable)
            self.assertEqual(rig.power.tdp, 14.0)
            self.assertEqual(len(probes), 1, "the resulting stable level must not keep probing")
        finally:
            rig.service.stop()
        self.assertEqual(rig.power.tdp, 15.0, "stop restores the user's limit")

    def test_locks_then_starts_there_next_time(self):
        rig = make_rig(VGame("g", 45.0), objective="autopilot")
        play(rig, 900)
        g = rig.service.governor
        self.assertTrue(g.stable, [e for e in rig.log if e["src"] == "governor"][-5:])
        gov = [e for e in rig.log if e["src"] == "governor"]
        kinds = [e["kind"] for e in gov]
        locked_at = len(kinds) - kinds[::-1].index("governor-stable")
        writes_after = [e for e in gov[locked_at:] if e["kind"] == "governor-tdp" and e["why"] == "window-held"]
        self.assertEqual(writes_after, [])   # locked: no probing down
        model = rig.service.governor.model
        stable = model.get("app:1245620|90|stable")
        self.assertIsNotNone(stable)
        # Next launch: no full-power measurement, the stable point at once.
        nxt = make_rig(VGame("g", 45.0), objective="autopilot")
        nxt.service.governor.model = model
        play(nxt, 30)
        phases = {r["phase"] for r in nxt.timeline}
        self.assertNotIn("measure", phases)
        self.assertEqual(nxt.timeline[-1]["point"], int(stable["point"]))

    def test_lighter_scene_unlocks(self):
        load = {"v": 1.0}
        rig = make_rig(VGame("g", 45.0, lambda t: load["v"]), objective="autopilot")
        play(rig, 900)
        self.assertTrue(rig.service.governor.stable)
        tdp = rig.power.tdp
        load["v"] = 1.6
        play(rig, 300)
        self.assertLess(rig.power.tdp, tdp)


if __name__ == "__main__":
    unittest.main()
