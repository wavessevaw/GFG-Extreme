"""Verify the archived 3.2.2 GSF software-Vulkan SDR reference capture.

This checks the preserved bytes, not image quality or Steam Deck behavior.
Usage: python tools/verify_gsf_reference.py path/to/gsf-3.2.2-sdr-reference.zip
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ARCHIVE_SHA256 = "af44b29599da4e8e54e1d88aa5361e4f00d3cd7068d58ad1f0119d31d11bca82"
MANIFEST_SHA256 = "7f1ff59c180f14098200496bf86e6668baeaeedbaeecd23084d1c183d0063b3d"
GSF_SHA = "62621c4f9b60fd3cb95edafb62a1a44a1bb2c21e"
GAMESCOPE_SHA = "aa289ea5977d8b21b92b0f246f0e8f0c225d180f"
SCENES = ("pan", "fast_pan", "objects_hud", "occlusion", "thin_lines", "scene_cut")
PHASES = {"x3": ("333", "667"), "x3_75": ("267", "733")}
HEADER = b"P6\n1280 800\n255\n"
FRAME_SIZE = len(HEADER) + 1280 * 800 * 3


def verify_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("reference manifest must be an object")
    if (manifest.get("gsf_commit") != GSF_SHA or manifest.get("gamescope_commit") != GAMESCOPE_SHA
            or manifest.get("size") != [1280, 800] or manifest.get("format") != "PPM P6 RGB8"
            or manifest.get("scenes") != list(SCENES)
            or manifest.get("phases") != {key: list(value) for key, value in PHASES.items()}):
        raise ValueError("reference metadata differs from the recorded capture")
    expected = {f"frames/{mode}/{scene}_t{phase}_{kind}.ppm"
                for mode, phases in PHASES.items() for scene in SCENES
                for phase in phases for kind in ("gen", "truth")}
    frames = manifest.get("frames")
    if not isinstance(frames, dict) or set(frames) != expected:
        raise ValueError("reference frame list is incomplete or unexpected")
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
           for value in frames.values()):
        raise ValueError("invalid frame SHA-256")
    return frames


def verify_archive(path, manifest_path):
    with Path(path).open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != ARCHIVE_SHA256:
            raise ValueError("archive SHA-256 mismatch")
    pinned = Path(manifest_path).read_bytes()
    if hashlib.sha256(pinned).hexdigest() != MANIFEST_SHA256:
        raise ValueError("pinned manifest SHA-256 mismatch")
    frames = verify_manifest(json.loads(pinned))
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive entry")
        if archive.read("manifest.json") != pinned:
            raise ValueError("archived manifest differs from the pinned manifest")
        for name, expected in frames.items():
            with archive.open(name) as source:
                header = source.read(len(HEADER))
                if header != HEADER:
                    raise ValueError(f"unexpected PPM header: {name}")
                digest = hashlib.sha256(header)
                size = len(header)
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
            if size != FRAME_SIZE or digest.hexdigest() != expected:
                raise ValueError(f"frame size or SHA-256 mismatch: {name}")
    return {"integrity": "PASS", "frames": len(frames), "image_quality": "UNVERIFIED",
            "evidence_class": "software Vulkan, SDR; not a Steam Deck test"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--manifest", default=str(Path(__file__).resolve().parents[1] /
                                                   "docs/baseline-3.2.2/gsf-sdr-reference-manifest.json"))
    args = parser.parse_args()
    try:
        result = verify_archive(args.archive, args.manifest)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"reference verification failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
