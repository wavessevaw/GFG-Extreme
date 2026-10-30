"""Telemetry levels: what GFG Extreme keeps on the Deck (nothing is sent anywhere).

  minimal   decisions only: the activity journal (policy sends and confirmations, pilot points,
            TDP writes, migrations, errors) and session summaries
  standard  + one line per second while a game runs (fps, real, pace, point, multiplier, TDP, draw,
            temperature, CPU/GPU load, GPU clock, fan, battery, CPU cap and GPU ceiling),
            the last 6 h, for the report zip
  debug     + the engine's raw status once a second, the last 30 min

Files rotate by size; the report zip (Setup -> Save report) collects them.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .user_files import own

# Per-second samples are written in batches (3.2.2): one file append every FLUSH_S instead of
# an open, write, stat every second while a game runs.
FLUSH_S = 30.0
LIMITS = {"samples.jsonl": 8 * 1024 * 1024, "engine.jsonl": 6 * 1024 * 1024, "sessions.jsonl": 1024 * 1024}


class Telemetry:
    def __init__(self, folder: Path, owner: Optional[Tuple[int, int]] = None) -> None:
        self.folder = Path(folder)
        self.owner = owner
        self.level = "standard"
        self._lock = threading.Lock()
        self._pending: Dict[str, list] = {}
        self._flushed_at = time.monotonic()

    def _queue(self, name: str, payload: Dict[str, Any]) -> None:
        line = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")) + "\n"
        with self._lock:
            self._pending.setdefault(name, []).append(line)
        if time.monotonic() - self._flushed_at >= FLUSH_S:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            pending, self._pending = self._pending, {}
            self._flushed_at = time.monotonic()
        for name, lines in pending.items():
            self._write(name, "".join(lines))

    def _append(self, name: str, payload: Dict[str, Any]) -> None:
        self.flush()
        self._write(name, json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")) + "\n")

    def _write(self, name: str, line: str) -> None:
        path = self.folder / name
        with self._lock:
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                new = not path.exists()
                with path.open("a", encoding="utf-8") as f:
                    f.write(line)
                if new:
                    own(path, self.owner)
                if path.stat().st_size > LIMITS.get(name, 4 * 1024 * 1024):
                    old = path.with_suffix(path.suffix + ".1")
                    path.replace(old)
                    own(old, self.owner)
            except OSError:
                pass

    def sample(self, payload: Dict[str, Any]) -> None:
        if self.level in ("standard", "debug"):
            self._queue("samples.jsonl", payload)

    def engine(self, status: Dict[str, Any]) -> None:
        if self.level == "debug" and status:
            self._queue("engine.jsonl", status)

    def session(self, summary: Dict[str, Any]) -> None:
        self._append("sessions.jsonl", summary)

    def files(self):
        self.flush()
        return sorted(p for p in self.folder.glob("*.jsonl*") if p.is_file())
