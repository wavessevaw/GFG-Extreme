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

    def test_extreme_reports_its_ceiling_and_confirmed_scales(self):
        ext = {"enabled": True, "state": "ACTIVE", "ceiling": {"ceiling_w": 15.0, "source": "stock-limit"},
               "applied": {"render_pct": 80}}
        rows = self.rows(10, tdp=15.0, extreme=ext) + self.rows(5, tdp=15.0, extreme={**ext, "applied": None})
        rep = analyze(bundle({"timeline.jsonl": timeline(rows), "diagnostics-x.log": (FIXED + "\n") * 30,
                              "self_test.json": "[]"}))
        self.assertEqual(rep["extreme"]["ceiling_w"], 15.0)
        self.assertEqual(rep["extreme"]["confirmed_scales"], {"80": 10})
        line = next(f for f in rep["findings"] if f.startswith("Extreme:"))
        self.assertIn("ceiling 15.0 W", line)
        self.assertIn("80%", line)
        self.assertNotIn("ABOVE", line)

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

    def test_rejection_cadence_is_the_measured_rate_not_the_plan(self):
        events = [{"event": "operating-point-rejected", "reason": "confirmation-timeout", "point": "30x3",
                   "cadence": {"delivered_output_fps": 48.0, "delivered_real_fps": 22.0,
                               "requested_output_fps": 90, "requested_real_fps": 30}}]
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "governor-events.jsonl": timeline(events)}))
        joined = "\n".join(rep["findings"])
        self.assertIn("30x3", joined)
        self.assertIn("output 48.0", joined)
        self.assertIn("real 22.0", joined)
        self.assertIn("asked output 90", joined)

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
        self.assertTrue(rep["findings"][0].startswith("Recorded with 1.0.0; this report is from"))

    def test_power_split_steps_and_ab_pairs_are_reported(self):
        step = lambda khz, level, why: {"event": "power-split", "reason": why, "cpu_khz": khz, "level": level}
        pair = lambda g: {"event": "power-split-ab", "reason": "measured", "gain": g, "mhz": g + 0.5,
                          "draw": 0.2, "real": 0.0}
        events = [step(3_000_000, 1, "step-down"), step(2_400_000, 2, "step-down"),
                  step(3_500_000, 0, "real-frames-short"), pair(6.0), pair(8.0), pair(7.0)]
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "governor-events.jsonl": timeline(events)}))
        split = rep["power_split"]
        self.assertEqual(split["lowest_khz"], 2_400_000)
        self.assertEqual(split["gain"]["n"], 3)
        text = "\n".join(rep["findings"])
        self.assertIn("the CPU clock went down to 2.4 GHz; the cap came off 1× for real frames short", text)
        self.assertIn("GPU clock per watt +7.0% (", text)
        self.assertIn("over 3 pairs; GPU clock +7.5%, draw -0.2%, real FPS +0.0", text)
        none = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "governor-events.jsonl": timeline([])}))
        self.assertIsNone(none["power_split"])

    def test_frequent_not_power_bound_holds_are_reported(self):
        # review 1.1.x: the guard holding because the draw was far under the cap was invisible in logs.
        hold = lambda d: {"event": "budget-guard-not-power-bound", "reason": "guard-not-power-bound:real-p5-short",
                          "draw_w": d, "cap_w": 10.0, "verdict": "real-p5-short"}
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()),
                              "governor-events.jsonl": timeline([hold(4.0), hold(5.0), hold(6.0)])}))
        self.assertEqual(rep["not_power_bound_holds"], {"count": 3, "draw_w_median": 5.0, "caps_w": [10.0]})
        self.assertIn("The guard held 3 times without adding watts", "\n".join(rep["findings"]))
        self.assertIn("median draw 5.0 W at 10 W", "\n".join(rep["findings"]))
        rare = analyze(bundle({"timeline.jsonl": timeline(self.rows()), "governor-events.jsonl": timeline([hold(4.0)])}))
        self.assertEqual(rare["not_power_bound_holds"]["count"], 1)
        self.assertFalse(any("without adding watts" in f for f in rare["findings"]), "a single hold is not a finding")

    def test_current_version_log_has_no_version_note(self):
        from gfg_plugin.log_report import CURRENT_VERSION
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows()),
                              "system.json": json.dumps({"plugin_version": f"GFG Extreme {CURRENT_VERSION} (engine x)"})}))
        self.assertFalse(any(f.startswith("Recorded with") for f in rep["findings"]))


