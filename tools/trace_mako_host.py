#!/usr/bin/env python3
"""Compile unmodified MAKO shaderchains against a host-call recording shim.

No DLL, shaders, Vulkan loader or GPU is used. Events are SIMULATED host calls.
The wrapper wiring follows the SDR context; source shaderchain constructors,
descriptor builder, scratch selectors and render methods execute unchanged.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

CHAINS = ("mipmaps", "alpha0", "alpha1", "beta0", "beta1", "gamma0", "gamma1", "delta0", "delta1", "generate")
HELPERS = ("utils.hpp", "utils.cpp", "managed_shader.hpp", "managed_shader.cpp", "image_prefix.hpp", "delta_scratch.hpp", "temporal_phases.hpp")
COMMON = ("helpers/pointers.hpp", "vulkan/vulkan.hpp", "vulkan/command_buffer.hpp", "vulkan/image.hpp", "vulkan/image_memory_pool.hpp", "vulkan/descriptor_pool.hpp", "vulkan/descriptor_set.hpp", "vulkan/shader.hpp", "vulkan/buffer.hpp", "vulkan/sampler.hpp")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(events):
    images = {e["id"]: e for e in events if e["event"] == "image"}
    dispatches = [e for e in events if e["event"] == "dispatch"]
    for event in dispatches:
        if any(i not in images for i in event["reads"] + event["writes"]):
            raise ValueError("dispatch references an unrecorded image")
        if any(v < 1 for v in event["groups"]):
            raise ValueError("dispatch has empty workgroup extent")
    owners = defaultdict(lambda: {"images": 0, "logical_bytes": 0})
    for image in images.values():
        owners[image["owner"]]["images"] += 1
        owners[image["owner"]]["logical_bytes"] += image["logical_bytes"]
    phases = defaultdict(lambda: {"dispatches": 0, "workgroups": 0, "image_barriers": 0})
    overlaps = []
    for event in dispatches:
        if event["frame"] != 0:
            continue
        row = phases[event["phase"]]
        row["dispatches"] += 1
        x, y, z = event["groups"]
        row["workgroups"] += x*y*z
        row["image_barriers"] += event["image_barriers"]
        both = set(event["reads"]) & set(event["writes"])
        if both:
            overlaps.append({"dispatch": event["id"], "images": sorted(both)})
    signatures = {}
    for frame in (0, 2, 3, 6):
        signatures[frame] = [(e["shader"], e["groups"], e["reads"], e["writes"])
                             for e in dispatches if e["frame"] == frame]
    return {"evidence": "SIMULATED", "images": len(images), "logical_bytes": sum(i["logical_bytes"] for i in images.values()),
            "allocations_by_owner": dict(owners), "first_pair": dict(phases),
            "bindings_repeat_at_6": signatures[0] == signatures[6],
            "bindings_repeat_at_2": signatures[0] == signatures[2],
            "bindings_repeat_at_3": signatures[0] == signatures[3],
            "sampled_storage_overlaps_first_pair": overlaps,
            "not_measured": ["GPU time", "VRAM allocation", "texture fetches", "bandwidth", "shader math", "image quality", "presentation"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mako", type=Path, required=True)
    parser.add_argument("--headers", type=Path, required=True, help="directory containing vulkan/vulkan_core.h")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args()
    if args.width < 64 or args.height < 64:
        parser.error("use dimensions >=64")
    args.out.mkdir(parents=True, exist_ok=False)
    src = args.mako / "engine/mako-backend/src"
    templates = Path(__file__).parent / "native_fg_trace"
    sources = {}
    report = {"schema": 1, "purpose": "host-call simulation; no GPU or proprietary shader",
              "width": args.width, "height": args.height, "scope": "SDR; modeled context wiring; actual unmodified chain/helper code",
              "source_sha256": sources, "runs": []}
    for relative in ("engine/mako-backend/src/mako.cpp", "engine/mako-common/include/mako-common/vulkan/image.hpp"):
        sources["reviewed/" + relative] = fingerprint(args.mako / relative)
    with tempfile.TemporaryDirectory(prefix="mako-host-trace-") as tmp:
        build = Path(tmp)
        for chain in CHAINS:
            for ext in ("hpp", "cpp"):
                relative = f"shaderchains/{chain}.{ext}"
                target = build / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src / relative, target)
                sources[relative] = fingerprint(src / relative)
        for helper in HELPERS:
            relative = "helpers/" + helper
            (build / "helpers").mkdir(exist_ok=True)
            shutil.copyfile(src / relative, build / relative)
            sources[relative] = fingerprint(src / relative)
        relative = "extraction/shader_registry.hpp"
        (build / "extraction").mkdir()
        shutil.copyfile(src / relative, build / relative)
        sources[relative] = fingerprint(src / relative)
        for path in COMMON:
            dest = build / "mako-common" / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text('#pragma once\n#include "sim.hpp"\n')
        for name in ("sim.hpp", "trace.cpp"):
            shutil.copyfile(templates / name, build / name)
            sources["harness/"+name] = fingerprint(templates / name)
        cmd = ["g++", "-std=c++20", "-O0", "-I"+str(build), "-I"+str(args.headers.resolve()),
               str(build / "trace.cpp"), str(build / "helpers/utils.cpp"),
               str(build / "helpers/managed_shader.cpp"),
               *[str(build / f"shaderchains/{c}.cpp") for c in CHAINS], "-o", str(build / "trace")]
        compiled = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (args.out / "compile.log").write_text(compiled.stdout)
        if compiled.returncode:
            print(compiled.stdout)
            raise SystemExit(compiled.returncode)
        report["compiler"] = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
        for scale in (1.0, 0.75, 0.5):
            for perf in (False, True):
                for outputs in (1, 2, 4):
                    stem = f"scale{scale}-perf{int(perf)}-outputs{outputs}"
                    output = subprocess.check_output([str(build / "trace"), str(args.width), str(args.height), str(outputs), str(int(perf)), str(scale)], text=True)
                    (args.out / (stem+".jsonl")).write_text(output)
                    summary = summarize([json.loads(line) for line in output.splitlines()])
                    assert summary["first_pair"]["prepass"]["dispatches"] == 34
                    assert summary["first_pair"]["synthesis"]["dispatches"] == 66*outputs
                    assert summary["bindings_repeat_at_6"]
                    report["runs"].append({"flow_scale": scale, "performance": perf, "outputs": outputs,
                                           "raw": stem+".jsonl", **summary})
        (args.out / "summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(f"Recorded {len(report['runs'])} configurations: {args.out / 'summary.json'}")


if __name__ == "__main__":
    main()
