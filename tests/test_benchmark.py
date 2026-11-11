import unittest
import helpers
from gfg_plugin.benchmark import AdaptiveBenchmark

CTX = dict(app=42, refresh=90, dock=False, ac=False, post='vibrance,detail=1')

class AdaptiveBenchmarkTest(unittest.TestCase):
    def run_sweep(self, mode, fps_for_watts, context=None):
        ctx = context or CTX
        b = AdaptiveBenchmark()
        b.start(context=ctx, mode=mode, ceiling=12, floor=5, ladder=[30, 36, 40, 45], now=0)
        for t in range(1, 800):
            fps = fps_for_watts(b.watts)
            b.feed(dict(seq=t, frame_ms=[1000/fps]*40, draw_w=b.watts*.8,
                        gpu=95, cpu=50, temp=65, tdp=b.watts, fresh=True), context=ctx, now=t)
            if not b.active: return b
        self.fail('Sweep did not terminate')

    def test_modes_choose_different_measured_points(self):
        curve = lambda w: min(52, w*5)
        quality = self.run_sweep('quality', curve)
        balanced = self.run_sweep('balanced', curve)
        battery = self.run_sweep('battery', curve)
        self.assertTrue(all(b.result['passed'] for b in (quality,balanced,battery)))
        self.assertGreater(quality.result['tdp'], balanced.result['tdp'])
        self.assertGreater(balanced.result['tdp'], battery.result['tdp'])
        self.assertEqual(battery.result['tdp'], 6)
        self.assertTrue(any(p['purpose']=='control' for p in battery.points))
        self.assertEqual(battery.points[-1]['purpose'], 'verify')

    def test_unachievable_target_is_not_success(self):
        b = self.run_sweep('battery', lambda w: 25)
        self.assertFalse(b.result['passed'])
        self.assertEqual(b.result['measured']['fps'],25)

    def test_cpu_bound_plateau_uses_actual_sweep(self):
        b = self.run_sweep('quality', lambda w: 48)
        self.assertEqual(b.result['tdp'],5)
        self.assertTrue(b.result['passed'])

    def test_lcd_target_uses_refresh(self):
        b = self.run_sweep('battery', lambda w: min(60,w*5), dict(CTX,refresh=60))
        self.assertEqual(b.result['target'],30)

    def test_external_changes_and_menu_abort(self):
        for change in ({'tdp':10},{'menu':True},{'temp':90},{'fresh':False}):
            b=AdaptiveBenchmark();b.start(context=CTX,mode='balanced',ceiling=12,floor=5,ladder=[30,40],now=0)
            s=dict(seq=1,frame_ms=[25]*40,draw_w=9,gpu=90,cpu=50,temp=65,tdp=12,fresh=True)
            b.feed(dict(s,**change),context=CTX,now=4)
            self.assertEqual(b.phase,'aborted')
            self.assertIsNone(b.result)

    def test_power_display_and_game_changes_abort(self):
        for ctx in (dict(CTX,ac=True),dict(CTX,refresh=60),dict(CTX,app=43),dict(CTX,post='')):
            b=AdaptiveBenchmark();b.start(context=CTX,mode='quality',ceiling=12,floor=5,ladder=[30,40],now=0)
            b.feed({},context=ctx,now=1)
            self.assertEqual(b.phase,'aborted')

    def test_unstable_scene_rejects_result(self):
        b=AdaptiveBenchmark();b.start(context=CTX,mode='autopilot',ceiling=12,floor=5,ladder=[30,40,45],now=0)
        for t in range(1,70):
            fps=50 if ((t-4)//6)%2==0 else 25
            b.feed(dict(seq=t,frame_ms=[1000/fps]*40,draw_w=9,gpu=90,cpu=50,temp=65,tdp=12,fresh=True),context=CTX,now=t)
            if not b.active: break
        self.assertEqual(b.phase,'aborted')

    def test_missing_power_or_frames_never_produces_recommendation(self):
        b=AdaptiveBenchmark();b.start(context=CTX,mode='quality',ceiling=12,floor=5,ladder=[30],now=0)
        for t in range(1,64):
            b.feed(dict(seq=t,fresh=True,temp=60,tdp=12,frame_ms=[],draw_w=None),context=CTX,now=t)
        self.assertEqual(b.phase,'aborted')

    def test_quality_seed_survives_new_governor_session(self):
        from test_core import FakeActuator
        from helpers import Clock
        from gfg_plugin.governor import PowerGovernor
        from test_controller_review import sample
        act=FakeActuator(); clock=Clock(); gov=PowerGovernor(act,None,clock=clock)
        gov.tick(sample(objective='quality',benchmark_seed=True,start_w=9,cap=45,real=45))
        self.assertTrue(gov.benchmark_seed)
        self.assertEqual(gov.start_hint,9)
        self.assertEqual(act.tdp,9)
        gov.stop()
