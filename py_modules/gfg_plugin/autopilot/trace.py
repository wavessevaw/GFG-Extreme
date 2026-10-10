"""Bounded, best-effort Autopilot decision journal.

One JSON object per line; never causes a control-loop failure.
The normal SessionRecorder exports only the bytes written during its recording.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
KEEP_BYTES = 2 * 1024 * 1024


def _safe(value, depth=0):
    if depth > 4:
        return None
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value[:256]
    if isinstance(value, (list, tuple)):
        return [_safe(item, depth + 1) for item in value[:40]]
    if isinstance(value, dict):
        return {str(k)[:64]: _safe(v, depth + 1)
                for k, v in list(value.items())[:60]}
    return type(value).__name__


class AutopilotTrace:
    def __init__(self, path, *, clock=time.time, monotonic=time.monotonic):
        self.path = Path(path)
        self.clock = clock
        self.monotonic = monotonic
        self._lock = threading.Lock()
        self.failures = 0

    def write(self, event, **fields):
        payload = {
            "schema": 1, "ts": round(self.clock(), 3),
            "mono": round(self.monotonic(), 6), "event": str(event)[:64],
        }
        payload.update({str(key): _safe(value) for key, value in fields.items()})
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as out:
                    out.write(line)
                if self.path.stat().st_size > MAX_BYTES:
                    with self.path.open("rb") as source:
                        source.seek(-KEEP_BYTES, os.SEEK_END)
                        data = source.read()
                    # The first retained line is normally partial.
                    data = data.split(b"\n", 1)[-1]
                    temp = self.path.with_name(self.path.name + ".tmp")
                    try:
                        with temp.open("wb") as out:
                            out.write(data)
                        os.replace(temp, self.path)
                    finally:
                        temp.unlink(missing_ok=True)
            except OSError:
                self.failures += 1
