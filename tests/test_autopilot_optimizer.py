import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Bottleneck as B, Perception
from gfg_plugin.autopilot.coordinator import MemoryView, plan
from gfg_plugin.autopilot.explain import explain
from gfg_plugin.autopilot.optimizer import Candidate
from gfg_plugin.autopilot.policy import Action, Knob, Strategy


def seen(primary, reason="measured", stale=False):
    return Perception(primary, (), 0.7, ("evidence",), (), reason, 0.0, 10.0, "game", stale)


def point(knob, value, real=45, stability=90, fidelity=1, draw=12, cost=0, measured=True, requires=()):
    return Candidate(knob, value, real, stability, fidelity, draw, cost, measured, requires, "window")


CURRENT = point("current", 0)
CAPS = ("power_cap", "flow_scale", "render_scale", "cpu_cap", "fg_ratio", "renderer-capacity")


class OptimizerAcceptanceTests(unittest.TestCase):
    def test_ac01_stable_delivery_does_not_spend_four_watts_for_two_fps(self):
        expensive = point("power_cap", 16, real=47, draw=16, cost=1)
        decision = plan(seen(B.STABLE), (expensive,), CURRENT, now=10,
                        ceiling_w=25, capabilities=CAPS, ack_ok=True)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertIn(("power_cap", 16, "watts-not-worth-the-gain"), decision.rejected)
        self.assertIsNone(explain(decision)["confirmed_gain"])

    def test_ac02_gpu_bound_rejects_a_cpu_boost(self):
        boost = point("cpu_cap", 3500, real=50, cost=1)
        flow = point("flow_scale", 0.7, real=49, draw=12, cost=0.2)
        decision = plan(seen(B.GPU_LIMITED), (boost, flow), CURRENT, now=10, capabilities=CAPS, ack_ok=True)
        self.assertEqual(decision.knob, Knob.FLOW_SCALE)
        self.assertIn(("cpu_cap", 3500, "cpu-boost-not-gpu-relevant"), decision.rejected)

    def test_ac03_cpu_bound_does_not_promise_a_scale_cut(self):
        decision = plan(seen(B.CPU_LIMITED), (point("render_scale", 0.9, real=46),),
                        CURRENT, now=10, capabilities=CAPS)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertIn(("render_scale", 0.9, "scale-will-not-fix-cpu"), decision.rejected)

    def test_ac05_and_ac06_stale_or_external_does_not_open_a_trial(self):
        stale = plan(seen(B.GPU_LIMITED, stale=True), (point("flow_scale", 0.7, real=49),),
                     CURRENT, now=10, capabilities=CAPS)
        external = plan(seen(B.UNKNOWN, "external-backend-observe-only"),
                        (point("flow_scale", 0.7, real=49),), CURRENT, now=10, capabilities=CAPS)
        self.assertEqual(stale.action, Action.OBSERVE)
        self.assertEqual(external.action, Action.OBSERVE)
        self.assertEqual(stale.rejected, ())
        self.assertIsNone(stale.knob)

    def test_ac07_scale_floor_ceiling_and_unconfirmed_capacity_are_excluded(self):
        decision = plan(seen(B.GPU_LIMITED), (
            point("render_scale", 0.7),
            point("power_cap", 30, real=60, draw=30),
            point("fg_ratio", 3, real=60),
        ), CURRENT, now=10, ceiling_w=15, capabilities=("power_cap", "render_scale", "fg_ratio"))
        reasons = {item[2] for item in decision.rejected}
        self.assertIn("below-user-scale", reasons)
        self.assertIn("above-power-ceiling", reasons)
        self.assertIn("renderer-capacity-unconfirmed", reasons)
        self.assertEqual(decision.action, Action.HOLD)

    def test_ac08_close_points_hold_in_both_contexts(self):
        close = (point("flow_scale", 0.75, real=45.4), point("power_cap", 13, real=45.5, draw=12.2))
        for primary in (B.GPU_LIMITED, B.STABLE):
            decision = plan(seen(primary), close, CURRENT, now=10, ceiling_w=15, capabilities=CAPS)
            again = plan(seen(primary), close, CURRENT, now=10, ceiling_w=15, capabilities=CAPS)
            self.assertEqual(decision, again)
            self.assertEqual(decision.action, Action.HOLD)
            self.assertIsNone(decision.knob)

    def test_ac09_unconsented_frame_os_act_is_not_started(self):
        decision = plan(seen(B.GPU_LIMITED), (point("frame_os_act", 1, real=55),),
                        CURRENT, now=10, capabilities=CAPS, frame_os_allowed=False)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertIn(("frame_os_act", 1, "frame-os-act-not-consented"), decision.rejected)

    def test_recover_returns_to_the_last_verified_point_without_a_new_trial(self):
        verified = point("current", 0, stability=90)
        dropped = point("current", 0, stability=60)
        decision = plan(seen(B.GPU_LIMITED), (point("power_cap", 18, real=70, draw=18),), dropped,
                        now=10, ceiling_w=25, capabilities=CAPS,
                        memory=MemoryView(last_verified=verified))
        self.assertEqual((decision.action, decision.strategy), (Action.RECOVER, Strategy.RECOVERY))
        self.assertIsNone(decision.knob)

    def test_hysteresis_blocks_a_strategy_change_but_not_a_repeat(self):
        better = point("flow_scale", 0.7, real=49)
        memory = MemoryView(strategy=Strategy.CRUISE, strategy_at=0)
        held = plan(seen(B.GPU_LIMITED), (better,), CURRENT, now=10, capabilities=CAPS, memory=memory, ack_ok=True)
        self.assertEqual(held.reason, "hysteresis")
        later = plan(seen(B.GPU_LIMITED), (better,), CURRENT, now=40, capabilities=CAPS, memory=memory, ack_ok=True)
        self.assertEqual(later.knob, Knob.FLOW_SCALE)

    def test_review_notes_ack_fidelity_and_unsupported_tool(self):
        omitted = plan(seen(B.GPU_LIMITED), (point("flow_scale", 0.7, real=49),), CURRENT, now=10, capabilities=CAPS)
        self.assertEqual(omitted.action, Action.HOLD)
        self.assertIn(("flow_scale", 0.7, "renderer-ack-missing"), omitted.rejected)
        ugly = point("flow_scale", 0.7, real=49, fidelity=0.2)
        decision = plan(seen(B.GPU_LIMITED), (ugly,), CURRENT, now=10, capabilities=CAPS, ack_ok=True)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertIn(("flow_scale", 0.7, "quality-or-stability-regression"), decision.rejected)
        scale = point("render_scale", 0.9, real=49)
        held = plan(seen(B.GPU_LIMITED), (scale,), CURRENT, now=10, capabilities=CAPS, ack_ok=True)
        self.assertEqual(held.action, Action.HOLD)
        self.assertIsNone(held.knob)
        broken = point("power_cap", 14, real=49, draw=float("nan"))
        safe = plan(seen(B.POWER_LIMITED), (broken,), CURRENT, now=10, ceiling_w=20, capabilities=CAPS, ack_ok=True)
        self.assertEqual(safe.action, Action.HOLD)
        self.assertIn(("power_cap", 14, "nonfinite-metric"), safe.rejected)
