#!/usr/bin/env python3
"""Replace only native x86_64 payloads in a verified release staging tree."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def elf(data):
    if len(data) < 20 or data[:6] != b"\x7fELF\x02\x01" or int.from_bytes(data[18:20], "little") != 62:
        raise ValueError("Frame Fusion requires native x86_64 ELF payloads")


def package(plugin: Path, build: Path):
    package_file = plugin / "package.json"
    metadata = json.loads(package_file.read_text(encoding="utf-8"))
    source = json.loads((plugin / "engine/gfg-fusion/source.json").read_text())
    patch = (plugin / "engine/gfg-fusion/renderer.patch").read_bytes()
    if digest(patch) != source["patch_sha256"]:
        raise ValueError("Frame Fusion source identity mismatch")
    bundle = metadata["remote_binary"][0]
    archive = plugin / "bin" / bundle["name"]
    original = archive.read_bytes()
    if digest(original) != bundle["sha256hash"]:
        raise ValueError("Baseline renderer archive checksum mismatch")
    replacements = {
        "lib/libmako-render.so": (build / "mako-render/libmako-render.so").read_bytes(),
        "lib/libmako-render-scaling.so": (build / "mako-render/libmako-render-scaling.so").read_bytes(),
        "bin/mako-cli": (build / "mako-cli/mako-cli").read_bytes(),
    }
    proof = (build / "mako-render/gfg-frame-fusion-tests").read_bytes()
    for data in (*replacements.values(), proof):
        elf(data)
    output = io.BytesIO()
    replaced = set()
    with tarfile.open(fileobj=io.BytesIO(original), mode="r:xz") as incoming, \
            tarfile.open(fileobj=output, mode="w:xz") as outgoing:
        for member in incoming:
            name = member.name.removeprefix("./")
            if name.startswith("/") or ".." in Path(name).parts or member.issym() or member.islnk():
                raise ValueError("Unexpected baseline renderer archive member")
            if name in replacements:
                data = replacements[name]
                member.size = len(data); member.mode = 0o755
                outgoing.addfile(member, io.BytesIO(data)); replaced.add(name)
            else:
                outgoing.addfile(member, incoming.extractfile(member) if member.isfile() else None)
        scope_metadata = json.dumps(source,sort_keys=True).encode('utf-8')
        member = tarfile.TarInfo('gfg-fusion-source.json')
        member.size=len(scope_metadata);member.mode=0o644;member.mtime=0
        outgoing.addfile(member,io.BytesIO(scope_metadata))
    if replaced != set(replacements):
        raise ValueError("Baseline archive is missing native renderer members")
    data = output.getvalue()
    temporary = archive.with_suffix(archive.suffix + ".fusion.tmp")
    temporary.write_bytes(data); temporary.replace(archive)
    bundle["version"] = "4.0.0-gfg.fusion.3"
    bundle["sha256hash"] = digest(data)
    bundle["frame_fusion"] = {"source": source, "base_archive_sha256": digest(original)}
    # The generated archive is a local fork, not the upstream asset at that URL.
    bundle["upstream_url"] = bundle.pop("url")
    metadata["bundled_renderer"] = bundle
    metadata.pop("remote_binary")
    metadata.pop("remote_binary_bundling", None)
    package_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    checksums = plugin / "bin/SHA256SUMS.txt"
    lines = checksums.read_text().splitlines()
    lines = [(digest(data) + "  " + bundle["name"]) if line.split()[-1] == bundle["name"] else line for line in lines]
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tools = plugin / "bin/gfg-fusion"
    tools.mkdir(parents=True, exist_ok=True)
    executable = tools / "gfg-frame-fusion-tests"
    executable.write_bytes(proof); executable.chmod(0o755)
    identity = {"schema": 1, "source": source, "native_libraries": {
        name: digest(content) for name, content in replacements.items()},
        "proof_sha256": digest(proof), "archive_sha256": digest(data),
        "unsupported": ["32-bit", "Flatpak", "HDR", "LS1"], "default_enabled": True, "autopilot_only": True}
    (tools / "manifest.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    print("Packaged Frame Fusion native fork:", digest(data))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--plugin", type=Path, required=True)
    p.add_argument("--build", type=Path, required=True)
    args = p.parse_args()
    package(args.plugin.resolve(), args.build.resolve())
