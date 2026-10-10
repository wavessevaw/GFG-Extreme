#!/usr/bin/env python3
"""First reproducible Autopilot audit run. Standard-library only.

Produces a deterministic manifest, per-test JSONL events and a verbose test log.
All fixtures are synthetic: this is NEVER a Steam Deck hardware certification.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    "test_autopilot_*.py",
    "test_governor_flow.py",
    "test_governor_restore_barrier.py",
    "test_governor_runtime.py",
    "test_session_recorder.py",
)


def revision():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL, timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return os.getenv("GITHUB_SHA") or "unknown"


class AuditResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, *, events):
        super().__init__(stream, descriptions, verbosity)
        self.events = events
        self.active = {}

    def log(self, event, test, **extra):
        item = {
            "schema": 1, "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "event": event, "test": test.id(), "test_kind": "synthetic",
            **extra,
        }
        with self.events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")

    def startTest(self, test):
        self.active[test.id()] = time.monotonic()
        self.log("test-start", test)
        super().startTest(test)

    def stopTest(self, test):
        began = self.active.pop(test.id(), time.monotonic())
        self.log("test-end", test, duration_ms=round((time.monotonic()-began)*1000, 3))
        super().stopTest(test)

    def addSuccess(self, test):
        self.log("pass", test)
        super().addSuccess(test)

    def addSkip(self, test, reason):
        self.log("skip", test, reason=reason)
        super().addSkip(test, reason)

    def addFailure(self, test, err):
        self.log("fail", test, traceback=self._exc_info_to_string(err, test)[-12000:])
        super().addFailure(test, err)

    def addError(self, test, err):
        self.log("error", test, traceback=self._exc_info_to_string(err, test)[-12000:])
        super().addError(test, err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=ROOT / "artifacts" / "autopilot-first-run")
    args = parser.parse_args()
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    events = out / "test-events.jsonl"
    events.write_text("", encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT / "py_modules"))
    loader = unittest.TestLoader()
    suites = [loader.discover(str(ROOT / "tests"), pattern=pattern, top_level_dir=str(ROOT / "tests"))
              for pattern in PATTERNS]
    suite = unittest.TestSuite(suites)
    started = dt.datetime.now(dt.timezone.utc)
    with (out / "test-run.log").open("w", encoding="utf-8") as logfile:
        runner = unittest.TextTestRunner(
            stream=logfile, verbosity=2, failfast=False,
            resultclass=lambda stream, descriptions, verbosity:
                AuditResult(stream, descriptions, verbosity, events=events),
        )
        result = runner.run(suite)
    ended = dt.datetime.now(dt.timezone.utc)
    report = {
        "schema": 1, "run_type": "SIMULATED_CI_NO_STEAM_DECK",
        "hardware_verified": False,
        "started_utc": started.isoformat(), "ended_utc": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "repository": "wavessevaw/GFG-Extreme", "revision": revision(),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "suite_patterns": list(PATTERNS), "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "successful": result.wasSuccessful(),
        "limitations": [
            "No Steam Deck, Gamescope, Vulkan frame generation or real PPT actuator was exercised",
            "Synthetic fixtures cannot prove renderer ACK ordering on hardware",
            "A separate user-operated device run must capture SessionRecorder ZIP",
        ],
        "files": ["test-run.log", "test-events.jsonl", "summary.json"],
    }
    (out / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    (out / "README.txt").write_text(
        "GFG Extreme Autopilot first-run audit, synthetic CI only.\n"
        "summary.json = exact SHA/test counts and limitations.\n"
        "test-run.log = verbose unittest output and stack traces.\n"
        "test-events.jsonl = UTC event for every test start/result/end.\n"
        "For actual Steam Deck capture, use Settings > Diagnostics > Start/Stop recording.\n"
        "Bundle must contain autopilot-trace.jsonl, timeline.jsonl, diagnostics,\n"
        "governor-events.jsonl, activity.jsonl, power-sensors.json and self_test.json.\n",
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in ("revision", "tests_run", "failures", "errors", "skipped", "successful", "run_type")}, indent=2))
    print("Artifacts:", out)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
