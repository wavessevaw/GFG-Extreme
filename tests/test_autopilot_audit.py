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
