import unittest
import helpers
from sandbox.run import make_rig
from sandbox.vdeck import VGame

class BenchmarkSessionTest(unittest.TestCase):
    def test_hud_start_cancel_restores_original_power_and_filters(self):
        r=make_rig(VGame('steady',60,noise=0),objective='battery',split=False,gpu_clock=False,user_tdp=11)
        r.settings.data['profiles']['default']['filters']['focus']=True
        seq=0
        original=r.service.ctl.status
        def status():
            return dict(original(),hud_input_version=1,hud_event_seq=seq,hud_event=1,
                        native_frame_ms=[20]*50,transfer='sdr')
        r.service.ctl.status=status
        for _ in range(5):
            r.engine.step();r.sensors.step();r.service.tick();r.clock.t+=1
        seq=1
        r.engine.step();r.sensors.step();r.service.tick()
        b=r.service.benchmark
        self.assertTrue(b.b.active,b.message)
        self.assertLessEqual(b.b.ceiling,11)
        self.assertIn('detail=1',b.b.context['post'])
        self.assertEqual(r.service.coord.wanted.multiplier,0)
        b.abort('cancel')
        self.assertEqual(r.power.tdp,11)
        self.assertIsNone(b.saved)
        self.assertTrue(r.settings.data['profiles']['default']['filters']['focus'])
        r.service.stop()

    def test_stop_during_sweep_restores_and_does_not_resume(self):
        r=make_rig(VGame('steady',60),split=False,gpu_clock=False,user_tdp=12)
        for _ in range(3):
            r.engine.step();r.sensors.step();r.service.tick();r.clock.t+=1
        b=r.service.benchmark
        st=dict(r.service.ctl.status(),hud_input_version=1,native_frame_ms=[20]*50,transfer='sdr')
        _,p=r.settings.profile_for(r.service.app)
        ctx=b.context(st,p,{},90,False)
        b.begin(st,p,ctx,r.clock.t)
        self.assertTrue(b.b.active,b.message)
        r.service.stop()
        self.assertEqual(r.power.tdp,12)
        self.assertIsNone(b.saved)
        self.assertEqual(b.b.phase,'aborted')

    def test_complete_hud_measure_apply_and_profile_persistence(self):
        r=make_rig(VGame('plateau',60,noise=0),objective='battery',split=False,gpu_clock=False,user_tdp=10)
        event=[0,0]
        original=r.service.ctl.status
        def status():
            base=original()
            # Deterministic native intervals are fixture data, not hardware measurements.
            fps=min(50, r.power.tdp*5)
            return dict(base,hud_input_version=1,hud_event_seq=event[0],hud_event=event[1],
                        native_frame_ms=[1000/fps]*40,transfer='sdr')
        r.service.ctl.status=status
        for t in range(500):
            if t==5: event[:]=[1,1]
            r.engine.step();r.sensors.step();r.service.tick();r.clock.t+=1
            b=r.service.benchmark
            if b.b.phase=='result' and b.saved is None: break
        self.assertIsNotNone(b.b.result, b.status())
        self.assertTrue(b.b.result['passed'],b.b.result)
        self.assertTrue(b.b.result['fg_verified'])
        event[:]=[2,3]
        r.engine.step();r.sensors.step();r.service.tick()
        records=r.settings.data.get('benchmarks',{})
        self.assertEqual(len(records),1,b.status())
        self.assertEqual(next(iter(records.values()))['mode'],'battery')
        self.assertEqual(b.b.phase,'idle')
        r.service.stop()

    def test_policy_echo_without_generated_frames_does_not_pass(self):
        from gfg_plugin.policy import Policy
        from gfg_plugin.benchmark_session import BenchmarkSession
        b=BenchmarkSession(None)
        b.saved=Policy(multiplier=3)
        b.display_start=dict(real=100,gen=50,repeat=0,focus_frames=10)
        st=dict(real=200,gen=50,repeat=0,focus_frames=30,focus_status='processing')
        self.assertFalse(b.display_evidence(st,dict(post='detail=1',hdr='sdr'))['passed'])
        st['gen']=250
        self.assertTrue(b.display_evidence(st,dict(post='detail=1',hdr='sdr'))['passed'])
        st['focus_frames']=10
        self.assertFalse(b.display_evidence(st,dict(post='detail=1',hdr='sdr'))['passed'])
        self.assertTrue(b.display_evidence(st,dict(post='detail=1',hdr='pq'))['passed'])
        st['gen']=0
        self.assertFalse(b.display_evidence(st,dict(post='',hdr='sdr'))['passed'])
