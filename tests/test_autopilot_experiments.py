import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.experiments import ExperimentConfig, Scheduler, SingleFlight
from gfg_plugin.autopilot.policy import Knob


class ExperimentTests(unittest.TestCase):
    def test_second_tool_cannot_start(self):
        slot = SingleFlight()
        self.assertIsNone(slot.start(Knob.POWER_CAP, 10))
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 11), "slot-busy")
        self.assertEqual(slot.knob, Knob.POWER_CAP)

    def test_drift_is_inconclusive_and_not_a_success(self):
        slot = SingleFlight()
        slot.start(Knob.FLOW_SCALE, 10)
        slot.record("baseline-a1", {"output": 90, "real": 45})
        slot.record("test-b", {"output": 90, "real": 45})
        slot.record("baseline-a2", {"output": 70, "real": 30})
        self.assertEqual(slot.judge(), "INCONCLUSIVE")
        self.assertEqual(slot.reason, "control-window-drift")
        self.assertNotEqual(slot.verdict, "ACCEPT")

    def test_delivery_drop_rejects_and_restore_clears_the_slot(self):
        slot = SingleFlight()
        slot.start(Knob.POWER_CAP, 10)
        slot.record("baseline-a1", {"output": 90, "real": 45})
        slot.record("test-b", {"output": 70, "real": 45})
        slot.record("baseline-a2", {"output": 90, "real": 45})
        self.assertEqual(slot.judge(), "REJECT")
        slot2 = SingleFlight()
        slot2.start(Knob.FLOW_SCALE, 10)
        slot2.abort("restore-pending")
        self.assertFalse(slot2.busy)
        self.assertEqual(slot2.verdict, "ABORTED")
        self.assertIsNone(slot2.start(Knob.POWER_CAP, 12))


def drive(slot, start, seq0, output, real, temp=70, context="scene"):
    result = None
    for index in range(5):
        result = slot.observe(seq0 + index, start + index * 1.5, real, output, temp, context)
    return result


class ProtocolTests(unittest.TestCase):
    def run_to_verdict(self, a2_output=90, a2_temp=70, context="scene"):
        slot = Scheduler(ExperimentConfig())
        self.assertIsNone(slot.start(Knob.POWER_CAP, 0, context, expected_gain=3))
        self.assertEqual(drive(slot, 0, 1, 90, 45), "apply")
        self.assertEqual(slot.ack(7, True), "settle")
        self.assertIsNone(slot.observe(6, 8, 48, 90, 70, context))
        self.assertEqual(drive(slot, 10, 6, 90, 48), "restore")
        self.assertEqual(slot.ack(17, True), "settle-a2")
        self.assertIsNone(slot.observe(11, 18, 45, a2_output, a2_temp, context))
        verdict = drive(slot, 20, 11, a2_output, 45, a2_temp, context)
        return slot, verdict

    def test_ac10_drift_is_inconclusive_and_is_not_learned(self):
        slot, verdict = self.run_to_verdict(a2_output=80)
        self.assertEqual(verdict, "control-window-drift")
        self.assertEqual(slot.result.verdict, "INCONCLUSIVE")
        self.assertFalse(slot.result.learned)
        self.assertEqual(slot.result.next_action, "HOLD")
        self.assertIsNone(slot.result.confidence)

    def test_temperature_change_is_not_a_win(self):
        slot, verdict = self.run_to_verdict(a2_temp=74)
        self.assertEqual(verdict, "temperature-drift")
        self.assertFalse(slot.result.learned)

    def test_clean_comparison_does_not_apply_a_winner_without_an_interval(self):
        slot, verdict = self.run_to_verdict()
        self.assertEqual(verdict, "benefit-held")
        self.assertEqual(slot.result.verdict, "ACCEPT")
        self.assertFalse(slot.result.learned)
        self.assertEqual(slot.result.next_action, "HOLD")
        self.assertEqual(slot.result.observed_metrics["confidence_interval"], "not-computed")

    def test_unknown_expected_gain_cannot_become_a_win(self):
        slot = Scheduler()
        self.assertIsNone(slot.start(Knob.POWER_CAP, 0, "scene", expected_gain=None))
        self.assertEqual(drive(slot, 0, 1, 90, 45), "apply")
        slot.ack(7, True)
        self.assertEqual(drive(slot, 10, 6, 90, 48), "restore")
        slot.ack(17, True)
        verdict = drive(slot, 20, 11, 90, 45)
        self.assertEqual(verdict, "benefit-not-claimed")
        self.assertEqual(slot.result.verdict, "REJECT")
        self.assertFalse(slot.result.learned)

    def test_second_controller_ack_loss_and_failed_restore(self):
        slot = Scheduler()
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 0, "scene", expected_gain=0.5), "expected-gain-too-small")
        self.assertIsNone(slot.start(Knob.POWER_CAP, 0, "scene", expected_gain=3))
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 1, "scene", expected_gain=3), "slot-busy")
        self.assertEqual(drive(slot, 0, 1, 90, 45), "apply")
        self.assertEqual(slot.observe(6, 30, 45, 90, 70, "scene"), "ack-missing")
        self.assertEqual(slot.restored(False), "restore-pending")
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 40, "other", expected_gain=3), "restore-pending")

    def test_scene_change_and_delivery_drop_restore_immediately(self):
        slot = Scheduler()
        slot.start(Knob.FLOW_SCALE, 0, "scene", expected_gain=3)
        self.assertEqual(drive(slot, 0, 1, 90, 45), "apply")
        self.assertEqual(slot.observe(6, 8, 45, 90, 70, "cutscene"), "scene-or-context-changed")
        self.assertEqual(slot.result.verdict, "INCONCLUSIVE")
        other = Scheduler()
        other.start(Knob.POWER_CAP, 0, "scene", expected_gain=3)
        drive(other, 0, 1, 90, 45)
        other.ack(7, True)
        self.assertEqual(other.observe(6, 11, 20, 50, 70, "scene"), "delivery-dropped")
        self.assertTrue(other.needs_restore)
        self.assertNotEqual(other.result.verdict, "ACCEPT")

    def test_repeated_sample_is_not_a_new_observation(self):
        slot = Scheduler()
        slot.start(Knob.POWER_CAP, 0, "scene", expected_gain=3)
        self.assertIsNone(slot.observe(1, 0, 45, 90, 70, "scene"))
        self.assertIsNone(slot.observe(1, 2, 80, 120, 70, "scene"))
        self.assertEqual(len(slot._windows["baseline-a1"].samples), 1)

    def test_crash_blocks_the_next_trial(self):
        slot = Scheduler()
        slot.start(Knob.POWER_CAP, 0, "scene", expected_gain=3)
        self.assertEqual(slot.crash("helper-restart").verdict, "ABORTED")
        self.assertEqual(slot.start(Knob.FLOW_SCALE, 5, "scene", expected_gain=3), "restore-pending")

