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
            with patch.object(svc.configuration, "get_current_profile_snapshot",
                              side_effect=AssertionError("other mode ran")):
                asyncio.run(svc._iteration_core())
            asyncio.run(svc._run_autopilot_power())
            asyncio.run(svc._run_autopilot_power())
            self.assertEqual(svc.power.writes, [])
        finally:
            fixture.tearDown()
