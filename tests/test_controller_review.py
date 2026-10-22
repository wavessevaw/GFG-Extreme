"""Behavior regressions from the 3.0.0 audit; no hardware access."""
import math
import unittest
from helpers import Clock
from test_core import FakeActuator
from gfg_plugin.autopilot import Autopilot
from gfg_plugin.governor import PowerGovernor, healthy
from gfg_plugin.pilot import PointPilot
from gfg_plugin.policy import Policy, PolicyCoordinator
from gfg_plugin.session_stats import SessionStats


def sample(**kw):
    s = dict(game=True, key='app:1|90', objective='balanced', cap=30, epoch=1,
             real=30., pace=1., over_budget=0., ring_miss=0., temp_c=70.)
    s.update(kw)
    return s


class ControllerReviewTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.act = FakeActuator()
        self.gov = PowerGovernor(self.act, None, clock=self.clock)

    def feed(self, seconds, **kw):
        for _ in range(seconds):
            self.clock.t += 1
            self.gov.tick(sample(**kw))

    def test_thermal_recovers_even_while_pilot_requests_ceiling(self):
        self.feed(1, temp_c=98)
        self.assertEqual(self.act.tdp, 4)
        self.feed(140, hold_ceiling=True)
        self.assertEqual(self.act.tdp, 15)
        self.assertIsNone(self.gov.thermal_ceiling)

    def test_quality_restores_user_power_after_cooling(self):
        self.feed(1, objective='quality', temp_c=98)
        self.feed(140, objective='quality')
        self.assertEqual(self.act.tdp, 15)

    def test_severe_real_drop_restores_within_three_new_samples(self):
        self.feed(1, objective='quality')
        self.gov._write(10, 'prior operating point')
        self.feed(3, objective='quality', real=0)
        self.assertEqual(self.act.tdp, 15)

    def test_unknown_temperature_does_not_relax_thermal_ceiling(self):
        self.feed(1, temp_c=98)
        self.feed(140, hold_ceiling=True, temp_c=None)
        self.assertEqual(self.act.tdp, 4)

    def test_sparse_samples_do_not_prove_window(self):
        self.gov.tick(sample())
        self.act.writes.clear()   # the first tick sets the start level (10/12 W, 3.0.1)
        self.clock.t += 10
        self.gov.tick(sample())
        self.assertEqual(self.act.writes, [])

    def test_nonfinite_pace_cannot_prove_health(self):
        # A missing pace stays allowed: with generation off there is none, and the Governor
        # must still save power then. Broken (non-finite) readings never prove health.
        for value in (math.nan, math.inf):
            with self.subTest(pace=value):
                verdict = healthy([dict(real=30, pace=value)], 30, True)
                self.assertIsNot(verdict['ok'], True)

    def test_active_clock_probe_holds_tdp_but_thermal_preempts(self):
        self.feed(1)
        self.act.writes.clear()
        self.feed(40, probe_active=True)
        self.assertEqual(self.act.writes, [])
        self.feed(1, probe_active=True, temp_c=98)
        self.assertEqual(self.act.tdp, 4)

    def test_clock_probe_end_requires_new_governor_window(self):
        self.feed(1)
        self.act.writes.clear()
        start = self.act.tdp
        self.feed(40, probe_active=True)
        self.feed(3)
        self.assertEqual(self.act.writes, [])
        self.feed(12)
        self.assertLess(self.act.tdp, start)

    def test_service_propagates_active_probe(self):
        from sandbox.run import make_rig
        from sandbox.vdeck import VGame
        r = make_rig(VGame('steady', 120, noise=0), fg='x3', objective='battery', split=False, gpu_clock=False)
        class ActiveProbe:
            changes = 0
            cpu = type('Cpu', (), {'owned': True})()
            def settling(self): return True
            def tick(self, ctx): return {'phase': 'probe'}
            def stop(self): pass
        try:
            for _ in range(40):
                r.engine.step(); r.sensors.step(); r.service.tick(); r.clock.t += 1
            r.service.split = ActiveProbe()
            before = r.power.tdp
            for _ in range(15):
                r.engine.step(); r.sensors.step(); r.service.tick(); r.clock.t += 1
            self.assertEqual(r.power.tdp, before)
        finally:
            r.service.stop()

    def test_restore_failure_blocks_new_claim_until_restored(self):
        class RestoreFailure(FakeActuator):
            fail = True
            def restore_if_owned(self):
                if self.fail:
                    return dict(success=False, restored=False, error='transient')
                return super().restore_if_owned()
        a = RestoreFailure()
        g = PowerGovernor(a, None, clock=self.clock)
        g.tick(sample())
        g._write(10, 'simulate existing lower operating point')
        g.tick(sample(game=False))
        g.tick(sample(key='app:2|90', objective='quality'))
        self.assertEqual(a.initial, 15)
        self.assertTrue(g.status()['restore_pending'])
        a.fail = False
        g.tick(sample(key='app:2|90', objective='quality'))
        self.assertEqual(a.initial, 15)
        self.assertEqual(a.tdp, 15)
        self.assertFalse(g.status()['restore_pending'])

    def test_stale_auto_cannot_lock_from_old_measurement(self):
        p = PointPilot(clock=self.clock)
        ctx = dict(fg='auto', objective='balanced', refresh=90, app=1, game=True,
                   confirmed=True, real=45, pace=1, at_ceiling=True,
                   engine=dict(auto=True, cap_fps=45, time_ns=1))
        p.tick(ctx)
        self.clock.t += 13
        ctx.update(confirmed=False, real=None, engine={})
        self.assertNotEqual(p.tick(ctx)['phase'], 'locked')

    def test_repeated_status_does_not_count_as_stability(self):
        p = PointPilot(clock=self.clock)
        ctx = dict(fg='auto', objective='balanced', refresh=90, app=1, game=True,
                   confirmed=True, real=45, pace=1, at_ceiling=True,
                   engine=dict(auto=True, cap_fps=45, time_ns=1))
        for _ in range(20):
            self.clock.t += 1
            result = p.tick(ctx)
        self.assertNotEqual(result['phase'], 'locked')

    def test_fresh_auto_still_locks(self):
        p = PointPilot(clock=self.clock)
        for _ in range(20):
            self.clock.t += 1
            result = p.tick(dict(fg='auto', objective='balanced', refresh=90, app=1, game=True,
                                confirmed=True, real=45, pace=1, at_ceiling=True,
                                engine=dict(auto=True, cap_fps=45, time_ns=int(self.clock()*1e9))))
        self.assertEqual(result['point'], 45)
        self.assertEqual(result['phase'], 'locked')

    def test_smoothness_thermal_hysteresis(self):
        a = Autopilot(clock=self.clock)
        modes = []
        for temp in (84.9, 85.1, 84.9, 85.1):
            modes.append(a.decide('smoothness', {}, temp)['objective'])
            self.clock.t += 1
        # 3.0.4: Autopilot is one adaptive mode; heat changes its reason, not its mode.
        self.assertEqual(modes, ['autopilot'] * 4)
        self.assertTrue(a.hot)

    def test_expensive_filter_change_invalidates_epoch(self):
        c = PolicyCoordinator(None, clock=self.clock)
        c.want(Policy(3))
        epoch = c.s.epoch
        c.want(Policy(3, post='smaa'))
        self.assertGreater(c.s.epoch, epoch)

    def test_no_energy_savings_inferred_from_unused_limit(self):
        s = SessionStats(); s.start('game', 0)
        for i in range(1, 61):
            s.add(i, output=90, real=30, tdp=15, draw=8, reference_w=15)
        self.assertIsNone(s.summary()['saved_wh'])

    def test_zero_fps_included_in_average(self):
        s = SessionStats(); s.start('game', 0)
        for i in range(1, 61):
            s.add(i, output=90 if i<=30 else 0, real=30 if i<=30 else 0,
                  tdp=15, draw=8, reference_w=15)
        self.assertEqual(s.summary()['avg_output_fps'], 45)
        self.assertEqual(s.summary()['avg_real_fps'], 15)
