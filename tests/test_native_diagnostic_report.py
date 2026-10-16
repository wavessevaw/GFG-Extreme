"""Diagnostic summaries must recognize the runtime's actual log messages."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("accept_report", ROOT / "scripts/accept_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class DiagnosticReportTests(unittest.TestCase):
    def test_runtime_retirement_counters_are_visible_without_smoke_test_output(self):
        text = report.render({
            "app.stderr.log":
                "[gfg-native] GPU bridge active: 1280x800 algo=lmc-gpu verify=0\n"
                "[gfg-native] GPU bridge retired real=30 synthetic=56 skipped=2 te_busy=1 "
                "ring_busy=0 acquire_not_ready=0 holds=1 errors=0 "
                "present_path_host_pixel_reads=0 present_path_cpu_waits=0 "
                "verify_checks=0 verify_distinct=0\n",
            "process-status.txt": "0\n",
        })
        for expected in ("real presents: 30", "synthetic presents: 56", "skipped outputs: 2",
                         "CPU waits on present path: 0", "Algorithm: **lmc-gpu**"):
            self.assertIn(expected, text)
        self.assertIn("Physical display / KMS scanout: **unobserved**", text)

    def test_smoke_counters_in_stdout_are_retained_as_fallback(self):
        text = report.render({"app.stdout.log":
            "GFG native: gpu stats bridges=1 sync_mode=3 real=8 synthetic=14 skipped=0 "
            "te_busy=0 ring_busy=0 errors=0\n"})
        self.assertIn("bridges: 1", text)
        self.assertIn("real presents: 8", text)
        self.assertIn("synthetic presents: 14", text)

    def test_recreated_swapchains_use_last_cumulative_snapshot_and_last_timings(self):
        text = report.render({"app.stderr.log":
            "[gfg-native] GPU bridge active: 1280x800 algo=lmc-gpu\n"
            "[gfg-native] GPU bridge retired real=1 synthetic=0 skipped=0 errors=0 "
            "present_path_host_pixel_reads=0 present_path_cpu_waits=0\n"
            "[gfg-native] gpu-bridge present_cpu frames=3 total_median_us=25.3 total_p95_us=25.3 "
            "layer_own_median_us=0.5 layer_own_p95_us=0.5\n"
            "[gfg-native] GPU bridge retired real=3503 synthetic=0 skipped=6996 errors=0 "
            "present_path_host_pixel_reads=0 present_path_cpu_waits=0\n"
            "[gfg-native] gpu-bridge present_cpu frames=3493 total_median_us=26.1 total_p95_us=48.0 "
            "layer_own_median_us=0.6 layer_own_p95_us=1.3\n"})
        self.assertIn("real presents: 3503", text)
        self.assertIn("skipped outputs: 6996", text)
        self.assertIn("Samples: 3493", text)
        self.assertIn("26.1 / 48.0", text)
        self.assertIn("no — zero generated outputs", text)
        self.assertIn("CPU passthrough timings do not measure generation cost", text)

    def test_initialization_and_monitor_start_do_not_prove_generation_or_completion(self):
        text = report.render({"app.stderr.log":
            "[gfg-native] GPU bridge active: 1280x800 algo=lmc-gpu\n"
            "[gfg-native] present-ids mode=2 monitor=1\n"
            "[gfg-native] fg_bypass reason=unsupported-present-metadata pid=1 pnext_types=[1000000000]\n"})
        self.assertIn("initialized in captured log: **yes**", text)
        self.assertIn("unsupported-present-metadata", text)
        self.assertIn("a monitor may have started without receiving IDs", text)
        self.assertNotIn("Synthetic WSI handoffs observed: **yes**", text)

    def test_device_generation_reports_backpressure_without_inventing_gpu_or_display_fps(self):
        text = report.render({"app.stderr.log":
            "[gfg-native] GPU bridge active: 1280x800 algo=lmc-gpu\n"
            "[gfg-native] present-ids policy=application-owned synthetic_ids=omitted monitor=0\n"
            "[gfg-native] GPU bridge retired real=3806 synthetic=3080 skipped=4522 "
            "te_busy=0 ring_busy=911 acquire_not_ready=1202 holds=468 errors=0 "
            "present_path_host_pixel_reads=0 present_path_cpu_waits=0\n"})
        for value in ("API handoffs per real present: 1.809× (not displayed FPS)",
                      "ring busy: 911", "image acquire not ready: 1202", "history holds including initialization: 468",
                      "GPU timestamp samples unavailable", "Application owns present IDs"):
            self.assertIn(value, text)
        self.assertNotIn("a monitor may have started", text)

    def test_gpu_elapsed_and_loss_scope_remain_separate_from_process_and_cpu_totals(self):
        text = report.render({"app.stderr.log":
            "[gfg-native] gpu-bridge skipped_outputs ring=2 te=4 history=2 acquire=1 bypass=0 error=0 "
            "ring_reclaimed=3 pid=1 bridge_frames=12\n"
            "[gfg-native] gpu-bridge gpu_elapsed samples=8 held_samples=2 output1_median_ms=4.200 "
            "output1_p95_ms=5.000 output2_median_ms=6.100 output2_p95_ms=8.000 scope=analysis-start-to-output-ready pid=1\n"
            "[gfg-native] gpu-bridge gpu_lmc_mean_ms stage=model ms=0.400 samples=8\n"})
        for value in ("per bridge, not process totals", "history restart after a gap: 2",
                      "selecting another free slot: 3", "Completed generated-pair samples: 8",
                      "4.200 / 5.000 ms", "6.100 / 8.000 ms", "model: 0.400 ms",
                      "transport copies and physical scanout are outside"):
            self.assertIn(value, text)
        self.assertNotIn("GPU timestamp samples unavailable", text)

    def test_later_unavailable_gpu_record_does_not_reuse_an_earlier_bridge_sample(self):
        text = report.render({"app.stderr.log":
            "gpu-bridge gpu_elapsed samples=8 held_samples=2 output1_median_ms=4.200 "
            "output1_p95_ms=5.000 output2_median_ms=6.100 output2_p95_ms=8.000\n"
            "gpu-bridge gpu_elapsed samples=0 unavailable=1\n"})
        self.assertIn("GPU timestamp samples unavailable", text)
        self.assertNotIn("4.200", text)


if __name__ == "__main__":
    unittest.main()
