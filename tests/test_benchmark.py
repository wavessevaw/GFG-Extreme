import unittest
import helpers
from gfg_plugin.benchmark import AdaptiveBenchmark

CTX = dict(app=42, refresh=90, dock=False, ac=False, post='vibrance,detail=1')

class AdaptiveBenchmarkTest(unittest.TestCase):
    def run_sweep(self, mode, fps_for_watts, context=None):
        ctx = context or CTX
        b = AdaptiveBenchmark()
        b.start(context=ctx, mode=mode, ceiling=12, floor=5, ladder=[30, 36, 40, 45], now=0)
        history = [b.watts]
        for t in range(1, 40):
            fps = fps_for_watts(b.watts)
            b.feed(dict(seq=t, frame_ms=[1000/fps]*40, draw_w=b.watts*.8,
                        gpu=95, cpu=50, temp=65, tdp=b.watts, fresh=True), context=ctx, now=t)
            if b.watts != history[-1]: history.append(b.watts)
            if not b.active:
                b.completed_at, b.watt_trace = t, history
                return b
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
        self.assertFalse(any(p['purpose']=='control' for p in battery.points))
        self.assertLessEqual(battery.completed_at, 15)
        self.assertEqual(battery.watt_trace.count(12), 1)
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
        for change in ({'tdp':10},{'menu':True},{'temp':90}):
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
        self.assertEqual(b.phase,'result')
        self.assertFalse(b.result['passed'])

    def test_missing_power_or_frames_never_produces_recommendation(self):
        b=AdaptiveBenchmark();b.start(context=CTX,mode='quality',ceiling=12,floor=5,ladder=[30],now=0)
        for t in range(1,64):
            b.feed(dict(seq=t,fresh=True,temp=60,tdp=12,frame_ms=[],draw_w=None),context=CTX,now=t)
        self.assertEqual(b.phase,'result')
        self.assertFalse(b.result['passed'])


    def test_quick_sweep_is_bounded_and_does_not_return_to_ceiling(self):
        for mode in ('quality','balanced','battery','autopilot'):
            b = self.run_sweep(mode, lambda w: min(50, w * 5))
            self.assertLessEqual(b.completed_at, 15, (mode, b.status()))
            self.assertTrue(b.result is not None)
            self.assertEqual(b.watt_trace.count(12), 1, b.watt_trace)
            steps = b.watt_trace
            # One upward jump is allowed solely to confirm the selected point.
            rises = sum(y > x for x, y in zip(steps, steps[1:]))
            self.assertLessEqual(rises, 1, steps)

    def test_one_stale_compositor_read_is_not_a_cancellation(self):
        b = AdaptiveBenchmark()
        b.start(context=CTX, mode='battery', ceiling=12, floor=5,
                ladder=[30, 40], now=0)
        b.feed(dict(seq=1, fresh=False), context=CTX, now=1)
        self.assertTrue(b.active)
        self.assertNotEqual(b.phase, 'aborted')

    def test_15_second_deadline_never_fabricates_measurements(self):
        b = AdaptiveBenchmark()
        b.start(context=CTX, mode='battery', ceiling=12, floor=5,
                ladder=[30, 40], now=0)
        for t in range(1, 17):
            b.feed(dict(seq=t, fresh=True, frame_ms=[], draw_w=None, tdp=12),
                   context=CTX, now=t)
        self.assertEqual(b.phase, 'result')
        self.assertFalse(b.result['passed'])
        self.assertEqual(b.result['confidence'], 'insufficient')

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

    def test_fractional_presentation_does_not_inflate_native_fps(self):
        from gfg_plugin.benchmark import summarize
        frames=[1000/45,1000/45,1000/45,1000/30]*10
        samples=[dict(frame_ms=frames,draw_w=9,gpu=90,cpu=40,temp=60) for _ in range(6)]
        result=summarize(samples)
        self.assertAlmostEqual(result['fps'],40)
        self.assertAlmostEqual(result['low_fps'],40)
        self.assertAlmostEqual(result['p95_ms'],1000/30)

    def test_out_of_ladder_applied_point_does_not_restart_full_power_probe(self):
        from gfg_plugin.pilot import PointPilot
        from helpers import Clock
        pilot=PointPilot(clock=Clock())
        r=pilot.tick(dict(app=42,refresh=90,fg='auto',objective='quality',
                          game=True,benchmark_applied=True,
                          benchmark_point=24,known_point=24))
        self.assertEqual(r['phase'],'locked')
        self.assertFalse(r['hold_ceiling'])
        self.assertGreaterEqual(r['point'],40)

    def test_applied_quality_point_is_not_clipped_to_half_refresh(self):
        from gfg_plugin.pilot import PointPilot
        from helpers import Clock
        pilot=PointPilot(clock=Clock())
        result=pilot.tick(dict(app=42,refresh=90,fg='auto',objective='quality',game=True,
                              benchmark_point=58,known_point=58))
        self.assertEqual(result['base_fps'],58)

    def test_battery_uses_measured_target_instead_of_old_lowest_point(self):
        from gfg_plugin.pilot import PointPilot
        from helpers import Clock
        pilot=PointPilot(clock=Clock())
        result=pilot.tick(dict(app=42,refresh=90,fg='auto',objective='battery',game=True,
                              above_x3=True,benchmark_point=30,known_point=30))
        self.assertEqual(result['base_fps'],30)
