#!/usr/bin/env python3
"""Repeat the quality/cost bench with alternating binary order.

Keeps every run, including regressions. Summary numbers are medians of the
per-run aggregates, not pooled frame percentiles. CPU Vulkan is not a Deck.
"""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--frames-root")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error("repeats must be positive")
    runs = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(args.repeats):
            first, second = ((args.baseline, args.candidate) if i % 2 == 0
                             else (args.candidate, args.baseline))
            result = Path(td) / "run.json"
            cmd = [sys.executable, str(Path(__file__).with_name("benchmark_temporal_90.py")),
                   "--baseline", first, "--candidate", second, "--scenes", args.scenes, "--out", str(result)]
            if args.frames_root:
                cmd += ["--frames-root", args.frames_root]
            subprocess.run(cmd, check=True)
            data = json.loads(result.read_text())
            if i % 2:
                for row in data["scenes"]:
                    row["baseline"], row["candidate"] = row["candidate"], row["baseline"]
                data["baseline_sha256"], data["candidate_sha256"] = data["candidate_sha256"], data["baseline_sha256"]
            runs.append(data)
            print(f"Completed paired run {i + 1}/{args.repeats}", flush=True)
    summary = []
    for scene in args.scenes.split(","):
        row = {"scene": scene}
        for label in ("baseline", "candidate"):
            results = [next(r for r in run["scenes"] if r["scene"] == scene)[label] for run in runs]
            row[label] = {key: statistics.median(r[key] for r in results)
                          for key, value in results[0].items() if isinstance(value, (int, float))}
        summary.append(row)
    args.out.write_text(json.dumps({"scope": "alternating runs on host Vulkan device; not Steam Deck",
                                   "aggregation": "median of per-run aggregates; raw runs included",
                                   "summary": summary, "runs": runs}, indent=2) + "\n")


if __name__ == "__main__":
    main()
