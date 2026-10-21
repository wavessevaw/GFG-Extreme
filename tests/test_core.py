import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import Clock

from gfg_plugin import autopilot, filters, pilot, settings
from gfg_plugin.governor import PowerGovernor, healthy
from gfg_plugin.policy import Policy, PolicyCoordinator


class FakeCtl:
    def __init__(self):
        self.vars = {}
        self.calls = []
        self.fail = False

    def set_var(self, name, value):
        if self.fail:
            raise RuntimeError("gamescopectl failed")
        self.calls.append((name, str(value)))
        self.vars[name] = str(value)


def engine_status(ctl, t, fresh=True, old=False):
    st = {"engine": "running", "fresh": fresh, "time_ns": int(t * 1e9)}
    if not old:
        st.update({"policy": int(ctl.vars.get("kfg_policy", 0)), "req_multiplier": int(ctl.vars.get("kfg_multiplier", 0)),
                   "req_base_fps": int(ctl.vars.get("kfg_base_fps", 0)),
                   "req_auto_floor": int(ctl.vars.get("kfg_auto_floor", 0)), "post": ctl.vars.get("kfg_post", "")})
    return st


class FiltersTest(unittest.TestCase):
    def test_post_string_and_presets(self):
        self.assertEqual(filters.to_post(filters.OFF), "")
        self.assertEqual(filters.to_post(filters.preset("vivid")), "vibrance,cas=0.35")
        cfg = filters.normalize({"effects": ["vignette", "bogus"], "sharpen": "dls", "sharpness": 2, "aa": "smaa"})
        self.assertEqual(filters.to_post(cfg), "vignette,dls=1:0.17,smaa")

    def test_legacy_vkbasalt(self):
        cfg = filters.from_legacy({"external_vulkan_layer": "vkbasalt", "vkbasalt_shader": "vibrance:noir",
                                   "vkbasalt_sharpening": "cas", "vkbasalt_sharpness": 0.5, "vkbasalt_antialiasing": "fxaa"})
        self.assertEqual(filters.to_post(cfg), "vibrance,noir,cas=0.5,fxaa")
        self.assertEqual(filters.from_legacy({"external_vulkan_layer": "mangohud"}), filters.OFF)


class SettingsTest(unittest.TestCase):
    def test_normalize_and_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            s = settings.Settings(Path(d) / "s.json")
            self.assertFalse(s.exists)
            s.update_profile("default", {"fg": "x3.75", "base_fps": 500, "objective": "nope"})
            p = s.data["profiles"]["default"]
            self.assertEqual((p["fg"], p["base_fps"], p["objective"]), ("x3.75", 90, "autopilot"))
            key = s.make_game_profile(1245620, "Elden Ring")
            self.assertEqual(key, "app:1245620")
            self.assertEqual(s.profile_for(1245620)[0], "app:1245620")
            self.assertEqual(s.profile_for(7)[0], "default")
            with self.assertRaises(ValueError):
                s.make_game_profile(0)
            again = settings.Settings(Path(d) / "s.json")
            self.assertEqual(again.data["profiles"]["app:1245620"]["name"], "Elden Ring")


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.ctl = FakeCtl()
        self.c = PolicyCoordinator(self.ctl, clock=self.clock)
        self.want = Policy(1, 0, "vibrance", "/dev/shm/h", 24)

    def tick(self, **kw):
        self.clock.t += 1
        return self.c.tick(engine_status(self.ctl, self.clock.t, **kw))

    def test_send_order_and_confirm(self):
        self.c.want(self.want)
        self.assertEqual(self.tick()["state"], "applying")
        names = [n for n, _ in self.ctl.calls]
        self.assertEqual(names, ["kfg_hud", "kfg_post", "kfg_auto_floor", "kfg_base_fps", "kfg_multiplier", "kfg_policy"])
        self.assertEqual(self.tick()["state"], "confirmed")
        sent = len(self.ctl.calls)
        for _ in range(5):
            self.tick()
        self.assertEqual(len(self.ctl.calls), sent, "nothing is re-sent while confirmed")

    def test_stale_holds_and_old_engine(self):
        self.c.want(self.want)
        self.assertEqual(self.tick(fresh=False)["state"], "hold")
        self.assertEqual(self.ctl.calls, [])
        self.assertEqual(self.tick(old=True)["state"], "outdated")
        self.assertEqual(self.ctl.calls, [])

    def test_errors_back_off(self):
        self.c.want(self.want)
        self.ctl.fail = True
        self.assertEqual(self.tick()["state"], "error")
        self.ctl.fail = False
        self.tick()  # inside the 1 s back-off? (1 s passed: retried)
        self.assertIn(self.c.s.state, ("applying", "error"))

    def test_restart_reapplies_and_rival_conflicts(self):
        self.c.want(self.want)
        self.tick(), self.tick()
        self.ctl.vars = {}  # Gamescope restarted
        self.tick()
        self.assertEqual(self.tick()["state"], "confirmed")
        for i in range(40):  # someone keeps switching to x3
            if i % 2 == 0:
                self.ctl.vars["kfg_multiplier"] = "3"
            self.tick()
            if self.c.s.state == "conflict":
                break
        self.assertEqual(self.c.s.state, "conflict")
        self.c.take_over()
        self.tick()
        self.assertEqual(self.tick()["state"], "confirmed")


class PilotTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.p = pilot.PointPilot(clock=self.clock)

    def run_ctx(self, n, **ctx):
        base = {"fg": "auto", "objective": "balanced", "refresh": 90, "game": True, "app": 1, "confirmed": True,
                "real": 45.0, "pace": 1.0, "at_ceiling": True, "engine": {"auto": True, "cap_fps": 45}}
        base.update(ctx)
        out = None
        for _ in range(n):
            self.clock.t += 1
            out = self.p.tick(base)
        return out

    def test_ladder(self):
        self.assertEqual(pilot.ladder(90), [24, 30, 35, 40, 45])
        self.assertEqual(pilot.ladder(60), [20, 25, 30])
        self.assertEqual(pilot.mult_label(90, 24), "x3.75")

    def test_measure_then_lock(self):
        out = self.run_ctx(3)
        self.assertEqual(out["phase"], "measure")
        self.assertTrue(out["hold_ceiling"])
        self.assertEqual((out["multiplier"], out["base_fps"], out["auto_floor"]), (1, 0, 24))
        out = self.run_ctx(15)
        self.assertEqual((out["phase"], out["point"], out["base_fps"]), ("locked", 45, 45))
        self.assertFalse(out["hold_ceiling"])

    def test_battery_locks_x375(self):
        out = self.run_ctx(2, objective="battery")
        self.assertEqual((out["point"], out["base_fps"], out["label"]), (24, 24, "x3.75"))

    def test_demotes_only_at_full_power(self):
        self.run_ctx(20)
        out = self.run_ctx(12, real=38.0, at_ceiling=False)
        self.assertEqual(out["point"], 45, "below the ceiling the Governor answers, not the pilot")
        out = self.run_ctx(12, real=38.0, at_ceiling=True)
        self.assertEqual(out["point"], 35)

    def test_fixed_choices(self):
        self.assertEqual(self.run_ctx(1, fg="x3")["multiplier"], 3)
        out = self.run_ctx(1, fg="x3.75")
        self.assertEqual((out["multiplier"], out["base_fps"]), (1, 24))
        out = self.run_ctx(1, fg="custom", base_fps=40)
        self.assertEqual(out["base_fps"], 40)
        self.assertEqual(self.run_ctx(1, fg="off")["multiplier"], 0)


class FakeActuator:
    def __init__(self, tdp=15.0):
        self.tdp, self.initial, self.owned, self.external, self.writes = tdp, None, False, False, []

    def claim(self):
        self.initial, self.owned = self.tdp, True
        return self.status()

    def set_tdp_w(self, w):
        self.tdp = w
        self.writes.append(w)
        return {"success": True, "state": self.status()}

    def verify_ownership(self):
        return self.status()

    def restore_if_owned(self):
        self.tdp, self.owned = self.initial, False
        return {"restored": True}

    def status(self):
        return {"owned": self.owned, "external_change": self.external, "initial_tdp_w": self.initial,
                "ceiling_tdp_w": self.initial, "minimum_tdp_w": 3.0, "draw_w": 9.0}


class GovernorTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.act = FakeActuator()
        self.g = PowerGovernor(self.act, None, clock=self.clock)

    def feed(self, n, **kw):
        s = {"game": True, "key": "app:1|90", "objective": "balanced", "cap": 45, "epoch": 1, "real": 45.0,
             "pace": 1.0, "over_budget": 0.0, "ring_miss": 0.0, "temp_c": 70.0}
        s.update(kw)
        for _ in range(n):
            self.clock.t += 1
            self.g.tick(s)

    def test_verdicts(self):
        self.assertTrue(healthy([{"real": 45, "pace": 1.0}] * 10, 45, True)["ok"])
        self.assertEqual(healthy([{"real": 40, "pace": 1.0}] * 10, 45, True)["reason"], "below-cap")
        self.assertEqual(healthy([{"real": 45, "pace": 0.98}] * 10, 45, True)["reason"], "pace")

    def test_steps_down_then_insures(self):
        self.feed(40)
        self.assertLess(self.act.tdp, 15.0)
        low = self.act.tdp
        self.feed(24, real=30.0)  # severe shortfall
        self.assertEqual(self.act.tdp, 15.0, "a clear shortfall goes back to full power at once")
        self.assertGreaterEqual(self.g.floor_fail[45], low)

    def test_quality_never_probes_and_hold(self):
        self.feed(60, objective="quality")
        self.assertEqual(self.act.writes, [])
        self.feed(30)
        self.assertLess(self.act.tdp, 15.0)
        self.feed(2, hold_ceiling=True)
        self.assertEqual(self.act.tdp, 15.0)

    def test_restore_on_exit(self):
        self.feed(40)
        self.feed(1, game=False)
        self.assertEqual(self.act.tdp, 15.0)
        self.assertFalse(self.act.owned)


class AutopilotTest(unittest.TestCase):
    def test_choices_and_hysteresis(self):
        clock = Clock()
        a = autopilot.Autopilot(clock=clock)
        self.assertEqual(a.decide("auto", {"external_power": True}, 60)["objective"], "quality")
        clock.t += 61
        self.assertEqual(a.decide("auto", {"external_power": True}, 88)["objective"], "balanced")
        clock.t += 61
        self.assertEqual(a.decide("auto", {"external_power": False, "percent": 19}, 60)["objective"], "battery")
        clock.t += 61
        self.assertEqual(a.decide("auto", {"external_power": False, "percent": 23}, 60)["objective"], "battery")
        clock.t += 61
        self.assertEqual(a.decide("auto", {"external_power": False, "percent": 26}, 60)["objective"], "balanced")
        self.assertEqual(a.decide("smoothness", {"external_power": False, "percent": 10}, 60)["objective"], "quality")
