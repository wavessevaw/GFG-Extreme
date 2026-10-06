"""Cheap, read-only host sensors for the Governor: temperature, GPU/CPU load, fan, battery draw.

Everything is read from sysfs/procfs without privileges or subprocesses, every path is optional,
and a missing sensor is reported as ``None`` rather than guessed.  ``HostSensors.sample`` is
called by the Governor loop at most every ``MIN_INTERVAL`` seconds, so the cost is a handful of
tiny file reads.
"""
from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Tuple


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _num(path: Path) -> Optional[float]:
    text = _read(path)
    if text is None:
        return None
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return None


class HostSensors:
    MIN_INTERVAL = 2.0
    SLOPE_WINDOW_S = 120.0
    THROTTLE_C = 90.0

    def __init__(
        self,
        *,
        hwmon_root: Path = Path("/sys/class/hwmon"),
        drm_root: Path = Path("/sys/class/drm"),
        power_supply_root: Path = Path("/sys/class/power_supply"),
        proc_stat: Path = Path("/proc/stat"),
        clock=time.monotonic,
    ) -> None:
        self.hwmon_root, self.drm_root = Path(hwmon_root), Path(drm_root)
        self.power_supply_root, self.proc_stat = Path(power_supply_root), Path(proc_stat)
        self.clock = clock
        self._last: Dict[str, Any] = {}
        self._last_at = -1e9
        self._cpu_prev: Optional[Tuple[int, int, Dict[str, Tuple[int, int]]]] = None
        self._temps: Deque[Tuple[float, float]] = deque(maxlen=120)

    # ------------------------------------------------------------------ public
    def sample(self, force: bool = False) -> Dict[str, Any]:
        now = self.clock()
        if not force and now - self._last_at < self.MIN_INTERVAL and self._last:
            return self._last
        self._last_at = now
        temp = self._temperature()
        value: Dict[str, Any] = {
            "temp_c": temp,
            "temp_slope_c_per_min": self._slope(now, temp),
            "thermal_headroom_c": round(self.THROTTLE_C - temp, 1) if temp is not None else None,
            "fan_rpm": self._fan(),
            **self._gpu(),
            **self._cpu(),
            **self._battery(),
        }
        self._last = value
        return value

    # ------------------------------------------------------------- temperature
    def _hwmons(self):
        try:
            return sorted(self.hwmon_root.glob("hwmon*"))
        except OSError:
            return []

    def _temperature(self) -> Optional[float]:
        """APU/GPU edge temperature in °C: the amdgpu hwmon, else k10temp."""
        best: Optional[float] = None
        for hwmon in self._hwmons():
            name = _read(hwmon / "name")
            if name not in ("amdgpu", "k10temp"):
                continue
            raw = _num(hwmon / "temp1_input")
            if raw is None:
                continue
            value = raw / 1000.0
            if name == "amdgpu":
                return round(value, 1)
            best = round(value, 1)
        return best

    def _slope(self, now: float, temp: Optional[float]) -> Optional[float]:
        if temp is None:
            return None
        self._temps.append((now, temp))
        while self._temps and now - self._temps[0][0] > self.SLOPE_WINDOW_S:
            self._temps.popleft()
        first = self._temps[0]
        if now - first[0] < 20.0:
            return None  # not enough history to call it a trend
        return round((temp - first[1]) / ((now - first[0]) / 60.0), 2)

    def _fan(self) -> Optional[float]:
        for hwmon in self._hwmons():
            rpm = _num(hwmon / "fan1_input")
            if rpm is not None:
                return rpm
        return None

    # --------------------------------------------------------------------- GPU
    def _gpu(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"gpu_busy_pct": None, "gpu_clock_mhz": None}
        try:
            devices = sorted(self.drm_root.glob("card*/device"))
        except OSError:
            devices = []
        for device in devices:
            busy = _num(device / "gpu_busy_percent")
            if busy is None:
                continue
            out["gpu_busy_pct"] = busy
            sclk = _read(device / "pp_dpm_sclk")
            if sclk:
                for line in sclk.splitlines():
                    if line.rstrip().endswith("*"):
                        try:
                            out["gpu_clock_mhz"] = float(line.split(":")[1].strip().split("Mhz")[0].strip().rstrip("*"))
                        except (IndexError, ValueError):
                            pass
            break
        return out

    # --------------------------------------------------------------------- CPU
    def _cpu(self) -> Dict[str, Any]:
        """Total and busiest-core utilisation since the previous sample (a CPU-bound game can show 40% total)."""
        text = _read(self.proc_stat)
        out: Dict[str, Any] = {"cpu_total_pct": None, "cpu_top_core_pct": None}
        if not text:
            return out
        cores: Dict[str, Tuple[int, int]] = {}
        total: Optional[Tuple[int, int]] = None
        for line in text.splitlines():
            if not line.startswith("cpu"):
                continue
            parts = line.split()
            try:
                values = [int(v) for v in parts[1:9]]
            except ValueError:
                continue
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            busy_total = sum(values)
            if parts[0] == "cpu":
                total = (busy_total - idle, busy_total)
            else:
                cores[parts[0]] = (busy_total - idle, busy_total)
        if total is None:
            return out
        previous = self._cpu_prev
        self._cpu_prev = (total[0], total[1], cores)
        if previous is None:
            return out

        def pct(now_pair: Tuple[int, int], old_pair: Tuple[int, int]) -> Optional[float]:
            dt = now_pair[1] - old_pair[1]
            return round(100.0 * (now_pair[0] - old_pair[0]) / dt, 1) if dt > 0 else None

        out["cpu_total_pct"] = pct(total, (previous[0], previous[1]))
        tops = [p for name, pair in cores.items() if name in previous[2] for p in [pct(pair, previous[2][name])] if p is not None]
        out["cpu_top_core_pct"] = max(tops) if tops else None
        return out

    # ----------------------------------------------------------------- battery
    def _battery(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"battery_pct": None, "battery_status": None, "battery_discharge_w": None}
        try:
            supplies = sorted(self.power_supply_root.glob("BAT*"))
        except OSError:
            supplies = []
        for supply in supplies:
            out["battery_pct"] = _num(supply / "capacity")
            out["battery_status"] = _read(supply / "status")
            power = _num(supply / "power_now")
            if power is None:
                current, voltage = _num(supply / "current_now"), _num(supply / "voltage_now")
                power = current * voltage / 1e6 if current is not None and voltage is not None else None
            if power is not None:
                out["battery_discharge_w"] = round(abs(power) / 1e6, 2)  # power is in µW here
            break
        return out


