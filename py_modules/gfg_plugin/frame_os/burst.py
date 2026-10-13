"""Short real-present cadence windows; a 64-frame median cannot qualify a 500 ms pulse."""
from __future__ import annotations

from typing import Any, Dict, Optional


class BurstCadence:
    def __init__(self) -> None:
        self._anchor = None
        self._last_ns = None
        self.last: Dict[str, Any] = {"available": False, "basis": "real-present-counter-delta"}

    def sample(self, telemetry: Dict[str, Any]) -> Optional[float]:
        values = [telemetry.get(k) for k in ("writer_pid", "applied_generation", "swapchain_recreations", "frames", "last_present_ns")]
        if not telemetry.get("live") or any(type(v) is not int or v < 0 for v in values) or values[0] <= 0 or values[4] <= 0:
            self._anchor = self._last_ns = None
            self.last = {"available": False, "basis": "real-present-counter-delta"}
            return None
        pid, generation, recreations, frames, ns = values
        key = (pid, generation, recreations)
        if ns == self._last_ns:
            self.last = {"available": False, "basis": "real-present-counter-delta"}
            return None  # a repeated publication is not new evidence
        self._last_ns = ns
        anchor = self._anchor
        self.last = {"available": False, "basis": "real-present-counter-delta"}
        if anchor is None or anchor[0] != key or frames <= anchor[1] or ns <= anchor[2] or ns-anchor[2] > 500_000_000:
            self._anchor = (key, frames, ns)
            return None
        span = (ns-anchor[2])/1e9
        count = frames-anchor[1]
        if span < 0.15 or count < 4:
            return None
        self._anchor = (key, frames, ns)
        hz = count/span
        self.last = {"available": True, "basis": "real-present-counter-delta", "real_hz": round(hz,3),
                     "frames": count, "span_ms": round(span*1000,3), "generation": generation, "writer_pid": pid,
                     "start_monotonic_s":anchor[2]/1e9,"end_monotonic_s":ns/1e9}
        return hz
