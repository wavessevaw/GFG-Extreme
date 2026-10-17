"""Release regressions: a short boost must end, scopes must close, logs must survive rotation."""
import asyncio
import json
import sys
import tempfile
import unittest
import zipfile
import time
from types import SimpleNamespace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'py_modules'))
from gfg_plugin.frame_os.policy import InjectionPolicy, EnergyBroker
from gfg_plugin.frame_os.burst import BurstCadence
from gfg_plugin.autopilot.power_window import PowerWindow
from gfg_plugin.autopilot.arbiter import _gain
from test_session_recorder import RecorderTests


class ShortBurstTests(unittest.TestCase):
    def test_seconds_between_pulses_are_not_unsuccessful_boost_exposure(self):
        p=InjectionPolicy(90,30)
        for i in range(6):
            t=i*5;p.tick(t,{'camera':0});p.tick(t+.2,{'camera':0})
            p.tick(t+.3,{'camera':.9});p.tick(t+2,{'camera':0})
            p.note_delivered(t+2,30,short_window=True,exposure_s=.2)
        self.assertAlmostEqual(p._boost_missing_s,1.2)
        self.assertFalse(any('boost-ineffective' in h for h in p.history))
    def test_a_partial_short_acceleration_does_not_need_to_hold_the_full_target(self):
        p=InjectionPolicy(90,30)
        for burst in range(6):
            t=burst*3;p.tick(t,{'camera':0});p.tick(t+.2,{'camera':0})
            for i in range(15):
                now=t+.3+i/10;p.tick(now,{'camera':.9})
                p.note_delivered(now,36,short_window=True)
            p.tick(t+2,{'camera':0})
        self.assertFalse(any('boost-ineffective' in h for h in p.history))
    def test_held_camera_stops_and_cannot_renew_a_long_boost(self):
        p=InjectionPolicy(90,30,broker=EnergyBroker(10,bank_j=100))
        levels=[p.tick(i/10,{'camera':.9,'idle_s':0},draw_w=10).level for i in range(200)]
        self.assertTrue(all(v=='boost' for v in levels[:15]))
        self.assertTrue(all(v=='calm' for v in levels[15:]))
        self.assertEqual(p.tick(20,{'camera':0,'idle_s':1}).level,'calm')
        p.tick(20.2,{'camera':0,'idle_s':1})
        self.assertEqual(p.tick(20.3,{'camera':.9,'idle_s':0}).level,'boost')

    def test_touch_gyro_is_bounded_until_another_contact(self):
        p=InjectionPolicy(90,30);p.configure_touch_boost(True)
        inp={'touch_signal_fresh':True,'right_stick_touch':True,'touch_generation':1,'gyro_dps':90,'idle_s':0}
        self.assertEqual(p.tick(0,inp).level,'boost')
        for i in range(1,100):
            d=p.tick(i/10,inp)
            if i>=15:self.assertEqual(d.level,'calm')
        p.tick(10,{**inp,'right_stick_touch':False})
        self.assertEqual(p.tick(10.2,{**inp,'touch_generation':2}).level,'boost')

    def test_menu_scope_cancels_scene_camera_and_contact(self):
        p=InjectionPolicy(90,30)
        p.tick(0,{'camera':.9,'idle_s':0})
        self.assertEqual(p.tick(.1,{'camera':.9,'idle_s':0},focused=False).level,'rest')
        self.assertEqual(p.tick(.2,{'camera':.9,'idle_s':0},focused=True).level,'calm')

    def test_unsuccessful_short_windows_back_off_across_distinct_bursts(self):
        p=InjectionPolicy(90,30)
        for burst in range(5):
            t=burst*3
            p.tick(t,{'camera':0,'idle_s':1});p.tick(t+.2,{'camera':0,'idle_s':1})
            for i in range(15):
                now=t+.3+i/10;p.tick(now,{'camera':.9,'idle_s':0})
                p.note_delivered(now,30,short_window=True)
            p.tick(t+2,{'camera':0,'idle_s':1})
        self.assertTrue(any('boost-ineffective' in h for h in p.history))


class BurstCadenceTests(unittest.TestCase):
    def telemetry(self,f,ns,**kw):
        return {'live':True,'writer_pid':10,'applied_generation':1,'swapchain_recreations':0,'frames':f,'last_present_ns':ns,**kw}

    def test_short_pulse_is_measured_even_when_the_long_median_is_still_calm(self):
        p=BurstCadence();p.sample(self.telemetry(100,1_000_000_000,present_interval_p50_ms=33.33))
        hz=p.sample(self.telemetry(109,1_200_000_000,present_interval_p50_ms=33.33))
        self.assertAlmostEqual(hz,45)
        self.assertIsNone(p.sample(self.telemetry(109,1_200_000_000)))

    def test_old_policy_new_writer_reset_and_long_gaps_cannot_be_counted(self):
        for kw in ({'applied_generation':2},{'writer_pid':11},{'swapchain_recreations':1},{'live':False}):
            p=BurstCadence();p.sample(self.telemetry(100,1_000_000_000))
            self.assertIsNone(p.sample(self.telemetry(109,1_200_000_000,**kw)))
        p=BurstCadence();p.sample(self.telemetry(100,1_000_000_000))
        self.assertIsNone(p.sample(self.telemetry(160,3_000_000_000)))


