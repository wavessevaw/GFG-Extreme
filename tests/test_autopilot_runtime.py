"""Real parser/cache integration with synthetic renderer logs; no device claims."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.autopilot.adapters import ObservationMonitor
from gfg_plugin.autopilot.observation import ObservationStream
from gfg_plugin.governor_telemetry import TelemetryObserver
from gfg_plugin.host_sensors import HostSensors

HEADER = "I MAKO Renderer: present diagnostics: "


def line(fields):
    return HEADER + " ".join(f"{k}={v}" for k, v in fields.items())


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.stream = ObservationStream()
        self.monitor = ObservationMonitor()
        self.args = dict(generation=1, profile="game", backend="gfg",
                         launch={"running": True, "launch_key": [12, 345, 100], "renderer_loaded": True},
                         target=90, focus=True, runtime_state="LOCKED")
        self.update(100)

    def update(self, now, **overrides):
        args = dict(self.args, launch_at=now, focus_at=now,
                    sensors={"sample_monotonic": now, "sample_seq": int(now),
                             "gpu_busy_pct": 50, "cpu_top_core_pct": 50})
        args.update(overrides)
        self.monitor.update(now=now, stream=self.stream, **args)
        return self.monitor.status(now)

    def feed(self, now, seq, output="90"):
        self.stream.consume({"operation": "adaptive-plan", "context": "r",
                             "current_base_fps": "45", "current_output_fps": output}, now, seq)

    def prime(self):
        self.feed(100, 1)
        self.update(100)
        for i in range(1, 6):
            self.feed(100+i*2, i+1)
            self.update(100+i*2)
        return self.monitor.status(110)

    def test_parser_replay_preserves_raw_measurement_provenance(self):
        observer = TelemetryObserver(Path("/unused"))
        for case in json.loads((ROOT / "tests/fixtures/autopilot_observation.json").read_text()):
            with self.subTest(case=case["name"]):
                observer.consume_line(line(case["fields"]), now=100)
                sample = observer.autopilot_observations.samples[-1]
                self.assertEqual((sample.real_fps, sample.output_fps), (case["real"], case["output"]))

    def test_polling_cache_does_not_add_evidence_or_refresh_age(self):
        self.assertEqual(self.prime()["perception"]["primary"], "STABLE")
        for _ in range(30):
            self.assertEqual(self.update(110)["sample_count"], 5)
        self.assertIsNone(self.monitor.status(114)["output_fps"])
        self.assertTrue(self.monitor.status(114)["perception"]["stale"])

    def test_zero_remains_zero_in_rpc_projection(self):
        self.prime()
        self.feed(111, 20, "0")
        self.assertEqual(self.update(111)["output_fps"], 0)
        self.assertEqual(self.monitor.status(111)["action"], "OBSERVE")
        self.assertFalse(self.monitor.status(111)["control_enabled"])

    def test_session_pid_reuse_profile_hz_generation_backend_invalidate(self):
        for change in ({"launch": {"running": True, "launch_key": [12, 999, 100], "renderer_loaded": True}},
                       {"profile": "other"}, {"target": 60}, {"generation": 2}, {"backend": "optiscaler"},
                       {"backend": "native"}, {"launch": {"running": False}}):
            with self.subTest(change=change):
                self.setUp()
                self.prime()
                result = self.update(110, **change)
                self.assertEqual(result["sample_count"], 0)
                self.assertIsNone(result["output_fps"])

    def test_menu_suspend_restore_sensor_failure_and_stale_focus(self):
        for change in ({"focus": False}, {"focus_at": 90}, {"restore_pending": True},
                       {"runtime_state": "PAUSED"}, {"poll_error": "read failed"}):
            self.setUp()
            self.prime()
            self.assertEqual(self.update(110, **change)["sample_count"], 0)
        self.setUp()
        self.prime()
        self.assertEqual(self.update(130)["sample_count"], 0)
        self.assertEqual(self.update(130, sensors={})["perception"]["primary"], "UNKNOWN")

    def test_profile_projection_does_not_leak_other_game(self):
        self.prime()
        value = self.monitor.status(110, "other")
        self.assertIsNone(value["output_fps"])
        self.assertEqual(value["perception"]["reason"], "profile-not-active")

    def test_backlog_and_spatial_events_do_not_create_independent_window(self):
        self.feed(100, 1)
        self.update(100)
        for seq in range(2, 50):
            self.feed(102, seq)
        self.assertEqual(self.update(102)["sample_count"], 1)
        self.stream.consume({"operation": "adaptive-plan", "role": "spatial", "context": "other",
                             "current_base_fps": "500", "current_output_fps": "500"}, 103, 50)
        self.assertEqual(self.stream.context, "r")
        self.assertEqual(len(self.stream.samples), 49)

    def test_single_focus_transition_remains_valid_within_continuous_session(self):
        self.feed(100, 1)
        self.update(100, focus_at=100)
        for i in range(1, 9):
            self.feed(100+i*2, i+1)
            result = self.update(100+i*2, focus_at=100)
        self.assertEqual(result["perception"]["primary"], "STABLE")
        self.assertEqual(self.update(140, focus_at=100)["sample_count"], 0)

    def test_focus_received_before_monitor_in_same_iteration_is_valid(self):
        self.feed(100, 1)
        self.update(100.01, focus_at=100)
        for i in range(1, 9):
            self.feed(100+i*2, i+1)
            result = self.update(100+i*2+.01, focus_at=100)
        self.assertEqual(result["perception"]["primary"], "STABLE")
        self.assertEqual(self.update(150, focus_at=100)["sample_count"], 0)

    def test_real_poll_uses_one_receipt_timestamp_for_a_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "renderer.log"
            path.write_text("")
            tick = [100.0]
            def clock():
                tick[0] += .001
                return tick[0]
            observer = TelemetryObserver(path, time_fn=clock)
            observer.poll()
            event = line({"operation": "adaptive-plan", "context": "r",
                          "current_base_fps": "45", "current_output_fps": "90"}) + "\n"
            with path.open("a") as handle:
                handle.write(event * 8)
            observer.poll()
            times = {s.timestamp_mono for s in observer.autopilot_observations.samples}
            self.assertEqual(len(times), 1)
            self.assertEqual(len(observer.autopilot_observations.samples), 8)

    def test_bounded_stream_and_reset(self):
        for i in range(200):
            self.feed(i, i+1)
            self.stream.consume({"operation": "generated-delivery-miss", "context": "r"}, i, i+1)
        self.assertLessEqual(len(self.stream.samples), 64)
        self.assertLessEqual(len(self.stream.pressure), 64)
        self.stream.reset()
        self.assertEqual(len(self.stream.samples), 0)

    def test_real_file_tailer_skips_backlog_and_resets_rotated_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "renderer.log"
            event = line({"operation": "adaptive-plan", "context": "r",
                          "current_base_fps": "30", "current_output_fps": "0"}) + "\n"
            path.write_text(event)
            observer = TelemetryObserver(path, time_fn=lambda: 100)
            observer.poll()
            self.assertFalse(observer.autopilot_observations.samples)
            with path.open("a") as handle:
                handle.write(event)
            observer.poll()
            self.assertEqual(observer.autopilot_observations.samples[-1].output_fps, 0)
            path.write_text("")
            observer.poll()
            self.assertFalse(observer.autopilot_observations.samples)

    def test_host_cache_preserves_acquisition_time_and_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clock = [100.0]
            sensors = HostSensors(hwmon_root=root, drm_root=root, power_supply_root=root,
                                  proc_stat=root / "missing", clock=lambda: clock[0])
            first = sensors.sample()
            clock[0] = 101.0
            cached = sensors.sample()
            self.assertEqual((cached["sample_monotonic"], cached["sample_seq"]), (100, 1))
            clock[0] = 102.0
            self.assertEqual(sensors.sample()["sample_seq"], 2)
            self.assertEqual(first["sample_monotonic"], 100)


class ServiceIntegrationTests(unittest.TestCase):
    def test_governor_status_observation_does_not_write_or_mutate_saved(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            svc._status.update(profile="game", state="LOCKED", observation_backend="gfg",
                               target_output_fps=90)
            svc._launch = dict(fixture.inspector.info)
            svc._launch_polled = fixture.t["now"]
            svc.observer.game_focused = True
            svc.observer.game_focused_at = fixture.t["now"]
            # Legacy get_status lazily initializes its scale_ignored_games map.
            svc.get_status("game")
            before_settings = json.dumps(svc._settings, sort_keys=True)
            with patch.object(svc.power, "set_tdp_w", side_effect=AssertionError("power write")), \
                 patch.object(svc.cpu, "restore", side_effect=AssertionError("CPU restore")), \
                 patch.object(svc, "_write_overlay_sync", side_effect=AssertionError("overlay write")):
                svc._update_autopilot_observation()
                value = svc.get_status("game")["autopilot_observation"]
                self.assertFalse(value["control_enabled"])
                self.assertEqual(value["action"], "OBSERVE")
                plan = svc.get_status("game")["autopilot_plan"]
                self.assertFalse(plan["armed"])
                self.assertFalse(plan["control_enabled"])
                svc._actuator_restore_errors["power"] = "readback mismatch"
                svc._update_autopilot_observation()
                self.assertEqual(svc.get_status("game")["autopilot_plan"]["action"], "RESTORE")
                self.assertFalse(svc._autopilot_slot.busy)
            self.assertEqual(json.dumps(svc._settings, sort_keys=True), before_settings)
            self.assertEqual(svc.MODES, ("budget", "balanced", "quality", "extreme"))
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
