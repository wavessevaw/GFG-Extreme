"""Per-game-session numbers for the player: how long, how smooth, how many watts.

The Governor feeds one sample per loop iteration while a managed game runs and FPS telemetry is
fresh.  Averages are time-weighted (each sample counts for the time since the previous one, capped
so a pause in telemetry cannot dominate).  ``reference_w`` is the TDP limit the Deck had before the
Governor took over, i.e. what the game would have been allowed without GFG.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

MAX_STEP_S = 5.0
MIN_SESSION_S = 30.0
MIN_MODE_S = 30.0  # a mode used for less than this (a misclick) does not make a session "mixed"


class SessionStats:
    def __init__(self) -> None:
        self.key: Optional[tuple] = None
        self._reset()

    def _reset(self) -> None:
        self.started: Optional[float] = None
        self.last: Optional[float] = None
        self.seconds = 0.0
        self._sums: Dict[str, float] = {}
        self._weights: Dict[str, float] = {}
        self.reference_w: Optional[float] = None
        self.max_temp_c: Optional[float] = None
        self.stutter_s = 0.0
        self.hot_s = 0.0
        self.mode_s: Dict[str, float] = {}
        self.frame_os_s: Dict[str, float] = {}
        self.benefit: Optional[Dict[str, Any]] = None

    def start(self, key: Any, now: float) -> None:
        self.key = tuple(key) if isinstance(key, (list, tuple)) else key
        self._reset()
        self.started = self.last = now

    def add(self, now: float, *, output: Optional[float], real: Optional[float], tdp: Optional[float],
            draw: Optional[float], reference_w: Optional[float], temp_c: Optional[float] = None,
            stuttering: bool = False, hot: bool = False, mode: Optional[str] = None,
            battery_w: Optional[float] = None, frame_os: Optional[str] = None,
            benefit: Optional[Dict[str, Any]] = None) -> None:
        if self.started is None or self.last is None:
            return
        dt = min(MAX_STEP_S, max(0.0, now - self.last))
        self.last = now
        if dt <= 0:
            return
        self.seconds += dt
        if mode:  # review 1.1.x: the mode at the exit alone misfiled mixed sessions
            self.mode_s[str(mode)] = self.mode_s.get(str(mode), 0.0) + dt
        if isinstance(benefit, dict) and benefit.get("ready"):
            # The meter is cumulative for the game, so its latest reading is the session average.
            self.benefit = {"response": benefit.get("response_pct"), "frames": benefit.get("frames_pct"),
                            "energy": benefit.get("energy_pct"), "estimate": bool(benefit.get("estimate")),
                            "measured": dict(benefit.get("measured") or {})}
        if frame_os:  # Frame OS decision (boost / calm / rest) while its layer answered
            self.frame_os_s[str(frame_os)] = self.frame_os_s.get(str(frame_os), 0.0) + dt
        for name, value in (("output", output), ("real", real), ("tdp", tdp), ("draw", draw), ("battery", battery_w)):
            if isinstance(value, (int, float)) and value > 0:
                self._sums[name] = self._sums.get(name, 0.0) + float(value) * dt
                self._weights[name] = self._weights.get(name, 0.0) + dt
        if isinstance(reference_w, (int, float)) and reference_w > 0:
            self.reference_w = float(reference_w)
        if isinstance(temp_c, (int, float)) and temp_c > 0:
            self.max_temp_c = max(self.max_temp_c or 0.0, float(temp_c))
        self.stutter_s += dt if stuttering else 0.0
        self.hot_s += dt if hot else 0.0

    def _avg(self, name: str) -> Optional[float]:
        weight = self._weights.get(name, 0.0)
        return round(self._sums[name] / weight, 1) if weight > 0 else None

    def summary(self) -> Optional[Dict[str, Any]]:
        if self.started is None or self.seconds < MIN_SESSION_S:
            return None
        tdp = self._avg("tdp")
        used = {m: t for m, t in self.mode_s.items() if t >= MIN_MODE_S}
        if not used and self.mode_s:
            top = max(self.mode_s, key=self.mode_s.get)
            used = {top: self.mode_s[top]}
        # Cap below the user's limit; a cap above it (Balanced/emergency) is no saving.
        saved_w = round(self.reference_w - tdp, 1) if self.reference_w and tdp else None
        saved_w = saved_w if saved_w and saved_w > 0 else None
        # Energy, not just watts: what the APU measurably drew below the user's limit over the time
        # played (the cap alone says what was allowed, not what was used); left out without a draw
        # sensor.  Battery minutes only when the battery's own discharge rate was measured.
        draw = self._avg("draw")
        draw_saved_w = self.reference_w - draw if self.reference_w and draw else None
        saved_wh = round(max(0.0, draw_saved_w or 0.0) * self.seconds / 3600.0, 2) or None
        battery = self._avg("battery")
        result = {
            "minutes": round(self.seconds / 60.0, 1),
            "avg_output_fps": self._avg("output"),
            "avg_real_fps": self._avg("real"),
            "avg_tdp_w": tdp,
            "avg_draw_w": draw,
            "reference_w": self.reference_w,
            "saved_w": saved_w,
            "saved_wh": saved_wh,
            "max_temp_c": round(self.max_temp_c, 0) if self.max_temp_c else None,
            "stutter_pct": round(100.0 * self.stutter_s / self.seconds),
            "hot_pct": round(100.0 * self.hot_s / self.seconds),
        }
        if used:
            result["modes"] = {m: round(t / 60.0, 1) for m, t in sorted(used.items(), key=lambda kv: -kv[1])}
            result["mode"] = next(iter(used)) if len(used) == 1 else "mixed"
        if self.frame_os_s:
            result["frame_os"] = {k: round(v / 60.0, 1) for k, v in sorted(self.frame_os_s.items(), key=lambda kv: -kv[1])}
        if self.benefit is not None:
            result["frame_os_benefit"] = dict(self.benefit)
        if saved_wh and battery and battery > 0:
            result["battery_minutes_gained"] = int(round(saved_wh / battery * 60.0))
        return result

    def finish(self) -> Optional[Dict[str, Any]]:
        result = self.summary()
        self.key = None
        self._reset()
        return result
