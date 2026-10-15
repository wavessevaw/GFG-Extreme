#!/usr/bin/env python3
"""Markdown tables from run_bench.py results (quality per segment, cost and class shares)."""
import json
import sys
from pathlib import Path

METHODS = ("repeat", "blend", "te_light", "te_full", "te_adaptive")


def main():
    for path in sys.argv[1:]:
        r = json.loads(Path(path).read_text())
        print(f"\n### {Path(path).stem}: {r['fps_real']:.1f} -> {r['fps_output']:.0f} FPS, {r['width']}x{r['height']}\n")
        print("| segment | pairs | " + " | ".join(m for m in METHODS) + " |")
        print("|---|---|" + "---|" * len(METHODS))
        for name, seg in r["segments"].items():
            cells = []
            for m in METHODS:
                v = seg["methods"].get(m)
                cells.append("–" if not v else f"{v['psnr_y']:.2f} / {v['ssim_y']:.3f} / {v['temporal_err']:.2f}")
            print(f"| {name} | {seg['pairs']} | " + " | ".join(cells) + " |")
        print("\n| segment | method | pair GPU ms (mean / p95 / p99) | analysis ms | per output ms | reuse / light / full share | seam excess |")
        print("|---|---|---|---|---|---|---|")
        for name, seg in r["segments"].items():
            for m in ("te_full", "te_light", "te_adaptive"):
                v = seg["methods"].get(m)
                if not v:
                    continue
                c = v["cost"]
                print(f"| {name} | {m} | {c['pair_ms']:.1f} / {c['pair_ms_p95']:.1f} / {c['pair_ms_p99']:.1f} | "
                      f"{c['pyramid_ms'] + c['analyze_ms'] + c['classify_ms']:.1f} | {c['per_output_ms']:.1f} | "
                      f"{c['share_reuse']:.2f} / {c['share_light']:.2f} / {c['share_full']:.2f} | "
                      f"{v.get('seam_excess', float('nan')):.3f} |")


if __name__ == "__main__":
    main()
