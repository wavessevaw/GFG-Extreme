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
    def test_own_truncation_keeps_the_session(self):
        """Audit 1.0.7: the size cap truncated the log and the shrink looked like a new game."""
        line = diag("fixed-plan", generated_per_real=2, observed_output_fps=90, generated_presented=10,
                    generated_skipped=0, configured_adaptive_target_fps=90, display_budget_hz=90) + "\n"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "diag.log"
            path.write_text("")
            observer = TelemetryObserver(path)
            observer.poll()
            with path.open("a") as handle:
                handle.write(line * 5)
            observer.poll()
            generation, samples = observer.session_generation, observer.sample_seq
            self.assertEqual(samples, 5)
            path.write_text("")                       # the service's size cap
            observer.rewind_after_truncation()
            with path.open("a") as handle:
                handle.write(line * 3)
            observer.poll()
            self.assertEqual(observer.session_generation, generation)
            self.assertEqual(observer.sample_seq, samples + 3)

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

class GeneratedCapacityTests(unittest.TestCase):
    """Lines from a field log."""

    APPLIED = ("MAKO Renderer: present diagnostics: operation=runtime-state-applied context=19104014532612 "
               "role=frame-generation state_revision=23 transition=live frame_generation_enabled=1 adaptive=0 "
               "target_fps=90 multiplier=3 base_fps_cap=28 adaptive_max_multiplier=4 "
               "frame_generation_resources_available=1 generated_frame_capacity=2 hdr=0")
    PENDING = ("MAKO Renderer: present diagnostics: operation=runtime-transition-pending context=19104014532612 "
               "role=frame-generation state_revision=23 reason=profile-resources generated_capacity_pending=1 "
               "available_generated_capacity=2 available_wsi_generated_capacity=2 requested_generated_capacity=3 "
               "process_restart_required=0 action=wait-for-natural-swapchain-recreation")

    def test_capacity_from_applied_and_pending_lines(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        self.assertIsNone(observer.current_max_multiplier)
        observer.consume_line(self.PENDING, now=1.0)
        self.assertEqual((observer.generated_capacity, observer.current_max_multiplier), (2, 3.0))
        observer.consume_line(self.APPLIED.replace("generated_frame_capacity=2", "generated_frame_capacity=3"), now=2.0)
        self.assertEqual(observer.current_max_multiplier, 4.0)
        self.assertEqual(observer.snapshot(now=2.0)["generated_capacity"], 3)

    def test_capacity_is_current_and_can_go_down_to_zero(self):
        """PR #37 review: 0 is a valid report (native only) and must replace a higher value."""
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(self.APPLIED, now=1.0)
        self.assertEqual(observer.current_max_multiplier, 3.0)
        observer.consume_line(self.APPLIED.replace("generated_frame_capacity=2", "generated_frame_capacity=0"), now=2.0)
        self.assertEqual(observer.current_max_multiplier, 1.0)

    def test_no_frame_generation_resources_means_native_only(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(self.APPLIED, now=1.0)
        observer.consume_line(self.APPLIED.replace("frame_generation_resources_available=1",
                                                   "frame_generation_resources_available=0"), now=2.0)
        self.assertEqual((observer.generated_capacity, observer.current_max_multiplier), (0, 1.0))



class LayerRoleIsolationTests(unittest.TestCase):
    def test_spatial_resource_messages_do_not_disable_generation_or_replace_application(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(GeneratedCapacityTests.APPLIED.replace("generated_frame_capacity=2", "generated_frame_capacity=3"), now=1)
        before = observer.snapshot(now=1)["last_application"]
        for operation in ("runtime-state-applied", "runtime-transition-pending"):
            observer.consume_line("MAKO Renderer: present diagnostics: "
                                  f"operation={operation} role=spatial context=0xcc "
                                  "frame_generation_resources_available=0 generated_frame_capacity=0 "
                                  "available_generated_capacity=0", now=2)
            self.assertEqual(observer.current_max_multiplier, 4)
            application = observer.snapshot(now=2)["last_application"]
            self.assertEqual(application["event_seq"], before["event_seq"])
            self.assertEqual(application["fields"], before["fields"])

    def test_spatial_rates_do_not_pollute_real_or_output_fps(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        line = ("MAKO Renderer: present diagnostics: operation=fixed-plan "
                "observed_output_fps=90 generated_per_real=2")
        observer.consume_line(line + " role=frame-generation", now=1)
        before = observer.sample_seq
        self.assertIsNone(observer.consume_line(line.replace("observed_output_fps=90", "observed_output_fps=15") + " role=spatial", now=2))
        self.assertEqual(observer.sample_seq, before)
        snapshot = observer.snapshot(now=2)
        self.assertEqual(snapshot["latest"]["real_fps"], 30)
        self.assertEqual(snapshot["latest"]["output_fps"], 90)

    def test_legacy_roleless_capacity_remains_supported(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        observer.consume_line(GeneratedCapacityTests.APPLIED.replace("role=frame-generation ", ""), now=1)
        self.assertEqual(observer.current_max_multiplier, 3)


class DeliveryEvidenceTests(unittest.TestCase):
    def test_measured_zero_output_is_not_replaced_with_ninety_fps_plan(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(diag("adaptive-plan", current_base_fps=30,
            generated=2, observed_output_fps=0, source_interval_mean_ms=33.333,
            requested_interval_mean_ms=11.111), now=1)
        self.assertEqual(sample.output_source, "measured")
        self.assertEqual(sample.output_fps, 0)
        self.assertEqual(observer.summary(now=1)["output"]["median"], 0)
        self.assertAlmostEqual(sample.real_fps, 30, places=2)

    def test_explicit_zero_with_real_cadence_remains_a_fresh_shortfall(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        sample = observer.consume_line(diag("fixed-plan", current_base_fps=30,
                                           generated=2, observed_output_fps=0), now=1)
        self.assertEqual(sample.real_fps, 30)
        self.assertEqual(sample.output_fps, 0)
        self.assertEqual(observer.sample_seq, 1)

    def test_plan_only_samples_do_not_enter_a_decision_window(self):
        observer = TelemetryObserver(Path("/nonexistent"))
        for index in range(8):
            observer.consume_line(diag("adaptive-plan", current_base_fps=30, generated=2), now=float(index))
        planned = observer.summary(20, now=8)
        self.assertEqual(planned["samples"], 0)
        self.assertEqual(planned["plan_samples"], 8)
        self.assertIsNone(planned["output"]["median"])
        self.assertIsNone(planned["real"]["median"])
        self.assertIsNone(planned["last_sample_seq"])
        observer.consume_line(diag("adaptive-plan", current_base_fps=30, current_output_fps=60, generated=2), now=9)
        mixed = observer.summary(20, now=9)
        self.assertEqual(mixed["samples"], 1)
        self.assertEqual(mixed["plan_samples"], 8)
        self.assertEqual(mixed["output"]["median"], 60)
        self.assertEqual(mixed["real"]["median"], 30)
