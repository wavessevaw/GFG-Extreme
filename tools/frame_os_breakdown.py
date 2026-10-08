#!/usr/bin/env python3
"""Where does a real frame's time go?  Evidence for GFG Frame OS from a recorded log.

Reads the renderer's ``present-breakdown`` lines (from a log zip or a diagnostics file) and
reports, per real frame: time blocked waiting for a swapchain image (``acquire_ms`` — queueing
that tick shaping removes), waiting for the game's GPU work (``render_fence_ms``), and the total
time the present call holds the game thread.  Usage: frame_os_breakdown.py <log.zip|diagnostics.log>
"""
from __future__ import annotations

import re
import statistics
import sys
import zipfile
from typing import Dict, Iterable, List

FIELD = re.compile(r"(\w+)=([-0-9.]+)")


def lines_from(path: str) -> Iterable[str]:
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.startswith("diagnostics-"):
                    yield from z.read(name).decode("utf-8", "replace").splitlines()
    else:
        with open(path, encoding="utf-8", errors="replace") as f:
            yield from f


def breakdown(lines: Iterable[str]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for line in lines:
        if "operation=present-breakdown" not in line:
            continue
        for key, value in FIELD.findall(line):
            if key.endswith("_ms"):
                out.setdefault(key, []).append(float(value))
    return out


def summary(data: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    def q(values: List[float], p: float) -> float:
        s = sorted(values)
        return round(s[min(len(s) - 1, int(p * (len(s) - 1)))], 2)
    return {k: {"n": len(v), "p50": q(v, 0.5), "p90": q(v, 0.9), "mean": round(statistics.fmean(v), 2)}
            for k, v in sorted(data.items()) if v}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        s = summary(breakdown(lines_from(path)))
        print(path)
        for key in ("total_ms", "render_fence_ms", "acquire_ms", "generated_present_ms", "schedule_ms"):
            if key in s:
                print(f"  {key:22s} {s[key]}")
