import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.experiments import SingleFlight
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
