#!/usr/bin/env python3
"""Decode a video clip into the bench sequence format (frames.npy + meta.json).

Every decoded frame is a real camera frame at the clip's native rate, so
dropping frames leaves real held-out targets.  Decoding uses ffmpeg; the clip
must be constant frame rate (checked from the stream header).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate,avg_frame_rate", "-of", "json", str(path)])
    s = json.loads(out)["streams"][0]
    return s["width"], s["height"], Fraction(s["r_frame_rate"]), Fraction(s["avg_frame_rate"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--start", type=float, default=0.0, help="seconds")
    ap.add_argument("--frames", type=int, default=180)
    ap.add_argument("--width", type=int, default=0, help="scale to this width (keeps aspect, even height)")
    ap.add_argument("--source-note", default="")
    args = ap.parse_args()
    w, h, rate, avg = probe(args.clip)
    if rate != avg:
        raise SystemExit(f"{args.clip}: variable frame rate ({rate} vs {avg}); not usable as ground truth")
    vf = []
    if args.width and args.width != w:
        h = int(round(h * args.width / w / 2)) * 2
        w = args.width
        vf = ["-vf", f"scale={w}:{h}:flags=lanczos"]
    args.out.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-ss", str(args.start), "-i", str(args.clip), *vf, "-frames:v", str(args.frames),
           "-vsync", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.check_output(cmd)
    n = len(raw) // (w * h * 3)
    frames = np.lib.format.open_memmap(args.out / "frames.npy", mode="w+", dtype=np.uint8, shape=(n, h, w, 3))
    frames[:] = np.frombuffer(raw[: n * w * h * 3], np.uint8).reshape(n, h, w, 3)
    frames.flush()
    fps = float(rate)
    meta = {"source": f"{args.clip.name} {args.source_note}".strip(), "fps": fps, "width": w, "height": h,
            "frames": n, "timestamps_s": [args.start + i / fps for i in range(n)],
            "segments": [{"name": args.clip.stem, "start": 0, "end": n}], "scene_cuts": []}
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"{args.out}: {n} frames {w}x{h} @ {fps:.3f}")


if __name__ == "__main__":
    main()
