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
             patch.object(self.svc, "_sync_flow", new=AsyncMock(side_effect=AssertionError("flow write"))):
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

    def test_context_change_does_not_drop_the_scale_before_ack(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("old",)
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc.overlay = object()
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 0.8}
        self.svc._base_for = lambda profile, saved: {}
        written = []

        def write(profile, config, key):
            written.append(config.get("flow_scale"))

        self.svc._write_overlay_sync = write
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 3, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.7, "event_seq": 3},
        }}
        asyncio.run(self.svc._sync_flow("game"))
        self.assertEqual(written, [0.8])
        self.assertEqual(self.svc._flow.phase, "wait-restore")
        self.assertEqual(self.svc._flow.context, ("old",))
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 4, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.8, "event_seq": 4},
        }}
        asyncio.run(self.svc._sync_flow("game"))
        self.assertFalse(self.svc._flow.change_outstanding())
        self.assertNotIn(0.7, written)

    def test_a_profile_switch_restores_the_old_overlay_instead_of_waiting_for_an_unreachable_ack(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game-a", "balanced", "point")
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        saved = {"game-a": {"flow_scale": 0.8}, "game-b": {"flow_scale": 1.0}}
        self.svc._saved_profile_config = lambda profile: saved[profile]
        self.svc._base_for = lambda profile, config: {"flow_scale": config["flow_scale"]}
        ensured = []

        class Overlay:
            def exists(self, profile):
                return True

            def ensure(self, profile, config, point_key="base"):
                ensured.append((profile, config.get("flow_scale"), point_key))

        self.svc.overlay = Overlay()
        self.svc._status["telemetry"] = {"snapshot": {"event_seq": 2, "latest": {}, "flow": {}}}
        asyncio.run(self.svc._sync_flow("game-b"))
        self.assertEqual(ensured, [("game-a", 0.8, "base")])
        self.assertNotEqual(self.svc._flow.phase, "wait-restore")
        self.assertFalse(self.svc._flow.change_outstanding())
        self.assertNotIn("game-a", self.svc._restore_pending)

    def test_a_missing_saved_profile_keeps_the_overlay_restore_barrier(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game-a", "balanced", "point")
        self.svc._point = {"key": "new", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {"flow_scale": 0.7}
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 1.0} if profile == "game-b" else None
        self.svc._base_for = lambda profile, config: {"flow_scale": config["flow_scale"]}

        class Overlay:
            def exists(self, profile):
                return True

            def ensure(self, profile, config, point_key="base"):
                raise AssertionError("missing Saved profile must not be written")

        self.svc.overlay = Overlay()
        self.svc._status["telemetry"] = {"snapshot": {"event_seq": 2, "latest": {}, "flow": {}}}
        asyncio.run(self.svc._sync_flow("game-b"))
        self.assertEqual(self.svc._restore_pending.get("game-a"), "profile-changed")
        self.assertEqual(self.svc._status["flow_control"]["reason"], "restore-not-confirmed")

    def test_the_second_flag_restores_a_dirty_flow_before_it_holds(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._autopilot_flow_enabled = True
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game",)
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc._status["profile"] = "game"
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 0.8}
        self.svc._base_for = lambda profile, saved: {}
        written = []
        self.svc._write_overlay_sync = lambda profile, config, key: written.append(config.get("flow_scale"))
        self.svc.overlay = object()
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 3, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.7, "event_seq": 3},
        }}
        self.svc._autopilot_slot.start(Knob.FLOW_SCALE, self.fixture.t["now"])
        self.svc._autopilot_power_enabled = True
        asyncio.run(self.svc._run_autopilot_exclusive())
        self.assertEqual(written, [0.8])
        self.assertTrue(self.svc._autopilot_flow_dirty())
        self.assertNotEqual(self.svc._status["autopilot_flow"]["reason"], "two-tools-requested")
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 4, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.8, "event_seq": 4},
        }}
        asyncio.run(self.svc._run_autopilot_exclusive())
        self.assertFalse(self.svc._autopilot_flow_dirty())
        self.assertEqual(self.svc._status["autopilot_flow"]["reason"], "two-tools-requested")

    def test_disabling_the_flag_keeps_reading_until_the_saved_scale_is_confirmed(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._autopilot_flow_enabled = False
        self.svc._autopilot_power_enabled = False
        self.svc._active_profile = "game"
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game",)
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc._status["profile"] = "game"
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 0.8}
        self.svc._base_for = lambda profile, saved: {}
        self.svc._write_overlay_sync = lambda profile, config, key: None
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 3, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.7, "event_seq": 3},
        }}
        shots = [
            {"event_seq": 3, "latest": {"context": "game"},
             "flow": {"context": "game", "value": 0.7, "event_seq": 3}},
            {"event_seq": 4, "latest": {"context": "game"},
             "flow": {"context": "game", "value": 0.8, "event_seq": 4}},
        ]
        polls = {"n": 0}
        real_poll = self.svc.observer.poll
        real_snapshot = self.svc.observer.snapshot

        def poll():
            polls["n"] += 1
            if polls["n"] > 2:
                return real_poll()

        def snapshot():
            if polls["n"] > 2:
                return real_snapshot()
            return shots[0 if polls["n"] <= 1 else 1]

        self.svc.observer.poll = poll
        self.svc.observer.snapshot = snapshot
        asyncio.run(self.svc._iteration_core())
        self.assertEqual(polls["n"], 1)
        self.assertTrue(self.svc._autopilot_flow_dirty())
        self.assertTrue(self.svc._autopilot_must_finish_first())
        asyncio.run(self.svc._iteration_core())
        self.assertGreaterEqual(polls["n"], 2)
        self.assertFalse(self.svc._autopilot_flow_dirty())
        self.assertFalse(self.svc._autopilot_must_finish_first())

    def test_switching_from_flow_to_power_does_not_apply_both(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._autopilot_flow_enabled = False
        self.svc._autopilot_power_enabled = True
        self.svc._active_profile = "game"
        self.svc._status["profile"] = "game"
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game",)
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc._saved_profile_config = lambda profile: {"flow_scale": 0.8}
        self.svc._base_for = lambda profile, saved: {}
        written = []
        self.svc._write_overlay_sync = lambda profile, config, key: written.append(config.get("flow_scale"))
        self.svc.overlay = object()
        self.svc.power.claim()
        self.svc.power.values.update(observed_tdp_w=10, ceiling_tdp_w=15, owned=True)
        self.svc._status["telemetry"] = {"snapshot": {
            "event_seq": 3, "latest": {"context": "game"},
            "flow": {"context": "game", "value": 0.7, "event_seq": 3},
        }}
        asyncio.run(self.svc._run_autopilot_exclusive())
        self.assertEqual(written, [0.8])
        self.assertEqual(self.svc.power.writes, [])
        self.assertTrue(self.svc._autopilot_flow_dirty())

    def test_a_new_game_does_not_wait_for_the_ended_renderer_ack(self):
        from gfg_plugin.governor_flow import FlowTrial
        self.svc._autopilot_flow_enabled = True
        self.svc._active_profile = "game"
        self.svc._flow = FlowTrial()
        self.svc._flow.original = 0.8
        self.svc._flow.wanted = 0.7
        self.svc._flow.phase = "b"
        self.svc._flow.context = ("game",)
        self.svc._point = {"key": "x", "base_target_fps": 45, "multiplier": 2}
        self.svc._point_deltas = {}
        self.svc._generation_seen = 1
        self.svc._launch_key = [1, 1, 1]
        self.svc.observer._session_generation = 2
        self.svc.inspector.info["launch_key"] = [9, 9, 9]
        self.svc._launch = None
        self.svc._launch_polled = -1e9
        asyncio.run(self.svc._poll_autopilot_observation("game"))
        self.assertNotEqual(self.svc._flow.phase, "wait-restore")
        self.assertFalse(self.svc._autopilot_flow_dirty())
        self.assertEqual(list(self.svc._launch_key), [9, 9, 9])
