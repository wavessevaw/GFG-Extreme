"""LPIPS v0.1 SqueezeNet comparison at two independent Gamescope sharpness settings."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
import torch
import lpips
from measure import METHODS, PREFIX, OUT, photo_chart, read, scores

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("scenes",type=Path); ap.add_argument("references",type=Path); ap.add_argument("results",type=Path)
    ap.add_argument("work",type=Path,nargs="+")
    args=ap.parse_args()
    torch.set_num_threads(2)
    metric=lpips.LPIPS(net="squeeze",version="0.1",verbose=False).eval()
    def tensor(im):
        return torch.from_numpy(np.array(im.convert("RGB"))).permute(2,0,1).unsqueeze(0).float()/127.5-1
    out={}
    for folder in args.work:
        settings=out[folder.name]={}
        for h in (480,500):
            w=h*8//5
            src=args.scenes/f"{w}x{h}"; ref=args.scenes/"1280x800"
            chart=photo_chart(args.references)
            names=[("photo",chart.resize((w,h),Image.Resampling.LANCZOS),chart)]
            for tag,lo,hi in [("real","source4","source4"),("x2","x2_f4_t1_gen","x2_f4_t1_truth"),
                              ("x3","x3_f4_t1_gen","x3_f4_t1_truth")]:
                names.append((tag,read(src/(PREFIX+lo+".ppm")),read(ref/(PREFIX+hi+".ppm"))))
            for tag,low,truth in names:
                proc=subprocess.run(["./replay",str(w),str(h),"1280","800"],cwd=folder,input=low.tobytes(),capture_output=True,check=True)
                results={}
                size=1280*800*4
                for i,key in enumerate(METHODS):
                    im=Image.frombytes("RGBA",OUT,proc.stdout[i*size:(i+1)*size])
                    with torch.inference_mode():
                        value=float(metric(tensor(im),tensor(truth)).item())
                    score,_=scores(im,truth)
                    results[key]={"lpips":round(value,6),"psnr_db":round(score[0],5),"ssim":round(score[1],5)}
                settings[f"{h}-{tag}"]=results
                args.results.write_text(json.dumps(out,indent=2)+"\n")
                print(folder.name,h,tag,flush=True)
if __name__=="__main__": main()
