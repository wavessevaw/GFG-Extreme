"""GPU clock ceiling. Real writes stay off until a Deck proves the restore path.

Reading the amdgpu files is allowed. Changing them is not, unless a test passes
an explicit backend with writes enabled. A failed write keeps ownership until
the previous level is read back.
"""
from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path


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


class FileBackend:
    def __init__(self, root: str = "/sys/class/drm") -> None:
        self.root = root

    def exists(self) -> bool:
        return self._paths() is not None

    def read(self):
        level_path, table_path = self._paths()
        return (Path(level_path).read_text(encoding="utf-8", errors="replace").strip(),
                Path(table_path).read_text(encoding="utf-8", errors="replace"))

    def write_level(self, text: str) -> None:
        with open(self._paths()[0], "w", encoding="utf-8") as handle:
            handle.write(text)

    def write_table(self, text: str) -> None:
        with open(self._paths()[1], "w", encoding="utf-8") as handle:
            handle.write(text)

    def _paths(self):
        levels = sorted(glob.glob(os.path.join(self.root, "card*", "device", "power_dpm_force_performance_level")))
        tables = sorted(glob.glob(os.path.join(self.root, "card*", "device", "pp_od_clk_voltage")))
        if not levels or not tables:
            return None
        return levels[0], tables[0]


class GpuClock:
    def __init__(self, backend=None, writes_enabled: bool = False, receipt_path: Path | None = None) -> None:
        self.backend = backend or FileBackend()
        self.writes_enabled = bool(writes_enabled)
        self.receipt_path = Path(receipt_path) if receipt_path else None
        self.phase = "idle"
        self.saved_level = None
        self.saved_max = None
        self.applied_max = None
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
                "min_mhz": int(found.group(1)), "max_mhz": high,
                "current_limit_mhz": clocks[-1] if clocks else high}

    def lower_ceiling(self) -> dict:
        if not self.writes_enabled:
            return {"applied": False, "reason": "writes-disabled"}
        if self.phase == "restore-pending":
            return {"applied": False, "reason": "restore-pending"}
        info = self.status()
        if not info.get("available"):
            return {"applied": False, "reason": info.get("reason") or "GPU_CLOCK_UNAVAILABLE"}
        target = int(info["current_limit_mhz"]) - STEP_MHZ
        if target < int(info["min_mhz"]):
            return {"applied": False, "reason": "no-headroom"}
        if self.phase == "idle":
            self.saved_level = info.get("level") or "auto"
            self.saved_max = int(info["current_limit_mhz"])
        self.phase = "partial"
        self._save()
        try:
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
        if self.phase == "owned" and info.get("available"):
            current = info.get("current_limit_mhz")
            if current not in (self.applied_max, self.saved_max):
                self._clear()
                return {"restored": False, "reason": "external-change", "yielded": True}
        if not info.get("available"):
            self.phase = "restore-pending"
            self._save()
            return {"restored": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        try:
            if self.saved_max is not None:
                self.backend.write_table(f"s 1 {int(self.saved_max)}")
                self.backend.write_table("c")
            self.backend.write_level(self.saved_level or "auto")
        except OSError as error:
            self.last_error = str(error)
            self.phase = "restore-pending"
            self._save()
            return {"restored": False, "reason": "restore-failed"}
        after = self.status()
        level_ok = after.get("level") == (self.saved_level or "auto")
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
        self.saved_max = None
        self.applied_max = None
        self._save()

    def _save(self) -> None:
        if self.receipt_path is None:
            return
        if self.phase == "idle":
            self.receipt_path.unlink(missing_ok=True)
            return
        payload = {"phase": self.phase, "saved_level": self.saved_level,
                   "saved_max": self.saved_max, "applied_max": self.applied_max}
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
        self.phase = payload["phase"]
        self.saved_level = payload.get("saved_level")
        self.saved_max = payload.get("saved_max")
        self.applied_max = payload.get("applied_max")