if __name__ == "__main__":
    unittest.main()


class FrameOsReportTests(unittest.TestCase):
    def rows(self, layer):
        return [{"t": float(i), "state": "LOCKED", "target": 90,
                 "frame_os": {"mode": "observe", "layer_installed": True, "level": "calm", "layer": layer}}
                for i in range(10)]

    def test_answering_layer_is_summarised(self):
        layer = {"live": True, "frames": 900, "freshness_ms": 21.5, "present_interval_p50_ms": 33.3,
                 "present_interval_p95_ms": 34.0, "swapchain_recreations": 1, "present_hold_ms": 20.4,
                 "engine": "DXVK"}
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows(layer)),
                              "game-processes.json": json.dumps([{"pid": 1, "frame_os_layer_loaded": True}])}))
        fo = rep["frame_os"]
        self.assertEqual((fo["frames"], fo["freshness_ms"], fo["loaded_in_game"]), (900, 21.5, True))
        self.assertIn("Frame OS (observe): the layer reported 900 frames", "\n".join(rep["findings"]))
        self.assertIn("engine DXVK", "\n".join(rep["findings"]))
        self.assertEqual(fo["present_hold_ms"], 20.4)

    def test_ab_results_are_reported(self):
        rows = self.rows({"live": True, "frames": 900, "freshness_ms": 13.0})
        for i, row in enumerate(rows):
            row["frame_os"].update(mode="act", ab_control="no-shaping" if i == 3 else None,
                                   proof={"response": {"n": 4, "mean": 46.5, "low": 38.0, "high": 55.0},
                                          "frames": {"n": 0}, "energy": {"n": 1, "mean": 12.0}})
        rep = analyze(bundle({"timeline.jsonl": timeline(rows),
                              "game-processes.json": json.dumps([{"pid": 1, "frame_os_layer_loaded": True}])}))
        text = "\n".join(rep["findings"])
        self.assertIn("response +46.5% (38.0..55.0) over 4 pairs [session provenance unknown]", text)
        self.assertIn("energy +12.0% over 1 pair [session provenance unknown]", text)
        self.assertIn("control windows 10.0% of samples", text)

    def test_stale_telemetry_does_not_answer(self):
        layer = {"live": False, "frames": 900, "freshness_ms": 21.5}
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows(layer)),
                              "game-processes.json": json.dumps([{"pid": 1, "frame_os_layer_loaded": True}])}))
        self.assertEqual((rep["frame_os"]["answering_share"], rep["frame_os"]["frames"]), (0, 0))
        self.assertIn("never reported live frames", "\n".join(rep["findings"]))

    def test_layer_not_loaded_is_called_out(self):
        rep = analyze(bundle({"timeline.jsonl": timeline(self.rows({})),
                              "game-processes.json": json.dumps([{"pid": 1, "comm": "Game.exe",
                                                                  "frame_os_layer_loaded": False,
                                                                  "env": {"GFG_FRAME_OS_SHM": "/dev/shm/gfg-frame-os"}}])}))
        self.assertIn("Game.exe did not load the Frame OS layer", "\n".join(rep["findings"]))
        self.assertIn("32-bit game?", "\n".join(rep["findings"]))

    def test_no_frame_os_rows_no_summary(self):
        rep = analyze(bundle({"timeline.jsonl": timeline([{"t": 0.0, "state": "LOCKED"}])}))
        self.assertIsNone(rep["frame_os"])


class FrameOsLateSwitchTests(unittest.TestCase):
    def test_game_started_before_frame_os_was_on(self):
        rows = [{"t": float(i), "state": "LOCKED", "frame_os": {"mode": "observe", "layer_installed": True, "layer": {}}}
                for i in range(5)]
        procs = [{"pid": 1, "comm": "game.exe", "frame_os_layer_loaded": False, "env": {"DISABLE_GFG_FRAME_OS": "1"}}]
        rep = analyze(bundle({"timeline.jsonl": timeline(rows), "game-processes.json": json.dumps(procs)}))
        self.assertIn("restart the game", "\n".join(rep["findings"]))
        self.assertNotIn("32-bit", "\n".join(rep["findings"]))


