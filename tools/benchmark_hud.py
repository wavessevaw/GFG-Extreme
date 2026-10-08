#!/usr/bin/env python3
"""Compare HUD pixels and CPU render cost against an optional release baseline."""
import argparse
import importlib.util
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from py_modules.gfg_plugin import hud_rings

SAMPLE = {"fps": 90, "real": 45, "target": 90, "tdp": 15, "limit": 15,
          "battery_min": 125, "battery_pct": 72,
          "frame_os": {"estimate": False, "level": "boost", "response": 47, "frames": 50, "energy": 9}}


def timing(module, preset, scale):
    times = []
    for fps in (87, 89, 88, 90, 86):
        start = time.process_time()
        module.render({**SAMPLE, "fps": fps}, preset, scale)
        times.append((time.process_time() - start) * 1000)
    return statistics.median(times)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline")
    args = parser.parse_args()
    baseline = None
    if args.baseline:
        spec = importlib.util.spec_from_file_location("py_modules.gfg_plugin._hud_baseline", args.baseline)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
    for preset in ("minimal", "detailed"):
        for scale in (1.0, 3.0):
            actual = hud_rings.render(SAMPLE, preset, scale)
            if baseline:
                expected = baseline.render(SAMPLE, preset, scale)
                assert actual[:2] == expected[:2]
                delta = max(abs(a - b) for a, b in zip(actual[2], expected[2]))
                assert delta <= 1, f"pixel mismatch: {preset} scale {scale}, delta {delta}"
            new_ms = timing(hud_rings, preset, scale)
            if baseline:
                old_ms = timing(baseline, preset, scale)
                print(f"{preset} scale={scale}: baseline={old_ms:.2f}ms cached={new_ms:.2f}ms speedup={old_ms/new_ms:.2f}x")
                assert new_ms < old_ms, "cached renderer must reduce CPU time on this runner"
            else:
                print(f"{preset} scale={scale}: cached={new_ms:.2f}ms")


if __name__ == "__main__":
    main()
