#!/usr/bin/env python3
"""Offline replay for GFG Governor telemetry/planner policy."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_core import OperatingPointPlanner
from gfg_plugin.governor_telemetry import TelemetryObserver


def run(path: Path, external: bool = False) -> dict:
    observer = TelemetryObserver(Path("/nonexistent"))
    latest_t = 0.0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        latest_t = float(item.get("t", latest_t))
        line = item.get("line")
        if line:
            observer.consume_line(str(line), now=latest_t)
    summary = observer.summary(window_seconds=max(12.0, latest_t + 1.0), now=latest_t)
    planner = OperatingPointPlanner()
    decision = planner.recommend(
        external_display=external,
        observed_p5_fps=(summary.get("real") or {}).get("p5"),
        observed_multiplier=(summary.get("multiplier") or {}).get("median"),
    )
    return {
        "file": str(path),
        "external_display": external,
        "summary": summary,
        "decision": decision.to_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--dock", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.session, external=args.dock), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
