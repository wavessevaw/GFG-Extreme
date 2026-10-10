import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.apply import ScheduledPower
from gfg_plugin.autopilot.policy import Knob


class Cap:
    def __init__(self, ceiling, current, owned=True):
        self.ceiling = ceiling
        self.current = current
        self.owned = owned
        self.writes = []
        self.restores = 0
        self.fail = False

    def status(self):
        return {"owned": self.owned, "ceiling_tdp_w": self.ceiling, "observed_tdp_w": self.current}

    def set_tdp_w(self, watts):
        self.writes.append(watts)
        if self.fail:
            return {"success": False, "error": "write failed", "state": self.status()}
        self.current = watts
        return {"success": True, "state": self.status()}

    def restore_if_owned(self):
        self.restores += 1
        if self.fail and self.writes:
            return {"success": False, "error": "restore failed", "state": self.status()}
        self.owned = False
        return {"success": True, "restored": True, "state": self.status()}


def feed(run, ceiling, count=5, start=0, output=60, real=30, owned=True, allow=True, other=False):
    outcome = None
    for index in range(count):
        outcome = run.step(now=start + index * 1.5, seq=index + 1, real=real, output=output,
                           context="scene", ceiling_w=ceiling, owned=owned, allow=allow, other_busy=other)
    return outcome


class ApplyTests(unittest.TestCase):
    def test_ac11_every_ceiling_is_the_devices_own_limit(self):
        for ceiling in (9, 12, 15, 20, 100):
            cap = Cap(ceiling, ceiling - 1)
            run = ScheduledPower(cap)
            outcome = feed(run, ceiling)
            self.assertEqual(outcome["requested_w"], ceiling)
            self.assertEqual(cap.writes, [ceiling])
            self.assertLessEqual(max(cap.writes), ceiling)

    def test_already_at_the_ceiling_does_not_invent_fifteen(self):
        cap = Cap(9, 9)
        run = ScheduledPower(cap)
        feed(run, 9)
        self.assertEqual(cap.writes, [])

    def test_ac12_external_owner_is_not_overwritten(self):
        cap = Cap(15, 10, owned=False)
        run = ScheduledPower(cap)
        outcome = feed(run, 15, owned=False)
        self.assertEqual(cap.writes, [])
        self.assertEqual(outcome["reason"], "power-not-owned")
        self.assertEqual(cap.restores, 0)

    def test_ac13_failed_write_restores_and_blocks_the_next_trial(self):
        cap = Cap(15, 12)
        cap.fail = True
        run = ScheduledPower(cap)
        outcome = feed(run, 15)
        self.assertEqual(outcome["restore_failed"], True)
        self.assertEqual(cap.writes, [13])
        again = run.step(now=30, seq=20, real=30, output=60, context="scene",
                         ceiling_w=15, owned=True, allow=True)
        self.assertFalse(again["wrote"])
        self.assertEqual(again["reason"], "restore-pending")
        self.assertEqual(cap.writes, [13])

    def test_ac15_flow_slot_blocks_the_power_write(self):
        cap = Cap(20, 12)
        run = ScheduledPower(cap)
        outcome = feed(run, 20, other=True)
        self.assertEqual(cap.writes, [])
        self.assertEqual(outcome["reason"], "other-tool-busy")
        self.assertFalse(run.scheduler.busy)
        self.assertNotEqual(run.scheduler.knob, Knob.FLOW_SCALE)

    def test_a_measurement_does_not_claim_a_gain_and_holds_the_one_slot(self):
        from gfg_plugin.autopilot.experiments import SingleFlight
        cap = Cap(15, 12)
        slot = SingleFlight()
        run = ScheduledPower(cap)
        first = run.step(now=0, seq=1, real=30, output=60, context="scene", ceiling_w=15,
                         owned=True, allow=True, slot=slot)
        self.assertFalse(first["wrote"])
        self.assertTrue(slot.busy)
        self.assertEqual(slot.knob, Knob.POWER_CAP)
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 1), "slot-busy")
        self.assertFalse(run.scheduler._claims)
        blocked = run.step(now=2, seq=2, real=30, output=60, context="scene", ceiling_w=15,
                           owned=True, allow=True, slot=slot, restore_pending=True)
        self.assertEqual(blocked["reason"], "restore-pending")
        self.assertEqual(cap.writes, [])
        self.assertFalse(slot.busy)
