#!/usr/bin/env python3
"""Validate the actual Decky ZIP before publishing, including version and native payloads."""
import json
import hashlib
import io
import re
import sys
import zipfile
import tarfile
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
        if "GFG-Extreme/engine/gfg-fusion/source.json" in names:
            source = json.loads(read("engine/gfg-fusion/source.json"))
            identity = json.loads(read("bin/gfg-fusion/manifest.json"))
            sha = lambda data: hashlib.sha256(data).hexdigest()
            if source != identity["source"] or sha(read("engine/gfg-fusion/renderer.patch")) != source["patch_sha256"]:
                raise ValueError("Frame Fusion source provenance mismatch")
            if identity.get("default_enabled") is not True or identity.get("autopilot_only") is not True:
                raise ValueError("Stable Frame Fusion must default on and be scoped to Autopilot")
            if sha(read("bin/gfg-fusion/gfg-frame-fusion-tests")) != identity["proof_sha256"]:
                raise ValueError("Frame Fusion proof executable mismatch")
            bundle = package.get("bundled_renderer") or package["remote_binary"][0]
            payload = read("bin/" + bundle["name"])
            if sha(payload) != bundle["sha256hash"] or sha(payload) != identity["archive_sha256"]:
                raise ValueError("Frame Fusion archive checksum mismatch")
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz") as native:
                for path, expected in identity["native_libraries"].items():
                    member = native.getmember("./" + path) if "./" + path in native.getnames() else native.getmember(path)
                    if sha(native.extractfile(member).read()) != expected:
                        raise ValueError("Frame Fusion native payload mismatch: " + path)

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

        release = tuple(map(int, version.split("-")[0].split(".")))
        if release >= (1, 6, 7) and not read("py_modules/gfg_plugin/governor_flow.py"):
            raise ValueError("empty bundled module: governor_flow.py")
        # GFG Theme (CSS Loader) was retired in 2.1.2 and must not ship again.
        if release >= (2, 1, 2) and any(
                name.startswith(ROOT + "themes/css-loader/")
                or name == ROOT + "py_modules/gfg_plugin/theme_installer.py" for name in names):
            raise ValueError("retired GFG Theme shipped in release")
        if any("/gfg-open/" in name for name in names):
            raise ValueError("retired generator shipped in release")
        if not read("dist/index.js") or not read("main.py"):
            raise ValueError("missing frontend/backend entrypoint")
    print(f"Decky archive verified: version {version}, CRC, paths, entrypoints and native payloads")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: check_release_archive.py ZIP VERSION")
    check(sys.argv[1], sys.argv[2])
