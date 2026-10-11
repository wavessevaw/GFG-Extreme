"""Regression cases from the 2.0.0 control-path audit, without hardware claims."""
import asyncio
import json
import unittest
from pathlib import Path

from test_autopilot_v2 import Arbiter, GpuClock, MemoryBackend, measured, view, decide
from test_half_rate_autopilot import HalfRateShading, StaticBackend
import test_governor_runtime as legacy
from gfg_plugin.frame_os.policy import InjectionPolicy, BOOST_BACKOFF_S


class ExperimentEvidenceTests(unittest.TestCase):
    def actor(self):
        a = Arbiter()
        a.begin("gpu-clock", "test", 0,
                measured(real=30, output=90, sample_seq=10, session="game"))
        return a

    def test_repeated_complete_window_times_out(self):
        a = self.actor()
        self.assertEqual(a.judge(19, measured(real=30, output=90,
                         sample_seq=10, session="game")), "rollback")
        self.assertEqual(a.reason, "measurement-lost")

    def test_temperature_protection_does_not_wait_for_new_fps(self):
        a = self.actor()
        self.assertEqual(a.judge(1, measured(real=30, output=90,
                         sample_seq=10, session="game", temp_c=92)), "rollback")
        self.assertEqual(a.reason, "thermal-limited")

    def test_overlapping_window_cannot_verify_gain(self):
        a = self.actor()
        self.assertEqual(a.judge(3, measured(real=35, output=90,
                         sample_seq=20, first_sample_seq=8, session="game")), "wait")
        self.assertEqual(a.state, "SETTLE")

    def test_nonfinite_fps_cannot_be_learned(self):
        for value in (float("nan"), float("inf")):
            with self.subTest(value=value):
                a = self.actor()
                self.assertEqual(a.judge(19, measured(real=value, output=90,
                                 sample_seq=20, session="game")), "rollback")
                self.assertEqual(decide(view(real_fps=value)).action, "PAUSE")


class RuntimeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.RuntimeBase()
        self.fixture.setUp()
        self.svc = self.fixture.svc

    def tearDown(self):
        self.fixture.tearDown()

    def prepare(self):
        svc = self.svc
        svc._active_profile = "game"
        svc._settings.setdefault("profiles", {}).setdefault("game", {})["enabled"] = True
        svc.set_mode("game", "autopilot")
        svc._menu_covering = lambda: False
        svc._clock = lambda: 50
        svc._evaluation_after_seq = 10
        svc._point_mode = "applied"
        svc._point = {"key": "30x3", "base_target_fps": 30, "multiplier": 3,
                      "target_output_fps": 90}
        svc._request = None
        return {"samples": 9, "sample_span_s": 9, "first_sample_seq": 11,
                "last_sample_seq": 20, "real": {"median": 30},
                "output": {"median": 90}, "multiplier": {"median": 3},
                "frametime": {"p95_ms": 33}}

    def test_stable_cpu_load_can_reach_clock_actuator(self):
        row = self.prepare()
        self.svc._status["sensors"] = {"cpu_top_core_pct": 95, "gpu_busy_pct": 40, "temp_c": 65,
                                       "gpu_clock_mhz": 1200}
        self.svc._autopilot_gpu = GpuClock(backend=MemoryBackend(), writes_enabled=True)
        self.assertTrue(asyncio.run(self.svc._autopilot_tick("game", row, 90)))
        self.assertEqual(self.svc._autopilot_arbiter.state, "SETTLE")
        self.assertTrue(self.svc._autopilot_gpu.owned)
        self.assertEqual(self.svc._autopilot_gpu.applied_max, 1100)

    def test_stable_gpu_load_can_reach_opted_in_shading_actuator(self):
        row = self.prepare()
        self.svc._status["sensors"] = {"cpu_top_core_pct": 40, "gpu_busy_pct": 95, "temp_c": 65}
        self.svc._settings["profiles"]["game"]["autopilot_shading"] = True
        self.svc._autopilot_half_rate = HalfRateShading(StaticBackend())
        self.assertTrue(asyncio.run(self.svc._autopilot_tick("game", row, 90)))
        self.assertEqual(self.svc._autopilot_arbiter.tool, "half-rate-shading")
        self.assertEqual(self.svc._autopilot_arbiter.state, "SETTLE")

    def test_flow_trial_blocks_resource_actuator(self):
        row = self.prepare()
        self.svc._flow.phase = "b"
        self.assertEqual(self.svc._autopilot_trial_ready(row, 90), (False, "resource-controller-busy"))

    def test_idle_gpu_restore_does_not_clear_shading_restore_lock(self):
        self.prepare()
        backend = StaticBackend()
        actor = self.svc._autopilot_half_rate = HalfRateShading(backend)
        actor.enable_trial()
        backend.fail = True
        self.assertFalse(self.svc._restore_autopilot_shading("stop"))
        self.assertTrue(self.svc._restore_autopilot_gpu("stop"))
        self.assertEqual(self.svc._autopilot_arbiter.state, "RESTORE_PENDING")
        self.assertEqual(self.svc._autopilot_arbiter.tool, "half-rate-shading")

    def test_restore_lock_blocks_other_modes(self):
        self.prepare()
        self.svc.set_mode("game", "quality")
        self.svc._autopilot_gpu.phase = "restore-pending"
        self.assertTrue(self.svc._autopilot_blocks_planned())
        asyncio.run(self.svc._iteration_core())
        self.assertEqual(self.svc._status["reason"], "autopilot-restore-pending")
        self.assertEqual(self.svc.power.writes, [])

    def test_menu_misses_never_lower_output_goal(self):
        row = self.prepare()
        self.svc._menu_covering = lambda: True
        for first in (11, 21, 31):
            missed = {**row, "real": {"median": 20}, "output": {"median": 40},
                      "first_sample_seq": first, "last_sample_seq": first + 9}
            self.assertEqual(self.svc._governor_target("game", 90, missed), 90)

    def test_silent_renderer_reaches_timeout_before_normal_freshness_gate(self):
        row = self.prepare()
        svc = self.svc
        svc._forced_mode_change = False
        svc._launch_key = [1, 1, 1]
        svc._autopilot_gpu = GpuClock(backend=MemoryBackend(), writes_enabled=True)
        svc._autopilot_gpu.lower_ceiling(1200)
        svc._autopilot_arbiter.begin("gpu-clock", "test", 0,
            measured(real=30, output=90, sample_seq=20, session=("game", str(svc._launch_key), None)))
        svc.observer.summary = lambda *args, **kwargs: row
        svc.observer.snapshot = lambda: {"available": False, "sample_age_ms": None}
        asyncio.run(svc._iteration_core())
        self.assertEqual(svc._autopilot_arbiter.reason, "measurement-lost")
        self.assertFalse(svc._autopilot_gpu.owned)
        self.assertEqual(svc.power.writes, [])

    def test_rejected_actuator_leaves_budget_available(self):
        row = self.prepare()
        svc = self.svc
        svc._status["sensors"] = {"cpu_top_core_pct": 40, "gpu_busy_pct": 95, "temp_c": 65}
        svc._settings["profiles"]["game"]["autopilot_shading"] = True
        svc._autopilot_half_rate = HalfRateShading(StaticBackend())
        svc._autopilot_arbiter.blocked_until["OPTIMIZE_SHADING"] = 100
        self.assertFalse(asyncio.run(svc._autopilot_tick("game", row, 90)))
        self.assertFalse(svc._autopilot_blocks_planned())
        self.assertFalse(svc._autopilot_half_rate.owned)

    def test_recorded_shading_skips_do_not_bypass_confirmation(self):
        row = self.prepare()
        lines = (Path(__file__).parent / "replay" / "autopilot_shading_skips_2_0_0.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 15)
        for line in lines:
            event = json.loads(line)
            with self.subTest(ts=event["ts"]):
                self.svc._point = ({"key": event["point"], "base_target_fps": 30, "multiplier": 3,
                                   "target_output_fps": 90} if event["point"] else None)
                replay = {**row, "output": {"median": event["output_fps"]}}
                if event["reason"] == "baseline-overlaps-transition":
                    replay["first_sample_seq"] = self.svc._evaluation_after_seq
                self.assertFalse(self.svc._autopilot_trial_ready(replay, 90)[0])

    def test_ineffective_boost_releases_governor_point(self):
        self.prepare()
        svc = self.svc
        svc._settings["frame_os_act_unlocked"] = True
        svc.set_frame_os_act_unlock(True)
        svc.set_frame_os("game", "act")
        svc._point_deltas = {"adaptive": False, "multiplier": 3, "base_fps_cap": 30}
        svc._injection = {"adaptive": True, "base_fps_cap": 45}
        svc.frame_os.last = {"telemetry": {"live": True}}
        svc.frame_os.policy = InjectionPolicy(output_hz=90, calm_real_hz=30)
        svc.frame_os.policy._boost_blocked_until = 170
        self.assertFalse(asyncio.run(svc._sync_injection("game")))
        self.assertIsNone(svc._injection)
        self.assertFalse(svc.frame_os.executor_active)
        self.assertEqual(svc._injection_hold_until, 170)


class ClockRecoveryTests(unittest.TestCase):
    def test_manual_step_never_raises_a_lightly_loaded_auto_gpu(self):
        actor = GpuClock(backend=MemoryBackend(), writes_enabled=True)
        self.assertTrue(actor.lower_ceiling(700)["applied"])
        self.assertEqual(actor.applied_max, 600)

    def test_qam_override_wins_during_restore_retry(self):
        backend = MemoryBackend()
        actor = GpuClock(backend=backend, writes_enabled=True)
        actor.lower_ceiling()
        backend.fail_at = "level"
        self.assertFalse(actor.restore()["restored"])
        backend.fail_at = None
        backend.maximum = 900
        self.assertTrue(actor.restore().get("yielded"))
        self.assertEqual(backend.maximum, 900)


class BurstDeliveryTests(unittest.TestCase):
    def test_short_failed_bursts_eventually_back_off(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        now = 100.0
        for _ in range(30):
            for _ in range(20):
                p.tick(now, {"camera": 1, "idle_s": 0})
                p.note_delivered(now, 30)
                now += 0.1
            now += 2
            p.tick(now, {"camera": 0, "idle_s": 0})
            p.note_delivered(now, 30)
            if now < p._boost_blocked_until:
                break
        self.assertGreater(p._boost_blocked_until, now)
        self.assertEqual(p.tick(now, {"camera": 1, "idle_s": 0}).reason, "boost-ineffective")
        self.assertEqual(p.tick(now + BOOST_BACKOFF_S + 1, {"camera": 1, "idle_s": 0}).level, "boost")

    def test_missing_cadence_does_not_count_as_failed_delivery(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        for i in range(60):
            now = 100 + i * .1
            p.tick(now, {"camera": 1, "idle_s": 0})
            p.note_delivered(now, None)
        self.assertLess(p._boost_blocked_until, 100)


if __name__ == "__main__":
    unittest.main()
