"""GPU clock ceiling (from GFG Extreme 2.x), through SteamOSManager's manual GPU clock.

The same interface as the Quick Access Menu's GPU clock slider, never AMD OverDrive sysfs.
A player's manual clock is never overridden. A failed write keeps ownership until the
previous level is read back; a receipt file brings the player's setting back after a crash.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

from .steamos_gpu import SteamOSGpuBackend


STEP_MHZ = 100
_RANGE = re.compile(r"SCLK:\s*(\d+)\s*Mhz\s*(\d+)\s*Mhz", re.I)
_LEVEL = re.compile(r"^(\d+):\s*(\d+)\s*Mhz", re.M)


class MemoryBackend:
    """Stand-in for the two sysfs files. A failure can land between commands."""

    def __init__(self, fail_at: str | None = None) -> None:
        self.level = "auto"
        self.minimum = 200
        self.maximum = 1600
        self.pending = None
        self.fail_at = fail_at
        self.writes: list = []

    def exists(self) -> bool:
        return True

    def read(self):
        table = f"OD_SCLK:\n0: {self.minimum}Mhz\n1: {self.maximum}Mhz\nOD_RANGE:\nSCLK: {self.minimum}Mhz {self.maximum}Mhz\n"
        return self.level, table

    def write_level(self, text: str) -> None:
        self.writes.append(("level", text))
        if self.fail_at == "level":
            raise OSError("level")
        self.level = text.strip()

    def write_table(self, text: str) -> None:
        self.writes.append(("table", text))
        if text.startswith("s 1"):
            if self.fail_at == "limit":
                raise OSError("limit")
            self.pending = int(text.split()[-1])
            return
        if text.strip() == "c":
            if self.fail_at == "commit":
                raise OSError("commit")
            if self.pending is not None:
                self.maximum = self.pending
                self.pending = None


class GpuClock:
    def __init__(self, backend=None, writes_enabled: bool = False, receipt_path: Path | None = None) -> None:
        # Only the SteamOSManager/QAM interface is used in production.
        # Never fall back to low-level AMDGPU OverDrive writes.
        self.backend = backend if backend is not None else SteamOSGpuBackend(home=os.environ.get("HOME"))
        self.writes_enabled = bool(writes_enabled)
        self.receipt_path = Path(receipt_path) if receipt_path else None
        self.phase = "idle"
        self.saved_level = None
        self.saved_manual = None
        self.saved_max = None
        self.applied_max = None
        self.restore_manual_started = False
        self.last_error = ""
        self._load()

    @property
    def owned(self) -> bool:
        return self.phase in ("partial", "owned", "restore-pending")

    def status(self) -> dict:
        base = {"owned": self.owned, "phase": self.phase, "limit_mhz": self.applied_max,
                "writes_enabled": self.writes_enabled, "last_error": self.last_error}
        if not self.backend.exists():
            return {**base, "available": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        try:
            level, table = self.backend.read()
        except OSError as error:
            self.last_error = str(error)
            return {**base, "available": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        found = _RANGE.search(table)
        if not found:
            return {**base, "available": False, "reason": "range-unreadable", "level": level}
        clocks = [int(item[1]) for item in _LEVEL.findall(table)]
        high = int(found.group(2))
        return {**base, "available": True, "reason": "ready", "level": level,
                "backend": type(self.backend).__name__,
                "manual_clock_mhz": getattr(self.backend, "manual_clock_mhz", None),
                "min_mhz": int(found.group(1)), "max_mhz": high,
                "current_limit_mhz": clocks[-1] if clocks else high}

    def lower_ceiling(self, observed_mhz: float | None = None) -> dict:
        if not self.writes_enabled:
            return {"applied": False, "reason": "writes-disabled"}
        if self.phase == "restore-pending":
            return {"applied": False, "reason": "restore-pending"}
        info = self.status()
        if not info.get("available"):
            return {"applied": False, "reason": info.get("reason") or "GPU_CLOCK_UNAVAILABLE"}
        # Never override the user's manual Steam GPU clock setting.
        if self.phase == "idle" and info.get("level") != "auto":
            return {"applied": False, "reason": "user-manual-clock"}
        if self.phase == "owned" and (info.get("level") != "manual"
                                       or info.get("current_limit_mhz") != self.applied_max):
            self._clear()
            return {"applied": False, "reason": "external-change"}
        current = int(info["current_limit_mhz"])
        if observed_mhz is not None:
            if (isinstance(observed_mhz, bool) or not isinstance(observed_mhz, (int, float))
                    or not math.isfinite(observed_mhz) or observed_mhz <= 0):
                return {"applied": False, "reason": "observed-clock-unavailable"}
            # SteamOSManager pins a manual frequency. Starting from its hardware
            # maximum could raise a lightly loaded GPU's actual clock. Start
            # below the observed clock as well as the currently allowed limit.
            current = min(current, int(observed_mhz))
        target = current - STEP_MHZ
        if target < int(info["min_mhz"]):
            return {"applied": False, "reason": "no-headroom"}
        return self._apply(target, info)

    def raise_ceiling(self) -> dict:
        """One step back up; at the player's own limit the clock is handed back instead."""
        if self.phase != "owned" or self.applied_max is None:
            return {"applied": False, "reason": "not-owned"}
        target = self.applied_max + STEP_MHZ
        if self.saved_max is not None and target >= self.saved_max:
            r = self.restore()
            return {"applied": bool(r.get("restored")), "reason": "restored", "restored": r.get("restored")}
        info = self.status()
        if not info.get("available"):
            return {"applied": False, "reason": info.get("reason") or "GPU_CLOCK_UNAVAILABLE"}
        if info.get("level") != "manual" or info.get("current_limit_mhz") != self.applied_max:
            self._clear()
            return {"applied": False, "reason": "external-change"}
        return self._apply(target, info)

    def _apply(self, target: int, info: dict) -> dict:
        if self.phase == "idle":
            self.saved_level = info.get("level") or "auto"
            self.saved_manual = info.get("manual_clock_mhz")
            self.saved_max = int(info["current_limit_mhz"])
        self.phase = "partial"
        self._save()
        try:
            if getattr(self.backend, "manual_is_fixed", False):
                # Program the stored QAM frequency while still in Auto, then
                # enable Manual; never briefly activate the old saved frequency.
                self.backend.write_table(f"s 1 {target}")
                self.backend.write_level("manual")
            else:
                self.backend.write_level("manual")
                self.backend.write_table(f"s 1 {target}")
            self.backend.write_table("c")
        except OSError as error:
            self.last_error = str(error)
            return self._fail("write-failed")
        after = self.status()
        if after.get("level") != "manual" or after.get("current_limit_mhz") != target:
            self.last_error = "readback-mismatch"
            return self._fail("readback-mismatch")
        self.phase = "owned"
        self.applied_max = target
        self._save()
        return {"applied": True, "reason": "ceiling-lowered", "limit_mhz": target}

    def restore(self) -> dict:
        if self.phase == "idle":
            return {"restored": True, "reason": "not-owned"}
        info = self.status()
        if (self.phase in ("owned", "restore-pending") and info.get("available")
                and self.applied_max is not None):
            if (info.get("level") == self.saved_level
                    and (self.saved_manual is None or info.get("manual_clock_mhz") == self.saved_manual)
                    and info.get("current_limit_mhz") == self.saved_max):
                self._clear()
                return {"restored": True, "reason": "already-restored"}
            current = info.get("current_limit_mhz")
            allowed = (self.applied_max, self.saved_max,
                       self.saved_manual if self.restore_manual_started else None)
            if (info.get("level") != "manual"
                    or current not in allowed):
                self._clear()
                return {"restored": False, "reason": "external-change", "yielded": True}
        if not info.get("available"):
            self.phase = "restore-pending"
            self._save()
            return {"restored": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        try:
            if self.saved_max is not None:
                self.restore_manual_started = True
                self._save()
                self.backend.write_table(f"s 1 {int(self.saved_manual if self.saved_manual is not None else self.saved_max)}")
                self.backend.write_table("c")
            self.backend.write_level(self.saved_level or "auto")
        except OSError as error:
            self.last_error = str(error)
            self.phase = "restore-pending"
            self._save()
            return {"restored": False, "reason": "restore-failed"}
        after = self.status()
        level_ok = after.get("level") == (self.saved_level or "auto")
        if self.saved_manual is not None:
            max_ok = after.get("manual_clock_mhz") == self.saved_manual
        else:
            max_ok = self.saved_max is None or after.get("current_limit_mhz") == self.saved_max
        if not (level_ok and max_ok):
            self.phase = "restore-pending"
            self._save()
            return {"restored": False, "reason": "restore-unconfirmed"}
        self._clear()
        return {"restored": True, "reason": "restored"}

    def _fail(self, reason: str) -> dict:
        restored = self.restore()
        if restored.get("restored"):
            return {"applied": False, "reason": reason, "restored": True}
        return {"applied": False, "reason": reason, "restored": False,
                "restore_reason": restored.get("reason")}

    def _clear(self) -> None:
        self.phase = "idle"
        self.saved_level = None
        self.saved_manual = None
        self.saved_max = None
        self.applied_max = None
        self.restore_manual_started = False
        self._save()

    def _save(self) -> None:
        if self.receipt_path is None:
            return
        if self.phase == "idle":
            self.receipt_path.unlink(missing_ok=True)
            return
        payload = {"phase": self.phase, "saved_level": self.saved_level,
                   "saved_manual": self.saved_manual,
                   "saved_max": self.saved_max, "applied_max": self.applied_max,
                   "restore_manual_started": self.restore_manual_started,
                   "backend": type(self.backend).__name__}
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temporary, self.receipt_path)

    def _load(self) -> None:
        if self.receipt_path is None or not self.receipt_path.is_file():
            return
        try:
            payload = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(payload, dict) or payload.get("phase") not in ("partial", "owned", "restore-pending"):
            return
        # Restart loses the arbiter's comparison window. Recover the receipt
        # through restore, never retain an experiment that cannot be judged.
        self.phase = "restore-pending"
        self.saved_level = payload.get("saved_level")
        self.saved_manual = payload.get("saved_manual")
        self.saved_max = payload.get("saved_max")
        self.applied_max = payload.get("applied_max")
        self.restore_manual_started = bool(payload.get("restore_manual_started"))
