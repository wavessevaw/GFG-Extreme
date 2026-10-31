"""Verify the exact clean GSF source tree and recorded reference generator hashes.

Usage: python tools/verify_gsf_baseline.py /path/to/GSF_Kedavra
This validates provenance only; it does not execute the engine or compare images.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", type=Path)
    args = p.parse_args()
    manifest = json.loads((Path(__file__).resolve().parents[1] / "docs/baseline-3.2.2/gsf-scenes.json").read_text(encoding="utf-8"))
    try:
        sha = git(args.repo, "rev-parse", "HEAD").decode().strip()
        dirty = git(args.repo, "status", "--porcelain", "--untracked-files=no")
        if sha != manifest["gsf_commit"] or dirty:
            raise ValueError("checkout must be clean and at the pinned GSF commit")
        for path, expected in manifest["source_sha256"].items():
            actual = hashlib.sha256(git(args.repo, "show", f"{sha}:{path}")).hexdigest()
            if actual != expected:
                raise ValueError(f"hash mismatch: {path}")
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip() if exc.stderr else str(exc)
        p.exit(1, f"BLOCKED: git failed: {detail}\n")
    except (OSError, ValueError) as exc:
        p.exit(1, f"BLOCKED: {exc}\n")
    print(f"Source provenance verified: {sha}; image quality remains UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