class FrameOsByLevelTests(unittest.TestCase):
    def test_boost_and_calm_are_reported_separately(self):
        def row(i, level, interval, fresh, acting):
            return {"t": float(i), "state": "LOCKED", "output": 90, "tdp": 12,
                    "frame_os": {"mode": "act", "layer_installed": True, "level": level, "acting": acting,
                                 "layer": {"live": True, "frames": 100 + i, "present_interval_p50_ms": interval,
                                           "freshness_ms": fresh, "present_hold_ms": fresh - 1}}}
        rows = [row(i, "calm", 33.3, 25.0, True) for i in range(5)] + [row(i, "boost", 33.3, 25.0, True) for i in range(5, 10)]
        rep = analyze(bundle({"timeline.jsonl": timeline(rows)}))
        by = rep["frame_os"]["by_level"]
        self.assertEqual((by["calm"]["samples"], by["boost"]["real_fps"]), (5, 30.0))
        joined = "\n".join(rep["findings"])
        self.assertIn("Frame OS by decision", joined)
        self.assertIn("boost did not raise the real frame rate", joined)


class AuditRegressionTests(unittest.TestCase):
    def report(self, rows):
        return analyze(bundle({"timeline.jsonl": timeline(rows)}))

    def extreme_row(self, **values):
        return {"t": 0.0, "state": "APPLY", "point": None, "tdp": 15.0,
                "tdp_fast": 15.0, "tdp_owned": True,
                "extreme": {"state": "APPLY", "ceiling": {"ceiling_w": 15.0}}, **values}

    def test_owned_transition_without_point_exposes_both_caps(self):
        report = self.report([self.extreme_row(tdp=20.0, tdp_fast=20.0)])
        ext = report["extreme"]
        self.assertEqual((ext["max_tdp_w"], ext["owned_above_ceiling_samples"]), (20.0, 1))
        self.assertIn("ABOVE THE CEILING in 1 owned samples", render(report))

    def test_fast_channel_only_violation_is_visible(self):
        ext = self.report([self.extreme_row(tdp_fast=20.0)])["extreme"]
        self.assertEqual((ext["max_tdp_w"], ext["above_ceiling_samples"]), (20.0, 1))

    def test_unowned_read_is_reported_without_attributing_a_gfg_write(self):
        report = self.report([self.extreme_row(tdp=20.0, tdp_owned=False)])
        ext = report["extreme"]
        self.assertIsNone(ext["max_tdp_w"])
        self.assertEqual((ext["max_observed_tdp_w"], ext["above_ceiling_samples"],
                          ext["owned_above_ceiling_samples"]), (20.0, 1, 0))
        self.assertIn("highest observed cap 20.0 W", render(report))
        self.assertNotIn("owned samples", render(report))

    def test_each_sample_uses_its_own_ceiling(self):
        a = self.extreme_row()
        b = self.extreme_row(t=1.0, tdp=9.0, tdp_fast=9.0,
                             extreme={"ceiling": {"ceiling_w": 9.0}})
        report = self.report([a, b])
        self.assertEqual(report["extreme"]["above_ceiling_samples"], 0)
        self.assertNotIn("ABOVE THE CEILING", render(report))

    def frame_row(self, proof, **extra):
        return {"t": 0.0, "state": "LOCKED", "frame_os": {
            "mode": "act", "proof": proof, **extra}}

    def test_old_archive_prior_is_not_reported_as_current_ab(self):
        proof = {"response": {"n": 9, "session_n": 0, "mean": 42.3,
                               "low": 33.3, "high": 51.3, "measured": True}}
        text = render(self.report([self.frame_row(proof)]))
        self.assertIn("historical; no pairs in this session", text)
        self.assertIn("not independently measured input-to-display latency", text)
        self.assertNotIn("A/B in game", text)

    def test_mixed_old_archive_does_not_invent_current_mean(self):
        proof = {"response": {"n": 9, "session_n": 2, "mean": 42.3, "measured": True}}
        text = render(self.report([self.frame_row(proof)]))
        self.assertIn("history + current session; 2 current pairs", text)

    def test_new_archive_reports_current_pairs_separately(self):
        proof = {"response": {"n": 10, "session_n": 1, "mean": 42.3, "measured": True,
                               "session": {"n": 1, "mean": 12.0, "measured": False}}}
        text = render(self.report([self.frame_row(proof)]))
        self.assertIn("response +12.0% over 1 pair [current session; preliminary]", text)
        self.assertNotIn("response +42.3%", text)

    def test_unknown_relay_device_count_is_not_zero(self):
        row = self.frame_row({}, input={"source": "relay", "events": 61021, "gamepads": None})
        report = self.report([row])
        self.assertIsNone(report["frame_os"]["input_gamepads"])
        self.assertIn("unknown number of gamepads", render(report))