class PowerProofTests(unittest.TestCase):
    def test_long_boost_memory_cannot_disable_the_new_short_policy(self):
        from gfg_plugin.frame_os.memory import GameMemory
        old={'pairs':{'frames':[0]*10,'response':[10]*10},'off':{'boost':2,'shaping':2},'sessions':3}
        new=GameMemory(old,boost_policy=1)
        self.assertFalse(new.disabled()['boost'])
        self.assertTrue(new.disabled()['shaping'])
        self.assertEqual(new.pairs['response'],[10]*10)
        self.assertEqual(new.pairs['frames'],[])
        self.assertEqual(new.to_record()['boost_policy'],1)
    def test_single_power_dip_cannot_accept_a_quality_tradeoff(self):
        before={'real':30,'output':90,'draw_w':13};after={**before,'draw_w':10}
        self.assertFalse(_gain(before,after))
        w=PowerWindow()
        for i,value in enumerate([13,13,13,13,10,13,13,13]):w.add(i,'game',i+1,value)
        a=w.summary(1,8)
        self.assertEqual(a['draw_w'],13)
        self.assertFalse(_gain({**before,**a},{**after,**a}))
        b={**a,'draw_w':12}
        self.assertTrue(_gain({**before,**a},{**after,**b}))

    def test_power_readings_cannot_leak_between_sessions_or_repeated_fps(self):
        w=PowerWindow()
        for i in range(10):w.add(i,'old',1,8)
        self.assertIsNone(w.summary(1,10)['draw_w'])
        w.add(10,'new',2,12)
        self.assertEqual(w.summary(1,10)['draw_samples'],1)


class RotationExportTests(unittest.TestCase):
    def test_start_before_launch_keeps_old_append_and_complete_new_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec,diag=RecorderTests().make(Path(tmp))
            async def scenario():
                await rec.start('game')
                with diag.open('a') as f:f.write('old append\n')
                diag.rename(diag.with_name(diag.name+'.1'))
                diag.write_text('NEW SESSION FIRST LINE\n'+'new data\n'*100)
                await asyncio.sleep(.05)
                return await rec.stop()
            result=asyncio.run(scenario())
            self.assertTrue(result['success'],result)
            with zipfile.ZipFile(result['file']) as z:
                text=z.read('diagnostics-present-diagnostics.log').decode().replace('\r\n','\n')
                self.assertTrue(text.startswith('old append\nNEW SESSION FIRST LINE\n'))
                index=json.loads(z.read('diagnostics-index.json'))['files'][0]
                self.assertTrue(index['rotation_detected'])
                self.assertFalse(index['initial_segment_unavailable'])


class DefaultsAndScopeTests(unittest.TestCase):
    def setUp(self):
        from test_governor_runtime import RuntimeBase
        self.fixture=RuntimeBase();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.svc=self.fixture.svc
        self.svc.DEFAULT_MODE='autopilot'

    def test_all_autopilot_switches_default_on_and_all_other_modes_close_fusion(self):
        s=self.svc
        self.assertTrue(s.frame_fusion_enabled())
        self.assertTrue(all(v for k,v in s.frame_os_features('game').items() if k != 'continuous_boost'))
        self.assertFalse(s.frame_os_features('game')['continuous_boost'])
        self.assertEqual(s._frame_os_mode('game'),'act')
        saved=s._saved_profile_config('game')
        self.assertTrue(s._base_for('game',saved)['gfg_frame_fusion'])
        for mode in ('budget','balanced','quality','extreme'):
            s._settings['profiles']['game']['mode']=mode
            self.assertFalse(s._base_for('game',saved)['gfg_frame_fusion'])
        s._settings['profiles']['game']['mode']='autopilot'
        s._settings['profiles']['game']['enabled']=False
        self.assertFalse(s._base_for('game',saved)['gfg_frame_fusion'])

    def test_expired_short_pulse_restores_power_inside_the_same_governor_wait(self):
        s=self.svc;s._active_profile='game';s.power.state.owned=True
        s._budget=SimpleNamespace(tdp_control=True,tdp=10,normal_max_w=15,min_w=3,last_reason='test')
        s.frame_os.configure(enabled=True,mode='act',output_hz=90,calm_real_hz=30,max_multiplier=3,calm_w=10)
        s.frame_os.executor_active=True
        s.frame_os.last={'decision':{'level':'boost','tdp_w':14,'boost_until':time.monotonic()+.15}}
        async def scenario():
            await s._apply_budget_tdp('game')
            await s._wait_governor(.35)
        asyncio.run(scenario())
        self.assertEqual(s.power.writes,[10])


if __name__=='__main__':unittest.main()
