#!/usr/bin/env python3
"""Compare the CPU fit with a Git baseline: exact models, then paired timings.

No Vulkan device is needed. Uses the full 1280x800 block grid and includes
camera motion, mixed planes, outliers and empty inputs. Times are host CPU
times, not Steam Deck results. Usage: python3 tools/benchmark_lmc_fit.py
"""
import argparse
import ctypes as C
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "engine/gfg-temporal/src"


class Plane(C.Structure):
    _fields_ = [("h", (C.c_float * 3) * 3), ("share", C.c_float)]


class Model(C.Structure):
    _fields_ = [("nlayers", C.c_uint32), ("layers", Plane * 3),
                ("npal", C.c_uint32), ("pal", (C.c_float * 2) * 4)]


def library(source, dest):
    subprocess.run(["cc", "-std=c11", "-O2", "-fPIC", "-shared", "-I", str(SRC),
                    str(source), "-lm", "-o", str(dest)], check=True)
    lib = C.CDLL(str(dest))
    lib.te_lmc_fit_alloc.restype = C.c_void_p
    lib.te_lmc_fit_free.argtypes = [C.c_void_p]
    lib.te_lmc_fit.argtypes = [C.c_void_p, C.POINTER(C.c_float), C.POINTER(C.c_ubyte),
                              C.POINTER(C.c_ubyte), C.c_int, C.c_int, C.c_int,
                              C.c_uint32, C.POINTER(Model), C.POINTER(Model)]
    return lib


def inputs(kind, bw=160, bh=100):
    rng = random.Random(471)
    vec = (C.c_float * (bw * bh * 2))()
    usable = (C.c_ubyte * (bw * bh))()
    hud = (C.c_ubyte * (bw * bh))()
    for i in range(bw * bh):
        x, y = (i % bw) * 8 + 3.5, (i // bw) * 8 + 3.5
        vx, vy = 8.0, 2.0
        if kind == "rotation":
            a = 0.014
            vx = x - (math.cos(a) * (x - 640) + math.sin(a) * (y - 400) + 640)
            vy = y - (-math.sin(a) * (x - 640) + math.cos(a) * (y - 400) + 400)
        elif kind == "planes":
            vx, vy = ((8.0 + 0.006 * x, 2.0) if x < 850 else (-5.0, 4.0 + 0.004 * y))
        elif kind == "outliers" and rng.random() < 0.35:
            vx, vy = rng.uniform(-60, 60), rng.uniform(-40, 40)
        elif kind == "noise":
            vx, vy = rng.uniform(-100, 100), rng.uniform(-100, 100)
        vec[2 * i], vec[2 * i + 1] = vx, vy
        usable[i] = kind != "empty"
        hud[i] = x < 120 and y < 80
    return vec, usable, hud, bw, bh


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-ref", default="v2.1.2-te.7")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    results = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        old = td / "old.c"
        old.write_bytes(subprocess.check_output(
            ["git", "show", f"{args.baseline_ref}:engine/gfg-temporal/src/te_lmc_fit.c"], cwd=ROOT))
        libs = [library(old, td / "old.so"), library(SRC / "te_lmc_fit.c", td / "new.so")]
        work = [lib.te_lmc_fit_alloc() for lib in libs]
        if not all(work):
            raise MemoryError("fit scratch allocation failed")
        try:
            for kind in ("translation", "rotation", "planes", "outliers", "noise", "empty"):
                data = inputs(kind)
                models = [Model(), Model()]
                elapsed = [[], []]
                checked = 0
                for seed in range(1, 17):
                    previous = [Model.from_buffer_copy(bytes(m)) for m in models]
                    # Alternate order; first two iterations warm both implementations.
                    for i in ((0, 1) if seed % 2 else (1, 0)):
                        start = time.perf_counter_ns()
                        rc = libs[i].te_lmc_fit(work[i], *data, 1, seed,
                                                C.byref(previous[i]) if seed % 3 else None,
                                                C.byref(models[i]))
                        took = (time.perf_counter_ns() - start) / 1e6
                        if rc:
                            raise RuntimeError(f"{kind}: fit failed ({rc})")
                        if seed > 2:
                            elapsed[i].append(took)
                    if bytes(models[0]) != bytes(models[1]):
                        raise AssertionError(f"model differs: {kind}, seed {seed}")
                    checked += 1
                before, after = map(statistics.median, elapsed)
                results.append(dict(scene=kind, models_bit_exact=checked,
                                    baseline_ms=before, candidate_ms=after,
                                    speedup=before / max(after, 1e-9)))
        finally:
            for lib, ptr in zip(libs, work):
                lib.te_lmc_fit_free(ptr)
    report = dict(baseline=args.baseline_ref, grid=[160, 100],
                  device="host CPU, not Steam Deck", results=results)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
