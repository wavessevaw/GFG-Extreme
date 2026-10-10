import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Host, Sample, Snapshot
from gfg_plugin.autopilot.policy import Knob


def gpu_snapshot(now):
    return Snapshot("game", now, tuple(Sample(i + 1, now - 10 + i * 2, "renderer", 30, 60) for i in range(5)),
                    Host(now, 5, 99, 40, 70), target_fps=90, context="renderer")


class FlowReservationTests(unittest.TestCase):
    def setUp(self):
        import test_governor_runtime as legacy
        self.fixture = legacy.RuntimeBase()
        self.fixture.setUp()
        self.svc = self.fixture.svc
        now = self.fixture.t["now"]
        self.svc.autopilot_observation.snapshot = gpu_snapshot(now)

    def tearDown(self):
        self.fixture.tearDown()

    def test_flag_off_does_not_call_the_tuner(self):
        with patch.object(self.svc, "_sync_flow", new=AsyncMock(side_effect=AssertionError("flow write"))):
            asyncio.run(self.svc._run_autopilot_flow())
        self.assertFalse(self.svc._autopilot_slot.busy)

    def test_without_a_locked_point_the_tuner_is_not_called(self):
        self.svc._autopilot_flow_enabled = True
        with patch.object(self.svc, "_sync_flow", new=AsyncMock(side_effect=AssertionError("flow write"))):
            asyncio.run(self.svc._run_autopilot_flow())
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "no-locked-point")
        self.assertFalse(self.svc._status["autopilot_flow"]["armed"])
        self.assertFalse(self.svc._autopilot_slot.busy)

    def test_power_slot_blocks_the_flow_tuner(self):
        self.svc._autopilot_flow_enabled = True
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc.overlay = object()
        self.svc._autopilot_slot.start(Knob.POWER_CAP, 1)
        with patch.object(self.svc, "_sync_flow", new=AsyncMock(side_effect=AssertionError("flow write"))):
            asyncio.run(self.svc._run_autopilot_flow())
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "single-flight-in-progress")
        self.assertEqual(self.svc._autopilot_slot.knob, Knob.POWER_CAP)

    def test_both_flags_write_nothing_and_skip_other_modes(self):
        self.svc._autopilot_power_enabled = True
        self.svc._autopilot_flow_enabled = True
        with patch.object(self.svc.power, "set_tdp_w", side_effect=AssertionError("power write")), \
             patch.object(self.svc, "_sync_flow", new=AsyncMock(side_effect=AssertionError("flow write"))), \
             patch.object(self.svc.configuration, "get_current_profile_snapshot",
                          side_effect=AssertionError("other mode ran")):
            asyncio.run(self.svc._iteration_core())
            asyncio.run(self.svc._run_autopilot_exclusive())
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "two-tools-requested")

    def test_a_busy_tuner_keeps_the_slot_and_power_does_not_write(self):
        self.svc._autopilot_flow_enabled = True
        self.svc._status["profile"] = "game"
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc.overlay = object()
        self.svc.power.claim()
        self.svc.power.values.update(ceiling_tdp_w=20, observed_tdp_w=12, owned=True)
        self.svc._autopilot_power_view = self.svc.power.status()

        async def accept(profile):
            self.svc._flow.phase = "a1"
            self.svc._flow.reason = "existing-tuner"

        with patch.object(self.svc, "_sync_flow", new=accept):
            asyncio.run(self.svc._run_autopilot_flow())
        self.assertEqual(self.svc._autopilot_slot.knob, Knob.FLOW_SCALE)
        self.assertTrue(self.svc._status["autopilot_flow"]["armed"])
        self.svc._autopilot_power_enabled = True
        self.svc._autopilot_flow_enabled = False
        asyncio.run(self.svc._run_autopilot_power())
        asyncio.run(self.svc._run_autopilot_power())
        self.assertEqual(self.svc.power.writes, [])

    def test_withdraw_writes_saved_scale_and_waits_for_renderer_ack(self):
        from gfg_plugin.governor_flow import FlowTrial
        now = self.fixture.t["now"]
        self.svc._autopilot_flow_enabled = True
        self.svc._status["profile"] = "game"
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc.overlay = object()
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("same",)
        self.svc._autopilot_slot.start(Knob.FLOW_SCALE, 1)
        self.svc.autopilot_observation.snapshot = gpu_snapshot(now - 1000)
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 0.8}
        self.svc._base_for = lambda profile, saved: {}
        written = []

        def write(profile, config, key):
            written.append(config["flow_scale"])

        self.svc._write_overlay_sync = write
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 3, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.7, "event_seq": 3},
        }}
        asyncio.run(self.svc._run_autopilot_flow())
        self.assertEqual(written, [0.8])
        self.assertEqual(self.svc._flow.phase, "wait-restore")
        self.assertTrue(self.svc._autopilot_slot.busy)
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "restore-before-release")
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 4, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.8, "event_seq": 4},
        }}
        asyncio.run(self.svc._run_autopilot_flow())
        self.assertEqual(self.svc._flow.phase, "done")
        self.assertFalse(self.svc._autopilot_slot.busy)
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "flow-restored")
