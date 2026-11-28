"""Run in the built replay directory. Inputs are the Kedavra courtyard dumps and photo references."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

METHODS = ("Bilinear", "Kedavra SR", "FSR 1", "NIS")
OUT = (1280, 800)
PREFIX = "h_courtyard_reversal_"

def read(path):
    with Image.open(path) as im:
        return im.convert("RGBA")

def photo_chart(ref):
    out = Image.new("RGBA", OUT, (127,127,127,255))
    for name, box in [("astronaut",(0,0,512,512)), ("brick",(512,0,960,400)),
                      ("grass",(960,0,1280,400)), ("chelsea",(0,512,448,800)),
                      ("gravel",(512,400,1024,800)), ("grass",(1024,400,1280,800)),
                      ("brick",(448,512,512,800))]:
        im=read(ref/(name+".png"))
        x,y,X,Y=box
        out.paste(im.crop((0,0,X-x,Y-y)),(x,y))
    return out

def luma(a):
    return a[:,:,0]*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722

def scores(image, truth):
    rgb=np.asarray(image,dtype=np.float32)[:,:,:3]
    ref=np.asarray(truth,dtype=np.float32)[:,:,:3]
    y,t=luma(rgb),luma(ref)
    err=rgb-ref
    # Non-overlapping 8x8 luminance SSIM, constants in 8-bit units.
    def mean(arr): return arr.reshape(100,8,160,8).mean((1,3))
    a,b=mean(y),mean(t)
    v1,v2=mean(y*y)-a*a,mean(t*t)-b*b
    cov=mean(y*t)-a*b
    s=((2*a*b+6.5025)*(2*cov+58.5225))/((a*a+b*b+6.5025)*(v1+v2+58.5225))
    return [float(-10*np.log10(max(1e-12,np.mean(err*err)/65025))),float(s.mean())], y-t

def panel(images,names,box,zoom):
    x,y,X,Y=box
    w,h=(X-x)*zoom,(Y-y)*zoom
    out=Image.new("RGB",(w*len(images),h+26),"#202028")
    draw=ImageDraw.Draw(out)
    for i,(im,name) in enumerate(zip(images,names)):
        out.paste(im.crop(box).resize((w,h),Image.Resampling.NEAREST),(i*w,26))
        draw.text((i*w+5,6),name,fill="white")
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("scenes",type=Path); ap.add_argument("references",type=Path); ap.add_argument("out",type=Path)
    args=ap.parse_args()
    dest=args.out; dest.mkdir(parents=True,exist_ok=True)
    refs=args.scenes/"1280x800"
    chart=photo_chart(args.references)
    report={}
    for h in [480,500,540,600,720,800]:
        w=h*8//5
        folder=args.scenes/f"{w}x{h}"
        if not folder.is_dir(): continue
        images=[("Photo","photo",chart.resize((w,h),Image.Resampling.LANCZOS),chart)]
        for f in range(2,6):
            name=PREFIX+f"source{f}.ppm"
            images.append(("Off",str(f),read(folder/name),read(refs/name)))
        for mult in (2,3):
            for f in range(3,6):
                for phase in range(mult):
                    stem=PREFIX+f"x{mult}_f{f}_t{phase}"
                    images.append((f"x{mult}",stem,read(folder/(stem+"_gen.ppm")),read(refs/(stem+"_truth.ppm"))))
        groups={}
        previous={}
        def record(group, names, outputs, truth):
            for method,output in zip(names,outputs):
                score,err=scores(output,truth)
                key=(group,method)
                temporal=float(np.abs(err-previous[key]).mean()) if key in previous else None
                previous[key]=err
                groups.setdefault(group,{}).setdefault(method,[]).append([*score,temporal])
        if (w,h)==OUT:
            for group,name,im,truth in images:
                record(group,["Native bypass"],[im],truth)
        else:
            timings=dest/f"timings-{h}.txt"
            with timings.open("wb") as timing, subprocess.Popen(["./replay",str(w),str(h),"1280","800"],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=timing) as p:
                for group,name,im,truth in images:
                    p.stdin.write(im.tobytes()); p.stdin.flush()
                    outputs=[Image.frombytes("RGBA",OUT,p.stdout.read(1280*800*4)) for _ in METHODS]
                    record(group,METHODS,outputs,truth)
                    if h==500 and group=="Photo":
                        panel([truth,*outputs],["800p reference",*METHODS],(142,70,290,209),2).save(dest/"photo.png")
                    if h==500 and group=="x3":
                        frame=panel([truth,*outputs],["800p reference",*METHODS],(530,300,750,472),1)
                        frame.save(dest/(name+".png"))
                p.stdin.close()
                if p.wait(): raise RuntimeError(timings.read_text())
        by_height={}
        for group,methods in groups.items():
            by_height[group]={}
            for method,records in methods.items():
                sums=[round(float(np.mean(col)),5) if col else None for col in
                      ([r[0] for r in records],[r[1] for r in records],[r[2] for r in records if r[2] is not None])]
                by_height[group][method]=dict(zip(("psnr_rgb_db","ssim_luma","temporal_delta_mae"),sums),frames=len(records))
        report[h]=by_height
        (dest/"metrics.json").write_text(json.dumps(report,indent=2)+"\n")
        print(h,by_height["Photo"],flush=True)
    seq=sorted(dest.glob(PREFIX+"x3_*.png"))
    if seq:
        subprocess.run(["ffmpeg","-loglevel","error","-y","-f","image2pipe","-framerate","6","-i","-",
            "-vf","loop=loop=3:size=9:start=0","-frames:v","36","-pix_fmt","yuv420p",str(dest/"motion.mp4")],
            input=b"".join(f.read_bytes() for f in seq),check=True)

if __name__=="__main__": main()
