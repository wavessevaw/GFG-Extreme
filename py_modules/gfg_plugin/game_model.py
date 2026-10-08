"""Remember what worked for a game, so the next session starts there instead of searching.

The Governor's search (settle -> lower watts -> upgrade quality) is the slow part of every
session.  After a point has held for a while, its operating point and TDP are stored under a
context key (profile, display target, mode).  A later session warm-starts from it; the usual
guard still protects the game if the remembered state no longer holds, so a stale entry costs
one short dip, never a stuck setting.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

MAX_ENTRIES = 200
MAX_AGE_S = 30 * 24 * 3600.0
MIN_RECORD_INTERVAL_S = 60.0
MAX_TDP_W = 30.0


def game_prefix(profile: str, app_id: str = "") -> str:
    """Per game when the Steam AppID is known (several games may share one profile), else per profile."""
    app = str(app_id or "").strip()
    return f"app:{app}" if app.isdigit() and app != "0" else str(profile).strip()


def context_key(profile: str, target: int, mode: str, app_id: str = "") -> str:
    return f"{game_prefix(profile, app_id)}|{int(target)}|{str(mode or 'budget')}"


def floor_key(profile: str, target: int, app_id: str = "") -> str:
    """Lower-power failures are physics of the game at a point, not of a mode: Battery and Balanced
    share them (review 1.1.x: a mode switch repeated a just-failed lower-power probe)."""
    return f"{game_prefix(profile, app_id)}|{int(target)}"


class GameModelStore:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.clock = clock
        self._entries: Dict[str, Dict[str, Any]] = {}
        # floor key -> point key -> [highest TDP a lower-power probe failed at, when, repeats]
        self._floors: Dict[str, Dict[str, list]] = {}
        self._last_write: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            # A damaged cache must never stop the Governor from starting.
            return
        entries = raw.get("entries") if isinstance(raw, dict) else None
        if isinstance(entries, dict):
            for key, entry in entries.items():
                if not self._valid(entry):
                    continue
                sanitized = dict(entry)
                failures = entry.get("failed")
                if isinstance(failures, dict):
                    sanitized["failed"] = {
                        point: list(value) for point, value in failures.items()
                        if isinstance(point, str) and self._valid_failure(value)
                    }
                else:
                    sanitized.pop("failed", None)
                self._entries[key] = sanitized
        floors = raw.get("floors") if isinstance(raw, dict) else None
        if isinstance(floors, dict):
            self._floors = {k: {p: list(v) for p, v in f.items() if self._valid_floor(v)}
                            for k, f in floors.items() if isinstance(f, dict)}

    @staticmethod
    def _finite_number(value: Any) -> bool:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        try:
            return math.isfinite(float(value))
        except (OverflowError, ValueError):
            # JSON may contain enormous ints or NaN/Infinity from a damaged
            # file. They must not crash startup or poison future decisions.
            return False

    @staticmethod
    def _valid(entry: Any) -> bool:
        if not isinstance(entry, dict) or not isinstance(entry.get("point"), str):
            return False
        tdp = entry.get("tdp_w")
        if tdp is not None and not (GameModelStore._finite_number(tdp)
                                    and 0 < tdp <= MAX_TDP_W):
            return False
        updated = entry.get("updated")
        confirmations = entry.get("confirmations", 0)
        return (GameModelStore._finite_number(updated) and updated >= 0
                and isinstance(confirmations, int) and not isinstance(confirmations, bool)
                and confirmations >= 0)

    @staticmethod
    def _valid_failure(value: Any) -> bool:
        return (isinstance(value, list) and len(value) == 2
                and all(GameModelStore._finite_number(x) for x in value)
                and 0 < value[0] <= MAX_TDP_W and value[1] >= 0)

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
            entry["failed"] = dict(previous["failed"])
            # A verified, newly held point supersedes the failure of that same
            # point. Otherwise a stale rejection would override fresh success
            # after a plugin reload and prevent a valid warm start.
            if tdp is not None:
                # An uncapped/observe-only confirmation proves output cadence,
                # not the wattage at which a previous cap failed.
                entry["failed"].pop(point, None)
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
            if self._valid_failure(v):
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
        worst = max(float(tdp_w), float(old[0])) if self._valid_failure(old) else float(tdp_w)
        failed[point] = [round(worst, 1), self.clock()]
        if len(failed) > 32:
            for stale in sorted(failed, key=lambda k: failed[k][1])[: len(failed) - 32]:
                del failed[stale]
        return self._save()

    # == BudgetController.FLOOR_BACKOFF_MAX_S: no floor failure blocks a level for longer.
    FLOOR_BACKOFF_MAX_S = 600.0

    @staticmethod
    def _valid_floor(v: Any) -> bool:
        return (isinstance(v, list) and len(v) == 3
                and all(GameModelStore._finite_number(x) for x in v)
                and 0 < v[0] <= MAX_TDP_W and v[1] >= 0
                and isinstance(v[2], int) and v[2] >= 1)

    def floor_failures(self, key: str) -> Dict[str, Tuple[float, float, int]]:
        """Lower-power probes that failed for this game: point -> (TDP, age in seconds, repeats).

        Like ``failures``: the age (not a re-anchored time) is returned, so a controller rebuilt
        by a mode switch or reload keeps the *remaining* back-off.  Older than the longest
        back-off: gone.
        """
        now = self.clock()
        out: Dict[str, Tuple[float, float, int]] = {}
        for point, v in (self._floors.get(key) or {}).items():
            age = max(0.0, now - float(v[1]))
            if age < self.FLOOR_BACKOFF_MAX_S:
                out[point] = (float(v[0]), age, int(v[2]))
        return out

    def record_floor_failure(self, key: str, point: str, tdp_w: Optional[float], count: int = 1) -> bool:
        """Remember 'point did not hold at tdp_w' (count-th time in a row); ``tdp_w`` None clears it
        (the level held: the scene got lighter)."""
        floors = self._floors.setdefault(key, {})
        if tdp_w is None:
            if floors.pop(point, None) is None:
                return False
        elif not 0 < float(tdp_w) <= MAX_TDP_W:
            return False
        else:
            floors[point] = [round(float(tdp_w), 1), self.clock(), max(1, min(int(count), 100))]
        now = self.clock()
        for k in list(self._floors):  # expired entries are dropped on every write
            self._floors[k] = {p: v for p, v in self._floors[k].items() if now - float(v[1]) < self.FLOOR_BACKOFF_MAX_S}
            if not self._floors[k]:
                del self._floors[k]
        return self._save()

    def forget(self, key: str) -> None:
        if self._entries.pop(key, None) is not None:
            self._save()

    def count_game(self, prefix: str) -> int:
        """How many entries were learned for one game (every target and mode)."""
        head = f"{prefix}|"
        return sum(1 for k in self._entries if k.startswith(head)) + sum(1 for k in self._floors if k.startswith(head))

    def forget_game(self, prefix: str) -> int:
        """Forget everything learned for one game (every target and mode); returns how many entries."""
        head = f"{prefix}|"
        gone = [k for k in self._entries if k.startswith(head)]
        floors = [k for k in self._floors if k.startswith(head)]
        for k in gone:
            del self._entries[k]
            self._last_write.pop(k, None)
        for k in floors:
            del self._floors[k]
        if gone or floors:
            self._save()
        return len(gone) + len(floors)

    def _save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "entries": self._entries, "floors": self._floors}, handle, sort_keys=True)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False
