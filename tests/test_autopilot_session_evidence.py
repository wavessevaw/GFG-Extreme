"""Session boundaries at the real Governor -> experiment adapter."""
import asyncio
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Sample, Snapshot


class ExperimentReceiptTests(unittest.TestCase):
    def setUp(self):
        import test_governor_runtime as legacy
        self.fixture = legacy.RuntimeBase()
        self.fixture.setUp()
        self.svc = self.fixture.svc
        self.now = self.fixture.t["now"]
        self.snapshot = Snapshot(
            "pid-start-profile-hz", self.now,
            (Sample(7, self.now, "renderer", 30, 0),),
            context="renderer")
        self.svc.autopilot_observation.snapshot = self.snapshot

    def tearDown(self):
        self.fixture.tearDown()

    def test_one_receipt_once_and_zero_is_measured(self):
        first = self.svc._autopilot_evidence()
        self.assertTrue(first[2])
        self.assertEqual(first[3].output_fps, 0)
        self.assertFalse(self.svc._autopilot_evidence()[2])

    def test_reused_renderer_sequence_is_new_only_in_a_new_session(self):
        self.assertTrue(self.svc._autopilot_evidence()[2])
        self.svc.autopilot_observation.snapshot = replace(self.snapshot, session_key="new-pid-start")
        self.assertTrue(self.svc._autopilot_evidence()[2])
        self.assertFalse(self.svc._autopilot_evidence()[2])

    def test_blocked_external_stale_and_cross_context_receipts_are_unavailable(self):
        for changes in (
            {"blocked_reason": "focus-unconfirmed-or-menu"},
            {"blocked_reason": "restore-pending"},
            {"backend": "native"},
            {"session_key": ""},
            {"timestamp_mono": self.now - 10},
            {"timestamp_mono": self.now + 1},
            {"context": "other-renderer"},
            {"samples": (Sample(8, self.now - 10, "renderer", 30, 90),)},
        ):
            with self.subTest(changes=changes):
                self.svc._autopilot_seen_seq = None
                self.svc.autopilot_observation.snapshot = replace(self.snapshot, **changes)
                seq, stamp, fresh, sample = self.svc._autopilot_evidence()
                self.assertEqual(seq, 0)
                self.assertFalse(fresh)
                self.assertIsNone(sample)

    def test_existing_cpu_and_frame_os_owners_block_new_experiments(self):
        from types import SimpleNamespace
        from gfg_plugin.autopilot.policy import Action, Knob
        self.svc._autopilot_power_enabled = True
        decision = SimpleNamespace(action=Action.TRIAL, knob=Knob.POWER_CAP)
        for owner in ("cpu", "frame-os", "request"):
            with self.subTest(owner=owner):
                self.svc.cpu.owned = owner == "cpu"
                self.svc.frame_os.enabled = owner == "frame-os"
                self.svc.frame_os.mode = "act"
                self.svc._request = object() if owner == "request" else None
                with patch("gfg_plugin.governor_service.decide", return_value=decision), \
                     patch.object(self.svc._autopilot_power, "step",
                                  return_value={"wrote": False}) as step:
                    asyncio.run(self.svc._run_autopilot_power())
                self.assertFalse(step.call_args.kwargs["allow"])
                self.assertTrue(self.svc._autopilot_conflicting_executor())

    def test_power_adapter_receives_full_session_identity(self):
        self.svc._autopilot_power_enabled = True
        with patch.object(self.svc._autopilot_power, "step",
                          return_value={"wrote": False}) as step:
            asyncio.run(self.svc._run_autopilot_power())
        self.assertEqual(step.call_args.kwargs["context"], self.snapshot.session_key)


if __name__ == "__main__":
    unittest.main()
