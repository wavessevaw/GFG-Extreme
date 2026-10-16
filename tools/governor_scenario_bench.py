#!/usr/bin/env python3
"""Deterministic closed-loop policy bench; synthetic, not a Deck emulator.

The plant has explicit FPS/watt and CPU ceilings. Write and sensor delays,
outages, noise, hot periods and a competing resource reservation are inputs.
Application/sequence gates model the service boundary; runtime tests separately
exercise that real boundary. This bench cannot prove Vulkan or QAM behavior.
"""
from __future__ import annotations
import argparse
from collections import deque
import importlib.util
import json
import random
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'py_modules')]
from gfg_plugin import governor_core as current

SCENARIOS=('menu_to_game','game_to_menu','long_idle_resume','pause_resume',
           'loading_resume','light_to_heavy','heavy_to_light','level_change',
           'shader_compilation','short_hang','generation_loss','telemetry_loss',
           'telemetry_recovery','user_limit','background_resume',
           'cpu_bound','gpu_bound','delayed_apply','sensor_noise','thermal_limit',
           'ineffective_power','competing_regulator')


def run(name, module=current, seconds=420, seed=213):
    rng=random.Random(seed)
    c=module.BudgetController(target_output_fps=90,now=0,min_tdp_w=3,max_tdp_w=15)
    c.current_max_multiplier=3
    applied=c.tdp;pending=None;after=0;last_fast_seq=0;seq=0;window=[];sensor=deque()
    trace=[];writes=[];below=0;draws=[];max_recovery=0;short_at=None
    apply_delay=3 if name=='delayed_apply' else 1
    sensor_delay=3 if name=='delayed_apply' else 1
    for t in range(seconds):
        # A 10 W workload at 3 real FPS/W, a 7 W easy scene, and capped CPU work.
        fps_w=3.2;cpu=100;generation=True;fresh=True;reserved=False;hot=False
        if name in ('menu_to_game','long_idle_resume','pause_resume','background_resume') and t<120:fps_w=7
        if name=='game_to_menu' and t>=120:fps_w=7
        if name=='light_to_heavy' and t<120:fps_w=7
        if name=='heavy_to_light' and t>=120:fps_w=7
        if name in ('loading_resume','level_change','shader_compilation','short_hang','generation_loss') and 120<=t<140:
            cpu=5 if name!='generation_loss' else 15;generation=False
        if name in ('telemetry_loss','telemetry_recovery') and 120<=t<145:fresh=False
        if name=='cpu_bound':cpu=28
        if name=='ineffective_power':cpu=20
        if name=='thermal_limit' and 120<=t<180:hot=True;cpu=20
        if name=='competing_regulator' and 120<=t<150:reserved=True
        if name=='user_limit' and t==120:
            # The service rebuilds non-Extreme controllers after ownership
            # changes. Model a new validated lower device ceiling, not an
            # unsupported call to Extreme's limit_power on Battery.
            c=module.BudgetController(target_output_fps=90,now=t,min_tdp_w=3,max_tdp_w=8)
            c.current_max_multiplier=3;pending=None;applied=c.tdp;after=seq;window=[]
        if pending and t>=pending[0]:
            applied=pending[1];pending=None;after=seq;window=[]
        real=min(c.point.base_target_fps,applied*fps_w,cpu)
        if name=='sensor_noise':real=max(1,real+rng.uniform(-.5,.5))
        output=min(c.target_output_fps,real*(c.point.multiplier if generation else 1))
        draw=min(applied,max(2,real/fps_w))
        draws.append(draw);below+=output<c.target_output_fps*.92
        if t>=140 and name in ('light_to_heavy','loading_resume','pause_resume'):
            if output<c.target_output_fps*.92 and short_at is None:short_at=t
            if output>=c.target_output_fps*.92 and short_at is not None:
                max_recovery=max(max_recovery,t-short_at);short_at=None
        seq+=1
        sensor.append((t,seq,real,output,draw,fresh))
        old=(c.point.key,c.tdp)
        c.set_thermal('hot' if hot else 'ok',t)
        if len(sensor)>sensor_delay:
            stamp,sample_seq,r,o,d,valid=sensor.popleft()
            valid=valid and t-stamp<=sensor_delay and sample_seq>after and pending is None
            if valid and not reserved:
                c.draw_w=d
                summary={'real':{'median':r,'p5':r},'output':{'median':o},'misses':0,'hard_pressure':0}
                verdict=module.window_verdict(summary,c.point)
                if sample_seq>last_fast_seq:
                    c.fast_check(t,None if verdict.stall else r,d);last_fast_seq=sample_seq
                if old==(c.point.key,c.tdp):
                    window.append((r,o))
                    if len(window)>=15:
                        rs=[v[0] for v in window];os=[v[1] for v in window]
                        summary={'real':{'median':statistics.median(rs),'p5':min(rs)},
                                 'output':{'median':statistics.median(os)}}
                        c.observe(t,module.window_verdict(summary,c.point),statistics.median(rs),statistics.median(os))
                        window=[]
            else:
                c.fast_check(t,None,None)
                window=[]
        changed=old!=(c.point.key,c.tdp)
        if changed:
            writes.append({'t':t,'before':old,'after':(c.point.key,c.tdp),'reason':c.last_reason})
            pending=(t+apply_delay,c.tdp);window=[];after=seq
        trace.append({'t':t,'real':round(real,3),'output':round(output,3),'requested_w':c.tdp,
                      'applied_w':applied,'ceiling_w':c.emergency_max_w,'point':c.point.key,
                      'phase':c.phase,'reason':c.last_reason,'reserved':reserved,'hot':hot})
    return {'scenario':name,'basis':'synthetic closed-loop plant; not hardware',
            'metrics':{'seconds':seconds,'below_goal_s':below,'actions':len(writes),
                       'failed_economy_probes':sum('probe-failed' in w['reason'] or 'economy-recovery' in w['reason'] for w in writes),
                       'max_completed_recovery_s':max_recovery,'unrecovered_at_end':short_at is not None,
                       'mean_plant_draw_w':round(statistics.mean(draws),3),
                       'peak_requested_w':max(x['requested_w'] for x in trace)},
            'decisions':writes,'trace':trace}


def load_core(path):
    spec=importlib.util.spec_from_file_location('audit_baseline_core',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    module=load_core(a.core) if a.core else current
    results=[run(name,module) for name in SCENARIOS]
    a.output.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({x['scenario']:x['metrics'] for x in results},indent=2))
