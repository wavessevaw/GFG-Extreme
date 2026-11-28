"""Real frames only. Test a lightweight translational history before allocating runtime buffers."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, minimum_filter, maximum_filter
from measure import OUT, luma, scores
from demo_replay import reconstruct


def frames(path):
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-vf","select=between(n\\,84\\,91)",
        "-vsync","0","-threads","1","-f","rawvideo","-pix_fmt","rgba","-"])
    return raw

def displacement(prev,curr):
    # Downsample for global translation; select a subpixel peak by parabolic fitting.
    a,b=prev[::2,::2],curr[::2,::2]
    win=np.outer(np.hanning(a.shape[0]),np.hanning(a.shape[1]))
    spectrum=np.fft.rfft2((b-b.mean())*win)*np.conj(np.fft.rfft2((a-a.mean())*win))
    corr=np.fft.irfft2(spectrum/np.maximum(abs(spectrum),1e-8),s=a.shape,axes=(0,1)).real
    peak=np.unravel_index(corr.argmax(),a.shape)
    shift=[]
    for axis,(i,dim) in enumerate(zip(peak,a.shape)):
        lo=list(peak);hi=list(peak);lo[axis]=(i-1)%dim;hi[axis]=(i+1)%dim
        left,right=corr[tuple(lo)],corr[tuple(hi)]
        denom=left+right-2*corr[peak]
        sub=np.clip(.5*(left-right)/denom,-.5,.5) if denom else 0
        shift.append(2*((i-dim if i>dim/2 else i)+sub))
    return np.asarray(shift)

def main():
    p=argparse.ArgumentParser();p.add_argument("videos",type=Path);p.add_argument("out",type=Path)
    args=p.parse_args()
    ref=np.frombuffer(frames(args.videos/"1280x800/footage.mkv"),np.uint8).reshape(8,800,1280,4)
    lo=np.frombuffer(frames(args.videos/"800x500/footage.mkv"),np.uint8).reshape(8,500,800,4)
    yy,xx=np.mgrid[:800,:1280].astype(np.float32)
    last_src=last_output=None; rows=[];old_err={}
    for frame,gt in zip(lo,ref):
        im=np.array(reconstruct(Image.fromarray(frame))[1],dtype=np.float32)
        if last_src is not None:
            shift=displacement(luma(last_src),luma(frame))*1.6
            coords=[yy-shift[0],xx-shift[1]]
            hist=np.stack([map_coordinates(last_output[:,:,i],coords,order=1,mode="nearest") for i in range(3)],axis=-1)
            rgb=im[:,:,:3]
            delta=np.abs(luma(hist)-luma(rgb));weight=.25*np.clip(1-delta/12,0,1)
            bounded=np.maximum(minimum_filter(rgb,size=(3,3,1)),np.minimum(hist,maximum_filter(rgb,size=(3,3,1))))
            combined=np.uint8(np.rint(rgb+(bounded-rgb)*weight[:,:,None]))
            row={"accepted_pct":float((weight>0).mean()*100)}
            for key,out in [("spatial",np.uint8(im)),("history",combined)]:
                sc,err=scores(out,gt)
                row[key]=dict(psnr_db=sc[0],ssim=sc[1],temporal_mae=float(np.abs(err-old_err[key]).mean()) if key in old_err else None)
                old_err[key]=err
            rows.append(row)
        last_src=frame;last_output=im
    args.out.write_text(json.dumps(rows,indent=2)+"\n")
if __name__=="__main__": main()
