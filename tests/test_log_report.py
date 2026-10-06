import io, json, sys, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.log_report import analyze, render  # noqa: E402

H = "I MAKO Renderer: present diagnostics: "
FIXED = H + "operation=fixed-plan generated_per_real=1 observed_output_fps=90 generated_presented=100 generated_skipped=0 configured_adaptive_target_fps=90 target_applies=0 display_budget_hz=90"


def bundle(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def timeline(rows):
    return "\n".join(json.dumps(r) for r in rows) + "\n"


class ReportTests(unittest.TestCase):
    def rows(self, n=20, **extra):
        base = {"state": "LOCKED", "reason": "x", "target": 90, "real": 45, "output": 90, "point": "45x2", "tdp": 9,
                "snapshot": {"available": True}, "sensors": {"temp_c": 70}, "diagnosis": {"bottleneck": "gpu"}}
        return [{"t": float(i), **base, **extra} for i in range(n)]

    def test_healthy_log_reports_parsed_fps_and_no_problems(self):
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "diagnostics-x.log": (FIXED + "\n") * 30,
                              "overlay/active.conf": "fps\n", "self_test.json": "[]"}))
        self.assertEqual(rep["diagnostics"]["fps_samples"], 30)
        self.assertEqual(rep["diagnostics"]["real_median"], 45)
        self.assertEqual(rep["target"], 90)
        self.assertEqual(rep["findings"][0].split(" against")[0], "Median output FPS 90")
        text = render(rep)
        self.assertIn("GFG Extreme log summary", text)

    def test_missing_diagnostics_and_failed_checks_are_called_out(self):
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows(state="PAUSED", reason="diagnostics-active-no-events",
                                                                    snapshot={"available": False}, output=None)),
                              "self_test.json": json.dumps([{"check": "overlay config published (active.conf)", "ok": False, "detail": "/x"}])}))
        joined = "\n".join(rep["findings"])
        self.assertIn("No renderer diagnostics", joined)
        self.assertIn("overlay config published", joined)
        self.assertIn("PAUSED for 20 of 20", joined)
        self.assertIn("never published", joined)

    def test_empty_timeline_is_reported(self):
        rep = analyze(bundle({"README.txt": "x"}))
        self.assertTrue(any("timeline is empty" in f for f in rep["findings"]))

    def test_lines_without_fps_are_distinguished_from_no_lines(self):
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()),
                              "diagnostics-x.log": (H + "operation=present-breakdown total_ms=5\n") * 5}))
        self.assertTrue(any("none carried an FPS reading" in f for f in rep["findings"]))


if __name__ == "__main__":
    unittest.main()
