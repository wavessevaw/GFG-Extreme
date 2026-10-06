#!/usr/bin/env python3
"""Print the verdict for a GFG Extreme log zip (the file Record log writes to the Desktop)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.log_report import summarize_zip  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: gfg_log_report.py GFG-Extreme-log-<date>.zip")
print(summarize_zip(sys.argv[1]), end="")
