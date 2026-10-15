#!/usr/bin/env python3
"""Decimate a recorded sequence, regenerate the dropped frames and score them.

For every segment of a sequence (frames.npy + meta.json) the bench keeps every
K-th frame as the real input, runs the GPU engine (te-bench) in the requested
modes and the trivial baselines, and compares each generated frame with the
real frame that was held out.  GPU stage times come from Vulkan timestamp
queries on whatever device te-bench runs on; on lavapipe that is a CPU
emulation and says nothing about Steam Deck speed.

Writes <work>/<name>.json with per-segment and overall results.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine/gfg-temporal/reference"))
from gfg_temporal_ref.metrics import psnr_y, ssim_y, seam_excess, temporal_error  # noqa: E402
from gfg_temporal_ref.core import repeat_nearest, linear_blend  # noqa: E402

CLASS_ORDER = ("reuse", "light", "full")


def run_engine(bench, seq, start, pairs, step, mode, work, tag, profile, extra=(), icd=None):
    out = work / f"{tag}.npy"
    js = work / f"{tag}.jsonl"
    an = work / f"{tag}_an"
    cmd = [str(bench), "--frames", str(seq / "frames.npy"), "--start", str(start), "--pairs", str(pairs),
           "--step", str(step), "--mode", mode, "--out", str(out), "--json", str(js), "--analysis", str(an), *extra]
    if profile:
        cmd.append("--profile")
    env = dict(os.environ)
    if icd:
        env["VK_ICD_FILENAMES"] = icd
    t0 = time.time()
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"te-bench failed ({proc.returncode}): {proc.stderr}")
    rows = [json.loads(line) for line in js.read_text().splitlines()]
    meta = json.loads((an / "meta.json").read_text())
    cls = np.fromfile(an / "classes.u8", np.uint8).reshape(-1, meta["tiles_y"], meta["tiles_x"])
    return np.load(out, mmap_mode="r"), rows, cls, time.time() - t0, proc.stderr.strip().splitlines()[0]


def score(frames, start, pairs, step, gen_fn, classes=None, tile=16):
    """Metrics of generated frames.  gen_fn(pair, i) returns output i of pair."""
    psnr, ssim, terr, seams = [], [], [], []
    for k in range(pairs):
        a_idx = start + k * step
        prev_out = frames[a_idx]
        prev_gt = frames[a_idx]
        for i in range(step - 1):
            gt = frames[a_idx + 1 + i]
            out = gen_fn(k, i)
            psnr.append(psnr_y(out, gt))
            ssim.append(ssim_y(out, gt))
            terr.append(temporal_error(prev_out, out, prev_gt, gt))
            prev_out, prev_gt = out, gt
            if classes is not None and i == step - 2:
                seams.append(seam_excess(out, gt, classes[k], tile))
        b = frames[a_idx + step]
        terr.append(temporal_error(prev_out, b, prev_gt, b))
    res = {"psnr_y": float(np.mean(psnr)), "psnr_y_p5": float(np.percentile(psnr, 5)), "ssim_y": float(np.mean(ssim)),
           "temporal_err": float(np.mean(terr)) * 255.0, "frames": len(psnr)}
    if seams:
        res["seam_excess"] = float(np.mean(seams)) * 255.0
    return res


def summarize_costs(rows, step):
    def mean(key):
        vals = [r[key] for r in rows]
        return float(np.mean(vals)) if vals else 0.0

    frames = [f for r in rows for f in r["frames"]]
    tiles = rows[0]["tiles"] if rows else 1
    out = {"pyramid_ms": mean("pyramid_ms"), "analyze_ms": mean("analyze_ms"), "classify_ms": mean("classify_ms"),
           "lists_ms": float(np.mean([f["lists_ms"] for f in frames])),
           "frame_ms": float(np.mean([f["total_ms"] for f in frames])),
           "frame_ms_p95": float(np.percentile([f["total_ms"] for f in frames], 95)),
           "frame_ms_p99": float(np.percentile([f["total_ms"] for f in frames], 99)),
           "scene_cuts": int(sum(r["scene_cut"] for r in rows)),
           "promoted": int(rows[-1]["promoted"]) if rows else 0,
           "confidence": mean("confidence")}
    for c in CLASS_ORDER:
        out[f"share_{c}"] = float(np.mean([f[c] / tiles for f in frames]))
        if rows and rows[0].get("profile"):
            vals = [f[f"{c}_ms"] for f in frames]
            out[f"{c}_ms"] = float(np.mean(vals))
    pair_ms = [r["pyramid_ms"] + r["analyze_ms"] + r["classify_ms"] + sum(f["total_ms"] for f in r["frames"]) for r in rows]
    out["pair_ms"] = float(np.mean(pair_ms))
    out["pair_ms_p95"] = float(np.percentile(pair_ms, 95))
    out["pair_ms_p99"] = float(np.percentile(pair_ms, 99))
    out["per_output_ms"] = out["pair_ms"] / (step - 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", type=Path, required=True)
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--bench", type=Path, default=ROOT / "engine/gfg-temporal/build/te-bench")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--modes", default="adaptive,full,light")
    ap.add_argument("--segments", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--icd", default=os.environ.get("VK_ICD_FILENAMES", ""))
    ap.add_argument("--no-ssim", action="store_true")
    ap.add_argument("--production-timing", action="store_true",
                    help="also run adaptive and full without per-executor barriers")
    args = ap.parse_args()
    meta = json.loads((args.seq / "meta.json").read_text())
    frames = np.load(args.seq / "frames.npy", mmap_mode="r")
    name = args.name or f"{args.seq.name}_x{args.step}"
    args.work.mkdir(parents=True, exist_ok=True)
    wanted = set(filter(None, args.segments.split(",")))
    global ssim_y
    if args.no_ssim:
        ssim_y = lambda a, b: float("nan")  # noqa: E731
    report = {"sequence": meta.get("source", str(args.seq)), "fps_source": meta["fps"], "step": args.step,
              "fps_real": meta["fps"] / args.step, "fps_output": meta["fps"], "width": meta["width"],
              "height": meta["height"], "segments": {}}
    for seg in meta["segments"]:
        if wanted and seg["name"] not in wanted:
            continue
        start = seg["start"]
        pairs = (seg["end"] - 1 - start) // args.step
        if pairs < 2:
            continue
        res = {"start": start, "pairs": pairs, "methods": {}}
        res["methods"]["repeat"] = score(frames, start, pairs, args.step,
                                         lambda k, i: repeat_nearest(frames[start + k * args.step],
                                                                     frames[start + (k + 1) * args.step],
                                                                     (i + 1) / args.step))
        res["methods"]["blend"] = score(frames, start, pairs, args.step,
                                        lambda k, i: linear_blend(frames[start + k * args.step],
                                                                  frames[start + (k + 1) * args.step],
                                                                  (i + 1) / args.step))
        for mode in filter(None, args.modes.split(",")):
            tag = f"{name}_{seg['name']}_{mode}"
            out, rows, cls, wall, device = run_engine(args.bench, args.seq, start, pairs, args.step, mode, args.work,
                                                      tag, True, icd=args.icd or None)
            m = score(frames, start, pairs, args.step, lambda k, i: out[k * (args.step - 1) + i], cls)
            m["cost"] = summarize_costs(rows, args.step)
            m["device"] = device
            m["wall_s"] = wall
            res["methods"][f"te_{mode}"] = m
            del out
            (args.work / f"{tag}.npy").unlink()
            if args.production_timing and mode in ("adaptive", "full"):
                out, rows, cls, wall, _ = run_engine(args.bench, args.seq, start, pairs, args.step, mode, args.work,
                                                     tag + "_prod", False, icd=args.icd or None)
                res["methods"][f"te_{mode}"]["cost_production"] = summarize_costs(rows, args.step)
                del out
                (args.work / f"{tag}_prod.npy").unlink()
        report["segments"][seg["name"]] = res
        print(f"{name} {seg['name']}: " + ", ".join(
            f"{k} {v['psnr_y']:.2f}dB" + (f"/{v['cost']['pair_ms']:.1f}ms" if "cost" in v else "")
            for k, v in res["methods"].items()), flush=True)
    (args.work / f"{name}.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
