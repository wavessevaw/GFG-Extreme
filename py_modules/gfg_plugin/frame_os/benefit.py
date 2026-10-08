"""What Frame OS gave the player this session, as three percentages (the Home rings).

* response — how much less time a real frame waits before it is shown, against the frame
  generator's own hold at this ratio ((m - 1) output slots + ~3 ms, measured on a Deck: x3 at
  90 Hz held ~25 ms, Act's just-in-time pacing ~13 ms);
* frames   — real frames in action (boost) against calm play;
* energy   — the cap Frame OS left unused against the Governor's own cap, over the session
  (rest savings minus boost spending; negative when boosts cost more than pauses saved).

Positive is better.  While Frame OS only measures (observe/shadow) the same numbers are estimates
of what Act would do: response from the boost cadence, energy from the decisions' watts.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

MIN_SECONDS = 2.0           # two seconds of live telemetry before the rings become meaningful
MIN_BOOST_SECONDS = 0.5     # a brief real-frame burst must show up; bursts accumulate
HOLD_OVERHEAD_MS = 3.0


def _mean(acc: list) -> Optional[float]:
    return acc[0] / acc[1] if acc[1] > 0 else None


class BenefitMeter:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.seconds = 0.0
        self.measured_s = 0.0
        self.fresh_act = [0.0, 0.0]          # freshness while acting (any level)
        self.real_calm = [0.0, 0.0]
        self.real_boost = [0.0, 0.0]
        self.boost_s = 0.0
        self.cap_ws = 0.0                    # Σ calm cap · dt
        self.saved_ws = 0.0                  # Σ (calm cap - Frame OS cap) · dt
        self.baseline_ms: Optional[float] = None
        self.planned_frames: Optional[float] = None
        self.planned_response_ms: Optional[float] = None
        self.acting_s = 0.0
        self.calm_real_hz: Optional[float] = None
        self._last: Optional[float] = None

    def add(self, now: float, *, acting: bool, level: Optional[str], telemetry: Dict[str, Any],
            output_hz: float, calm_real_hz: float, boost_real_hz: float,
            calm_w: Optional[float], tdp_w: Optional[float], counted: bool = True) -> None:
        dt = 0.0 if self._last is None else max(0.0, min(1.0, now - self._last))
        self._last = now
        if not counted:
            return      # an A/B control window is not Act: it never enters the session numbers
        if dt <= 0 or not telemetry.get("live") or output_hz <= 0 or calm_real_hz <= 0:
            return
        self.seconds += dt
        self.acting_s += dt if acting else 0.0
        self.calm_real_hz = calm_real_hz
        ratio = output_hz / calm_real_hz
        self.baseline_ms = (ratio - 1.0) * 1000.0 / output_hz + HOLD_OVERHEAD_MS
        if boost_real_hz > calm_real_hz:
            self.planned_frames = (boost_real_hz / calm_real_hz - 1.0) * 100.0
            self.planned_response_ms = 1000.0 / calm_real_hz - 1000.0 / boost_real_hz
        fresh = telemetry.get("freshness_ms")
        interval = telemetry.get("present_interval_p50_ms")
        real = 1000.0 / interval if isinstance(interval, (int, float)) and interval > 0 else None
        if acting and isinstance(fresh, (int, float)) and fresh > 0:
            self.fresh_act[0] += fresh * dt
            self.fresh_act[1] += dt
        if real is not None and level == "calm":
            self.real_calm[0] += real * dt
            self.real_calm[1] += dt
        if real is not None and level == "boost":
            self.real_boost[0] += real * dt
            self.real_boost[1] += dt
            self.boost_s += dt
        if isinstance(calm_w, (int, float)) and calm_w > 0 and isinstance(tdp_w, (int, float)):
            self.cap_ws += calm_w * dt
            self.saved_ws += (calm_w - tdp_w) * dt

    def summary(self) -> Dict[str, Any]:
        estimate = self.acting_s < 0.5 * self.seconds
        ready = self.seconds >= MIN_SECONDS
        out: Dict[str, Any] = {"estimate": estimate, "ready": ready, "seconds": round(self.seconds)}
        if not ready:
            return {**out, "response_pct": None, "frames_pct": None, "energy_pct": None}
        energy = round(100.0 * self.saved_ws / self.cap_ws, 1) if self.cap_ws > 0 else None
        if estimate:
            fresh = self.baseline_ms
            response = (round(100.0 * self.planned_response_ms / fresh, 1)
                        if self.planned_response_ms and fresh else None)
            frames = round(self.planned_frames, 1) if self.planned_frames is not None else None
        else:
            act = _mean(self.fresh_act)
            response = (round(100.0 * (self.baseline_ms - act) / self.baseline_ms, 1)
                        if act is not None and self.baseline_ms else None)
            calm, boost = _mean(self.real_calm) or self.calm_real_hz, _mean(self.real_boost)
            if calm and boost is not None and self.boost_s >= MIN_BOOST_SECONDS:
                frames = round(100.0 * (boost - calm) / calm, 1)
            elif calm and self.acting_s >= MIN_SECONDS and self.boost_s == 0:
                # No boost yet is a measured 0%, not an indefinitely broken "—" ring.
                frames = 0.0
            else:
                frames = None
        return {**out, "response_pct": response, "frames_pct": frames, "energy_pct": energy,
                "energy_basis": "tdp-cap-delta", "frames_basis": "pacer-real-present-interval"}
