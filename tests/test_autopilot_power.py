import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Host, Sample, Snapshot
from gfg_plugin.autopilot.perception import perceive
from gfg_plugin.autopilot.policy import Action, Knob, decide
from gfg_plugin.autopilot.power_trial import PowerTrial


class Cap:
    def __init__(self, ceiling=15, current=12, owned=True):
        self.owned = owned
        self.ceiling = ceiling
        self.current = current
        self.writes = []
        self.restores = 0
        self.fail_write = False
        self.fail_restore = False
        self.lie = None

    def status(self):
        return {"owned": self.owned, "ceiling_tdp_w": self.ceiling, "observed_tdp_w": self.current,
                "restore_pending": False}

    def set_tdp_w(self, watts):
        self.writes.append(watts)
        if self.fail_write:
            return {"success": False, "error": "write failed", "state": self.status()}
        self.current = self.lie if self.lie is not None else watts
        return {"success": True, "state": self.status()}

    def restore_if_owned(self):
        self.restores += 1
        if self.fail_restore:
            return {"success": False, "error": "restore failed", "state": self.status()}
        self.owned = False
        self.current = 12
        return {"success": True, "restored": True, "state": self.status()}


def power_limited():
    snap = Snapshot("game", 108, tuple(Sample(i + 1, 100 + i * 2, "renderer", 30, 60) for i in range(5)),
                    Host(108, 5, 50, 40, 70, apu_draw_w=14.8, verified_cap_w=15), target_fps=90, context="renderer")
    return perceive(snap, 108)


def trial(perception, ceiling=15):
    return decide(perception, now=108, power_ceiling_w=ceiling)


class PowerTrialTests(unittest.TestCase):
    def test_one_step_never_passes_the_ceiling_and_does_not_keep_the_winner(self):
        cap = Cap(ceiling=15, current=14)
        run = PowerTrial(cap, cooldown_s=30)
        window = {"output": 60, "real": 30}
        plan = trial(power_limited())
        self.assertEqual(plan.knob, Knob.POWER_CAP)
        self.assertEqual(run.step(plan, window, now=10)["reason"], "baseline-a1")
        ack = run.step(plan, window, now=11)
        self.assertEqual(ack["requested_w"], 15)
        self.assertEqual(cap.writes, [15])
        self.assertEqual(run.step(plan, window, now=12)["reason"], "restored-for-a2")
        done = run.step(plan, window, now=13)
        self.assertEqual(done["verdict"], "REJECT")
        self.assertFalse(done["reapplied"])
        self.assertEqual(cap.writes, [15])
        self.assertGreaterEqual(cap.restores, 1)
        self.assertEqual(run.step(plan, window, now=14)["reason"], "trial-cooldown")
        self.assertEqual(cap.writes, [15])

    def test_already_at_ceiling_or_unowned_does_not_write(self):
        window = {"output": 60, "real": 30}
        plan = trial(power_limited(), 15)
        for cap in (Cap(ceiling=15, current=15), Cap(owned=False)):
            run = PowerTrial(cap)
            run.step(plan, window, now=10)
            self.assertEqual(cap.writes, [])

    def test_bad_ack_restores_and_blocks_another_tool(self):
        cap = Cap()
        cap.lie = 100
        run = PowerTrial(cap, cooldown_s=0)
        plan = trial(power_limited())
        window = {"output": 60, "real": 30}
        run.step(plan, window, now=10)
        undone = run.step(plan, window, now=11)
        self.assertEqual(undone["action"], "RESTORE")
        self.assertEqual(cap.writes, [13])
        self.assertFalse(run.slot.busy)
        other = decide(power_limited(), now=12, flow_available=True)
        self.assertNotEqual(other.knob, Knob.POWER_CAP)
        self.assertFalse(run.step(other, window, now=12)["wrote"])

    def test_hold_and_disabled_flag_do_not_write(self):
        cap = Cap()
        run = PowerTrial(cap)
        held = decide(perceive(Snapshot("game", 108, tuple(Sample(i + 1, 100 + i * 2, "renderer", 45, 90) for i in range(5)),
                                        Host(108, 5, 40, 40, 60), target_fps=90, context="renderer"), 108), now=108)
        self.assertEqual(held.action, Action.HOLD)
        self.assertFalse(run.step(held, {"output": 90, "real": 45}, now=10)["wrote"])
        self.assertEqual(cap.writes, [])


