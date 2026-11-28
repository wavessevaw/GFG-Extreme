"""Tic-aligned lossless game outputs from a stock DSDA-Doom install and Freedoom's own demo."""
import argparse
import os
from pathlib import Path
import struct
import subprocess


def main():
    p=argparse.ArgumentParser()
    p.add_argument("wad",type=Path);p.add_argument("out",type=Path)
    p.add_argument("--dsda",default="dsda-doom")
    args=p.parse_args()
    root=args.out.resolve();root.mkdir(parents=True,exist_ok=True)
    with args.wad.open("rb") as f:
        magic,count,directory=struct.unpack("<4sii",f.read(12))
        assert magic==b"IWAD"
        f.seek(directory); lumps=f.read(16*count)
        address,length=next((a,n) for a,n,name in struct.iter_unpack("<ii8s",lumps) if name.rstrip(b"\0")==b"DEMO1")
        f.seek(address); demo=f.read(length)
    assert demo[0]==109 and demo[9:13]==bytes([1,0,0,0])
    short=root/"short.lmp";short.write_bytes(demo[:13+4*190]+bytes([128]))
    (root/"data").mkdir(exist_ok=True);(root/"config").mkdir(exist_ok=True)
    env=dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",SDL_RENDER_DRIVER="software",
             XDG_DATA_HOME=str(root/"data"),XDG_CONFIG_HOME=str(root/"config"))
    for size in ("1280x800","800x500","768x480"):
        sub=root/size;sub.mkdir(exist_ok=True)
        (sub/"capture.cfg").write_text(
            'cap_videocommand "ffmpeg -loglevel error -f rawvideo -pix_fmt rgb24 -r %r -s %wx%h -i - -c:v ffv1 -threads 2 -y footage.mkv"\n'
            'cap_soundcommand "cat > /dev/null"\ncap_muxcommand "true"\ncap_remove_tempfiles 0\n'
            f'cap_fps 35\nuncapped_framerate 0\nrender_wipescreen 0\nscreen_resolution "{size}"\n')
        subprocess.run([args.dsda,"-iwad",str(args.wad.resolve()),"-timedemo",str(short),"-geom",size+"w",
              "-vidmode","sw","-nomusic","-nomouse","-nojoy","-config","capture.cfg","-viddump","sample.mkv"],
              cwd=sub,env=env,check=True)
        frames=subprocess.check_output(["ffprobe","-v","error","-count_frames","-select_streams","v","-show_entries",
                "stream=nb_read_frames","-of","csv=p=0","footage.mkv"],cwd=sub,text=True)
        if int(frames.strip())!=189:raise RuntimeError(f"{size}: {frames.strip()} captured frames")
if __name__=="__main__":main()
