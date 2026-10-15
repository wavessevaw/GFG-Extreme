#!/usr/bin/env python3
"""Read-only device inventory and optional local licensed MAKO reference run.

No installer, networking, game injection, power changes or proprietary payloads.
Python 3 standard library only. See research/DECK_CONNECTION.md.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import zipfile


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def redact(text, private=()):
    for value in sorted((str(x) for x in private if x), key=len, reverse=True):
        text = text.replace(value, "<private-path>")
    return text.replace(str(Path.home()), "~")


def run_command(argv, timeout=30, private=(), env_overrides=None):
    started = time.monotonic()
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, errors="replace", start_new_session=True,
                                   env={**os.environ, **(env_overrides or {})})
    except OSError as exc:
        return {"status": "UNAVAILABLE", "error": redact(str(exc), private)}
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        status = "COMPLETED" if process.returncode == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        status = "TIMEOUT"
    return {"status": status, "returncode": process.returncode,
            "wall_seconds": time.monotonic() - started,
            "stdout": redact(stdout, private), "stderr": redact(stderr, private)}


def device_inventory(sys_root=Path("/sys")):
    inventory = {"model": read_text(sys_root / "class/dmi/id/product_name"),
                 "board": read_text(sys_root / "class/dmi/id/board_name"), "gpus": [], "power": []}
    for card in sorted((sys_root / "class/drm").glob("card[0-9]*")):
        if not re.fullmatch(r"card\d+", card.name):
            continue
        device = card / "device"
        fields = ("vendor", "device", "gpu_busy_percent", "mem_info_vram_total",
                  "mem_info_vram_used", "power_dpm_force_performance_level", "pp_dpm_sclk")
        item = {field: read_text(device / field) for field in fields}
        item["card"] = card.name
        item["sensors"] = []
        for hwmon in sorted((device / "hwmon").glob("hwmon*")):
            item["sensors"].append({field: read_text(hwmon / field) for field in
                                    ("name", "temp1_input", "power1_average", "power1_cap")})
        inventory["gpus"].append(item)
    for power in sorted((sys_root / "class/power_supply").glob("*")):
        inventory["power"].append({field: read_text(power / field) for field in
                                   ("type", "online", "status", "capacity", "power_now")})
    return inventory


def quality_plan(multiplier):
    times = ",".join(format(i / multiplier, ".9f") for i in range(1, multiplier))
    # Upstream requires >=12 source steps. Ten history steps and two pairs
    # keep the first diagnostic packet small. This is NOT a performance run.
    return ";".join(["history"] * 10 + [times] * 2)


def pack(root, output):
    """Only known report/image extensions; never include a model or symlink."""
    allowed = {".json", ".log", ".tsv", ".ppm", ".txt"}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() not in allowed:
                continue
            archive.write(path, path.relative_to(root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new ZIP; never overwrites")
    parser.add_argument("--vulkan", action="store_true", help="also run vulkaninfo --summary")
    parser.add_argument("--mako-cli", type=Path, help="trusted existing MAKO CLI executable")
    parser.add_argument("--dll", type=Path, help="local lawful Lossless.dll; hash/size only by default")
    parser.add_argument("--oracle", action="store_true", help="run licensed MAKO reference locally")
    parser.add_argument("--fp16", action="store_true", help="request FP16; default is explicit FP32")
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--flow", type=float, default=1.0)
    parser.add_argument("--multiplier", type=int, choices=(2, 3, 5), default=3)
    parser.add_argument("--scene", choices=("camera-pan", "motion-boundary", "traffic", "crowd", "hud-disocclusion"), default="camera-pan")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("output already exists; choose another ZIP name")
    if not 0.25 <= args.flow <= 1.0:
        parser.error("flow must be in [0.25, 1]")
    if args.oracle and (args.dll is None or args.mako_cli is None):
        parser.error("--oracle requires --dll and --mako-cli")
    for path in (args.dll, args.mako_cli):
        if path is not None and not path.is_file():
            parser.error("specified local input is not a file")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    private = [str(p.resolve()) for p in (args.dll, args.mako_cli) if p]
    with tempfile.TemporaryDirectory(prefix="gfg-native-probe-") as tmp:
        root = Path(tmp)
        report = {"schema": 1, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "probe_sha256": digest(__file__), "purpose": "inventory-and-reference-smoke",
                  "evidence": {"original_windows_lsfg": "NOT TESTED", "physical_presentation": "NOT TESTED",
                               "deck_performance_comparison": "NOT TESTED"},
                  "os_release": read_text("/etc/os-release"), "hardware": device_inventory(),
                  "commands": {"kernel": run_command(["uname", "-srm"]),
                               "libc": run_command(["getconf", "GNU_LIBC_VERSION"])}}
        if args.vulkan:
            report["commands"]["vulkan"] = run_command(["vulkaninfo", "--summary"])
        for label, path in (("model", args.dll), ("mako_cli", args.mako_cli)):
            if path:
                report[label] = {"sha256": digest(path), "bytes": path.stat().st_size}
        if args.oracle:
            cli, dll = str(args.mako_cli.resolve()), str(args.dll.resolve())
            flags = [] if args.fp16 else ["--no-fp16"]
            # A GFG-patched CLI must not silently use TE for the LSFG reference.
            oracle_env = {"GFG_TEMPORAL_ENGINE": "off"}
            report["commands"]["inspect"] = run_command(
                [cli, "inspect-dll", "--dll", dll, "--lsfg", *flags], 120, private, oracle_env)
            if report["commands"]["inspect"]["status"] == "COMPLETED":
                plan = quality_plan(args.multiplier)
                report["reference_config"] = {"backend": "MAKO+LSFG", "width": 1280, "height": 800,
                    "scene": args.scene, "sequence_plan": plan, "flow": args.flow,
                    "requested_precision": "fp16" if args.fp16 else "fp32", "performance": args.performance,
                    "timestamps_are_normalized": True, "real_time_fps": None,
                    "environment_overrides": oracle_env}
                report["commands"]["reference"] = run_command([
                    cli, "quality-regression", "--dll", dll, *flags,
                    "--scene", args.scene, "--width", "1280", "--height", "800",
                    "--flow", str(args.flow), "--sequence-plan", plan,
                    "--output", str(root / "reference"),
                    *(["--performance-mode"] if args.performance else [])], 240, [*private, tmp], oracle_env)
                # GPU completion/readback only. Never label the images presented.
                report["evidence"]["reference_attempt"] = report["commands"]["reference"]["status"]
            else:
                report["evidence"]["reference_attempt"] = "NOT TESTED"
        report["hardware_after"] = device_inventory()
        manifest = {str(p.relative_to(root)): {"sha256": digest(p), "bytes": p.stat().st_size}
                    for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}
        (root / "artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        pack(root, args.out)
    print(f"Report: {args.out}\nSHA-256: {digest(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
