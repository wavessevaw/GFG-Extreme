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


if __name__ == "__main__":
    unittest.main()
