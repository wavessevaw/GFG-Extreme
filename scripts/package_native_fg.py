#!/usr/bin/env python3
"""Package a private FG3 GPU development artifact; never a release candidate.

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
EXTENSIONS = {".c", ".h", ".inc", ".comp", ".glsl", ".py", ".md", ".json", ".sh", ".txt", ".gd", ".tscn", ".godot"}


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
    if b"[gfg-native] GPU bridge active" not in raw:
        raise ValueError("GPU transport is missing; refusing CPU/pass-through artifact")
    if b"rgba_to_rgb" in raw or b"OWN TE8 CPU bridge active" in raw:
        raise ValueError("Legacy CPU pixel transport must not ship in FG3 GPU artifact")
    return raw


def source_files() -> dict[str, bytes]:
    selected = {}
    for directory in ("engine/gfg-native", "engine/gfg-temporal"):
        base = ROOT / directory
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if any(
                part in ("build", "__pycache__", ".git", "results")
                or part == "build-te"
                or part.startswith(("build-", "build_"))
                for part in path.relative_to(base).parts
            ):
                continue
            if path.suffix not in EXTENSIONS and path.name not in ("Makefile",):
                continue
            if path.stat().st_size > 1_000_000:
                raise ValueError(f"Unexpectedly large source file {path}")
            selected["SOURCE/" + path.relative_to(ROOT).as_posix()] = path.read_bytes()
    if not any(name.endswith("src/te_engine.c") for name in selected):
        raise ValueError("Corresponding Temporal Engine source missing")
    if not any(name.endswith("src/gpu_bridge.c") for name in selected):
        raise ValueError("Corresponding Vulkan transport source missing")
    return selected


def worktree_dirty(packaged: dict[str, bytes]) -> bool:
    """Ignore unrelated CI logs while rejecting source changes in the package."""
    diff = subprocess.run([
        "git", "diff", "--quiet", "HEAD", "--",
        "engine/gfg-native", "engine/gfg-temporal", "scripts/accept_report.py",
        "scripts/package_native_fg.py", "LICENSE.md",
    ], cwd=ROOT)
    if diff.returncode == 1:
        return True
    if diff.returncode != 0:
        raise subprocess.CalledProcessError(diff.returncode, diff.args)

    included_paths = {
        name.removeprefix("SOURCE/")
        for name in packaged
        if name.startswith("SOURCE/")
    }
    included_paths.update({
        "engine/gfg-native/VkLayer_gfg_native.json",
        "engine/gfg-native/package/install.sh",
        "engine/gfg-native/package/uninstall.sh",
        "engine/gfg-native/package/rollback.sh",
        "engine/gfg-native/package/gfg-native.sh",
        "engine/gfg-native/package/diagnose.sh",
        "engine/gfg-native/package/BUILD-ENVIRONMENT.txt",
        "engine/gfg-native/package/README.ru.md",
        "scripts/accept_report.py",
        "scripts/package_native_fg.py",
        "LICENSE.md",
    })
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).split(b"\0")
    return any(
        path.decode("utf-8", "surrogateescape") in included_paths
        for path in untracked if path
    )


def package(binary: Path, outdir: Path, version: str, build_environment: str | None = None) -> Path:
    if not re.fullmatch(r"0\.0\.0-fg3-internal\.[0-9]+", version):
        raise ValueError("Only 0.0.0-fg3-internal.N development artifacts are authorized before hardware acceptance")
    files = {
        "libVkLayer_gfg_native.so": native_elf(binary),
        "VkLayer_gfg_native.json": (ROOT / "engine/gfg-native/VkLayer_gfg_native.json").read_bytes(),
        "install.sh": (ROOT / "engine/gfg-native/package/install.sh").read_bytes(),
        "uninstall.sh": (ROOT / "engine/gfg-native/package/uninstall.sh").read_bytes(),
        "rollback.sh": (ROOT / "engine/gfg-native/package/rollback.sh").read_bytes(),
        "gfg-native.sh": (ROOT / "engine/gfg-native/package/gfg-native.sh").read_bytes(),
        "diagnose.sh": (ROOT / "engine/gfg-native/package/diagnose.sh").read_bytes(),
        "accept_report.py": (ROOT / "scripts/accept_report.py").read_bytes(),
        "BUILD-ENVIRONMENT.txt": (ROOT / "engine/gfg-native/package/BUILD-ENVIRONMENT.txt").read_bytes(),
        "README.ru.md": (ROOT / "engine/gfg-native/package/README.ru.md").read_bytes(),
        "LICENSE.md": (ROOT / "LICENSE.md").read_bytes(),
    }
    files.update(source_files())
    manifest = json.loads(files["VkLayer_gfg_native.json"])
    if manifest["layer"]["name"] != "VK_LAYER_GFG_native" or \
       manifest["layer"]["library_path"] != "./libVkLayer_gfg_native.so":
        raise ValueError("Native manifest identity mismatch")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = worktree_dirty(files)
    provenance = {
        "schema": 1,
        "version": version,
        "source_commit": None if dirty else commit,
        "source_base_commit": commit,
        "source_worktree_dirty": dirty,
        "source_identity": "SHA256SUMS.txt covers included corresponding source",
        "algorithm": "GFG LMC GPU model fit; shared analysis; t=1/3,2/3 (tiles diagnostic opt-in)",
        "transport": "application-device GPU image copies; no CPU pixel staging",
        "multiplier": 3,
        "architecture": "linux-x86_64",
        "runtime_requires": ["Vulkan 1.2", "64-bit Linux"],
        "runtime_forbidden": ["MAKO Renderer", "Lossless Scaling", "Lossless.dll"],
        "build_environment": build_environment or (
            "GitHub Actions ubuntu-22.04, gcc-12, Vulkan-Headers v1.4.365; see BUILD-ENVIRONMENT.txt"
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else "Local build; environment not attested. BUILD-ENVIRONMENT.txt describes the canonical CI rebuild."
        ),
        "stage": "internal development; NOT COMPLETED",
        "hardware_acceptance": False,
        "physical_display_verified": False,
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
    parser.add_argument("--version", default="0.0.0-fg3-internal.4")
    parser.add_argument("--build-environment", help="Actual build environment; otherwise inferred from GitHub Actions or marked unattested")
    args = parser.parse_args()
    package(args.binary.resolve(), args.outdir.resolve(), args.version, args.build_environment)
