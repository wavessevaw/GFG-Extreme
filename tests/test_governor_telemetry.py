import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_telemetry import TelemetryObserver


def diag(operation="adaptive-ramp", **fields):
    body = " ".join([f"operation={operation}"] + [f"{k}={v}" for k, v in fields.items()])
    return f"I MAKO Renderer: present diagnostics: {body}"


class GovernorTelemetryTests(unittest.TestCase):
    def test_direct_measured_fps_has_priority(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(diag(current_base_fps=45, current_output_fps=90), now=1.0)
        self.assertAlmostEqual(sample.real_fps, 45)
        self.assertAlmostEqual(sample.output_fps, 90)
        self.assertAlmostEqual(sample.effective_multiplier, 2)
        self.assertEqual(sample.output_source, "measured")

    def test_scheduler_interval_yields_real_and_output(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(diag(source_interval_mean_ms=22.2222, requested_interval_mean_ms=11.1111), now=2.0)
        self.assertAlmostEqual(sample.real_fps, 45.0, places=1)
        self.assertAlmostEqual(sample.output_fps, 90.0, places=1)
        self.assertAlmostEqual(sample.effective_multiplier, 2.0, places=1)

    def test_fixed_plan_derives_real_fps_from_output_and_ratio(self):
        # Renderer v4 fixed-plan has no base-FPS field. Regression: Beta.2
        # discarded these lines, so fixed 2x/3x never produced any evidence.
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(
            diag("fixed-plan", generated_per_real=2, observed_output_fps=89.7,
                 generated_presented=120, generated_skipped=0,
                 configured_adaptive_target_fps=90, display_budget_hz=90),
            now=1.0,
        )
        self.assertIsNotNone(sample)
        self.assertAlmostEqual(sample.real_fps, 29.9, places=2)
        self.assertAlmostEqual(sample.output_fps, 89.7, places=2)
        self.assertAlmostEqual(sample.effective_multiplier, 3.0, places=2)
        self.assertEqual(sample.output_source, "measured")

    def test_present_breakdown_is_timing_only_and_yields_no_fps(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(
            diag("present-breakdown", total_ms=11.1, render_fence_ms=3.0, schedule_ms=0.2),
            now=1.0,
        )
        self.assertIsNone(sample)
        self.assertEqual(observer.event_seq, 1)
        self.assertEqual(observer.sample_seq, 0)

    def test_fixed_plan_without_positive_output_is_not_evidence(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        self.assertIsNone(observer.consume_line(
            diag("fixed-plan", generated_per_real=2, observed_output_fps=0), now=1.0))

    def test_pressure_events_are_counted(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(diag("generated-delivery-miss"), now=10.0)
        observer.consume_line(diag("pipeline-busy-bypass"), now=10.1)
        observer.consume_line(diag(current_base_fps=45, current_output_fps=90), now=10.2)
        summary = observer.summary(window_seconds=2, now=11.0)
        self.assertEqual(summary["hard_pressure"], 1)
        self.assertEqual(summary["misses"], 1)
        self.assertEqual(summary["bypasses"], 1)

    def test_first_poll_skips_historical_backlog(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "diag.log"
            path.write_text(diag(current_base_fps=45, current_output_fps=90) + "\n", encoding="utf-8")
            observer = TelemetryObserver(path)
            observer.poll()
            self.assertEqual(observer.sample_seq, 0)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(diag(current_base_fps=46, current_output_fps=90) + "\n")
            observer.poll()
            self.assertEqual(observer.sample_seq, 1)

    def test_after_seq_prevents_cached_sample_counting_as_fresh(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(diag(current_base_fps=45, current_output_fps=90), now=1.0)
        seq = observer.sample_seq
        self.assertEqual(observer.summary(window_seconds=10, after_seq=seq, now=2.0)["samples"], 0)
