#!/usr/bin/env python3
"""Compose a FULL 2.1.6 Decky archive plus a separately opt-in native GSF lab.
Never replaces the published stable release and never silently activates Vulkan.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

BASE = "GFG-Extreme/"
NATIVE = "GFG-Native-FG/"
VERSION = "2.1.6-gsf.lab1"
NATIVE_VERSION = "0.0.0-fg3-internal.10"
EXPECTED_SOURCE = "db04b3dfb5dbe3e2dac66761de7e397b1315b0fc"
ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def safe(name, prefix):
    return (name.startswith(prefix) and not name.endswith("/")
            and ".." not in Path(name).parts and "\\" not in name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stable", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    ensure(args.stable.is_file() and args.native.is_file(), "source ZIP missing")
    original = {}
    descriptions = {}
    stable_modes = {}
    with zipfile.ZipFile(args.stable) as stable:
        ensure(stable.testzip() is None, "stable CRC failure")
        for member in stable.infolist():
            if member.is_dir():
                continue
            ensure(safe(member.filename, BASE), "unsafe stable path")
            ensure(member.filename not in original, "duplicate stable ZIP member")
            original[member.filename] = stable.read(member)
            stable_modes[member.filename] = copy.copy(member)
    ensure(json.loads(original[BASE + "package.json"])["version"] == "2.1.6",
           "not the required official stable 2.1.6")
    flatpaks = [n for n in original if n.startswith(BASE + "bin/") and n.endswith(".flatpak")]
    ensure(len(flatpaks) == 3, "missing any of the three official Flatpak bundles")
    required = [
        "main.py", "dist/index.js", "bin/gfg-diagnostics",
        "bin/gfg-frame-os/libVkLayer_gfg_pacer.so",
        "bin/gfg-frame-os/libVkLayer_gfg_hud.so",
        "bin/gfg-fusion/manifest.json",
        "py_modules/gfg_plugin/governor_service.py",
        "py_modules/gfg_plugin/installation.py",
        "py_modules/gfg_plugin/frame_os/runner.py",
    ]
    for name in required:
        ensure(BASE + name in original, "missing stable component: " + name)
    ensure(any(n.startswith(BASE + "bin/gfg-shell/") for n in original),
           "missing compiled GFG Shell")
    ensure(len(args.stable.read_bytes()) > 75_000_000,
           "stable archive unexpectedly small; fail closed")
    native_files = {}
    native_modes = {}
    with zipfile.ZipFile(args.native) as native:
        ensure(native.testzip() is None, "native CRC failure")
        for member in native.infolist():
            if member.is_dir():
                continue
            ensure(safe(member.filename, NATIVE), "unsafe native path")
            rel = member.filename[len(NATIVE):]
            ensure(rel not in native_files, "duplicate native component")
            native_files[rel] = native.read(member)
            native_modes[rel] = (member.external_attr >> 16) & 0o777
    manifest = json.loads(native_files["MANIFEST.json"])
    ensure(manifest.get("version") == NATIVE_VERSION, "wrong GSF version")
    ensure(manifest.get("source_commit") == EXPECTED_SOURCE and
           manifest.get("source_worktree_dirty") is False,
           "GSF artifact missing verified source identity")
    ensure(manifest.get("hardware_acceptance") is False and
           manifest.get("physical_display_verified") is False,
           "do not ship false hardware claims")
    ensure(sha(native_files["libVkLayer_gfg_native.so"]) == manifest["elf_sha256"],
           "GSF ELF hash mismatch")
    for line in native_files["SHA256SUMS.txt"].decode().splitlines():
        h, name = line.split("  ", 1)
        ensure(name in native_files and sha(native_files[name]) == h,
               "native component hash mismatch: " + name)
    ensure(native_files["libVkLayer_gfg_native.so"][:6] == b"\x7fELF\x02\x01",
           "native library is not 64-bit ELF")
    ensure(int.from_bytes(native_files["libVkLayer_gfg_native.so"][18:20], "little") == 62,
           "native library not x86-64")
    plugin = dict(original)
    for rel, data in native_files.items():
        full = BASE + "bin/gfg-native/" + rel
        ensure(full not in plugin, "native collision with stable payload: " + full)
        plugin[full] = data
    additions = {
        BASE + "bin/gfg-native/gfg-gsf-lab.sh":
            (ROOT / "scripts" / "gsf_lab_safe_launcher.sh").read_bytes(),
        BASE + "GSF-LAB-README.ru.md":
            (ROOT / "docs" / "GSF_LAB_216_README.ru.md").read_bytes(),
    }
    for path, data in additions.items():
        ensure(path not in plugin, "lab helper collides with stable payload")
        plugin[path] = data
    pkg = json.loads(plugin[BASE + "package.json"])
    pkg["base_version"] = "2.1.6"
    pkg["version"] = VERSION
    pkg["gfgPrerelease"] = True
    pkg["gsfLab"] = {
        "enabled_by_default": False,
        "automatic_layer_install": False,
        "requires_manual_opt_in": True,
        "component_version": NATIVE_VERSION,
        "component_source_commit": EXPECTED_SOURCE,
        "hardware_accepted": False,
        "plugin_ui_integrated": False,
    }
    plugin[BASE + "package.json"] = (json.dumps(pkg, indent=2) + "\n").encode()
    lock = json.loads(plugin[BASE + "package-lock.json"])
    lock["version"] = VERSION
    lock["packages"][""]["version"] = VERSION
    plugin[BASE + "package-lock.json"] = (json.dumps(lock, indent=2) + "\n").encode()
    for name, variable in [
        ("governor_service.py", "VERSION"),
        ("log_report.py", "CURRENT_VERSION"),
    ]:
        path = BASE + "py_modules/gfg_plugin/" + name
        old = plugin[path].decode("utf-8")
        new, count = re.subn(r'^' + variable + r' = "2\.1\.6"(?=\s|$)',
                             variable + ' = "' + VERSION + '"',
                             old, count=1, flags=re.M)
        ensure(count == 1, "cannot update " + name + " version")
        plugin[path] = new.encode()
    for name in ("plugin.py", "session_recorder.py"):
        path = BASE + "py_modules/gfg_plugin/" + name
        old = plugin[path]
        ensure(b"GFG Extreme 2.1.6" in old, "version string missing in " + name)
        plugin[path] = old.replace(b"GFG Extreme 2.1.6",
                                   ("GFG Extreme " + VERSION).encode())
    path = BASE + "GSF-LAB-MANIFEST.json"
    plugin[path] = (json.dumps({
        "schema": 1, "stable_source": "GFG Extreme v2.1.6",
        "stable_source_zip_sha256": sha(args.stable.read_bytes()),
        "gsf_source": EXPECTED_SOURCE,
        "gsf_zip_sha256": sha(args.native.read_bytes()),
        "gsf_elf_sha256": manifest["elf_sha256"],
        "hardware_status": "NOT TESTED",
        "auto_activation": False,
        "game_launch_status": "USER REPORTED CRASH ON PREVIOUS GSF BUILD; THIS LAB UNTESTED",
        "stable_members_unchanged_except_version_files":
            len(original) - 6,
    }, indent=2) + "\n").encode()
    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / ("GFG-Extreme-" + VERSION + ".zip")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as target:
        for name, data in sorted(plugin.items()):
            if name in stable_modes:
                info = stable_modes[name]
                target.writestr(info, data)
            else:
                info = zipfile.ZipInfo(name, (2026, 10, 17, 0, 0, 0))
                info.create_system = 3
                rel = name.removeprefix(BASE + "bin/gfg-native/")
                mode = native_modes.get(rel, 0o755 if name.endswith(".sh") else 0o644)
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(destination) as verified:
        ensure(verified.testzip() is None, "final ZIP CRC failure")
        actual = set(verified.namelist())
        ensure(set(original) <= actual, "lost stable files")
        for name, content in original.items():
            if name not in {
                BASE + "package.json", BASE + "package-lock.json",
                BASE + "py_modules/gfg_plugin/governor_service.py",
                BASE + "py_modules/gfg_plugin/log_report.py",
                BASE + "py_modules/gfg_plugin/plugin.py",
                BASE + "py_modules/gfg_plugin/session_recorder.py"
            }:
                ensure(verified.read(name) == content,
                       "stable file unexpectedly modified: " + name)
        for rel, data in native_files.items():
            ensure(verified.read(BASE + "bin/gfg-native/" + rel) == data,
                   "native component mutated after packaging: " + rel)
    ensure(destination.stat().st_size > 75_000_000,
           "output has lost full stable payload")
    checksum = sha(destination.read_bytes())
    (args.out / "SHA256SUMS.txt").write_text(checksum + "  " + destination.name + "\n")
    print(f"GSF LAB PACKAGE: {destination} ({destination.stat().st_size:,} bytes)")
    print("SHA256: " + checksum)
    print("Full stable entries retained: " + str(len(original)))
    print("Optional native entries added: " + str(len(native_files)))
    print("No GSF layer automatically enabled.")


if __name__ == "__main__":
    main()
