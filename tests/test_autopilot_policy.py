import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Bottleneck as B, Host, Sample, Snapshot
from gfg_plugin.autopilot.perception import perceive
from gfg_plugin.autopilot.policy import Action, Knob, Strategy, decide


def seen(output=90, real=45, gpu=50, cpu=40, primary_pressure=()):
    snap = Snapshot("game", 108, tuple(Sample(i + 1, 100 + i * 2, "renderer", real, output) for i in range(5)),
                    Host(108, 5, gpu, cpu, 70), pressure=primary_pressure, target_fps=90, context="renderer")
    return perceive(snap, 108)


class PolicyTests(unittest.TestCase):
    def test_stable_delivery_holds_instead_of_spending_watts(self):
        plan = decide(seen(), now=108, flow_available=True, power_ceiling_w=25)
        self.assertEqual((plan.action, plan.strategy, plan.knob), (Action.HOLD, Strategy.CRUISE, None))
        self.assertFalse(plan.armed)

    def test_gpu_hypothesis_names_only_flow_scale(self):
        plan = decide(seen(60, gpu=99, cpu=40), now=108, flow_available=True, power_ceiling_w=25)
        self.assertEqual(plan.knob, Knob.FLOW_SCALE)
        self.assertEqual(plan.action, Action.TRIAL)
        self.assertFalse(plan.armed)
        self.assertNotEqual(plan.knob, Knob.POWER_CAP)

    def test_cpu_bound_does_not_offer_scale_or_a_boost(self):
        plan = decide(seen(60, gpu=40, cpu=99), now=108, flow_available=True, power_ceiling_w=25)
        self.assertEqual(plan.action, Action.HOLD)
        self.assertIsNone(plan.knob)
        self.assertEqual(plan.reason, "cpu-bound-no-scale-or-boost")

    def test_unknown_stale_and_external_only_observe(self):
        self.assertEqual(decide(seen(None), now=108).action, Action.OBSERVE)
        external = perceive(Snapshot("game", 108, backend="optiscaler", context="renderer"), 108)
        self.assertEqual(decide(external, now=108, flow_available=True).action, Action.OBSERVE)
        self.assertFalse(decide(external, now=108).armed)

    def test_two_tools_at_once_hold(self):
        gpu = seen(60, gpu=99, cpu=40)
        both = replace(gpu, secondary=(B.POWER_LIMITED,))
        plan = decide(both, now=108, flow_available=True, power_ceiling_w=15)
        self.assertEqual(plan.action, Action.HOLD)
        self.assertIsNone(plan.knob)

    def test_restore_barrier_blocks_a_new_trial(self):
        plan = decide(seen(60, gpu=99, cpu=40), now=108, restore_pending=True, flow_available=True)
        self.assertEqual(plan.action, Action.RESTORE)
        self.assertTrue(plan.release_slot)
        self.assertFalse(plan.armed)

    def test_open_slot_rejects_the_other_tool(self):
        plan = decide(seen(60, gpu=99, cpu=40), now=108, flow_available=True,
                      slot_busy=True, slot_knob=Knob.POWER_CAP)
        self.assertEqual((plan.action, plan.knob, plan.reason),
                         (Action.TRIAL, Knob.POWER_CAP, "single-flight-in-progress"))

    def test_same_inputs_repeat_the_same_decision(self):
        perception = seen(60, gpu=99, cpu=40)
        self.assertEqual(decide(perception, now=108, flow_available=True),
                         decide(perception, now=108, flow_available=True))
