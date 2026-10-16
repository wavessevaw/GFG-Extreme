"""Sustained Boost is opt-in, Autopilot scoped, and still fails closed."""
import asyncio
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
from gfg_plugin.frame_os.policy import EnergyBroker, InjectionPolicy
from gfg_plugin.frame_os.runner import FrameOsRunner
from test_frame_os_proof import FakeChannel, FakeReader


class ContinuousPolicyTests(unittest.TestCase):
    def test_stays_boosted_for_minutes_without_input_or_saved_energy(self):
        p = InjectionPolicy(90, 30, broker=EnergyBroker(10))
        p.configure_continuous_boost(True)
        for i in range(1801):
            d = p.tick(i / 10, {}, draw_w=14, focused=True)
            self.assertEqual((d.level, d.real_hz, d.tdp_w), ('boost', 45, 14))
        self.assertEqual(p.broker.bank_j, 0)

    def test_off_returns_to_short_pulses_and_menu_always_cancels(self):
        p = InjectionPolicy(90, 30)
        p.configure_continuous_boost(True)
        self.assertEqual(p.tick(0, {}).level, 'boost')
        for rest_allowed in (True, False):
            p.rest_allowed = rest_allowed
            self.assertNotEqual(p.tick(5, {}, focused=False).level, 'boost')
        p.configure_continuous_boost(False)
        self.assertEqual(p.tick(6, {}).level, 'calm')
        p.tick(6.2, {})
        self.assertEqual(p.tick(6.3, {'camera': .9}).level, 'boost')
        self.assertEqual(p.tick(8, {'camera': .9}).level, 'calm')

    def test_disabled_or_ineffective_boost_is_not_forced(self):
        p = InjectionPolicy(90, 30)
        p.configure_continuous_boost(True)
        p.boost_allowed = False
        self.assertEqual(p.tick(0, {}).reason, 'boost-off-for-game')
        p.boost_allowed = True
        p._boost_blocked_until = 120
        self.assertEqual(p.tick(1, {}).reason, 'boost-ineffective')

    def test_continuous_delivery_must_sustain_the_requested_cadence(self):
        p = InjectionPolicy(90, 30)
        p.configure_continuous_boost(True)
        for i in range(40):
            p.tick(i / 10, {})
            p.note_delivered(i / 10, 36, short_window=True, exposure_s=.1)
        self.assertEqual(p.tick(4, {}).reason, 'boost-ineffective')


class ContinuousRunnerTests(unittest.TestCase):
    def test_live_ticks_renew_watts_but_stopped_runner_expires_them(self):
        now = [0.0]
        r = FrameOsRunner(FakeChannel(), clock=lambda: now[0], reader_factory=FakeReader)
        config = dict(enabled=True, mode='act', output_hz=90, calm_real_hz=30,
                      max_multiplier=4, calm_w=10, continuous_boost_enabled=True)
        r.configure(**config)
        r.executor_active = True
        for t in (0, 1, 2, 30, 90):
            now[0] = t
            status = r.tick(t)
            self.assertEqual(status['decision']['level'], 'boost')
            self.assertEqual(r.tdp_offset_w, 4)
        now[0] = 91
        self.assertEqual(r.tdp_offset_w, 0)
        r.configure(**{**config, 'continuous_boost_enabled': False})
        self.assertEqual(r.tick(91)['decision']['level'], 'calm')
        self.assertEqual(r.tdp_offset_w, 0)


class ContinuousSettingTests(unittest.TestCase):
    def setUp(self):
        from test_governor_runtime import RuntimeBase
        self.f = RuntimeBase()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.s = self.f.svc

    def test_opt_in_persists_independently_and_failed_save_rolls_back(self):
        s = self.s
        self.assertFalse(s.frame_os_features('game')['continuous_boost'])
        self.assertTrue(s.set_frame_os_feature('game', 'continuous_boost', True)['success'])
        self.assertTrue(s.frame_os_features('game')['continuous_boost'])
        self.assertFalse(s.frame_os_features('other')['continuous_boost'])
        with patch.object(s, '_save_settings', side_effect=OSError('full')):
            self.assertFalse(s.set_frame_os_feature('game', 'continuous_boost', False)['success'])
        self.assertTrue(s.frame_os_features('game')['continuous_boost'])
        self.assertFalse(s.set_frame_os_feature('game', 'continuous_boost', 'true')['success'])

    def test_disabling_cancels_active_decision_before_next_tick(self):
        s = self.s
        s._active_profile = 'game'
        s.set_frame_os_feature('game', 'continuous_boost', True)
        s.frame_os.configure(enabled=True, mode='act', output_hz=90, calm_real_hz=30,
                             max_multiplier=4, calm_w=10, continuous_boost_enabled=True)
        s.frame_os.policy.tick(0, {})
        s.set_frame_os_feature('game', 'continuous_boost', False)
        self.assertEqual(s.frame_os.last['decision']['level'], 'calm')
        self.assertFalse(s.frame_os.policy.boost_allowed)

    def test_configuration_scopes_continuous_boost_to_locked_autopilot(self):
        from gfg_plugin.governor_core import BudgetController
        s = self.s
        s._budget = BudgetController(target_output_fps=90, now=0)
        s._budget.phase = 'locked'
        s._point = {'key': s._budget.point.key}
        s._status['enabled'] = True
        s.set_frame_os_feature('game', 'continuous_boost', True)
        s.set_frame_os_feature('game', 'boost', False)
        for mode in ('budget', 'balanced', 'quality', 'extreme', 'autopilot'):
            with self.subTest(mode=mode), patch.object(s, '_frame_os_mode', return_value='act'):
                s._settings['profiles']['game']['mode'] = mode
                s._configure_frame_os('game')
                self.assertEqual(s.frame_os.policy.continuous_boost_enabled, mode == 'autopilot')
                self.assertEqual(s.frame_os.policy.boost_allowed, mode == 'autopilot')
        s._budget.phase = 'search_down'
        with patch.object(s, '_frame_os_mode', return_value='act'):
            s._configure_frame_os('game')
        self.assertFalse(s.frame_os.policy.boost_allowed)

    def test_sustained_watts_obey_normal_ceiling_and_scope(self):
        s = self.s
        s._settings['profiles']['game']['mode'] = 'autopilot'
        s.power.state.owned = True
        s._budget = SimpleNamespace(tdp_control=True, tdp=14, normal_max_w=15,
                                    min_w=3, last_reason='continuous-test')
        s.frame_os.configure(enabled=True, mode='act', output_hz=90, calm_real_hz=30,
                             max_multiplier=4, calm_w=14, continuous_boost_enabled=True)
        s.frame_os.executor_active = True
        s.frame_os.last = {'decision': {'level': 'boost', 'tdp_w': 18}}
        asyncio.run(s._apply_budget_tdp('game'))
        self.assertEqual(s.power.writes[-1], 14)
        s._settings['profiles']['game']['mode'] = 'balanced'
        asyncio.run(s._apply_budget_tdp('game'))
        self.assertEqual(s.power.writes[-1], 14)


if __name__ == '__main__':
    unittest.main()
