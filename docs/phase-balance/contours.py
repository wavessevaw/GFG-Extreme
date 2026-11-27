"""Track vertical grille bars in the rendered courtyard through both real endpoints."""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image

def pixels(path):
    with Image.open(path) as im:
        return np.asarray(im).astype(np.float32)

def position(image, predicted):
    height,width=image.shape[:2]
    radius=round(width*0.017)
    lo=round(predicted)-radius
    if lo<1 or lo+2*radius>=width-1 or abs(predicted-width/2)<30:
        return None
    strip=image[round(height*.49):round(height*.53),lo:lo+2*radius+1]
    distance=np.abs(strip-[22,33,41]).max(axis=2)
    weight=np.maximum(0,1-distance/26).mean(axis=0)
    if weight.sum()<max(1,width*.002):
        return None
    return lo+float(np.average(np.arange(weight.size),weights=weight))

def expected(time,k,width):
    yaw=.14*math.sin(14*time)
    x=(k*.47-(.16-1.7*time))/2.7
    return width*(.5+.7*(x*math.cos(yaw)-math.sin(yaw))/(math.cos(yaw)+x*math.sin(yaw)))

def evaluate(old,new,mode):
    scene='h_courtyard_reversal'
    times=np.array([0,42,68,119,151,190,247,277])/1000
    errors=[[],[]]; missing=[0,0]; total=0; step_by_phase=[]
    for frame in range(1,8):
        prev={}
        for phase in range(mode+1):
            name=f'{scene}_x{mode}_f{frame}_t{phase}'
            endpoint=phase in (0,mode)
            truth_name=f'{scene}_source{frame-1+int(phase==mode)}.ppm' if endpoint else name+'_truth.ppm'
            truth=pixels(old/truth_name)
            if not np.array_equal(truth,pixels(new/truth_name)): raise ValueError('Input mismatch')
            outs=[truth,truth] if endpoint else [pixels(d/(name+'_gen.ppm')) for d in (old,new)]
            time=times[frame-1]+phase/mode*(times[frame]-times[frame-1])
            current={}
            for k in range(-6,7):
                x=expected(time,k,truth.shape[1]); target=position(truth,x)
                if target is None: continue
                hits=[position(im,x) for im in outs]
                if not endpoint:
                    total+=1
                    for i in range(2): missing[i]+=hits[i] is None
                if None in hits: continue
                current[k]=np.array(hits)-target
                if k in prev:
                    err=current[k]-prev[k]
                    for i in range(2): errors[i].append(err[i])
            prev=current
    return dict(paired_steps=len(errors[0]),rms_pixels=np.sqrt(np.mean(np.square(errors),axis=1)).tolist(),
                missing=missing,intermediate_observations=total)
if __name__=='__main__':
    print(json.dumps({m:evaluate(*map(Path,sys.argv[1:]),m) for m in (2,3)},indent=2))
