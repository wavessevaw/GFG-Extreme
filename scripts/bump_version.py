#!/usr/bin/env python3
"""Set the product version everywhere it is written.  Usage: scripts/bump_version.py 1.0.1"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sub(path: str, pattern: str, repl: str, count: int = 1) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
    if n == 0:
        sys.exit(f"{path}: pattern not found: {pattern}")
    file.write_text(new, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: bump_version.py X.Y.Z")
    v = sys.argv[1]
    sub("package.json", r'^(  "version": )"[^"]+"', rf'\g<1>"{v}"')
    sub("package-lock.json", r'^(  "version": )"[^"]+"', rf'\g<1>"{v}"')
    sub("package-lock.json", r'^(      "version": )"[^"]+"(,\n      "license")', rf'\g<1>"{v}"\2')
    sub("py_modules/gfg_plugin/governor_service.py", r'^VERSION = "[^"]+"', f'VERSION = "{v}"')
    sub("py_modules/gfg_plugin/governor_service.py", r"\(GFG Extreme [0-9.]+\)", f"(GFG Extreme {v})")
    sub("py_modules/gfg_plugin/plugin.py", r'"GFG Extreme [0-9.]+ started"', f'"GFG Extreme {v} started"')
    sub("py_modules/gfg_plugin/session_recorder.py", r'"GFG Extreme [0-9.]+ \(engine', f'"GFG Extreme {v} (engine')
    sub("py_modules/gfg_plugin/log_report.py", r'^CURRENT_VERSION = "[^"]+"', f'CURRENT_VERSION = "{v}"')
    print(f"version set to {v}")


if __name__ == "__main__":
    main()
