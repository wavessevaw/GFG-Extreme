"""Remember what worked for a game, so the next session starts there instead of searching.

The Governor's search (settle -> lower watts -> upgrade quality) is the slow part of every
session.  After a point has held for a while, its operating point and TDP are stored under a
context key (profile, display target, mode).  A later session warm-starts from it; the usual
guard still protects the game if the remembered state no longer holds, so a stale entry costs
one short dip, never a stuck setting.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

MAX_ENTRIES = 200
MAX_AGE_S = 30 * 24 * 3600.0
MIN_RECORD_INTERVAL_S = 60.0
MAX_TDP_W = 30.0


def context_key(profile: str, target: int, mode: str, app_id: str = "") -> str:
    """Per game when the Steam AppID is known (several games may share one profile), else per profile."""
    app = str(app_id or "").strip()
    who = f"app:{app}" if app.isdigit() and app != "0" else str(profile).strip()
    return f"{who}|{int(target)}|{str(mode or 'budget')}"


class GameModelStore:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.clock = clock
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._last_write: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        entries = raw.get("entries") if isinstance(raw, dict) else None
        if isinstance(entries, dict):
            self._entries = {k: v for k, v in entries.items() if self._valid(v)}

    @staticmethod
    def _valid(entry: Any) -> bool:
        if not isinstance(entry, dict) or not isinstance(entry.get("point"), str):
            return False
        tdp = entry.get("tdp_w")
        if tdp is not None and not (isinstance(tdp, (int, float)) and 0 < float(tdp) <= MAX_TDP_W):
            return False
        return isinstance(entry.get("updated"), (int, float)) and isinstance(entry.get("confirmations", 0), int)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._entries.get(key)
        if entry is None or self.clock() - float(entry["updated"]) > MAX_AGE_S:
            return None
        if int(entry.get("confirmations", 0)) < 1 or entry.get("point") is None:
            return None  # only failures are known: nothing to warm-start from
        return dict(entry)

    def record(self, key: str, point: str, tdp_w: Optional[float]) -> bool:
        """Remember a point that has held.  Rate-limited; returns True if the file was written."""
        now = self.clock()
        if now - self._last_write.get(key, -1e9) < MIN_RECORD_INTERVAL_S:
            return False
        tdp = round(float(tdp_w), 1) if tdp_w is not None else None
        if tdp is not None and not 0 < tdp <= MAX_TDP_W:
            return False
        previous = self._entries.get(key)
        same = previous is not None and previous["point"] == point and previous.get("tdp_w") == tdp
        confirmations = (int(previous.get("confirmations", 0)) + 1) if same else 1
        entry = {"point": point, "tdp_w": tdp, "updated": now, "confirmations": min(confirmations, 1000)}
        if previous is not None and isinstance(previous.get("failed"), dict):
            entry["failed"] = previous["failed"]
        self._entries[key] = entry
        self._last_write[key] = now
        if len(self._entries) > MAX_ENTRIES:
            oldest = sorted(self._entries, key=lambda k: self._entries[k]["updated"])[: len(self._entries) - MAX_ENTRIES]
            for stale in oldest:
                del self._entries[stale]
        return self._save()

    # Session-scale: a point that failed in one scene can hold in a lighter one later, so a failure
    # only bridges controller restarts (mode switches, plugin reloads) within the same play session.
    FAILURE_TTL_S = 10 * 60.0  # == BudgetController.REJECT_TTL_S

    def failures(self, key: str) -> Dict[str, Tuple[float, float]]:
        """Points that did not hold for this game: key -> (highest TDP it failed at, age in seconds).

        The age is returned (not just the TDP) so a reload keeps the *remaining* TTL instead of
        restarting it; expired entries are not returned.
        """
        entry = self._entries.get(key) or {}
        now = self.clock()
        raw = entry.get("failed") if isinstance(entry.get("failed"), dict) else {}
        out: Dict[str, Tuple[float, float]] = {}
        for k, v in raw.items():
            if isinstance(v, list) and len(v) == 2:
                age = max(0.0, now - float(v[1]))
                if age < self.FAILURE_TTL_S:
                    out[k] = (float(v[0]), age)
        return out

    def record_failure(self, key: str, point: str, tdp_w: Optional[float]) -> bool:
        """Remember 'point did not hold at tdp_w' (keeps the highest TDP it failed at)."""
        if tdp_w is None or not 0 < float(tdp_w) <= MAX_TDP_W:
            return False
        entry = self._entries.setdefault(key, {"point": point, "tdp_w": None, "updated": self.clock(),
                                               "confirmations": 0})
        failed = entry.setdefault("failed", {})
        old = failed.get(point)
        worst = max(float(tdp_w), float(old[0])) if isinstance(old, list) and len(old) == 2 else float(tdp_w)
        failed[point] = [round(worst, 1), self.clock()]
        if len(failed) > 32:
            for stale in sorted(failed, key=lambda k: failed[k][1])[: len(failed) - 32]:
                del failed[stale]
        return self._save()

    def forget(self, key: str) -> None:
        if self._entries.pop(key, None) is not None:
            self._save()

    def _save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "entries": self._entries}, handle, sort_keys=True)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False
