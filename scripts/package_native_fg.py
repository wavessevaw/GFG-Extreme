#!/usr/bin/env python3
"""Package the *independent* TE8 Vulkan layer for a Steam Deck device trial.

No MAKO binaries, Lossless.dll, commercial models or installer mutation.
The full corresponding GFG native/Temporal source is bundled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = "GFG-Native-FG"
EXTENSIONS = {".c", ".h", ".comp", ".glsl", ".py", ".md", ".json", ".sh", ".txt", ".gd", ".tscn", ".godot"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native_elf(binary: Path) -> bytes:
    raw = binary.read_bytes()
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01" or raw[18:20] != (62).to_bytes(2, "little"):
        raise ValueError("GFG Native needs a Linux x86_64 ELF shared object")
    dynamic = subprocess.run(["readelf", "-d", str(binary)], check=True,
                             capture_output=True, text=True).stdout
    for forbidden in ("libmako", "Lossless.dll", "MAKO-Renderer"):
        if forbidden.lower() in dynamic.lower():
            raise ValueError(f"Prohibited runtime dependency: {forbidden}")
    if "libvulkan" in dynamic.lower():
        # libvulkan is allowed. This path does not require MAKO/LSFG.
        pass
    return raw


def source_files() -> dict[str, bytes]:
    selected = {}
    for directory in ("engine/gfg-native", "engine/gfg-temporal"):
        base = ROOT / directory
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if any(part in ("build", "build-te", "__pycache__", ".git", "results")
                   for part in path.relative_to(base).parts):
                continue
            if path.suffix not in EXTENSIONS and path.name not in ("Makefile",):
                continue
            if path.stat().st_size > 1_000_000:
                raise ValueError(f"Unexpectedly large source file {path}")
            selected["SOURCE/" + path.relative_to(ROOT).as_posix()] = path.read_bytes()
    if not any(name.endswith("src/te_engine.c") for name in selected):
        raise ValueError("Corresponding Temporal Engine source missing")
    if not any(name.endswith("src/cpu_bridge.c") for name in selected):
        raise ValueError("Corresponding Vulkan transport source missing")
    return selected


def package(binary: Path, outdir: Path, version: str) -> Path:
    if not re.fullmatch(r"2\.1\.2-native\.[0-9]+", version):
        raise ValueError("Expected prerelease version 2.1.2-native.N")
    files = {
        "libVkLayer_gfg_native.so": native_elf(binary),
        "VkLayer_gfg_native.json": (ROOT / "engine/gfg-native/VkLayer_gfg_native.json").read_bytes(),
        "install.sh": (ROOT / "engine/gfg-native/package/install.sh").read_bytes(),
        "uninstall.sh": (ROOT / "engine/gfg-native/package/uninstall.sh").read_bytes(),
        "gfg-native.sh": (ROOT / "engine/gfg-native/package/gfg-native.sh").read_bytes(),
        "README.ru.md": (ROOT / "engine/gfg-native/package/README.ru.md").read_bytes(),
        "LICENSE.md": (ROOT / "LICENSE.md").read_bytes(),
    }
    files.update(source_files())
    manifest = json.loads(files["VkLayer_gfg_native.json"])
    if manifest["layer"]["name"] != "VK_LAYER_GFG_native" or \
       manifest["layer"]["library_path"] != "./libVkLayer_gfg_native.so":
        raise ValueError("Native manifest identity mismatch")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    provenance = {
        "schema": 1,
        "version": version,
        "source_commit": commit,
        "algorithm": "GFG Temporal Engine TE8 LMC",
        "transport": "Vulkan GPU/CPU host-io/CPU/GPU",
        "architecture": "linux-x86_64",
        "runtime_requires": ["Vulkan 1.2", "64-bit Linux"],
        "runtime_forbidden": ["MAKO Renderer", "Lossless Scaling", "Lossless.dll"],
        "stage": "opt-in hardware-trial, physical display unverified",
        "elf_sha256": digest(files["libVkLayer_gfg_native.so"]),
    }
    files["MANIFEST.json"] = (json.dumps(provenance, sort_keys=True, indent=2) + "\n").encode()
    checksum = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(files.items()))
    files["SHA256SUMS.txt"] = checksum.encode()

    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / ("GFG-Native-FG-v" + version.replace(".", "_") + ".zip")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, strict_timestamps=True) as archive:
        for name, data in sorted(files.items()):
            zi = zipfile.ZipInfo(f"{ARTIFACT_ROOT}/{name}", date_time=(2026, 10, 15, 0, 0, 0))
            zi.create_system = 3
            zi.external_attr = (0o100755 if name.endswith((".sh", ".so")) else 0o100644) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failure: {bad}")
    (outdir / "SHA256SUMS.txt").write_text(f"{digest(path.read_bytes())}  {path.name}\n")
    print(f"Native FG test package: {path} sha256={digest(path.read_bytes())}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--version", default="2.1.2-native.1")
    args = parser.parse_args()
    package(args.binary.resolve(), args.outdir.resolve(), args.version)
