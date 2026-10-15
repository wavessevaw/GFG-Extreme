#!/usr/bin/env python3
"""Build the opt-in native Fusion Core from a pinned renderer and reviewed patch."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
FUSION = ROOT / "engine/gfg-fusion"


def run(*args, cwd=None):
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def build(work: Path, headers: Path, sanitize=False, native_no_dll=False):
    metadata = json.loads((FUSION / "source.json").read_text())
    patch = FUSION / "renderer.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != metadata["patch_sha256"]:
        raise ValueError("Frame Fusion patch differs from its recorded source identity")
    source, output = work / "source", work / ("sanitized" if sanitize else "build")
    work.mkdir(parents=True, exist_ok=True)
    if not (source / ".git").exists():
        source.mkdir()
        run("git", "init", "-q", source)
        run("git", "-C", source, "remote", "add", "origin", metadata["repository"])
        run("git", "-C", source, "fetch", "--depth=1", "origin", metadata["commit"])
        run("git", "-C", source, "checkout", "--detach", "FETCH_HEAD")
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if head != metadata["commit"]:
        raise ValueError("Frame Fusion renderer source has the wrong commit")
    native_marker = source / ".gfg-native-bridge"
    if native_marker.exists() and not native_no_dll:
        raise ValueError("This build tree has native no-DLL modifications; use a fresh work directory")
    if not (native_no_dll and native_marker.exists()):
        reverse = subprocess.run(["git", "-C", str(source), "apply", "--reverse", "--check", str(patch)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reverse.returncode:
            run("git", "-C", source, "apply", "--check", patch)
            run("git", "-C", source, "apply", patch)
        if native_no_dll:
            run(sys.executable, ROOT / "engine/gfg-native/bootstrap.py", "--source", source)
            native_marker.write_text("gfg-native-dll-free-te-bootstrap-v1\n")
    if not (headers / "vulkan/vulkan_core.h").is_file():
        raise ValueError("Pinned Vulkan-Headers are required")
    # Generated payloads always come from the upstream owning generator.
    # Neither the review patch nor this builder edits embedded arrays by hand.
    if metadata.get("shader_source_changed"):
        run(sys.executable, source / "engine/scripts/generate-spatial-scaling-spirv.py")
    # GFG Temporal Engine library (off at run time unless GFG_TEMPORAL_ENGINE selects it)
    temporal = ROOT / "engine/gfg-temporal"
    temporal_build = work / ("temporal-sanitized" if sanitize else "temporal")
    run("make", "-C", temporal, f"BUILD={temporal_build}", "lib")
    run("cmake", "-S", source / "engine", "-B", output,
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo" if sanitize else "-DCMAKE_BUILD_TYPE=Release",
        "-DMAKO_BUILD_UI=OFF", "-DMAKO_BUILD_CLI=ON", "-DMAKO_BUILD_VK_LAYER=ON",
        "-DBUILD_TESTING=ON", "-DMAKO_REQUIRE_NATIVE_PACKAGE_HEADERS=ON",
        f"-DMAKO_VULKAN_HEADERS_INCLUDE_DIR={headers}",
        f"-DGFG_FUSION_TEST_SOURCE={FUSION / 'tests/integration.cpp'}",
        f"-DGFG_TEMPORAL_SOURCE_DIR={temporal}",
        f"-DGFG_TEMPORAL_LIBRARY={temporal_build / 'libgfg-temporal.a'}",
        f"-DMAKO_ENABLE_SANITIZERS={'ON' if sanitize else 'OFF'}")
    run("cmake", "--build", output, "--parallel", "2")
    if not sanitize:
        run("ctest", "--test-dir", output, "--output-on-failure", "-E", "^gfg-frame-fusion$")
        run(output / "mako-render/gfg-frame-fusion-tests")
        run(output / "mako-render/gfg-frame-fusion-tests", "--profile")
    else:
        run("ctest", "--test-dir", output, "--output-on-failure", "-L", "portable-policy")
    print(f"Frame Fusion source={head} patch={metadata['patch_sha256']} build={output}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--headers", type=Path, required=True)
    parser.add_argument("--sanitized", action="store_true")
    parser.add_argument("--native-no-dll", action="store_true",
                        help="Experimental GFG Temporal Engine: bypass MAKO LSFG DLL bootstrap")
    args = parser.parse_args()
    build(args.work.resolve(), args.headers.resolve(), args.sanitized, args.native_no_dll)
