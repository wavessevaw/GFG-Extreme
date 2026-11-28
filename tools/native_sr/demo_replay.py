"""Replay a deterministic game capture through the pinned Kedavra FG test host.
The only substitution in the temporary host is its source/reference frame provider.
Run from a scratch directory with ./replay and spv/ from build.sh.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess as sp
import tempfile
import numpy as np
from PIL import Image
from measure import METHODS, OUT, PREFIX, panel, scores, read

READ = """
static void read_demo(int tick, int w, int h, unsigned char *out) {
    char path[4096];
    snprintf(path,sizeof(path),"%s/%03d.rgba",getenv("DEMO_INPUT"),tick);
    FILE *f = fopen(path,"rb");
    if (!f || fread(out,4,(size_t)w*h,f)!=(size_t)w*h || fgetc(f)!=EOF) {
        fprintf(stderr,"Wrong size or missing capture %s",path); exit(2);
    }
    fclose(f);
}
"""

def render_host(ked, work):
    engine=ked/"kedavra/engine"
    s=(engine/"kfg_vktest.c").read_text()
    s=s.replace("static int hard_suite(",READ+"\nstatic int hard_suite(",1)
    for a,b in (("render(s, sequence_time(s, f, 0, mode), w, h, B);","read_demo(f*mode,w,h,B);"),
                ("render(s, sequence_time(s, f - 1, j, mode), w, h, T);","read_demo((f-1)*mode+j,w,h,T);")):
        assert s.count(a)==1
        s=s.replace(a,b)
    src=work/"demo_host.c"; src.write_text(s)
    sp.run(["cc","-std=gnu11","-O2","-I"+str(engine),str(src),str(engine/"kfg_vk.c"),"-lvulkan","-lm","-o",str(work/"host")],check=True)

def capture(video, folder, size):
    w,h=size
    raw=sp.check_output(["ffmpeg","-v","error","-i",str(video),"-vf","select=between(n\\,84\\,105)","-vsync","0",
                         "-f","rawvideo","-pix_fmt","rgba","-threads","1","-"])
    assert len(raw)==w*h*4*22, (video,len(raw))
    for i in range(22):
        (folder/f"{i:03d}.rgba").write_bytes(raw[i*w*h*4:(i+1)*w*h*4])

def fg(ked,root,folder,size):
    env=dict(os.environ,KFG_HARD_X2="1",KFG_DETAIL_SEQUENCE_OUT=str(folder),DEMO_INPUT=str(folder))
    with (folder/"engine.log").open("w") as log:
        sp.run([str(root/"host"),"--spv",str(ked/"kedavra/build"),"--size","%dx%d"%size,"--hard","--regular-courtyard",
                "--scene","h_courtyard_reversal"],env=env,stdout=log,stderr=sp.STDOUT,check=True)

def reconstruct(img):
    data=sp.run(["./replay",*map(str,img.size),"1280","800"],input=img.convert("RGBA").tobytes(),capture_output=True,check=True).stdout
    n=1280*800*4
    assert len(data)==4*n
    return [Image.frombytes("RGBA",OUT,data[i*n:(i+1)*n]) for i in range(4)]

def main():
    p=argparse.ArgumentParser();p.add_argument("ked",type=Path);p.add_argument("videos",type=Path);p.add_argument("out",type=Path)
    args=p.parse_args();ked=args.ked.resolve();dest=args.out.resolve();dest.mkdir(parents=True,exist_ok=True)
    report={}
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);render_host(ked,root)
        ref=root/"native";ref.mkdir();capture(args.videos/"1280x800/footage.mkv",ref,OUT)
        truth=[Image.frombytes("RGBA",OUT,(ref/f"{i:03d}.rgba").read_bytes()) for i in range(22)]
        for h in (480,500):
            size=(h*8//5,h); folder=root/str(h);folder.mkdir()
            capture(args.videos/("%dx%d"%size)/"footage.mkv",folder,size)
            fg(ked,root,folder,size)
            after=root/f"large-{h}";after.mkdir()
            # Architecture A: reconstruct real inputs at 800p, then run the same FG.
            for i in range(22):
                lo=Image.frombytes("RGBA",size,(folder/f"{i:03d}.rgba").read_bytes())
                (after/f"{i:03d}.rgba").write_bytes(reconstruct(lo)[1].tobytes())
            fg(ked,root,after,OUT)
            settings=report[str(h)]={}
            for m in (1,2,3):
                stats={};prev={};clip=[]
                steps=range(6,14) if m==1 else range(0,m*7)
                for tick in steps:
                    if m==1:
                        low=Image.frombytes("RGBA",size,(folder/f"{tick:03d}.rgba").read_bytes())
                    else:
                        name=PREFIX+f"x{m}_f{1+tick//m}_t{tick%m}_gen.ppm"
                        low=read(folder/name)
                    outs=reconstruct(low)
                    names=list(METHODS)
                    if m>1:
                        names.append("SR before FG")
                        outs.append(read(after/name))
                    for im,method in zip(outs,names):
                        v,err=scores(im,truth[tick]); t=float(np.abs(err-prev[method]).mean()) if method in prev else None
                        stats.setdefault(method,[]).append([*v,t]);prev[method]=err
                    if h==500 and m==3:
                        clip.append(panel([truth[tick],outs[0],outs[1],outs[2]],["800p reference","Bilinear","Kedavra SR","FSR 1"],(400,210,670,440),1))
                settings[str(m)]={k:dict(frames=len(rows),psnr_db=np.mean([r[0] for r in rows]).item(),
                    ssim=np.mean([r[1] for r in rows]).item(),temporal_delta_mae=np.mean([r[2] for r in rows[1:]]).item()) for k,rows in stats.items()}
                if clip:
                    clip[8].save(dest/"freedoom.png")
                    sp.run(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","%dx%d"%clip[0].size,
                            "-r","12","-i","-","-vf","loop=loop=2:size=21:start=0","-frames:v","63","-pix_fmt","yuv420p",
                            str(dest/"freedoom.mp4")],input=b"".join(im.tobytes() for im in clip),check=True)
                (dest/"freedoom.json").write_text(json.dumps(report,indent=2)+"\n")
                print(h,m,flush=True)
if __name__=="__main__":main()
