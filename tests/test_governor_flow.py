import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.governor_flow import FlowTrial
from gfg_plugin.governor_core import TrialLadder
from gfg_plugin.governor_telemetry import TelemetryObserver


class FlowTests(unittest.TestCase):
    def run_trial(self, mode="budget", change=None, stale_ack=False):
        trial = FlowTrial()
        actual, ack, event = .8, 1, 1
        requests = []
        for now in range(150):
            lower = actual < .8
            sample = {"seq": now, "real": 30, "output": 90, "draw": 9.2 if lower else 10,
                      "gpu": 86 if lower else 95, "temp": 70, "p95": 11.2}
            if mode == "quality":
                sample.update(gpu=60, draw=10.5 if actual > .8 else 10)
            if change:
                change(trial, sample, now)
            event += 1
            wanted = trial.step(now=now, context=("game", mode), mode=mode, eligible=True,
                                saved_flow=.8, actual_flow=actual, ack_seq=ack, event_seq=event,
                                sample=sample, target=90, base_target=30)
            if wanted is not None:
                requests.append(wanted)
                actual = wanted
                if not stale_ack:
                    event += 1
                    ack = event
        return trial, requests

    def test_battery_requires_real_draw_saving_and_fresh_aba_confirmation(self):
        trial, requests = self.run_trial()
        self.assertEqual(requests, [.7, .8, .7])
        self.assertEqual(trial.phase, "held")
        self.assertAlmostEqual(trial.proof["apu_draw_change_pct"], -8)
        self.assertEqual(trial.actual, .7)
        self.assertFalse(trial.busy)

    def test_each_mode_has_a_distinct_acceptance_goal(self):
        for mode in ("extreme", "balanced"):
            trial, _ = self.run_trial(mode)
            self.assertEqual(trial.phase, "held")
        trial, requests = self.run_trial("quality")
        self.assertEqual(requests, [.9, .8, .9])
        self.assertEqual(trial.phase, "held")
        self.assertEqual(trial.reason, "higher-flow-resolution-held")

    def test_no_saving_reverts_even_if_gpu_load_drops(self):
        trial, requests = self.run_trial(change=lambda t, s, n: s.update(draw=10))
        self.assertEqual(requests, [.7, .8])
        self.assertEqual(trial.phase, "done")
        self.assertIsNone(trial.proof)
        self.assertEqual(trial.reason, "no-useful-benefit")

    def test_regression_aborts_and_restores_without_a_claim(self):
        def change(t, sample, now):
            if t.phase == "b":
                sample.update(real=15, output=45)
        trial, requests = self.run_trial(change=change)
        self.assertEqual(requests, [.7, .8])
        self.assertEqual(trial.phase, "done")
        self.assertIsNone(trial.proof)
        self.assertEqual(trial.reason, "output-starved")

    def test_scene_drift_rejects_apparent_gain(self):
        def change(t, sample, now):
            if t.phase == "a2":
                sample["draw"] = 13
        trial, _ = self.run_trial(change=change)
        self.assertEqual(trial.phase, "done")
        self.assertEqual(trial.reason, "control-window-drift")
        self.assertIsNone(trial.proof)

    def test_stale_ack_and_duplicate_samples_do_not_prove_a_change(self):
        trial, requests = self.run_trial(stale_ack=True)
        self.assertEqual(requests, [.7, .8])
        self.assertEqual(trial.phase, "done")
        self.assertIsNone(trial.proof)
        trial, requests = self.run_trial(change=lambda t, s, n: s.update(seq=1))
        self.assertEqual(requests, [])
        self.assertEqual(trial.reason, "flow-window-timeout")

    def test_missing_or_nonfinite_draw_cannot_prove_battery_savings(self):
        for bad in (None, float("nan"), float("inf"), True):
            trial, _ = self.run_trial(change=lambda t, s, n: s.update(draw=bad))
            self.assertEqual(trial.phase, "done")
            self.assertIsNone(trial.proof)

    def test_menu_or_cpu_probe_restores_held_flow(self):
        trial, _ = self.run_trial()
        result = trial.step(now=200, context=("game", "budget"), mode="budget", eligible=False,
                            saved_flow=.8, actual_flow=.7, ack_seq=999, event_seq=1000,
                            sample=None, target=90, base_target=30)
        self.assertEqual(result, .8)
        self.assertEqual(trial.phase, "wait-restore")
        trial.step(now=201, context=("game", "budget"), mode="budget", eligible=False,
                   saved_flow=.8, actual_flow=.8, ack_seq=1001, event_seq=1001,
                   sample=None, target=90, base_target=30)
        self.assertEqual(trial.phase, "done")

    def test_quality_preserves_resolution_and_other_ladders_keep_scale_tools(self):
        for target in (60, 90):
            quality = TrialLadder(target_output_fps=target, preserve_resolution=True)
            ordinary = TrialLadder(target_output_fps=target)
            self.assertTrue(all(p.render_scale_pct == 100 for p in quality.candidates()))
            self.assertTrue(any(p.render_scale_pct < 100 for p in ordinary.candidates()))

    def test_telemetry_only_exposes_applied_flow_for_matching_renderer_role(self):
        observer = TelemetryObserver(ROOT / "absent.log")
        prefix = "MAKO Renderer: present diagnostics: "
        observer.consume_line(prefix + "operation=runtime-transition-pending context=0xaa effective_flow_scale=0.7 role=frame-generation", now=1)
        self.assertIsNone(observer.snapshot(now=1)["flow"])
        observer.consume_line(prefix + "operation=runtime-state-applied context=0xbb role=frame-generation effective_flow_scale=0.8 frame_generation_resources_available=1", now=2)
        self.assertEqual(observer.snapshot(now=2)["flow"]["context"], "0xbb")
        observer.consume_line(prefix + "operation=runtime-state-applied context=0xaa role=spatial effective_flow_scale=0.7", now=3)
        self.assertEqual(observer.snapshot(now=3)["flow"]["value"], .8)
        observer._reset_session()
        self.assertIsNone(observer.snapshot(now=4)["flow"])


    def test_failed_restore_keeps_probes_paused_and_retries_saved_value(self):
        trial = FlowTrial()
        trial.context = ("game", "budget")
        trial.original = .8
        trial.wanted = .8
        trial.phase = "wait-restore"
        trial.started = 0
        trial.mark = 100
        wanted = trial.step(now=16, context=trial.context, mode="budget", eligible=False,
                            saved_flow=.8, actual_flow=.7, ack_seq=101, event_seq=102,
                            sample=None, target=90, base_target=30)
        self.assertEqual(wanted, .8)
        self.assertTrue(trial.busy)
        self.assertEqual(trial.reason, "restore-not-confirmed")
        trial.step(now=17, context=trial.context, mode="budget", eligible=False,
                   saved_flow=.8, actual_flow=.8, ack_seq=103, event_seq=104,
                   sample=None, target=90, base_target=30)
        self.assertFalse(trial.busy)
        self.assertIsNone(trial.wanted)


    def test_resource_ack_grace_cannot_mask_severe_output_starvation(self):
        def starved_wait(trial, sample, now):
            if trial.phase == "wait-b":
                sample.update(real=15, output=45)
        trial, requests = self.run_trial(change=starved_wait)
        self.assertEqual(requests, [.7, .8])
        self.assertEqual(trial.phase, "done")
        self.assertEqual(trial.reason, "output-starved")
        self.assertIsNone(trial.proof)


    def test_starvation_during_restore_wait_still_requires_saved_ack(self):
        trial = FlowTrial()
        trial.context = ("game", "budget")
        trial.original = .8
        trial.wanted = .8
        trial.phase = "wait-a"
        trial.started = 0
        trial.mark = 100
        result = trial.step(now=1, context=trial.context, mode="budget", eligible=True,
                            saved_flow=.8, actual_flow=.7, ack_seq=99, event_seq=101,
                            sample={"seq": 1, "real": 15, "output": 45}, target=90, base_target=30)
        self.assertEqual(result, .8)
        self.assertEqual(trial.phase, "wait-restore")
        self.assertTrue(trial.busy)

    def held_step(self, trial, *, seq=200, real=30, output=90, actual=.7, now=200):
        return trial.step(now=now, context=("game", "budget"), mode="budget", eligible=True,
                          saved_flow=.8, actual_flow=actual, ack_seq=999, event_seq=1000,
                          sample={"seq": seq, "real": real, "output": output},
                          target=90, base_target=30)

    def test_accepted_trial_reverts_immediately_on_later_severe_starvation(self):
        trial, _ = self.run_trial()
        self.assertEqual(self.held_step(trial, real=15, output=45), .8)
        self.assertEqual(trial.reason, "output-starved")
        self.assertEqual(trial.phase, "wait-restore")
        self.assertIsNone(trial.proof)
        self.assertFalse(trial.status()["accepted"])
        self.assertTrue(trial.busy)

    def test_held_moderate_shortfall_requires_two_distinct_consecutive_samples(self):
        trial, _ = self.run_trial()
        self.assertIsNone(self.held_step(trial, real=27, output=82))
        self.assertIsNone(self.held_step(trial, real=27, output=82, now=201))
        self.assertEqual(trial.phase, "held")  # rereading one sample is not a second failure
        self.assertEqual(self.held_step(trial, seq=201, real=27, output=82, now=202), .8)
        self.assertEqual(trial.reason, "held-cadence-regression")
        self.assertIsNone(trial.proof)

    def test_healthy_frame_resets_held_shortfall_counter(self):
        trial, _ = self.run_trial()
        self.held_step(trial, real=27, output=82)
        self.held_step(trial, seq=201, now=201)
        self.held_step(trial, seq=202, real=27, output=82, now=202)
        self.assertEqual(trial.phase, "held")
        self.assertEqual(trial.held_misses, 1)

    def test_held_actual_change_or_missing_ack_invalidates_benefit(self):
        for actual in (.8, .6, None, float("nan")):
            trial, _ = self.run_trial()
            self.assertEqual(self.held_step(trial, actual=actual), .8)
            self.assertEqual(trial.reason, "held-flow-not-confirmed")
            self.assertIsNone(trial.proof)
            self.assertTrue(trial.busy)

    def test_held_invalid_frame_evidence_cannot_retain_success(self):
        for bad in (None, True, float("nan"), float("inf")):
            trial, _ = self.run_trial()
            self.assertEqual(self.held_step(trial, real=bad), .8)
            self.assertEqual(trial.reason, "invalid-frame-evidence")

    def test_incomplete_applied_flow_supersedes_previous_ack(self):
        prefix = "MAKO Renderer: present diagnostics: "
        for invalid in ("", " effective_flow_scale=nan", " effective_flow_scale=2"):
            observer = TelemetryObserver(ROOT / "absent.log")
            observer.consume_line(prefix + "operation=runtime-state-applied context=0xaa role=frame-generation effective_flow_scale=0.7 frame_generation_resources_available=1 lighter_model=0", now=1)
            first = observer.snapshot(now=1)["flow"]["event_seq"]
            observer.consume_line(prefix + "operation=runtime-state-applied context=0xaa role=frame-generation frame_generation_resources_available=0" + invalid, now=2)
            flow = observer.snapshot(now=2)["flow"]
            self.assertIsNone(flow["value"])
            self.assertFalse(flow["resources"])
            self.assertGreater(flow["event_seq"], first)
