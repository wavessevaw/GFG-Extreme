"""Power Governor: the lowest TDP at which the game still holds its frame cap.

KEDAVRA holds the game at a base frame cap (the one Auto picked, the player's Custom cap, or
refresh / multiplier). Below the cap the game cannot run faster anyway, so watts above what it
needs to hold the cap only make heat. The Governor measures in 10 s windows and moves the
TDP (slowPPT/fastPPT, through steamos-manager or sysfs) one step at a time:

  healthy window (game at >= 97 % of the cap, pace >= 99.5 %, no ring misses, generation on
  budget, temperature fine)           -> 1 W lower (Battery, Balanced)
  unhealthy window                    -> 2 W higher at once, and the failed TDP is remembered
                                         so the next probes stop above it

Smoothness always wins: a window that fails is never answered with fewer watts. Quality never
probes down. Balanced keeps one extra watt above the lowest TDP that held. Without a cap (frame
generation off, or Auto still deciding) the Governor only watches.

Safety: the player's own TDP when the Governor took over is the ceiling and comes back when
the game ends or the plugin stops; a TDP changed outside GFG (Steam's slider) pauses the
Governor for the rest of the session; 90 C and above (where the APU starts to throttle) lowers
the ceiling 1 W per window, 97 C goes to the minimum at once.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

WINDOW_S = 10.0
SETTLE_S = 2.0
LEARN_AFTER_S = 60.0
STEP_DOWN_W = 1.0
STEP_UP_W = 2.0
SEVERE_RATIO = 0.85
BALANCED_MARGIN_W = 1.0
MIN_TDP_W = 4.0
HOT_C = 90.0
CRITICAL_C = 97.0
OBJECTIVES = ("battery", "balanced", "quality")


def healthy(window: List[Dict[str, Any]], cap: int, temp_ok: bool) -> Dict[str, Any]:
    """Verdict for one window of 1 s samples, with the reason a failed window failed."""
    n = len(window)
    if n == 0 or cap <= 0:
        return {"ok": None, "reason": "no-data"}
    real = sum(s.get("real") or 0.0 for s in window) / n
    paces = [s["pace"] for s in window if s.get("pace") is not None]
    pace = sum(paces) / len(paces) if paces else None
    over = sum(s.get("over_budget") or 0.0 for s in window) / n
    miss = sum(s.get("ring_miss") or 0.0 for s in window)
    out = {"real": round(real, 2), "pace": None if pace is None else round(pace, 4),
           "over_budget": round(over, 2), "ring_miss": miss}
    if real < 0.97 * cap:
        return {**out, "ok": False, "reason": "below-cap"}
    if pace is not None and pace < 0.995:
        return {**out, "ok": False, "reason": "pace"}
    if over >= 1.0:
        return {**out, "ok": False, "reason": "gpu-budget"}
    if miss > 0:
        return {**out, "ok": False, "reason": "ring-miss"}
    if not temp_ok:
        return {**out, "ok": False, "reason": "thermal"}
    return {**out, "ok": True, "reason": "holds"}


class PowerGovernor:
    def __init__(self, actuator: Any, model: Any, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.actuator = actuator
        self.model = model
        self.clock = clock
        self.journal = journal
        self.enabled = True
        self._reset_session()

    def _reset_session(self) -> None:
        self.key: Optional[str] = None
        self.objective = "balanced"
        self.owned = False
        self.paused = ""  # reason the Governor stopped for this session
        self.tdp: Optional[float] = None
        self.ceiling: Optional[float] = None
        self.thermal_ceiling: Optional[float] = None
        self.floor_fail: Dict[int, float] = {}  # cap -> highest TDP at which it failed
        self.lowest_ok: Optional[float] = None
        self.hold = False
        self.window: List[Dict[str, Any]] = []
        self.window_start = 0.0
        self.changed_at = -1e9
        self.healthy_since: Optional[float] = None
        self.epoch = -1
        self.cap = 0
        self.last: Dict[str, Any] = {}
        self.learned = False

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    # ------------------------------------------------------------------ session
    def stop(self, reason: str = "session-end") -> Dict[str, Any]:
        result: Dict[str, Any] = {"restored": False}
        if self.owned:
            result = self.actuator.restore_if_owned()
            self._note("governor-restore", reason=reason, restored=result.get("restored"), error=result.get("error"))
        self._reset_session()
        return result

    def _limits(self) -> Dict[str, Optional[float]]:
        st = self.actuator.status()
        low = max(MIN_TDP_W, float(st.get("minimum_tdp_w") or 0.0))
        return {"low": low, "ceiling": st.get("initial_tdp_w") or st.get("ceiling_tdp_w"), "draw": st.get("draw_w")}

    def _start(self, key: str, objective: str) -> None:
        claim = self.actuator.claim()
        if not claim.get("owned"):
            self.paused = claim.get("error") or "TDP control is not available"
            self._note("governor-unavailable", error=self.paused)
            return
        self.owned = True
        self.key = key
        self.objective = objective
        lim = self._limits()
        self.ceiling = float(lim["ceiling"] or 15.0)
        self.tdp = self.ceiling
        failures = self.model.floor_failures(key) if self.model else {}
        for point, (tdp, _age, _n) in failures.items():
            if point.startswith("cap") and point[3:].isdigit():
                self.floor_fail[int(point[3:])] = tdp
        self._note("governor-start", key=key, objective=objective, ceiling_w=self.ceiling)

    def _warm_start(self, cap: int) -> None:
        """A point that held before starts one watt above the TDP it held at."""
        learned = self.model.get(f"{self.key}|cap{cap}") if self.model else None
        if self.objective != "quality" and learned and learned.get("tdp_w") and self.ceiling:
            self._write(min(self.ceiling, float(learned["tdp_w"]) + 1.0), "warm-start")

    def _write(self, watts: float, why: str) -> bool:
        lim = self._limits()
        ceiling = min(x for x in (self.ceiling, self.thermal_ceiling) if x is not None)
        target = round(max(lim["low"] or MIN_TDP_W, min(ceiling, watts)), 1)
        if self.tdp is not None and abs(target - self.tdp) < 0.05:
            return False
        result = self.actuator.set_tdp_w(target)
        if not result.get("success"):
            state = result.get("state") or {}
            if state.get("external_change"):
                self._pause("TDP changed outside GFG Extreme (Steam's slider?): the Governor stays off for this game")
            else:
                self._note("governor-write-failed", watts=target, error=result.get("error"))
            return False
        self._note("governor-tdp", watts=target, was=self.tdp, why=why)
        self.tdp = target
        self.changed_at = self.clock()
        self.window = []
        return True

    def _pause(self, reason: str) -> None:
        self.paused = reason
        self.owned = False
        self._note("governor-paused", reason=reason)

    # ------------------------------------------------------------------ tick
    def tick(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """One second. sample: key (game|refresh|objective), objective, cap (the locked point,
        0 = none), hold_ceiling, epoch, real, pace, over_budget, ring_miss (per second), temp_c,
        game (bool: a game is running)."""
        now = self.clock()
        if not self.enabled or not sample.get("game"):
            if self.owned or self.key:
                self.stop("no-game" if self.enabled else "disabled")
            return self.status()
        key = str(sample.get("key") or "")
        objective = sample.get("objective") if sample.get("objective") in OBJECTIVES else "balanced"
        if key != self.key:
            if self.owned:
                self.stop("context-change")
            self._reset_session()
            self.key = key
            if self.enabled:
                self._start(key, objective)
            self.window_start = now
        if objective != self.objective and self.owned:
            self.objective = objective
            self.window = []
            self.window_start = now
            if objective == "quality":
                self._write(self.ceiling or 15.0, "quality")
        if self.paused or not self.owned:
            return self.status()
        if self.actuator.verify_ownership().get("external_change"):
            self._pause("TDP changed outside GFG Extreme (Steam's slider?): the Governor stays off for this game")
            return self.status()

        temp = sample.get("temp_c")
        if temp is not None and temp >= CRITICAL_C:
            self.thermal_ceiling = self._limits()["low"]
            self._write(self.thermal_ceiling or MIN_TDP_W, "critical-temperature")
            return self.status()
        if sample.get("hold_ceiling"):
            # The pilot measures the game or tries a higher point: full power, no verdicts.
            self.hold = True
            self._write(self.ceiling or 15.0, "pilot-measures")
            self.window, self.window_start, self.healthy_since = [], now, None
            return self.status()
        self.hold = False
        cap = int(sample.get("cap") or 0)
        if sample.get("epoch") != self.epoch or cap != self.cap:
            if cap != self.cap and cap > 0:
                self.learned = False
                self._warm_start(cap)
            self.epoch = sample.get("epoch")
            self.cap = cap
            self.window = []
            self.window_start = now
            self.healthy_since = None
        if self.cap <= 0:
            self.window = []
            self.window_start = now
            self.last = {"ok": None, "reason": "no-cap"}
            return self.status()
        if now - self.changed_at < SETTLE_S:
            self.window_start = now
            return self.status()
        self.window.append(sample)
        if now - self.window_start < WINDOW_S:
            return self.status()
        temp_ok = temp is None or temp < HOT_C
        verdict = healthy(self.window, self.cap, temp_ok)
        self.window = []
        self.window_start = now
        self.last = verdict
        self._decide(now, verdict, temp)
        return self.status()

    def _decide(self, now: float, verdict: Dict[str, Any], temp: Optional[float]) -> None:
        assert self.tdp is not None and self.ceiling is not None
        if temp is not None and temp >= HOT_C:
            # Too hot: the ceiling comes down a watt per window until it cools.
            self.thermal_ceiling = max(self._limits()["low"] or MIN_TDP_W, (self.thermal_ceiling or self.tdp) - 1.0)
            self._write(self.tdp, "hot")
            return
        if self.thermal_ceiling is not None and temp is not None and temp < HOT_C - 5:
            self.thermal_ceiling = None
        if verdict["ok"] is False:
            self.healthy_since = None
            if verdict["reason"] in ("below-cap", "pace", "gpu-budget", "ring-miss"):
                if self.tdp < self.ceiling:
                    self.floor_fail[self.cap] = max(self.floor_fail.get(self.cap, 0.0), self.tdp)
                    if self.model:
                        self.model.record_floor_failure(self.key, f"cap{self.cap}", self.tdp)
                # Insurance: a clear shortfall goes back to full power at once.
                severe = verdict.get("real", 0.0) < SEVERE_RATIO * self.cap
                self._write(self.ceiling if severe else self.tdp + STEP_UP_W,
                            f"window-failed:{verdict['reason']}" + (":severe" if severe else ""))
            return
        if verdict["ok"] is not True:
            return
        self.lowest_ok = self.tdp if self.lowest_ok is None else min(self.lowest_ok, self.tdp)
        if self.healthy_since is None:
            self.healthy_since = now
        if not self.learned and now - self.healthy_since >= LEARN_AFTER_S and self.model:
            self.learned = bool(self.model.record(f"{self.key}|cap{self.cap}", "tdp", self.tdp))
        if self.objective == "quality":
            return
        floor = self.floor_fail.get(self.cap, 0.0) + (1.0 if self.objective == "battery" else 1.0 + BALANCED_MARGIN_W)
        target = self.tdp - STEP_DOWN_W
        if target < floor:
            return
        if self._write(target, "window-held"):
            self.healthy_since = None
            self.learned = False

    def at_ceiling(self) -> bool:
        """Nothing left to raise: the TDP is at its ceiling, or the Governor does not manage it."""
        if not self.owned or self.paused or self.tdp is None or self.ceiling is None:
            return True
        ceiling = min(x for x in (self.ceiling, self.thermal_ceiling) if x is not None)
        return self.tdp >= ceiling - 0.05

    def status(self) -> Dict[str, Any]:
        act = self.actuator.status() if self.actuator else {}
        return {
            "enabled": self.enabled,
            "owned": self.owned,
            "paused": self.paused,
            "objective": self.objective,
            "managing": bool(self.owned and self.cap > 0 and not self.paused),
            "tdp_w": self.tdp,
            "ceiling_w": self.ceiling,
            "thermal_ceiling_w": self.thermal_ceiling,
            "floor_fail_w": self.floor_fail.get(self.cap),
            "hold": self.hold,
            "at_ceiling": self.at_ceiling(),
            "cap": self.cap,
            "window": self.last,
            "draw_w": act.get("draw_w"),
            "method": act.get("method"),
        }
