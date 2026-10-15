#!/usr/bin/env python3
"""Experimental mechanisms A-G on the reference implementation.

Each configuration processes the same consecutive real-frame pairs of every
segment (history included), scores the generated frames against the held-out
ones and reports the exact texture-fetch counts the reference executed.  Fetch
counts are operation counts, not GPU time: they say what a mechanism removes,
not what it would save on a particular GPU.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine/gfg-temporal/reference"))
from gfg_temporal_ref import Params, TemporalEngine  # noqa: E402
from gfg_temporal_ref.metrics import psnr_y, ssim_y, temporal_error  # noqa: E402

CONFIGS = {
    "adaptive": ([], {}),
    "full-all": ([], {"adaptive": False, "force_class": 2}),
    "light-all": ([], {"adaptive": False, "force_class": 1}),
    "A-checker": (["A"], {}),
    "B-2x1": (["B2x1"], {}),
    "B-1x2": (["B1x2"], {}),
    "B-2x2": (["B2x2"], {}),
    "C-chroma": (["C"], {}),
    "D-nearest": (["D"], {}),
    "E-motion": (["E"], {}),
    "F-dual": (["F"], {}),
    "G-interleave": (["G"], {}),
}


def run(frames, segments, step, pairs, name):
    exps, over = CONFIGS[name]
    rows = []
    fetch = {}
    for seg in segments:
        eng = TemporalEngine(Params(**over), exps)
        start = seg["start"]
        n = min(pairs, (seg["end"] - 1 - start) // step)
        eng.push(frames[start], [])
        ts = [(i + 1) / step for i in range(step - 1)]
        for k in range(n):
            a = start + k * step
            outs, rep = eng.push(frames[a + step], ts)
            for stage, value in rep.ops.tex.items():
                fetch[stage] = fetch.get(stage, 0) + value
            prev_o, prev_g = frames[a], frames[a]
            for i, out in enumerate(outs):
                gt = frames[a + 1 + i]
                rows.append((seg["name"], psnr_y(out, gt), ssim_y(out, gt), temporal_error(prev_o, out, prev_g, gt)))
                prev_o, prev_g = out, gt
    outputs = len(rows)
    return {"config": name, "experiments": exps, "params": over, "outputs": outputs,
            "psnr_y": float(np.mean([r[1] for r in rows])), "ssim_y": float(np.mean([r[2] for r in rows])),
            "temporal_err": float(np.mean([r[3] for r in rows])) * 255,
            "per_segment": {s["name"]: float(np.mean([r[1] for r in rows if r[0] == s["name"]]))
                            for s in segments if any(r[0] == s["name"] for r in rows)},
            "fetches_per_output": {k: v / outputs for k, v in fetch.items()},
            "fetches_total_per_output": sum(fetch.values()) / outputs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", type=Path, required=True)
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--pairs", type=int, default=10, help="consecutive pairs per segment")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    meta = json.loads((args.seq / "meta.json").read_text())
    frames = np.load(args.seq / "frames.npy", mmap_mode="r")
    results = [run(frames, meta["segments"], args.step, args.pairs, c) for c in args.configs.split(",")]
    args.out.write_text(json.dumps({"sequence": meta.get("source"), "step": args.step, "pairs": args.pairs,
                                    "results": results}, indent=1))
    for r in results:
        print(f"{r['config']:13s} PSNR {r['psnr_y']:.2f} SSIM {r['ssim_y']:.4f} tErr {r['temporal_err']:.2f} "
              f"fetches/output {r['fetches_total_per_output'] / 1e6:.1f}M", flush=True)


if __name__ == "__main__":
    main()
