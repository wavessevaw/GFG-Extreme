"""Playtime target: battery hours -> APU power ceiling, and the budget search inside it."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(ROOT / "tests"))

from gfg_plugin import playtime  # noqa: E402
from gfg_plugin.governor_core import BudgetController  # noqa: E402

H = 3600.0


def bat(wh, watts, discharging=True):
    return {"available": True, "discharging": discharging, "energy_uwh": wh * 1e6, "power_uw": watts * 1e6}


class PlannerTests(unittest.TestCase):
    def settle(self, p, now, battery, draw, steps=60):
        out = None
        for i in range(steps):
            out = p.update(now + i, battery=battery, apu_draw_w=draw, min_w=4.0, max_w=15.0)
        return out

    def test_three_hours_from_a_full_oled_battery(self):
        # 50 Wh, Deck draws 16 W now (APU 11 W, rest 5 W): 3 h allows 15.8 W total -> APU ~10.8 W
        p = playtime.PlaytimePlanner()
        p.set_target(3.0, 0.0)
        out = self.settle(p, 0.0, bat(50, 16), 11.0)
        self.assertEqual(out["state"], "holding")
        self.assertAlmostEqual(out["others_w"], 5.0, delta=0.2)
        self.assertAlmostEqual(out["cap_w"], 10.5, delta=0.6)
        self.assertEqual(out["forecast_min"], int(50 / 16 * 60))

    def test_a_short_target_needs_no_limit_and_an_impossible_one_is_tight(self):
        p = playtime.PlaytimePlanner()
        p.set_target(1.0, 0.0)
        out = self.settle(p, 0.0, bat(50, 16), 11.0)
        self.assertEqual((out["state"], out["cap_w"]), ("on-track", None))
        p.set_target(8.0, 0.0)
        out = self.settle(p, 0.0, bat(40, 12), 7.0)
        self.assertEqual(out["state"], "tight")
        self.assertEqual(out["cap_w"], 4.0, "as low as the Deck goes")
        self.assertLess(out["reachable_min"], 8 * 60)
        self.assertGreater(out["reachable_min"], 4 * 60)

    def test_charging_reached_and_no_battery_lift_the_limit(self):
        p = playtime.PlaytimePlanner()
        p.set_target(3.0, 0.0)
        self.assertEqual(p.update(0, battery=bat(50, 16, discharging=False), apu_draw_w=11, min_w=4, max_w=15)["state"],
                         "charging")
        self.assertIsNone(p.update(3 * H, battery=bat(5, 16), apu_draw_w=11, min_w=4, max_w=15)["cap_w"])
        self.assertEqual(p.update(3 * H, battery=bat(5, 16), apu_draw_w=11, min_w=4, max_w=15)["state"], "reached")
        p.set_target(2.0, 0.0)
        self.assertEqual(p.update(0, battery={"available": False}, apu_draw_w=None, min_w=4, max_w=15)["state"],
                         "no-battery")

    def test_the_ceiling_does_not_wander(self):
        p = playtime.PlaytimePlanner()
        p.set_target(3.0, 0.0)
        caps = set()
        for i in range(600):
            draw = 11.0 + (0.8 if i % 2 else -0.8)     # a noisy draw sensor
            out = p.update(float(i), battery=bat(50 - i * 0.004, 16 + (1 if i % 3 else -1)), apu_draw_w=draw,
                           min_w=4.0, max_w=15.0)
            if i > 60:
                caps.add(out["cap_w"])
        self.assertLessEqual(len(caps), 2, f"ceiling moved through {sorted(caps)}")

    def test_restore_only_a_target_still_ahead(self):
        p = playtime.PlaytimePlanner()
        p.restore(3.0, 1000.0, now=2000.0)
        self.assertIsNone(p.deadline)
        p.restore(3.0, 5000.0, now=2000.0)
        self.assertEqual((p.target_h, p.deadline), (3.0, 5000.0))
        p.set_target(None, 0.0)
        self.assertEqual(p.update(0, battery=bat(50, 16), apu_draw_w=11, min_w=4, max_w=15), {"active": False})


class CeilingTests(unittest.TestCase):
    def test_the_cap_bounds_every_ceiling_and_lifts_cleanly(self):
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        ctl.tdp = 12.0
        self.assertTrue(ctl.set_playtime_cap(9.0))
        self.assertEqual((ctl.tdp, ctl.normal_max_w, ctl.emergency_max_w, ctl.ideal_max_w), (9.0, 9.0, 9.0, 9.0))
        self.assertFalse(ctl.set_playtime_cap(10.0))
        self.assertEqual(ctl.tdp, 9.0, "a higher cap never raises the TDP by itself")
        ctl.set_playtime_cap(None)
        self.assertEqual((ctl.normal_max_w, ctl.emergency_max_w, ctl.ideal_max_w), (15.0, 20.0, 11.0))
        ctl.set_playtime_cap(1.0)
        self.assertEqual(ctl.normal_max_w, ctl.min_w, "never below the Deck's floor")

    def test_a_heavy_scene_under_the_cap_trades_ratio_for_watts(self):
        from test_governor_budget import Game, run
        ctl = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        game = Game(2.8)                    # 30 real needs ~10.7 W
        ctl.set_playtime_cap(8.0)
        now, trace = run(ctl, game, 0.0, 60)
        self.assertLessEqual(max(t[1] for t in trace), 8.0, "never above the playtime ceiling")
        self.assertLess(ctl.point.base_target_fps, 30, "a deeper ratio keeps the output instead")


if __name__ == "__main__":
    unittest.main()
