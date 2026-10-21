"""Telemetry levels: what GFG Extreme keeps on the Deck (nothing is sent anywhere).

  minimal   decisions only: the activity journal (policy sends and confirmations, pilot points,
            TDP writes, migrations, errors) and session summaries
  standard  + one line per second while a game runs (fps, pace, point, TDP, draw, temperature),
            the last 6 h, for the report zip
  debug     + the engine's raw status once a second, the last 30 min

Files rotate by size; the report zip (Setup -> Save report) collects them.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .user_files import own

LIMITS = {"samples.jsonl": 8 * 1024 * 1024, "engine.jsonl": 6 * 1024 * 1024, "sessions.jsonl": 1024 * 1024}


class Telemetry:
    def __init__(self, folder: Path, owner: Optional[Tuple[int, int]] = None) -> None:
        self.folder = Path(folder)
        self.owner = owner
        self.level = "standard"
        self._lock = threading.Lock()

    def _append(self, name: str, payload: Dict[str, Any]) -> None:
        path = self.folder / name
        line = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")) + "\n"
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
            self._append("samples.jsonl", payload)

    def engine(self, status: Dict[str, Any]) -> None:
        if self.level == "debug" and status:
            self._append("engine.jsonl", status)

    def session(self, summary: Dict[str, Any]) -> None:
        self._append("sessions.jsonl", summary)

    def files(self):
        return sorted(p for p in self.folder.glob("*.jsonl*") if p.is_file())
