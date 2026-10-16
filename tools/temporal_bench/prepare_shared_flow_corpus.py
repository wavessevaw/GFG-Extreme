#!/usr/bin/env python3
"""Reproduce the GSF prototype corpus, with pinned CC-BY camera inputs.

Synthetic targets are rendered at 90 Hz. Camera targets retain 60000/1001 Hz;
they are neither game captures nor a 30-to-90 test. No display is exercised.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

from render_game_scene import render

REV='57978890822836f2b4743852f04f62fc511757e4'
BASE=f'https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/{REV}/'
FILES={
    'bolt-multi-size-detection.mp4':('bolt.mp4','bfee06e6953a8eb2694d8c851ebca88a6341f9765543781dd3d8ebe7c5d38a4b'),
    'worker-zone-detection.mp4':('worker.mp4','b8b58b8100a81600bc42ee7ee082ced777b12a32a3619139ef289d27cbdcd284'),
    'LICENSE':('LICENSE-camera.txt','e7edaaaeb0cd6da6a3dd97c54f3e8443ef027be685253fab64bf6eed2419ee7e'),
}
WINDOWS=[('target-strafe',0,.45),('target-objects',1.9,.45),
         ('target-fastturn',3.25,.45),('target-hud',4.8,.45),
         ('target-postcut',6.1,.45),('target-crosscut',5.98,.12)]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reuse',action='store_true',help='reuse existing decoded/rendered arrays, record their hashes')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for remote,(local,expected) in FILES.items():
        p=a.out/local
        if not p.exists():
            tmp=p.with_suffix(p.suffix+'.download')
            with urllib.request.urlopen(BASE+remote,timeout=60) as r,tmp.open('wb') as f:
                while b:=r.read(1<<20):f.write(b)
            if sha(tmp)!=expected:raise RuntimeError(f'checksum mismatch: {remote}')
            tmp.replace(p)
        if sha(p)!=expected:raise RuntimeError(f'checksum mismatch: {p}')
    seq=[]
    for name,clip,start,count in [('bolt-small','bolt.mp4',5,31),('worker-small','worker.mp4',10,61)]:
        p=a.out/name
        if not a.reuse or not (p/'frames.npy').exists():
            subprocess.run([sys.executable,str(Path(__file__).with_name('extract_video.py')),str(a.out/clip),
                '--out',str(p),'--start',str(start),'--frames',str(count),'--width','384',
                '--source-note',f'Intel IoT DevKit sample-videos@{REV}; CC-BY-4.0; native 60000/1001 FPS'],check=True)
        seq.append(p)
    for name,start,duration in WINDOWS:
        p=a.out/name;p.mkdir(exist_ok=True)
        if not a.reuse or not (p/'frames.npy').exists():
            m=render(p,90,1280,800,duration,1,start)
            if name=='target-crosscut':
                m['segments']=[dict(name='crosscut',start=0,end=m['frames'])]
                (p/'meta.json').write_text(json.dumps(m,indent=1))
        seq.append(p)
    manifest=dict(camera_repository='https://github.com/intel-iot-devkit/sample-videos',
        camera_revision=REV,camera_license='CC-BY-4.0',camera_files=FILES,sequences=[])
    for p in seq:
        manifest['sequences'].append(dict(name=p.name,frames_sha256=sha(p/'frames.npy'),
            meta_sha256=sha(p/'meta.json'),meta=json.loads((p/'meta.json').read_text())))
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Corpus manifest:',a.out/'manifest.json')

if __name__=='__main__':main()
