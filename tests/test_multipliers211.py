"""Normal quarter-step range, launch reservation and actual renderer limits."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
from gfg_plugin.governor_core import BudgetController, TrialLadder


class MultiplierRangeTests(unittest.TestCase):
    def test_every_budget_mode_offers_deep_quarter_steps_but_obeys_live_capacity(self):
        for hz in (60, 90):
            for flavor, minimize in (('battery', False), ('balanced', False),
                                     ('extreme', False), ('battery', True)):
                with self.subTest(hz=hz, flavor=flavor, autopilot=minimize):
                    c = BudgetController(target_output_fps=hz, now=0,
                                         flavor=flavor, minimize_tdp=minimize)
                    for ratio in (3.25, 3.5, 3.75):
                        i = next(i for i, p in enumerate(c.points)
                                 if p.multiplier == ratio and p.render_scale_pct == 100)
                        self.assertFalse(c.points[i].degraded)
                        c.current_max_multiplier = 3
                        self.assertFalse(c._usable(i, 0))
                        c.current_max_multiplier = 4
                        self.assertTrue(c._usable(i, 0))
                    self.assertEqual(c.rejected, {})

    def test_quality_can_reach_x375_within_its_trial_limit(self):
        for hz in (60, 90):
            with self.subTest(hz=hz):
                ladder = TrialLadder(target_output_fps=hz, preserve_resolution=True)
                tried = []
                while (point := ladder.next_point(lambda p: None)) is not None:
                    tried.append(point.multiplier)
                    ladder.mark_attempt()
                    ladder.reject(point.key, 'real-below-cap')
                self.assertEqual(tried, [1 + n / 4 for n in range(12)])
                self.assertEqual(ladder.attempts, ladder.MAX_ATTEMPTS)


class LaunchCapacityTests(unittest.TestCase):
    def setUp(self):
        from test_governor_runtime import RuntimeBase
        self.fixture = RuntimeBase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_all_modes_reserve_x4_without_overwriting_saved_or_enabling_fusion_elsewhere(self):
        s = self.fixture.svc
        saved = s._saved_profile_config('game')
        before = copy.deepcopy(saved)
        for mode in ('budget', 'balanced', 'quality', 'extreme', 'autopilot'):
            with self.subTest(mode=mode):
                s._settings['profiles']['game']['mode'] = mode
                base = s._base_for('game', saved)
                self.assertEqual(base['adaptive_max_multiplier'], 4)
                self.assertEqual(base['gfg_frame_fusion'], mode == 'autopilot')
                self.assertEqual(saved, before)
        s._settings['profiles']['game']['enabled'] = False
        self.assertFalse(s._base_for('game', saved)['gfg_frame_fusion'])


if __name__ == '__main__':
    unittest.main()
