#!/usr/bin/env python3
"""Read-only, content-addressed historical evidence index. No hardware claims.

Accepts directories of JSONL, renderer text logs and diagnostic ZIPs. Archives
and members are hashed independently; aliases retain their source identity.
Rules produce observations, never claims that correlation proves causation.
"""
from __future__ import annotations
import argparse
import base64
import collections
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile


def number(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def timestamp(row):
    for k in ('t', 'ts', 'elapsed_s'):
        if number(row.get(k)) is not None:
            return float(row[k])
    try:
        return dt.datetime.fromisoformat(row['time_utc'].replace('Z', '+00:00')).timestamp()
    except (KeyError, ValueError, TypeError):
        return None


def normalized(row):
    tele = row.get('telemetry') or {}
    hw = row.get('hardware') or row.get('sensors') or {}
    return dict(t=timestamp(row), real=number(row.get('real', tele.get('real_fps'))),
                output=number(row.get('output', row.get('measured_output_fps', tele.get('measured_output_fps')))),
                target=number(row.get('target', row.get('controller_target_fps'))),
                tdp=number(row.get('tdp')), draw=number(row.get('apu_w', hw.get('apu_power_w'))),
                multiplier=number(row.get('mult', tele.get('effective_multiplier'))),
                gpu=number(hw.get('gpu_busy_pct')), cpu=number(hw.get('cpu_top_core_pct', hw.get('cpu_util_pct'))),
                clock=number(hw.get('gpu_clock_mhz')), temp=number(hw.get('temp_c', hw.get('apu_temp_c'))),
                age=number((row.get('snapshot') or tele).get('sample_age_ms')),
                point=row.get('point'), state=row.get('state'), reason=row.get('reason'))


def analyze(data, name):
    fields = collections.Counter(); types = collections.Counter(); versions = set()
    errors = []; findings = []; decisions = []; samples = []; times = []; raw_count = 0; transitions = []
    previous = None; last_down = None; previous_target = None; last_seq = None
    for line_no, raw in enumerate(data.decode('utf-8', errors='replace').splitlines(), 1):
        if not raw.strip():
            continue
        raw_count += 1
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            if name.endswith(('.jsonl', '.json')):
                errors.append(line_no)
            # Text diagnostics are inventoried too, without inventing timestamps.
            for k in ('base_fps', 'target_fps', 'source_interval_mean_ms', 'requested_interval_mean_ms'):
                if re.search(r'\b' + k + r'=', raw): fields[k] += 1
            continue
        if not isinstance(row, dict): continue
        kind = row.get('event', row.get('type', 'sample'))
        types[str(kind)] += 1
        for k in ('gfg_version', 'version', 'governor_version'):
            if row.get(k) is not None: versions.add(str(row[k]))
        x = normalized(row); t = x['t']
        if t is not None: times.append(t)
        for k, v in x.items():
            if v is not None: fields[k] += 1
        ref = {'line': line_no, 't': t}
        if row.get('event'):
            keep = ('event','reason','before','after','watts','point','tdp_w','verdict','real','draw_w')
            decisions.append({**ref, **{k:row[k] for k in keep if k in row}})
        if x['real'] is None or x['output'] is None: continue
        samples.append({**ref, **x})
        def flag(rule, detail, start=None):
            findings.append({'rule':rule, 'start_line':start or line_no, 'end_line':line_no,
                             't':t, 'detail':detail, 'confidence':'observation-only',
                             'root_cause_confirmed':False})
        if previous and t is not None and previous['t'] is not None:
            gap = t-previous['t']
            controls = ('tdp','target','multiplier','point','clock')
            changes = {k:[previous[k],x[k]] for k in controls if previous[k] is not None and x[k] is not None and previous[k]!=x[k]}
            if changes:
                transitions.append({**ref,'changes':changes,'before_real':previous['real'],
                                    'before_output':previous['output'],'after_real':x['real'],
                                    'after_output':x['output'],'reason':x['reason'],
                                    'application_confirmed':False})
            if gap < 0: flag('timestamp-regression', {'delta_s':gap})
            if 0 <= gap <= 10 and x['tdp'] is not None and previous['tdp'] is not None and x['tdp'] < previous['tdp']-.4:
                last_down = {**previous, 'line':line_no}
            if last_down and 0 <= t-last_down['t'] <= 30:
                if x['output'] < last_down['output']*.85:
                    flag('fps-drop-after-cap-reduction', {'before_output':last_down['output'], 'output':x['output'],
                         'before_cap':last_down['tdp'], 'cap':x['tdp']}, last_down['line'])
                    last_down = None
                elif x['target'] is not None and last_down['target'] is not None and x['target'] < last_down['target']:
                    flag('goal-drop-after-cap-reduction', {'before_target':last_down['target'],'target':x['target']},last_down['line'])
            if x['target'] is not None and previous['target'] is not None and x['target'] != previous['target']:
                if previous_target is not None and t-previous_target < 120:
                    flag('rapid-target-switch', {'seconds_since_previous':t-previous_target})
                previous_target=t
            if (0 <= gap <= 10 and x['tdp'] is not None and previous['tdp'] is not None
                and x['tdp'] != previous['tdp'] and x['multiplier'] is not None
                and previous['multiplier'] is not None and x['multiplier'] != previous['multiplier']):
                flag('multiple-controls-between-samples', {'cap':[previous['tdp'],x['tdp']],
                     'multiplier':[previous['multiplier'],x['multiplier']]})
        if x['age'] is not None and x['age'] > 2500:
            flag('stale-sample-visible', {'age_ms':x['age']})
        previous=x
    # Collapse adjacent observations of the same rule into bounded intervals.
    intervals=[]
    for f in findings:
        if intervals and f['rule']==intervals[-1]['rule'] and f['start_line']<=intervals[-1]['end_line']+2:
            intervals[-1]['end_line']=f['end_line'];intervals[-1]['observations']+=1
        else: intervals.append({**f,'observations':1})
    return {'records':raw_count,'record_types':dict(types),'versions':sorted(versions),
            'duration_s':max(times)-min(times) if len(times)>1 else None,
            'first_timestamp':min(times) if times else None,'last_timestamp':max(times) if times else None,
            'fields':dict(fields),'parse_error_lines':errors,'anomalies':intervals,
            'decisions':decisions,'transitions':transitions,'samples':len(samples),
            'metrics':{'below_target_samples':sum(s['target'] is not None and s['output'] < .92*s['target'] for s in samples),
                       'mean_draw_w':sum(s['draw'] for s in samples if s['draw'] is not None)/max(1,sum(s['draw'] is not None for s in samples))
                                     if any(s['draw'] is not None for s in samples) else None}}


def run(roots, output):
    output.mkdir(parents=True,exist_ok=True); inventory=[]; contents={}; archives={}
    def member(data, source, name):
        sha=hashlib.sha256(data).hexdigest()
        item={'source':source,'name':name,'sha256':sha,'bytes':len(data)}
        if sha not in contents:
            contents[sha]=analyze(data,name)
            (output/(sha+'.json')).write_text(json.dumps(contents[sha],indent=2,sort_keys=True)+'\n')
        item.update({k:contents[sha][k] for k in ('records','duration_s','versions','fields','samples')})
        item['status']='partial' if contents[sha]['parse_error_lines'] else 'processed'
        item['analysis']=sha+'.json';inventory.append(item)
    def archive(data, source):
        sha=hashlib.sha256(data).hexdigest();item={'source':source,'sha256':sha,'bytes':len(data),'status':'processed'}
        if sha in archives: item['duplicate_of']=archives[sha]
        else:
            archives[sha]=source
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    item['members']=len(z.infolist())
                    item['member_names']=[i.filename for i in z.infolist()]
                    try:
                        system=json.loads(z.read('system.json'))
                        item['version']=system.get('plugin_version')
                    except (KeyError,ValueError):pass
                    for info in z.infolist():
                        if info.is_dir():continue
                        if info.filename.endswith(('.jsonl','.log')):
                            member(z.read(info),source,info.filename)
                        elif info.filename.endswith('.zip'):archive(z.read(info),source+'!'+info.filename)
            except (zipfile.BadZipFile,RuntimeError,OSError) as e:item.update(status='unreadable',error=str(e))
        inventory.append(item)
    for root in roots:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            source=p.relative_to(root).as_posix(); data=p.read_bytes()
            if p.suffix=='.zip':archive(data,source)
            elif p.suffix in ('.jsonl','.log'):member(data,source,p.name)
            elif 'base64' in p.name or '.b64.' in p.name:
                try:archive(base64.b64decode(data,validate=False),source)
                except ValueError as e:inventory.append({'source':source,'status':'unreadable','error':str(e)})
    result={'schema':1,'rule_semantics':'correlation only; no measured hardware effects inferred',
            'sources':inventory,'unique_contents':len(contents),'unique_archives':len(archives)}
    (output/'inventory.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'sources':len(inventory),'unique_contents':len(contents),'unique_archives':len(archives),
                      'anomaly_intervals':sum(len(x['anomalies']) for x in contents.values()),
                      'records':sum(x['records'] for x in contents.values())}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('roots',nargs='+',type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.roots,a.output)
