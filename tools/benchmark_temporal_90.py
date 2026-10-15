#!/usr/bin/env python3
"""Compare two Vulkan generators at 30->90 on deterministic held-out frames.

Analytic scenes are synthetic ground truth, not commercial-game captures.
Reports every scene, including regressions. Vulkan CPU-device timings do not
establish Steam Deck speed. Requires numpy and NVIDIA flip-evaluator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import statistics
import tempfile

import flip_evaluator
import numpy as np


def texture(x, y):
    return np.stack([0.5 + 0.22 * np.sin(x * 0.17) * np.cos(y * 0.13),
                     0.5 + 0.21 * np.sin(y * 0.19 + x * 0.07),
                     0.5 + 0.24 * np.cos(x * 0.11 - y * 0.15)], -1)


def scene(name, frame, w, h):
    y, x = np.mgrid[:h, :w].astype(float)
    speed = 7.0 if name == "fast-pan" else 2.0
    rgb = texture(x - speed * frame, y - 0.5 * frame)
    if name in ("occlusion", "thin-posts"):
        if name == "occlusion":
            mask = (np.abs(x - (w * 0.3 + frame * 4)) < w * 0.13) & (y > h * 0.15)
        else:
            mask = ((x + frame * 3) % 47 < 3) & (y > 25)
        fg = texture(x + frame * 3 + 71, y + 19) * [1.1, 0.6, 0.7]
        rgb = np.where(mask[..., None], fg, rgb)
    if name == "blade":
        a = frame * 0.07
        u, v = x - w * 0.5, y - h * 0.6
        along, across = u * np.cos(a) + v * np.sin(a), -u * np.sin(a) + v * np.cos(a)
        mask = (along > 0) & (along < h * 0.65) & (np.abs(across) < 1.6)
        rgb = np.where(mask[..., None], [0.92, 0.94, 0.99], rgb)
    if name == "specular":
        glow = np.exp(-((x - w * 0.3 - frame * 6) ** 2 + (y - h * 0.5) ** 2) / 100)
        rgb = np.clip(rgb + glow[..., None] * 0.7, 0, 1)
    # A fixed high-contrast HUD, over moving content; changing glyph pixels
    # exercise the still-counter without assuming every UI element is static.
    if name == "hud":
        panel = (x < w * 0.3) & (y < h * 0.25)
        glyph = (((x.astype(int) // 3 + y.astype(int) // 3) % 2) == 0)
        rgb = np.where(panel[..., None], np.where(glyph[..., None], 0.95, 0.05), rgb)
    return np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)


def score(generated, truth):
    flips, edges = [], []
    for got, expected in zip(generated, truth):
        fm, _, _ = flip_evaluator.evaluate(expected.astype(np.float32) / 255,
                                           got.astype(np.float32) / 255, "LDR",
                                           applyMagma=False, computeMeanError=False)
        fm = np.asarray(fm).reshape(expected.shape[:2])
        flips.append(float(fm.mean()))
        border = np.zeros(fm.shape[:2], bool)
        border[:8] = border[-8:] = True
        border[:, :8] = border[:, -8:] = True
        edges.append(float(fm[border].mean()))
    return dict(mean_flip=float(np.mean(flips)), p95_frame_flip=float(np.percentile(flips, 95)),
                border_flip=float(np.mean(edges)), generated_frames=len(generated))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pairs", type=int, default=6)
    ap.add_argument("--width", type=int, default=384)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--scenes", default="pan,fast-pan,occlusion,thin-posts,blade,specular,hud")
    ap.add_argument("--frames-root", type=Path, help="existing Godot scenes; discard the first 10 warmup frames")
    args = ap.parse_args()
    report = dict(input_fps=30, target_fps=90, width=args.width, height=args.height,
                  scope="synthetic held-out frames; not measured game FPS",
                  baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
                  timing_scope="Vulkan timestamps on host device; first two pairs excluded; not Deck timings",
                  scenes=[])
    env = dict(os.environ)
    if "TE_ICD" in env:
        env["VK_ICD_FILENAMES"] = env["TE_ICD"]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for name in args.scenes.split(","):
            if args.frames_root:
                from PIL import Image
                files = sorted((args.frames_root / name).glob("f*.png"))[10:10 + args.pairs * 3 + 1]
                if len(files) != args.pairs * 3 + 1:
                    raise ValueError(f"{name}: not enough freshly rendered frames")
                frames = np.stack([np.asarray(Image.open(f).convert("RGB")) for f in files])
            else:
                frames = np.stack([scene(name, k, args.width, args.height) for k in range(args.pairs * 3 + 1)])
            src = td / "source.npy"
            report.update(width=frames.shape[2], height=frames.shape[1])
            np.save(src, frames)
            truth = frames[[k for k in range(len(frames)) if k % 3]]
            row = dict(scene=name)
            for label, exe in (("baseline", args.baseline), ("candidate", args.candidate)):
                output = td / f"{label}.npy"
                stats_file = td / f"{label}.jsonl"
                subprocess.run([str(exe.resolve()), "--frames", str(src), "--algo", "lmc",
                                "--step", "3", "--out", str(output), "--json", str(stats_file)], check=True, env=env)
                row[label] = score(np.load(output), truth)
                stats = [json.loads(line) for line in stats_file.read_text().splitlines()][2:]
                if stats:
                    row[label]["gpu_pair_ms_median"] = statistics.median(
                        s["pyramid_ms"] + s["analyze_ms"] + s["classify_ms"]
                        + sum(f["total_ms"] for f in s["frames"]) for s in stats)
                    row[label]["fit_gap_ms_median"] = statistics.median(s["lmc_ms"]["fit_wait"] for s in stats)
                    row[label]["field_ms_median"] = statistics.median(s["lmc_ms"]["field"] for s in stats)
                    row[label]["passes_ms_median"] = {
                        key: statistics.median(s["lmc_ms"][key] for s in stats)
                        for key in stats[0]["lmc_ms"]}
                    if "pair_ready_ms" in stats[0]:
                        row[label]["pair_ready_ms_median"] = statistics.median(s["pair_ready_ms"] for s in stats)
                        row[label]["cpu_fit_ms_median"] = statistics.median(s["cpu_fit_ms"] for s in stats)
            report["scenes"].append(row)
            print(json.dumps(row), flush=True)
            args.out.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
