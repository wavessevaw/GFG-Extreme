#!/usr/bin/env python3
"""Validate the actual Decky ZIP before publishing, including version and native payloads."""
import json
import re
import sys
import zipfile
from pathlib import PurePosixPath

ROOT = "GFG-Extreme/"


def check(path, version):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP entries")
        for name in names:
            parts = PurePosixPath(name).parts
            if not name.startswith(ROOT) or ".." in parts or "\\" in name:
                raise ValueError(f"unsafe or unexpected ZIP path: {name}")
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failed: {bad}")

        def read(name):
            return archive.read(ROOT + name)

        package = json.loads(read("package.json"))
        lock = json.loads(read("package-lock.json"))
        versions = [package["version"], lock["version"], lock["packages"][""]["version"]]
        for file, constant in (
            ("py_modules/gfg_plugin/governor_service.py", "VERSION"),
            ("py_modules/gfg_plugin/log_report.py", "CURRENT_VERSION"),
        ):
            found = re.search(r'^' + constant + r' = "([^"]+)"', read(file).decode(), re.M)
            if found is None:
                raise ValueError(f"version missing: {file}")
            versions.append(found.group(1))
        if versions != [version] * len(versions):
            raise ValueError(f"version mismatch: {versions}, expected {version}")

        for layer in ("pacer", "hud"):
            base = "bin/gfg-frame-os/"
            library = f"libVkLayer_gfg_{layer}.so"
            data = read(base + library)
            if (data[:6] != b"\x7fELF\x02\x01" or len(data) < 20
                    or int.from_bytes(data[18:20], "little") != 62):
                raise ValueError(f"not a 64-bit little-endian x86 ELF: {library}")
            manifest = json.loads(read(base + f"VkLayer_gfg_{layer}.json"))
            if PurePosixPath(manifest["layer"]["library_path"]).name != library:
                raise ValueError(f"wrong library in {layer} manifest")

        if any("/gfg-open/" in name for name in names):
            raise ValueError("retired generator shipped in release")
        if not read("dist/index.js") or not read("main.py"):
            raise ValueError("missing frontend/backend entrypoint")
    print(f"Decky archive verified: version {version}, CRC, paths, entrypoints and native payloads")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: check_release_archive.py ZIP VERSION")
    check(sys.argv[1], sys.argv[2])
