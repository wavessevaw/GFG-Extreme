import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.boost import Boost, boost_cap  # noqa: E402
from gfg_plugin.policy import Policy  # noqa: E402


class FakeCtl:
    def __init__(self):
        self.sent = []

    def set_var(self, name, value):
        self.sent.append((name, int(value)))


class Coord:
    hold_until = -1e9


class BoostTest(unittest.TestCase):
    def setUp(self):
        self.t = 100.0
        self.ctl, self.coord = FakeCtl(), Coord()
        self.b = Boost(self.ctl, self.coord, clock=lambda: self.t, threaded=False)
        self.want = Policy(multiplier=1, base_fps=30)
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=self.want, headroom=60.0)

    def run_stick(self, deflection, seconds, dt=0.05):
        for _ in range(int(round(seconds / dt))):
            self.b.stick(int(deflection * 32767), 0)
            self.t += dt
            self.b.step(self.t)

    def test_a_flick_does_not_boost(self):
        self.run_stick(0.5, 0.4)
        self.run_stick(0.0, 0.5)
        self.assertEqual(self.ctl.sent, [])

    def test_a_turn_boosts_and_gives_the_multiplier_back_fast(self):
        self.run_stick(0.5, 0.7)
        self.assertEqual(self.ctl.sent, [("kfg_base_fps", boost_cap(90, 1.75)), ("kfg_multiplier", 1)])  # medium: x1.75
        self.assertTrue(self.b.active)
        self.assertGreater(self.coord.hold_until, self.t)
        self.run_stick(0.0, 0.3)
        self.assertFalse(self.b.active)
        self.assertEqual(self.ctl.sent[-2:], [("kfg_base_fps", 30), ("kfg_multiplier", 1)])

    def test_a_sharp_turn_boosts_sooner_and_deeper_within_headroom(self):
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=self.want, headroom=55.0)
        self.run_stick(0.9, 0.35)
        self.assertEqual(self.ctl.sent[0], ("kfg_base_fps", 55))   # x1.5 would be 60: the game renders 55

    def test_short_boost_then_the_stick_must_rest(self):
        self.run_stick(0.5, 0.65)
        self.assertTrue(self.b.active)
        self.run_stick(0.5, 1.6)
        self.assertFalse(self.b.active, "a boost lasts 1.5 s at most")
        self.run_stick(0.5, 2.0)
        self.assertFalse(self.b.active, "no new boost until the stick rests")
        self.run_stick(0.0, 0.1)
        self.run_stick(0.5, 0.7)
        self.assertTrue(self.b.active)

    def test_no_headroom_no_boost(self):
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=self.want, headroom=33.0)
        self.run_stick(0.9, 1.0)
        self.assertEqual(self.ctl.sent, [])
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=self.want, headroom=None)
        self.run_stick(0.9, 1.0)
        self.assertEqual(self.ctl.sent, [])

    def test_off_without_generation_or_setting(self):
        self.b.configure(enabled=False, mult=1.5, refresh=90, wanted=self.want, headroom=60.0)
        self.run_stick(0.9, 1.0)
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=Policy(multiplier=0), headroom=60.0)
        self.run_stick(0.9, 1.0)
        self.assertEqual(self.ctl.sent, [])

    def test_fixed_x3_goes_back_to_x3(self):
        want = Policy(multiplier=3, base_fps=0)
        self.b.configure(enabled=True, mult=1.5, refresh=90, wanted=want, headroom=60.0)
        self.run_stick(0.9, 0.4)
        self.run_stick(0.0, 0.3)
        self.assertEqual(self.ctl.sent[-2:], [("kfg_base_fps", 0), ("kfg_multiplier", 3)])

    def test_headroom_estimate(self):
        # 30 real at 80 % GPU with generation filling 90 Hz: about 36 fps without some generated frames.
        self.assertAlmostEqual(Boost.estimate_headroom(90, 30, 80, 400, 2500), 35.9, places=1)
        self.assertIsNone(Boost.estimate_headroom(90, None, 80, 400, 2500))


if __name__ == "__main__":
    unittest.main()
