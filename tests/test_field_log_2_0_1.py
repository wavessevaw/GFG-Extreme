"""Control conflicts observed in the 20261012-003441 physical Deck recording.

These exercise actual observers, actuator admission and power rollback. The
recorded values are evidence inputs, never claims about hardware gains.
"""
import asyncio
import json
import unittest
from pathlib import Path

import test_governor_runtime as legacy
from test_autopilot_v2 import GpuClock, MemoryBackend
from test_half_rate_autopilot import HalfRateShading, StaticBackend
from test_extreme import POLICY_OFF
from gfg_plugin.governor_core import BudgetController, WindowVerdict


class FieldLogControlTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.FrameOsIntegrationTests()
        self.fixture.setUp()
        self.svc = self.fixture.svc

    def tearDown(self):
        self.fixture.tearDown()

    def confirmed(self, mode="autopilot"):
        svc = self.svc
        svc._active_profile = "game"
        svc.set_mode("game", mode)
        svc._forced_mode_change = False
        svc._menu_covering = lambda: False
        svc._point = {"key": "30x3", "base_target_fps": 30, "multiplier": 3,
                      "render_scale_pct": 100, "target_output_fps": 90, "degraded": False,
                      "requires_scale_validation": False}
        svc._point_mode = "applied"
        svc._request = None
        svc._point_deltas = {"adaptive": False, "multiplier": 3, "base_fps_cap": 30}
        svc._launch = self.fixture.inspector.info
        svc._launch_key = svc._launch["launch_key"]
        svc._budget = BudgetController(target_output_fps=90, now=0, max_tdp_w=20)
        svc._budget.phase = "locked"
        svc._budget.locked_since = svc._budget.settled_since = 0
        svc._budget.draw_w = 20
        svc._status["sensors"] = {"cpu_top_core_pct": 40, "gpu_busy_pct": 95, "temp_c": 65}
        return {"samples": 10, "sample_span_s": 9, "first_sample_seq": 1,
                "last_sample_seq": 10, "real": {"median": 30}, "output": {"median": 90},
                "multiplier": {"median": 3}, "frametime": {"p95_ms": 33}}

    def test_ordinary_budget_windows_do_not_starve_the_shading_baseline(self):
        self.confirmed()
        svc = self.svc
        svc._settings["profiles"]["game"]["autopilot_shading"] = True
        svc._autopilot_half_rate = HalfRateShading(StaticBackend())
        # As in the recording: uninterrupted 30x3; the ordinary Budget window
        # is consumed every six seconds while Autopilot requires eight.
        for second in range(1, 20):
            self.fixture.feed(1, 30, 90, dt=1)
            if second % 6 == 0:
                svc._evaluation_after_seq = svc.observer.sample_seq
        row = svc.observer.summary(svc.WINDOW_SECONDS, after_seq=svc._autopilot_transition_seq)
        self.assertLessEqual(row["first_sample_seq"], svc._evaluation_after_seq)
        self.assertEqual(svc._autopilot_trial_ready(row, 90), (True, "confirmed-game-cadence"))
        self.assertTrue(asyncio.run(svc._autopilot_tick("game", row, 90)))
        self.assertTrue(svc._autopilot_half_rate.owned)
        self.assertEqual(svc._autopilot_arbiter.tool, "half-rate-shading")

    def test_a_real_tdp_write_still_requires_a_new_baseline(self):
        row = self.confirmed()
        self.fixture.feed(10, 30, 90, dt=1)
        svc = self.svc
        svc.power.claim()
        svc._applied_tdp = 20
        svc._budget.tdp = 19
        self.assertTrue(asyncio.run(svc._apply_budget_tdp("game")))
        self.assertEqual(svc._autopilot_transition_seq, svc.observer.sample_seq)
        self.assertEqual(svc._autopilot_trial_ready(row, 90)[1], "baseline-overlaps-transition")
        self.fixture.feed(10, 30, 90, dt=1)
        clean = svc.observer.summary(12, after_seq=svc._autopilot_transition_seq)
        self.assertTrue(svc._autopilot_trial_ready(clean, 90)[0])

    def test_full_loop_reaches_shading_after_consuming_an_ordinary_power_window(self):
        self.confirmed()
        svc = self.svc
        svc.power.claim()
        svc.power.values.update(observed_tdp_w=10, current_tdp_w=10, draw_w=10)
        svc._applied_tdp = 10
        svc._budget.locked_since = svc._budget.settled_since = svc._clock()
        svc._settings["profiles"]["game"]["autopilot_shading"] = True
        svc._autopilot_half_rate = HalfRateShading(StaticBackend())
        sensors = dict(svc._status["sensors"])
        svc.sensors.sample = lambda force=False: sensors
        for _ in range(14):
            self.fixture.feed(1, 30, 90, dt=1)
            asyncio.run(svc._iteration())
            if svc._autopilot_half_rate.owned:
                break
        self.assertTrue(svc._autopilot_half_rate.owned)
        self.assertGreater(svc._evaluation_after_seq, 0, "Budget actually consumed a healthy window")

    def test_full_loop_can_lower_the_goal_after_three_independent_misses_at_the_ceiling(self):
        self.confirmed()
        svc = self.svc
        svc.power.claim()
        svc.power.values.update(observed_tdp_w=20, current_tdp_w=20, draw_w=20)
        svc._applied_tdp = svc._budget.tdp = 20
        svc.observer._generated_capacity = 3
        sensors = dict(svc._status["sensors"])
        svc.sensors.sample = lambda force=False: sensors
        for _ in range(45):
            self.fixture.feed(1, 26, 78, dt=1)
            asyncio.run(svc._iteration())
            if svc._status.get("target_output_fps") == 60:
                break
        self.assertEqual(svc._status["target_output_fps"], 60)
        self.assertIsNone(svc._budget, "the old 90 FPS controller was released")

    def test_an_unchanged_overlay_does_not_restart_baseline_collection(self):
        self.confirmed()
        svc = self.svc
        svc._ensure_overlay_sync("game", svc._point_deltas, "30x3")
        before = svc._autopilot_transition_seq
        self.fixture.feed(10, 30, 90, dt=1)
        self.assertIsNone(svc._ensure_overlay_sync("game", svc._point_deltas, "30x3"))
        self.assertEqual(svc._autopilot_transition_seq, before)
        svc._ensure_overlay_sync("game", {**svc._point_deltas, "flow_scale": .7}, "30x3")
        self.assertEqual(svc._autopilot_transition_seq, svc.observer.sample_seq)

    def test_goal_misses_survive_collection_of_the_next_disjoint_window(self):
        self.confirmed()
        svc = self.svc
        snapshot = {"sample_age_ms": 0, "session_generation": None}
        for first in (1, 11, 21):
            # An ordinary evaluation consumed these numbers, without changing
            # the actual point. The 2.0.1 goal path incorrectly refused them.
            svc._evaluation_after_seq = first + 9
            row = {"samples": 10, "sample_span_s": 9, "first_sample_seq": first,
                   "last_sample_seq": first + 9, "real": {"median": 26}, "output": {"median": 78}}
            target = svc._governor_target("game", 90, row, snapshot=snapshot)
            self.assertEqual(target, 60 if first == 21 else 90)
            waiting = svc._governor_target("game", 90, {"samples": 0}, snapshot=snapshot)
            self.assertEqual(waiting, target)

    def test_menu_or_stale_telemetry_interrupts_goal_misses(self):
        row = self.confirmed()
        row.update(real={"median": 26}, output={"median": 78})
        svc = self.svc
        fresh = {"sample_age_ms": 0, "session_generation": None}
        self.assertEqual(svc._governor_target("game", 90, row, snapshot=fresh), 90)
        self.assertEqual(svc._autopilot_targets.pending_n, 1)
        svc._governor_target("game", 90, {"samples": 0}, snapshot={**fresh, "sample_age_ms": 3000})
        self.assertEqual(svc._autopilot_targets.pending_n, 0)
        svc._menu_covering = lambda: True
        self.assertEqual(svc._governor_target("game", 90, row, snapshot=fresh), 90)
        self.assertEqual(svc._autopilot_targets.pending_n, 0)

    def test_display_change_is_honored_while_collecting_a_new_goal_window(self):
        self.confirmed()
        svc = self.svc
        fresh = {"sample_age_ms": 0, "session_generation": None}
        svc._governor_target("game", 90, {"samples": 0}, snapshot=fresh)
        self.assertEqual(svc._governor_target("game", 60, {"samples": 0}, snapshot=fresh), 60)
        self.assertEqual(svc._autopilot_targets.target, 60)

    def test_emergency_auto_hold_allows_a_confirmed_down_probe_and_rollback(self):
        row = self.confirmed()
        svc = self.svc
        svc._budget.tdp = 20
        svc._budget._lock(0, "budget-point-holds")
        svc._clock = lambda: 150
        svc.power.values.update(draw_w=20, ceiling_tdp_w=20)
        svc._autopilot_gpu = GpuClock(backend=MemoryBackend(), writes_enabled=True)
        self.assertFalse(asyncio.run(svc._autopilot_tick("game", row, 90)))
        self.assertEqual(svc._status["autopilot"]["reason"], "recover-emergency-power")
        self.assertFalse(svc._budget.hold_planned)
        self.assertEqual(svc._budget.observe(150, WindowVerdict(True, False, "holds"), 30, 90), "move")
        self.assertEqual(svc._budget.tdp, 19)
        svc._budget.last_good = (svc._budget.idx, 20)
        svc._budget.observe(158, WindowVerdict(False, True, "real-below-cap"), 26, 78)
        self.assertEqual(svc._budget.tdp, 20, "a failed lower cap must restore working watts")

    def test_emergency_research_does_not_bypass_critical_temperature_or_resource_trial(self):
        row = self.confirmed()
        svc = self.svc
        svc._budget.tdp = 20
        svc._status["sensors"]["temp_c"] = 92
        asyncio.run(svc._autopilot_tick("game", row, 90))
        self.assertEqual(svc._autopilot_plan, "pause")
        svc._status["sensors"]["temp_c"] = 65
        svc._autopilot_arbiter.begin("gpu-clock", "test", svc._clock(),
                                   svc._autopilot_evidence(row, ("game", str(svc._launch_key), None)))
        self.assertTrue(asyncio.run(svc._autopilot_tick("game", row, 90)))
        self.assertTrue(svc._budget.hold_planned)
        self.assertEqual(svc.power.writes, [])

    def test_act_cannot_freeze_an_emergency_cap_and_yields_an_existing_overlay(self):
        self.fixture._act_live_point()
        svc = self.svc
        svc._budget.tdp = 20
        svc.frame_os.last = {"telemetry": {"live": True}}
        self.assertFalse(svc._act_power_settled())
        self.assertFalse(asyncio.run(svc._sync_injection("game")))
        svc._injection = {"adaptive": True, "base_fps_cap": 45}
        svc._injection_started_at = svc._clock()
        self.assertFalse(asyncio.run(svc._sync_injection("game")))
        self.assertIsNone(svc._injection)
        events = [json.loads(s) for s in Path(svc.events_path).read_text().splitlines()]
        self.assertTrue(any(e.get("reason") == "emergency-power-research" for e in events))
        self.assertEqual(svc._injection_starvation_yields, 0)

    def test_extreme_keeps_its_user_ceiling_with_act(self):
        self.confirmed("extreme")
        svc = self.svc
        svc._budget = BudgetController(target_output_fps=90, now=0, max_tdp_w=20, flavor="extreme")
        svc._budget._lock(0, "holds")
        svc._clock = lambda: 100
        self.assertTrue(svc._act_power_settled())

    def test_recorded_scale_override_is_blocked_before_a_scaled_point_is_requested(self):
        self.confirmed()
        svc = self.svc
        svc._launch["app_id"] = "recorded-game"
        svc.observer.consume_line(POLICY_OFF, now=self.fixture.t["now"])
        self.assertFalse(svc._budget_can_scale({"scale_capable": True}))
        self.assertEqual(svc._game_ignores_scale("game"), "game-ignores-render-scale")
        svc.set_mode("game", "balanced")
        self.assertFalse(svc._budget_can_scale({"scale_capable": True}))
        events = [json.loads(s) for s in Path(svc.events_path).read_text().splitlines()]
        self.assertEqual(sum(e.get("event") == "render-scale-blocked" for e in events), 1)

    def test_an_inactive_native_scaler_is_not_a_permanent_game_refusal(self):
        self.confirmed()
        svc = self.svc
        native = POLICY_OFF.replace("application-extent-override-no-source-presentation-split", "scaling-disabled")
        svc.observer.consume_line(native, now=self.fixture.t["now"])
        self.assertTrue(svc._budget_can_scale({"scale_capable": True}))
        self.assertIsNone(svc._game_ignores_scale("game"))


if __name__ == "__main__":
    unittest.main()
