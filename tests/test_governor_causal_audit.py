"""Counterexamples found during the 2.1.3 audit, rather than policy snapshots."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'py_modules')]
from gfg_plugin.governor_core import BudgetController, WindowVerdict, window_verdict

GOOD = WindowVerdict(True, False, 'holds')
BAD = WindowVerdict(False, True, 'real-below-cap', short=True)


def controller():
    return BudgetController(target_output_fps=90, now=0, min_tdp_w=3, max_tdp_w=15)


class CausalAuditTests(unittest.TestCase):
    def test_deep_generating_gameplay_is_not_a_loading_screen(self):
        c=controller()
        for real in (5, 10, 12, 14):
            with self.subTest(real=real):
                v=window_verdict({'real':{'p5':real,'median':real},'output':{'median':real*3}},c.point)
                self.assertFalse(v.stall)
                self.assertTrue(v.short)

    def test_locked_play_refreshes_work_memory_beyond_fifteen_minutes(self):
        c=controller();c.phase='locked';c.tdp=c.draw_w=10;c.hold_probes=True
        for now in range(15, 1500, 15):c.observe(now,GOOD,30,90)
        self.assertEqual(c._work_tdp(1500),10)

    def test_work_point_from_different_cadence_does_not_inflate_recovery(self):
        c=controller();c.tdp=c.draw_w=14;c._remember_held(1)
        c.idx=next(i for i,p in enumerate(c.points) if p.key=='45x2')
        c.tdp=c.draw_w=9;c._remember_held(2)
        self.assertEqual(c._work_tdp(3),9)
        c._now=3
        self.assertEqual(c.status()['work_tdp_w'],9,'diagnostics must match the actual context')
        c._now=1000
        self.assertIsNone(c.status()['work_tdp_w'],'expired evidence cannot remain live in status')

    def test_work_memory_has_a_cardinality_bound(self):
        c=controller();c.tdp=c.draw_w=10
        for n in range(2000):c._remember_held(n/10)
        self.assertLessEqual(len(c.held),128)

    def test_slow_rollback_restores_work_point_without_draw_sensor(self):
        c=controller();c.tdp=c.draw_w=13;c._remember_held(1)
        c.tdp=6;c.draw_w=None;c.last_good=(c.idx,7);c.phase='search_down';c.probe='down'
        c.observe(30,BAD,15,45)
        self.assertEqual(c.tdp,13)
        self.assertEqual(c.phase,'upgrade')
        self.assertEqual(c.good,0)

    def test_marginal_economy_failure_does_not_restore_a_heavier_scene(self):
        c=controller();c.tdp=c.draw_w=13;c._remember_held(1)
        c.tdp=6;c.draw_w=None;c.last_good=(c.idx,7);c.phase='search_down';c.probe='down'
        c.observe(30,WindowVerdict(False,False,'real-below-cap',short=True),27,81)
        self.assertEqual(c.tdp,7,'mild probe failure needs its rollback point, not historical maximum')

    def test_periodic_slow_recovery_needs_two_windows_before_reprobe(self):
        c=controller();c.tdp=c.draw_w=13;c._remember_held(1)
        c.tdp=6;c.draw_w=None;c.last_good=(c.idx,7);c.phase='probe';c.probe='down'
        c.observe(30,BAD,15,45)
        self.assertEqual(c.tdp,13)
        self.assertEqual(c.observe(300,GOOD,30,90),'hold')
        self.assertIsNone(c.probe)
        self.assertIsNone(c.settled_since)

    def test_expired_lock_cannot_reprobe_on_single_new_healthy_window(self):
        c=controller();c.tdp=7;c._fast_raise(1)
        self.assertEqual(c.observe(100,GOOD,30,90),'hold')
        self.assertIsNone(c.probe)

    def test_invalid_draw_never_proves_binding(self):
        for draw in (float('inf'),float('nan'),True,-1):
            with self.subTest(draw=draw):
                c=controller();c.tdp=6
                c.fast_check(1,15,draw);c.fast_check(2,15,draw)
                self.assertEqual(c.tdp,6)

    def test_hot_apu_does_not_take_fast_watt_increase(self):
        c=controller();c.tdp=6;c.set_thermal('hot',1)
        c.fast_check(1,15,6);c.fast_check(2,15,6)
        self.assertEqual(c.tdp,6)

    def test_locked_new_power_is_not_proven_until_two_fresh_windows(self):
        c=controller();c.phase='locked';c.tdp=10;c.last_good=(c.idx,10)
        c.tdp=6;c.fast_check(1,15,6);c.fast_check(2,15,6)
        self.assertEqual(c.last_good,(c.idx,10))
        self.assertIsNone(c.settled_since)
        c.draw_w=c.tdp
        c.observe(15,GOOD,30,90)
        self.assertEqual(c.last_good,(c.idx,10))
        c.observe(30,GOOD,30,90)
        self.assertEqual(c.last_good,(c.idx,c.tdp))
        self.assertIsNotNone(c.settled_since)


class TargetRecoveryAuditTests(unittest.TestCase):
    def service(self,c):
        from gfg_plugin.autopilot.planner import TargetPolicy
        from gfg_plugin.governor_service import GovernorService
        s=GovernorService.__new__(GovernorService)
        s._mode=lambda p:'autopilot';s._profile_enabled=lambda p:True
        s._autopilot_arbiter=SimpleNamespace(freeze_tdp=False);s._autopilot_targets=TargetPolicy()
        s._autopilot_preference=lambda p:'auto';s._menu_since=None;s._menu_covering=lambda:False
        s._autopilot_transition_seq=0;s._generation_seen=None;s._clock=lambda:100
        s._status={};s._budget=c
        return s

    def summary(self,n):
        return {'samples':8,'real':{'median':15},'output':{'median':45},
                'first_sample_seq':n-7,'last_sample_seq':n,'sample_span_s':4}

    def test_unreachable_historical_watts_cannot_hold_goal_forever(self):
        c=controller();c.tdp=c.draw_w=7;c.normal_max_w=7;c.held=[(1,13)]
        s=self.service(c)
        for n in (10,20,30):goal=s._governor_target('game',90,self.summary(n))
        self.assertEqual(goal,45)

    def test_recovery_discards_pending_downshift_evidence(self):
        c=controller();c.tdp=c.draw_w=10
        s=self.service(c)
        s._governor_target('game',90,self.summary(10))
        s._governor_target('game',90,self.summary(20))
        c.held=[(90,13)]
        self.assertEqual(s._governor_target('game',90,self.summary(30)),90)
        c.tdp=c.draw_w=13
        self.assertEqual(s._governor_target('game',90,self.summary(40)),90,
                         'misses before recovery are not evidence against its result')

    def test_recovery_at_lower_goal_does_not_disagree_with_target_policy(self):
        c=BudgetController(target_output_fps=45,now=0,min_tdp_w=3,max_tdp_w=15)
        c.tdp=c.draw_w=6;c.held=[(90,10)]
        s=self.service(c)
        s._autopilot_targets.update(90,None,None,'auto',False,now=0)
        s._autopilot_targets.target=45
        summary=self.summary(10);summary['real']['median']=7;summary['output']['median']=21
        self.assertEqual(s._governor_target('game',90,summary),45,
                         'power recovery must preserve current goal until TargetPolicy trials 90')


if __name__=='__main__':unittest.main()