def diagnose(sensors: Dict[str, Any], *, cap_w: Optional[float] = None, draw_w: Optional[float] = None,
             frametime: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One plain-language verdict: what limits the game and whether the machine is healthy."""
    gpu, top = sensors.get("gpu_busy_pct"), sensors.get("cpu_top_core_pct")
    if cap_w and draw_w is not None and draw_w >= 0.97 * cap_w:
        bottleneck = "power"
    elif gpu is not None and gpu >= 90:
        bottleneck = "gpu"
    elif top is not None and top >= 90 and (gpu is None or gpu < 80):
        bottleneck = "cpu"
    elif gpu is None and top is None:
        bottleneck = "unknown"
    else:
        bottleneck = "none"
    headroom, slope = sensors.get("thermal_headroom_c"), sensors.get("temp_slope_c_per_min")
    if headroom is not None and headroom < 8:
        thermal = "hot"
    elif slope is not None and slope > 1.5 and (sensors.get("temp_c") or 0) > 70:
        thermal = "heating"
    else:
        thermal = "ok" if headroom is not None else "unknown"
    stutter = (frametime or {}).get("stutter_ratio")
    smooth = "unknown" if stutter is None else ("stuttering" if stutter > 0.05 else "smooth")
    return {"bottleneck": bottleneck, "thermal": thermal, "smoothness": smooth}
