#!/usr/bin/env python3
"""Compare experimental shared flow with GPU LMC on identical held-out frames.

No WSI/display claims. Quality runs download; timing runs explicitly do not.
One-output ablation checks identical inputs/history and first-output pixels.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engine/gfg-temporal/reference'))
from gfg_temporal_ref.metrics import psnr_y,ssim_y,temporal_error
from gfg_temporal_ref.core import luma,to_float


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def score(seq,out,start,pairs,step):
    ps,ss,roi,te=[],[],[],[];duplicates=0;equal_outputs=0;dynamic=0
    for k in range(pairs):
        i=start+k*step;a=seq[i];b=seq[i+step];prev=a;pg=a
        if np.array_equal(out[2*k],out[2*k+1]):equal_outputs+=1
        for j in range(2):
            gt=seq[i+j+1];im=out[2*k+j]
            ps.append(float(psnr_y(im,gt)));ss.append(float(ssim_y(im,gt)))
            te.append(float(temporal_error(prev,im,pg,gt))*255)
            mask=np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)>5
            mask|=np.max(np.abs(gt.astype(np.int16)-a.astype(np.int16)),axis=2)>5
            if mask.any():
                dynamic+=1
                error=luma(to_float(im))-luma(to_float(gt));mse=float(np.mean(error[mask]**2))
                roi.append(99.0 if mse<1e-12 else -10*np.log10(mse))
                duplicates+=int(np.array_equal(im,a) or np.array_equal(im,b))
            prev,pg=im,gt
        te.append(float(temporal_error(prev,b,pg,b))*255)
    return dict(psnr_y=float(np.mean(ps)),ssim_y=float(np.mean(ss)),
                motion_roi_psnr=float(np.mean(roi)) if roi else None,
                temporal_error=float(np.mean(te)),dynamic_outputs=dynamic,
                endpoint_duplicates=duplicates,equal_output_pairs=equal_outputs,outputs=2*pairs)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bench',type=Path,required=True)
    ap.add_argument('--sequence',type=Path,action='append',required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--pairs',type=int,default=6)
    ap.add_argument('--timing-repeats',type=int,default=2)
    ap.add_argument('--algorithms',default='lmc-gpu,shared-flow,shared-flow-dense')
    ap.add_argument('--segments',default='')
    ap.add_argument('--check-sharing',action='store_true')
    args=ap.parse_args();args.work.mkdir(parents=True,exist_ok=True)
    if args.pairs<2 or args.timing_repeats<1:ap.error('need >=2 pairs and >=1 timing repeat')
    report=dict(schema=1,scope='offscreen Vulkan; not Deck GPU performance or physical scanout',
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                bench_sha256=sha(args.bench),timing_warmup_pairs_discarded=1,segments=[])
    selected=set(filter(None,args.segments.split(',')))
    algos=args.algorithms.split(',')
    def run(path,start,pairs,algo,stem,download=True,outputs=2,validate=False):
        js=args.work/(stem+'.jsonl');out=args.work/(stem+'.npy');log=args.work/(stem+'.log')
        cmd=[str(args.bench),'--frames',str(path),'--start',str(start),'--pairs',str(pairs),
             '--step','3','--outputs',str(outputs),'--algo',algo,'--json',str(js)]
        cmd+=['--out',str(out)] if download else ['--no-download']
        if validate:cmd+=['--validation']
        began=time.monotonic()
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        log.write_text('command='+json.dumps(cmd)+'\n'+p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(f'{algo} failed ({p.returncode}); {log}')
        rows=[json.loads(x) for x in js.read_text().splitlines()]
        if len(rows)!=pairs or not all(r['timed'] and r['outputs']==outputs for r in rows):
            raise RuntimeError('missing outputs or GPU timestamps')
        return rows,np.load(out,mmap_mode='r') if download else None,time.monotonic()-began
    for seqdir in args.sequence:
        meta=json.loads((seqdir/'meta.json').read_text());path=seqdir/'frames.npy'
        frames=np.load(path,mmap_mode='r')
        for seg in meta['segments']:
            if selected and seg['name'] not in selected:continue
            start=seg['start'];pairs=min(args.pairs,(min(len(frames),seg['end'])-start-1)//3)
            if pairs<2:continue
            name=seqdir.name+'-'+seg['name'];base=dict(name=name,input_sha256=sha(path),
                source=meta['source'],fps_source=meta['fps'],fps_real=meta['fps']/3,
                width=int(frames.shape[2]),height=int(frames.shape[1]),start=start,pairs=pairs,methods={})
            for algo in algos:
                rows,out,wall=run(path,start,pairs,algo,name+'-'+algo+'-quality',validate=True)
                m=score(frames,out,start,pairs,3);m['allocation_bytes']=rows[0]['allocation_bytes']
                m['quality_run_first_pair_gpu_ms']=rows[0]['pair_ready_ms'];m['quality_process_wall_s']=wall
                m['cut_flags']=sum(r['scene_cut'] for r in rows)
                m['timing_rows']=[];m['device_log']=name+'-'+algo+'-quality.log'
                base['methods'][algo]=m
                if args.check_sharing:
                    one,o,_=run(path,start,pairs,algo,name+'-'+algo+'-one-output',outputs=1,validate=True)
                    m['first_output_bit_exact_with_single_output']=bool(np.array_equal(o,out[::2]))
                    if not m['first_output_bit_exact_with_single_output']:raise RuntimeError('output count changes first output/history')
            # Rotate algorithm order to avoid always granting a warmer/colder position.
            for repeat in range(args.timing_repeats):
                order=algos[repeat%len(algos):]+algos[:repeat%len(algos)]
                for algo in order:
                    rows,_,_=run(path,start,pairs,algo,f'{name}-{algo}-timing-{repeat}',download=False)
                    base['methods'][algo]['timing_rows']+=rows[1:]
            for algo,m in base['methods'].items():
                rows=m.pop('timing_rows');m['timing_samples']=len(rows)
                for key,vals in dict(analysis_ms=[r['analysis_ms'] for r in rows],
                    s1_ms=[r['frames'][0]['total_ms'] for r in rows],s2_ms=[r['frames'][1]['total_ms'] for r in rows],
                    first_ready_ms=[r['first_ready_ms'] for r in rows],pair_ready_ms=[r['pair_ready_ms'] for r in rows],
                    cpu_submit_ms=[r['cpu_submit_ms'] for r in rows],cpu_total_ms=[r['cpu_total_ms'] for r in rows]).items():
                    m[key]=dict(median=float(np.median(vals)),p95=float(np.percentile(vals,95)))
            baseline=base['methods'].get('lmc-gpu')
            if baseline:
                for algo,m in base['methods'].items():
                    if algo=='lmc-gpu':continue
                    m['vs_lmc']=dict(psnr_delta=m['psnr_y']-baseline['psnr_y'],
                        motion_roi_delta=(m['motion_roi_psnr']-baseline['motion_roi_psnr']) if m['motion_roi_psnr'] is not None else None,
                        temporal_ratio=m['temporal_error']/max(baseline['temporal_error'],1e-9),
                        pair_gpu_ratio=m['pair_ready_ms']['median']/baseline['pair_ready_ms']['median'])
                    v=m['vs_lmc'];m['software_gate_pass']=bool(v['psnr_delta']>=-.3 and
                        (v['motion_roi_delta'] is None or v['motion_roi_delta']>=-1) and
                        v['temporal_ratio']<=1.05 and v['pair_gpu_ratio']<=.85)
            report['segments'].append(base)
            (args.work/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
            print(name,[(a,round(m['psnr_y'],3),round(m['pair_ready_ms']['median'],3),m.get('software_gate_pass')) for a,m in base['methods'].items()],flush=True)
    if not report['segments']:raise RuntimeError('no usable segment')
    print('Wrote',args.work/'comparison.json','; promotion gates are results, not proof of physical 90 FPS')

if __name__=='__main__':main()
