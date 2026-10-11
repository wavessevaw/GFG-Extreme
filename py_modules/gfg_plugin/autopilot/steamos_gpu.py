"""SteamOS Quick Access GPU clock, through the SteamOSManager session D-Bus.

This is the same GPU-performance property interface as SteamOS's manual clock
control. It is NOT AMD OverDrive; no direct sysfs writes, root, or shell.

Optional GpuPerformanceLevel1 support is detected at runtime. The backend is
intentionally unavailable when SteamOSManager does not publish the property.
"""
from __future__ import annotations

import re

from ..steamos_tdp import BUS_NAME, OBJECT_PATH, SteamOSManagerTdp

INTERFACE = "com.steampowered.SteamOSManager1.GpuPerformanceLevel1"


class SteamOSGpuBackend(SteamOSManagerTdp):
    """Backend adapter for GpuClock, using Steam's session-bus GPU properties.

    `manual` applies a fixed manual GPU frequency, not an overclock/ceiling.
    Read-back checks the SteamOSManager property rather than observed GPU MHz
    (observed clocks can fluctuate with the workload).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.manual_clock_mhz = None
        self.low_mhz = None
        self.high_mhz = None

    def exists(self) -> bool:
        return bool(self._which("busctl") or self._which("steamosctl"))

    def _get(self, prop: str, cmd: str, typ: str):
        busctl = self._which("busctl")
        if busctl:
            ok, out = self._runner([busctl, "--user", "get-property",
                                    BUS_NAME, OBJECT_PATH, INTERFACE, prop])
            if ok and out.startswith(typ + " "):
                value = out[len(typ) + 1:].strip().strip('"')
                if typ == "u":
                    try:
                        return int(value)
                    except ValueError:
                        pass
                else:
                    return value
        ctl = self._which("steamosctl")
        if ctl:
            ok, out = self._runner([ctl, cmd])
            if ok:
                # steamosctl reads print e.g. 'GPU performance level: auto'.
                value = out.rsplit(":", 1)[-1].strip()
                if typ == "u":
                    match = re.search(r"\d+", value)
                    return int(match.group()) if match else None
                return value.strip('"')
        return None

    def _set(self, prop: str, value, typ: str, cmd: str) -> None:
        ctl = self._which("steamosctl")
        errors = []
        if ctl:
            ok, result = self._runner([ctl, cmd, str(value)])
            if ok:
                return
            errors.append(result)
        busctl = self._which("busctl")
        if busctl:
            ok, result = self._runner([busctl, "--user", "set-property",
                                       BUS_NAME, OBJECT_PATH, INTERFACE, prop,
                                       typ, str(value)])
            if ok:
                return
            errors.append(result)
        raise OSError("SteamOSManager GPU property rejected: " +
                      "; ".join(errors or ["no-steamosctl-or-busctl"]))

    def read(self):
        level = self._get("GpuPerformanceLevel", "get-gpu-performance-level", "s")
        low = self._get("ManualGpuClockMin", "get-manual-gpu-clock-min", "u")
        high = self._get("ManualGpuClockMax", "get-manual-gpu-clock-max", "u")
        manual = self._get("ManualGpuClock", "get-manual-gpu-clock", "u")
        if (level not in ("auto", "manual", "low", "high", "profile_peak")
                or not isinstance(low, int) or not isinstance(high, int)
                or not isinstance(manual, int) or not 100 <= low < high <= 3000
                or not low <= manual <= high):
            raise OSError("SteamOSManager GpuPerformanceLevel1 not readable")
        self.manual_clock_mhz = manual
        self.low_mhz, self.high_mhz = low, high
        # Preserve the GpuClock contract; in auto mode the GPU is allowed to
        # reach the hardware maximum, while ManualGpuClock stores the user
        # setting for later restoration.
        selected = manual if level == "manual" else high
        table = (f"OD_SCLK:\n0: {low}Mhz\n1: {selected}Mhz\n"
                 f"OD_RANGE:\nSCLK: {low}Mhz {high}Mhz\n")
        return level, table

    def write_level(self, text: str) -> None:
        level = text.strip()
        if level not in ("auto", "manual", "low", "high", "profile_peak"):
            raise OSError("unsupported SteamOS GPU level")
        self._set("GpuPerformanceLevel", level, "s", "set-gpu-performance-level")

    def write_table(self, text: str) -> None:
        # Compatibility with the existing transactional GpuClock adapter.
        # SteamOSManager changes ManualGpuClock atomically; there is no AMD
        # pp_od_clk_voltage commit operation.
        if text.strip() == "c":
            return
        match = re.fullmatch(r"s 1 (\d+)", text.strip())
        if not match:
            raise OSError("unsupported GPU clock command")
        clock = int(match.group(1))
        if (self.low_mhz is None or self.high_mhz is None
                or not self.low_mhz <= clock <= self.high_mhz):
            raise OSError("GPU clock outside SteamOSManager range")
        self._set("ManualGpuClock", clock, "u", "set-manual-gpu-clock")
