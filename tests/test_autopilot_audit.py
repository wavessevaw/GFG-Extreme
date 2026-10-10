"""Audit logging regression tests. Synthetic data only, no Steam Deck hardware."""
import asyncio
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.autopilot.trace import AutopilotTrace
from gfg_plugin.session_recorder import SessionRecorder, compact_status


class AuditTraceTests(unittest.TestCase):
    def test_structured_trace_is_jsonl_bounded_to_serializable_finite_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime" / "autopilot-trace.jsonl"
            trace = AutopilotTrace(path, clock=lambda: 10.0, monotonic=lambda: 2.0)
            trace.write("observation", seq=7, fps=42.0, invalid=float("nan"),
                        reasons=["fresh", "stable"], unknown=object())
            entry = json.loads(path.read_text().strip())
            self.assertEqual(entry["schema"], 1)
            self.assertEqual((entry["ts"], entry["mono"]), (10, 2))
            self.assertEqual((entry["seq"], entry["fps"], entry["invalid"]), (7, 42.0, None))
            self.assertEqual(entry["unknown"], "object")
            self.assertEqual(trace.failures, 0)

    def test_timeline_contains_decision_actuator_and_ack_state(self):
        status = {
            "autopilot_observation": {"real_fps": 45, "output_fps": 90, "sample_count": 5},
            "autopilot_plan": {"action": "TRIAL", "reason": "power-limited"},
            "autopilot_power": {"requested_w": 11, "observed_w": 11, "reason": "ack"},
            "autopilot_flow": {"phase": "wait-restore"},
            "autopilot_debug": {"scheduler_phase": "test-b", "last_renderer_seq": 91},
        }
        snap = compact_status(status)["autopilot"]
        self.assertEqual(snap["observation"]["real_fps"], 45)
        self.assertEqual(snap["decision"]["action"], "TRIAL")
        self.assertEqual(snap["power"]["observed_w"], 11)
        self.assertEqual(snap["flow"]["phase"], "wait-restore")
        self.assertEqual(snap["debug"]["last_renderer_seq"], 91)

    def test_live_governor_observation_reaches_trace_without_enabling_flags(self):
        import test_governor_runtime as legacy
        fixture = legacy.RuntimeBase()
        fixture.setUp()
        try:
            svc = fixture.svc
            self.assertFalse(svc._autopilot_power_enabled)
            self.assertFalse(svc._autopilot_flow_enabled)
            svc._update_autopilot_observation()
            path = svc.autopilot_trace_path
            self.assertTrue(path.is_file())
            entries = [json.loads(line) for line in path.read_text().splitlines()]
            events = [item for item in entries if item.get("event") == "observation"]
            self.assertTrue(events)
            self.assertIn("perception", events[-1])
            self.assertIn("source", events[-1])
            self.assertIn("watts", events[-1])
            self.assertIn("scheduler", events[-1])
            self.assertEqual(events[-1]["enabled"], {"power": False, "flow": False})
        finally:
            fixture.tearDown()

    def test_second_deck_log_schema_is_output_only_not_measured_real_fps(self):
        """Field 1.7.1: base_fps is ambiguous; do not quietly turn it into C1 evidence."""
        from gfg_plugin.autopilot.observation import ObservationStream
        stream = ObservationStream()
        stream.consume({
            "operation": "fixed-plan", "context": "sanitized-frame-stream",
            "base_fps": "29.9983", "multiplier": "3",
            "generated_per_real": "2", "observed_output_fps": "82.9954",
        }, 100.0, 100)
        sample = stream.samples[-1]
        self.assertIsNone(sample.real_fps)
        self.assertAlmostEqual(sample.output_fps, 82.9954)
        self.assertEqual(sample.seq, 100)

        stream.consume({
            "operation": "adaptive-plan", "context": "sanitized-frame-stream",
            "base_fps": "29.9888", "target_fps": "90", "generated": "2",
        }, 101.0, 101)
        sample = stream.samples[-1]
        self.assertIsNone(sample.real_fps)
        self.assertIsNone(sample.output_fps)
        self.assertEqual(sample.seq, 101)

        stream.consume({
            "operation": "fixed-plan", "context": "sanitized-frame-stream",
            "measured_base_fps": "30.0", "observed_output_fps": "88.5",
        }, 102.0, 102)
        sample = stream.samples[-1]
        self.assertEqual((sample.real_fps, sample.output_fps), (30.0, 88.5))
        self.assertEqual(sample.seq, 102)

    def test_session_recorder_exports_only_trace_from_the_recording(self):
        async def run(tmp):
            home = Path(tmp) / "home"
            config = Path(tmp) / "config"
            runtime = Path(tmp) / "runtime"
            config.mkdir()
            runtime.mkdir()
            path = runtime / "autopilot-trace.jsonl"
            trace = AutopilotTrace(path, clock=lambda: 100.0, monotonic=lambda: 1.0)
            trace.write("before", seq=1)
            recorder = SessionRecorder(
                user_home=home, config_dir=config, runtime_state_dir=runtime,
                wrapper_path=config / "wrapper.sh", status_provider=lambda: {},
                events_path=runtime / "governor-events.jsonl",
                diagnostics_paths=[], saved_config_path=config / "profile.json",
                layer_files={}, autopilot_trace_path=path,
                clock=lambda: 100.0, process_probe=lambda: [], power_probe=lambda: [],
            )
            recorder.self_test = lambda: []
            recorder._system_info = lambda: {"device_verified": False}
            started = await recorder.start("synthetic-game")
            self.assertTrue(started["success"])
            await asyncio.sleep(0)  # let the initial 1 Hz sample be captured
            trace.write("during", seq=2, phase="restore-a")
            ended = await recorder.stop()
            self.assertTrue(ended["success"], ended)
            with zipfile.ZipFile(ended["file"]) as output:
                lines = output.read("autopilot-trace.jsonl").decode().splitlines()
                self.assertEqual(len(lines), 1)
                self.assertEqual(json.loads(lines[0])["event"], "during")
                meta = json.loads(output.read("autopilot-trace-meta.json"))
                self.assertTrue(meta["available"])
                self.assertEqual(meta["bytes"], len((lines[0] + "\n").encode()))
                self.assertIn("autopilot", output.read("timeline.jsonl").decode())

        # A same-event-loop Start/Stop is required by the sampler task.
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run(tmp))


if __name__ == "__main__":
    unittest.main()
