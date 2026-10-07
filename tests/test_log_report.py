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

    def test_overlay_burst_before_game_exit_is_reported(self):
        act = [{"ts": 100.0 + i, "kind": "set_governor_hud"} for i in range(6)] + [{"ts": 120.0, "kind": "game-exited"}]
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "activity.jsonl": timeline(act)}))
        self.assertEqual(rep["overlay_burst_before_exit"], 6)
        self.assertTrue(any("6 in-game overlay changes" in f for f in rep["findings"]))

    def test_renderer_capacity_fallback_is_reported(self):
        pending = (H + "operation=runtime-transition-pending state_revision=23 generated_capacity_pending=1 "
                   "available_generated_capacity=2 requested_generated_capacity=3\n")
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "diagnostics-x.log": pending * 3}))
        self.assertEqual(rep["diagnostics"]["capacity_waits"], 3)
        self.assertTrue(any("at most x3" in f for f in rep["findings"]))

    def test_time_waiting_for_confirmation_and_mode_switches_are_reported(self):
        rows = self.rows(10) + self.rows(10, state="APPLY", reason="awaiting-fresh-evidence")
        events = [{"event": "operating-point-rejected", "reason": "confirmation-timeout", "point": "36x2.5"},
                  {"event": "operating-point-released", "reason": "governor-mode-changed"}]
        rep = analyze(bundle({"timeline.jsonl": timeline(rows), "governor-events.jsonl": timeline(events)}))
        self.assertEqual(rep["apply_share"], 0.5)
        self.assertEqual(rep["mode_switches"], 1)
        joined = "\n".join(rep["findings"])
        self.assertIn("50% of the session waiting", joined)
        self.assertIn("switched 1 times", joined)

    def test_heat_and_stutter_are_reported(self):
        rows = self.rows(10) + self.rows(10, reason="thermal-quality-held:heating",
                                         diagnosis={"thermal": "heating", "smoothness": "stuttering"})
        rep = analyze(bundle({"timeline.jsonl": timeline(rows)}))
        self.assertEqual((rep["warm_share"], rep["stutter_share"], rep["thermal_holds"]), (0.5, 0.5, 10))
        joined = "\n".join(rep["findings"])
        self.assertIn("hot or heating up 50% of the time; quality steps were held back for heat in 10 samples", joined)
        self.assertIn("stutter (spikes over the median) in 50%", joined)

    def test_repeated_failed_power_probes_and_version_are_reported(self):
        step = lambda w: {"event": "budget-step", "reason": "probe-failed:starved",
                          "before": {"tdp_w": w}, "after": {"tdp_w": w + 1}}
        events = [step(9.0)] * 5 + [step(8.0)] * 2 + [{"event": "budget-step", "reason": "testing-lower-power",
                                                       "before": {"tdp_w": 10.0}, "after": {"tdp_w": 9.0}}]
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "governor-events.jsonl": timeline(events),
                              "system.json": json.dumps({"plugin_version": "GFG Extreme 1.0.0"})}))
        self.assertEqual(rep["failed_power_probes"], {"8 W": 2, "9 W": 5})
        self.assertIn("failed repeatedly at the same level (9 W x5)", "\n".join(rep["findings"]))
        self.assertIn("recorded with: GFG Extreme 1.0.0", render(rep))


if __name__ == "__main__":
    unittest.main()
