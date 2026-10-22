"""Audit probes of v3.0.0 controllers; no hardware writes, only fake actuators."""
import sys,json
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/workspace/gfg-300-audit/source')
sys.path[:0]=[str(root/'py_modules'),str(root/'tests'),str(root)]
from helpers import Clock
from test_core import FakeActuator
from gfg_plugin.governor import PowerGovernor, healthy
from gfg_plugin.autopilot import Autopilot
from gfg_plugin.pilot import PointPilot
from gfg_plugin.session_stats import SessionStats
from gfg_plugin.gpu_clock import GpuClock, MemoryBackend
from gfg_plugin.gpu_clock_control import GpuClockControl
out={}
def sample(**kw):
 s=dict(game=True,key='app:1|90',objective='balanced',cap=30,epoch=1,real=30.,pace=1.,over_budget=0.,ring_miss=0.,temp_c=70.)
 s.update(kw);return s
def gov():
 c=Clock();a=FakeActuator();g=PowerGovernor(a,None,clock=c);return c,a,g
out['missing_pace_accepted']=healthy([dict(real=30,pace=None)],30,True)
out['10pct_one_second_dip_accepted']=healthy([dict(real=30,pace=1)]*9+[dict(real=27,pace=1)],30,True)
c,a,g=gov();g.tick(sample(objective='quality',temp_c=98))
for _ in range(35):c.t+=1;g.tick(sample(objective='quality'))
out['cooled_quality']={'tdp':a.tdp,'thermal_ceiling':g.thermal_ceiling,'window':g.last}
c,a,g=gov();g.tick(sample(temp_c=98))
for _ in range(35):c.t+=1;g.tick(sample(hold_ceiling=True))
out['cooled_while_pilot_measures']={'tdp':a.tdp,'thermal_ceiling':g.thermal_ceiling,'hold':g.hold}
c=Clock();ap=Autopilot(clock=c);m=[]
for temp in [84.9,85.1,84.9,85.1]:
 m.append(ap.decide('smoothness',dict(external_power=True),temp)['objective']);c.t+=1
out['thermal_smoothness_flap']=m
c,a,g=gov();g.tick(sample());c.t+=10;g.tick(sample())
out['two_samples_ten_seconds']={'writes':a.writes,'window':g.last}
c,a,g=gov();g.tick(sample(objective='quality'));g._write(10,'fixture-start');c.t+=2;g.tick(sample(objective='quality'))
start=c.t;restored=None
for i in range(1,13):
 c.t+=1;g.tick(sample(objective='quality',real=0))
 if a.tdp==15 and restored is None:restored=c.t-start
out['severe_zero_fps_recovery_seconds']=restored
c,a,g=gov();g.tick(sample());g.floor_fail[30]=13;c.t+=4000
for _ in range(60):c.t+=1;g.tick(sample())
out['expired_local_failure_floor']={'tdp':a.tdp,'failure':g.floor_fail[30]}
c=Clock();p=PointPilot(clock=c);ctx=dict(fg='auto',refresh=90,objective='balanced',game=True,app=1,engine=dict(auto=True,cap_fps=45),confirmed=True,real=45,pace=1,at_ceiling=True)
p.tick(ctx);c.t+=1;p.tick(ctx)
c.t+=13;ctx['confirmed']=False;ctx['real']=None;ctx['engine']={}
out['pilot_locks_on_stale_measurement']=p.tick(ctx)
s=SessionStats();s.start('app',0)
for i in range(1,61):s.add(i,output=90,real=30,tdp=15,draw=8,reference_w=15,mode='quality')
out['unmodified_tdp_claimed_saving']=s.summary()
c=Clock();gpu=GpuClock(MemoryBackend(),writes_enabled=True);gc=GpuClockControl(gpu,clock=c)
gpu.lower_ceiling();gc.baseline=dict(draw=10.,real=30.);gc.reals.append(30);gc.draws.append(9);gc.phase='verify'
gc._judge(c(),30)
out['gpu_trial_one_sample_accepted']={'phase':gc.phase,'owned':gc.owned,'blocked_until':gc.blocked_until}
# Service production wiring with only its injected split interface replaced: an active trial
# is not included in the Governor sample, allowing a TDP probe while split.settling() is true.
from sandbox.run import make_rig
from sandbox.vdeck import VGame
r=make_rig(VGame('stable',120,noise=0),fg='x3',objective='battery',split=False,gpu_clock=False)
for _ in range(40):r.engine.step();r.sensors.step();r.service.tick();r.clock.t+=1
class Trial:
 changes=0
 cpu=type('Cpu',(),{'owned':True})()
 def settling(self):return True
 def tick(self,ctx):return dict(phase='probe')
 def stop(self):pass
r.service.split=Trial();before=r.power.tdp
for _ in range(15):r.engine.step();r.sensors.step();r.service.tick();r.clock.t+=1
out['governor_during_split_trial']={'tdp_before':before,'tdp_after':r.power.tdp,'split_settling':True}
r.service.stop()
class FailRestore(FakeActuator):
 def restore_if_owned(self):return dict(restored=False,success=False,error='injected transient restore failure')
c=Clock();a=FailRestore();g=PowerGovernor(a,None,clock=c)
g.tick(sample());g._write(10,'fixture-start');g.tick(sample(game=False))
forgotten=g.key is None and not g.owned
c.t+=1;g.tick(sample(key='app:2|90',objective='quality'))
out['restore_failure_then_new_game']={'governor_forgot_pending_restore':forgotten,'saved_original_after_new_claim':a.initial,'actual_tdp':a.tdp}
print(json.dumps(out,indent=2))
