"""Steam Deck GPU clock ceiling via the amdgpu sysfs Steam itself uses.

Measured MHz is not a ceiling. This adapter only lowers the maximum sclk by
one step, and only after it has read a real range. If the files are missing,
it returns GPU_CLOCK_UNAVAILABLE and writes nothing.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path


STEP_MHZ = 100
_RANGE = re.compile(r"SCLK:\s*(\d+)\s*Mhz\s*(\d+)\s*Mhz", re.I)
_LEVEL = re.compile(r"^(\d+):\s*(\d+)\s*Mhz", re.M)


class GpuClock:
    def __init__(self, root: str = "/sys/class/drm") -> None:
        self.root = root
        self.saved_level = None
        self.saved_max = None
        self.applied_max = None
        self.owned = False
        self.last_error = ""

    def status(self) -> dict:
        paths = self._paths()
        if paths is None:
            return {"available": False, "reason": "GPU_CLOCK_UNAVAILABLE",
                    "owned": self.owned, "limit_mhz": self.applied_max}
        try:
            table = Path(paths[1]).read_text(encoding="utf-8", errors="replace")
            level = Path(paths[0]).read_text(encoding="utf-8", errors="replace").strip()
        except OSError as error:
            self.last_error = str(error)
            return {"available": False, "reason": "GPU_CLOCK_UNAVAILABLE",
                    "owned": self.owned, "limit_mhz": self.applied_max}
        found = _RANGE.search(table)
        if not found:
            return {"available": False, "reason": "range-unreadable",
                    "owned": self.owned, "limit_mhz": self.applied_max}
        low, high = int(found.group(1)), int(found.group(2))
        clocks = [int(item[1]) for item in _LEVEL.findall(table)]
        current = clocks[-1] if clocks else high
        return {"available": True, "reason": "ready", "level": level,
                "min_mhz": low, "max_mhz": high, "current_limit_mhz": current,
                "owned": self.owned, "limit_mhz": self.applied_max}

    def lower_ceiling(self) -> dict:
        info = self.status()
        if not info.get("available"):
            return {"applied": False, "reason": info.get("reason") or "GPU_CLOCK_UNAVAILABLE"}
        low, current = info["min_mhz"], info["current_limit_mhz"]
        target = current - STEP_MHZ
        if target < low or target >= current:
            return {"applied": False, "reason": "no-headroom"}
        paths = self._paths()
        if paths is None:
            return {"applied": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        if not self.owned:
            self.saved_level = info.get("level") or "auto"
            self.saved_max = current
        try:
            self._write(paths[0], "manual")
            self._write(paths[1], f"s 1 {int(target)}")
            self._write(paths[1], "c")
        except OSError as error:
            self.last_error = str(error)
            return {"applied": False, "reason": "write-failed"}
        self.owned = True
        self.applied_max = int(target)
        return {"applied": True, "reason": "ceiling-lowered", "limit_mhz": int(target)}

    def restore(self) -> dict:
        if not self.owned:
            return {"restored": True, "reason": "not-owned"}
        paths = self._paths()
        if paths is None:
            self.last_error = "path-lost"
            return {"restored": False, "reason": "GPU_CLOCK_UNAVAILABLE"}
        try:
            if self.saved_max is not None:
                self._write(paths[1], f"s 1 {int(self.saved_max)}")
                self._write(paths[1], "c")
            self._write(paths[0], self.saved_level or "auto")
        except OSError as error:
            self.last_error = str(error)
            return {"restored": False, "reason": "restore-failed"}
        self.owned = False
        self.applied_max = None
        return {"restored": True, "reason": "restored"}

    def _paths(self):
        levels = sorted(glob.glob(os.path.join(self.root, "card*", "device", "power_dpm_force_performance_level")))
        tables = sorted(glob.glob(os.path.join(self.root, "card*", "device", "pp_od_clk_voltage")))
        if not levels or not tables:
            return None
        return levels[0], tables[0]

    @staticmethod
    def _write(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