class ServicePowerGateTests(unittest.TestCase):
    def test_flag_off_does_not_write_and_flag_on_skips_the_other_modes(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc.power.claim()
            svc.power.values.update(ceiling_tdp_w=15, observed_tdp_w=12, draw_w=14.8, owned=True)
            svc._autopilot_power_view = svc.power.status()
            svc.autopilot_observation.snapshot = Snapshot(
                "game", fixture.t["now"], tuple(Sample(i + 1, fixture.t["now"] - 10 + i * 2, "renderer", 30, 60) for i in range(5)),
                Host(fixture.t["now"], 5, 50, 40, 70, apu_draw_w=14.8, verified_cap_w=15),
                target_fps=90, context="renderer")
            with patch.object(svc.power, "set_tdp_w", side_effect=AssertionError("power write")):
                asyncio.run(svc._run_autopilot_power())
            svc._autopilot_power_enabled = True
            asyncio.run(svc._iteration_core())
            asyncio.run(svc._run_autopilot_power())
            asyncio.run(svc._run_autopilot_power())
            self.assertEqual(svc.power.writes, [])
            svc._restore_pending = True
            asyncio.run(svc._run_autopilot_power())
            self.assertEqual(svc.power.writes, [])
            self.assertEqual(svc._status["autopilot_power"]["reason"], "restore-pending")
        finally:
            fixture.tearDown()

    def test_the_flag_still_polls_and_follows_a_profile_change(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc._settings.setdefault("profiles", {}).setdefault("other", {})["enabled"] = True
            svc._settings["profiles"]["other"]["mode"] = "quality"
            polls = []
            original = svc.observer.poll

            def poll():
                polls.append(1)
                return original()

            svc.observer.poll = poll
            svc.configuration.get_current_profile_snapshot = lambda: (
                "other", {"config": {"fg_backend": "gfg"}})
            asyncio.run(svc._iteration_core())
            self.assertTrue(polls)
            self.assertEqual(svc._active_profile, "other")
            self.assertEqual(svc.power.writes, [])
        finally:
            fixture.tearDown()

    def test_a_flag_on_refreshes_the_launch_probe_before_six_seconds(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc._launch_polled = fixture.t["now"] - 7
            svc.observer.consume_line(legacy.fixed_plan(30, 60), now=fixture.t["now"])
            asyncio.run(svc._iteration_core())
            self.assertLessEqual(fixture.t["now"] - svc._launch_polled, 6)
            self.assertEqual(svc._status.get("target_output_fps"), 90)
            fixture.t["now"] += 7
            svc.observer.consume_line(legacy.fixed_plan(30, 60), now=fixture.t["now"])
            asyncio.run(svc._iteration_core())
            svc.observer.game_focused = True
            svc.observer.game_focused_at = fixture.t["now"]
            svc._update_autopilot_observation()
            self.assertLessEqual(fixture.t["now"] - svc._launch_polled, 6)
            self.assertNotEqual(svc.autopilot_observation.snapshot.blocked_reason, "launch-probe-stale")
        finally:
            fixture.tearDown()

    def test_a_failed_trial_rollback_retries_the_pretrial_cap_without_releasing_ownership(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc._active_profile = "game"
            svc.power.claim()
            svc.power.values.update(observed_tdp_w=11, initial_tdp_w=8, owned=True)
            svc._autopilot_power.baseline_w = 10
            svc._autopilot_power.rollback_due = True
            svc._actuator_restore_errors["power"] = "baseline-restore-failed"
            svc._actuator_restore_at = fixture.t["now"]
            restores = []
            original_restore = svc.power.restore_if_owned

            def restore():
                restores.append("user-ppt")
                return original_restore()

            original_set = svc.power.set_tdp_w
            fails = {"left": 1}

            def set_tdp(value):
                if fails["left"]:
                    fails["left"] -= 1
                    return {"success": False, "error": "write failed", "state": svc.power.status()}
                return original_set(value)

            svc.power.restore_if_owned = restore
            svc.power.set_tdp_w = set_tdp
            asyncio.run(svc._iteration_core())
            self.assertEqual(svc.power.writes, [])
            self.assertEqual(restores, [])
            fixture.t["now"] += 6
            asyncio.run(svc._iteration_core())
            self.assertEqual(restores, [])
            self.assertTrue(svc.power.state.owned)
            self.assertTrue(svc._restoration_blocked())
            fixture.t["now"] += 6
            asyncio.run(svc._iteration_core())
            self.assertEqual(svc.power.writes, [10])
            self.assertEqual(restores, [])
            self.assertTrue(svc.power.state.owned)
            self.assertFalse(svc._restoration_blocked())
            self.assertEqual(svc.power.values["observed_tdp_w"], 10)
            asyncio.run(svc._iteration_core())
            self.assertEqual(svc.power.writes, [10])
        finally:
            fixture.tearDown()

    def test_a_profile_switch_verifies_the_trial_cap_before_the_user_cap(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc._active_profile = "game"
            svc.power.claim()
            svc.power.values.update(observed_tdp_w=11, initial_tdp_w=8, owned=True)
            svc._autopilot_power.baseline_w = 10
            svc._autopilot_power.scheduler.start(Knob.POWER_CAP, fixture.t["now"], "scene", None)
            svc._settings.setdefault("profiles", {}).setdefault("other", {})["enabled"] = True
            order = []
            original_set = svc.power.set_tdp_w
            original_restore = svc.power.restore_if_owned

            def set_tdp(value):
                order.append(("set", value, svc.power.state.owned))
                return original_set(value)

            def restore():
                order.append(("release", svc.power.values.get("observed_tdp_w"), svc.power.state.owned))
                return original_restore()

            svc.power.set_tdp_w = set_tdp
            svc.power.restore_if_owned = restore
            svc.configuration.get_current_profile_snapshot = lambda: (
                "other", {"config": {"fg_backend": "gfg"}})
            asyncio.run(svc._iteration_core())
            set_at = next(index for index, item in enumerate(order) if item[:2] == ("set", 10))
            release_at = next(index for index, item in enumerate(order) if item[0] == "release")
            self.assertLess(set_at, release_at)
            self.assertTrue(order[set_at][2])
            self.assertFalse(any(item[0] == "set" and item[2] is False for item in order))
            self.assertFalse(svc.power.state.owned)
            self.assertFalse(svc._restoration_blocked())
            self.assertEqual(svc.power.values["observed_tdp_w"], 10)
        finally:
            fixture.tearDown()

    def test_the_second_flag_puts_back_an_applied_watt_before_it_holds(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc.power.claim()
            svc.power.values.update(observed_tdp_w=11, initial_tdp_w=8, owned=True)
            svc._autopilot_power.baseline_w = 10
            svc._autopilot_power.scheduler.start(Knob.POWER_CAP, fixture.t["now"], "scene", None)
            svc._autopilot_flow_enabled = True
            asyncio.run(svc._run_autopilot_exclusive())
            self.assertEqual(svc.power.writes, [10])
            self.assertEqual(svc.power.values["observed_tdp_w"], 10)
            self.assertTrue(svc.power.state.owned)
            self.assertEqual(svc._status["autopilot_power"]["reason"], "two-tools-requested")
            self.assertIsNone(svc._autopilot_power.baseline_w)
        finally:
            fixture.tearDown()

    def test_turning_the_flag_off_restores_eleven_watts_before_the_governor(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._active_profile = "game"
            svc.power.claim()
            svc.power.values.update(observed_tdp_w=11, owned=True)
            svc._autopilot_power.baseline_w = 10
            svc._autopilot_power.scheduler.start(Knob.POWER_CAP, fixture.t["now"], "scene", None)
            svc._autopilot_power_enabled = False
            seen = []

            async def sync(profile, config):
                seen.append((svc._autopilot_power.baseline_w, svc.power.values["observed_tdp_w"],
                             svc._autopilot_power.scheduler.busy))

            svc._sync_overlay = sync
            asyncio.run(svc._iteration())
            self.assertEqual(svc.power.writes[0], 10)
            self.assertEqual(seen[0], (None, 10, False))
            self.assertFalse(svc._autopilot_change_outstanding())
        finally:
            fixture.tearDown()

    def test_a_new_game_is_not_adopted_while_the_old_point_is_still_applied(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._autopilot_power_enabled = True
            svc._active_profile = "game"
            svc._point = {"key": "30x3", "multiplier": 3, "base_target_fps": 30}
            svc._point_deltas = {}
            svc.observer._session_generation = 1
            svc._generation_seen = 1
            svc._launch_key = [1, 1, 1]
            svc.inspector.info["launch_key"] = [9, 9, 9]
            svc._launch = None
            svc._launch_polled = -1e9
            asyncio.run(svc._iteration_core())
            self.assertFalse(svc._point and list(svc._launch_key) == [9, 9, 9])
            svc._autopilot_power_enabled = False
            asyncio.run(svc._iteration())
            self.assertFalse(svc._point and list(svc._launch_key) == [9, 9, 9])
        finally:
            fixture.tearDown()
