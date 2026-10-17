"""Trajectory invariants across reproducible transitions, using real policy."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from governor_scenario_bench import SCENARIOS,run


class ScenarioBenchTests(unittest.TestCase):
    def test_all_scenarios_respect_limits_and_reservations(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                r=run(name)
                for row in r['trace']:
                    self.assertGreaterEqual(row['requested_w'],3)
                    self.assertLessEqual(row['requested_w'],row['ceiling_w'])
                self.assertTrue(all(not (120<=w['t']<150) for w in r['decisions'])
                                if name=='competing_regulator' else True)
                self.assertLess(r['metrics']['actions'],80,'no 1 Hz policy oscillation')

    def test_active_resume_recovers_in_a_bounded_time(self):
        for name in ('light_to_heavy','pause_resume','loading_resume'):
            with self.subTest(scenario=name):
                r=run(name)
                self.assertFalse(r['metrics']['unrecovered_at_end'])
                self.assertLessEqual(r['metrics']['max_completed_recovery_s'],35)

    def test_replay_is_deterministic(self):
        self.assertEqual(run('sensor_noise'),run('sensor_noise'))


if __name__=='__main__':unittest.main()
