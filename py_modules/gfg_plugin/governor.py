"""Power Governor: the lowest TDP at which the game still holds its frame cap.

KEDAVRA holds the game at a base frame cap (the one Auto picked, the player's Custom cap, or
refresh / multiplier). Below the cap the game cannot run faster anyway, so watts above what it
needs to hold the cap only make heat. GFG 2.x's rule, "up fast, down carefully, all session
long", drives the TDP (slowPPT/fastPPT, through steamos-manager or sysfs):

  start      Battery 10 W, Balanced 12 W (or one watt above what held last time), Quality the
             player's TDP. The pilot's measurement and trials run at the player's TDP.
  down       an 8 s window that holds (game at >= 97 % of the cap, pace >= 99 %, no ring misses,
             generation on budget, temperature fine) steps down. The step follows the headroom:
             when the APU draws clearly less than the limit, the limit goes straight to the draw
             plus a margin; before the first failure of a session 2 W per 5 s window, then 1 W.
  up fast    every second: the last 3 s short of the cap while the draw sits at the limit (the
             limit is what holds the game back) -> the last level that held at once, or +2 W
             (+3 W when far short). A step that failed is a floor for this point that expires
             (5 min, doubling to 30 min when the same level fails again).
  re-probe   held floors expire, so a lighter scene gets its watts back down later.

Smoothness always wins: a window that fails is never answered with fewer watts. Quality never
probes down. Balanced keeps one extra watt above the lowest TDP that failed. Without a cap
(frame generation off, or Auto still deciding) the Governor only watches. While Power Split or
the GPU clock ceiling tries a step ("experiment"), the TDP does not probe down.

Safety: the player's own TDP when the Governor took over is the ceiling and comes back when
the game ends or the plugin stops; a TDP changed outside GFG (Steam's slider) pauses the
Governor for the rest of the session; 90 C and above (where the APU starts to throttle) lowers
the ceiling 1 W per window, 97 C goes to the minimum at once, and the ceiling comes back after
30 s under 85 C.
"""
from __future__ import annotations

import math
import statistics
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

WINDOW_S = 8.0
FAST_WINDOW_S = 5.0
SETTLE_S = 2.0
LEARN_AFTER_S = 60.0
STEP_DOWN_W = 1.0
FAST_STEP_W = 2.0
# Autopilot (user, 3.0.4): starts at 15 W and measures; tolerates 8-10 % dips of the game's
# frame rate (watts come back only for a deeper fall); targets 12 W, ideally 9-10 W.
START_W = {"battery": 10.0, "balanced": 12.0, "autopilot": 15.0}
HOLD_RATIO = {"autopilot": 0.92}          # window mean vs cap that still holds (default 0.97)
SHORT_RATIO = {"autopilot": 0.90}         # fast guard: under this share of the cap -> watts back
# Autopilot: a short sharp drop is no reason for watts (user, 3.0.4). The fast guard needs the
# drop to last: 5 of the last 6 seconds short; windows judge the median, not the mean.
SUSTAIN_S = 6
# 2.1.6's p5 rule: a window steps down only while its low end (p5 of the 1 s readings) stays near
# the cap. A dip that deep is no reason for watts, but no reason to take more away either.
P5_RATIO = {"autopilot": 0.85, "battery": 0.85}   # default 0.90
DRAW_MARGIN_W = 1.5          # limit kept above the measured draw when jumping down to it
DRAW_JUMP_W = 3.0            # draw this far under the limit: the limit is not what holds the game
DRAW_BINDING_W = 1.2         # draw this close to the limit: the limit is what holds the game
FAST_SHORT_RATIO = 0.92      # last 3 s under this share of the cap ...
FAST_GAP_S = 3.0             # ... raise, at most once per this many seconds
STEP_UP_W = 2.0
SEVERE_RATIO = 0.85
SEVERE_STEP_W = 3.0
FLOOR_BACKOFF_S = 300.0      # a level that failed is not tried again for this long ...
FLOOR_BACKOFF_MAX_S = 1800.0  # ... doubling on each repeat up to this
PACE_MIN = 0.99              # the pilot locks points at the same pace
COVERAGE = 0.6               # share of a window's seconds with a real-frame reading
BALANCED_MARGIN_W = 1.0
MIN_TDP_W = 4.0
HOT_C = 90.0
COOL_C = 85.0
COOL_S = 30.0
CRITICAL_C = 97.0
# Plugging or unplugging the charger makes SteamOS put its own TDP for that power source back.
# That is not the player moving the slider: an outside change this close to a charger change is
# taken over again (its value becomes the new ceiling) instead of pausing the Governor.
AC_GRACE_S = 15.0
# Autopilot (Deck report 3.0.7: 18 W, x3.75, 80+ C): never above 15 W, even when SteamOS's TDP
# was higher at the start (Steam's limit off). From 80 C it is "warm": the pilot does not climb
# above its point (no watts for a higher one) until 30 s under 75 C.
AUTOPILOT_MAX_W = 15.0
WARM_C = {"autopilot": 80.0}
WARM_COOL_C = 75.0
EXTERNAL_WAIT_S = 10.0       # an outside change waits this long for the charger to show up
OBJECTIVES = ("battery", "balanced", "quality", "autopilot")


def healthy(window: List[Dict[str, Any]], cap: int, temp_ok: bool, hold: float = 0.97,
            median: bool = False) -> Dict[str, Any]:
    """Verdict for one window of 1 s samples, with the reason a failed window failed. A missing
    pace is allowed (no generation running); a non-finite reading is broken telemetry."""
    n = len(window)
    if any(isinstance(s.get(k), float) and not math.isfinite(s[k]) for s in window for k in ("real", "pace")):
        return {"ok": None, "reason": "incomplete-telemetry"}
    reals = [s["real"] for s in window if s.get("real") is not None]
    if n == 0 or cap <= 0 or len(reals) < max(1, COVERAGE * n):
        return {"ok": None, "reason": "no-data"}
    real = statistics.median(reals) if median else sum(reals) / len(reals)
    paces = [s["pace"] for s in window if s.get("pace") is not None]
    pace = sum(paces) / len(paces) if paces else None
    over = sum(s.get("over_budget") or 0.0 for s in window) / n
    miss = sum(s.get("ring_miss") or 0.0 for s in window)
    p5 = sorted(reals)[int(0.05 * len(reals))]
    out = {"real": round(real, 2), "low": round(min(reals), 2), "p5": round(p5, 2), "pace": None if pace is None else round(pace, 4),
           "over_budget": round(over, 2), "ring_miss": miss}
    if real < hold * cap:
        return {**out, "ok": False, "reason": "below-cap"}
    if pace is not None and pace < PACE_MIN:
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
        self.restore_pending = False
        self.ac: Optional[bool] = None
        self.ac_changed_at = -1e9
        self._reset_session()

    def _reset_session(self) -> None:
        self.key: Optional[str] = None
        self.objective = "balanced"
        self.owned = False
        self.paused = ""  # reason the Governor stopped for this session
        self.external_at: Optional[float] = None  # an outside TDP change seen, not yet explained
        self.tdp: Optional[float] = None
        self.ceiling: Optional[float] = None
        self.player_ceiling: Optional[float] = None   # SteamOS's TDP when the Governor took over
        self.thermal_ceiling: Optional[float] = None
        self.cool_since: Optional[float] = None
        self.warm = False                             # Autopilot from 80 C: no climbing
        self.warm_cool_since: Optional[float] = None
        # cap -> (TDP that failed, until, repeats): no probe at or below that TDP until then
        self.floors: Dict[int, Tuple[float, float, int]] = {}
        self.last_good: Dict[int, float] = {}   # cap -> lowest TDP that held a whole window
        self.lowest_ok: Optional[float] = None
        self.held_at_tdp = False                # a window held since the last TDP write
        self.dips = False                       # the last held window dipped under the p5 line
        self.probe_from: Optional[float] = None  # the level a step down came from (until it holds)
        self.hold = False
        self.window: List[Dict[str, Any]] = []
        self.window_start = 0.0
        self.recent: Deque[Optional[float]] = deque(maxlen=SUSTAIN_S)
        self.started: set = set()
        self.fast_at = -1e9
        self.changed_at = -1e9
        self.healthy_since: Optional[float] = None
        self.epoch: Any = -1
        self.cap = 0
        self.last: Dict[str, Any] = {}
        self.learned = False
        self.fast = True

    @property
    def floor_fail(self) -> Dict[int, float]:
        """Active floors (cap -> the TDP that failed), for status and tests."""
        now = self.clock()
        return {c: f[0] for c, f in self.floors.items() if now < f[1]}

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
        if result.get("success") is False or result.get("error"):
            # The player's TDP is still owed: retried every tick, no new claim until it is back.
            self.restore_pending = True
            self.window = []
            return result
        self.restore_pending = False
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
        self.player_ceiling = float(lim["ceiling"] or 15.0)
        self.ceiling = self._ceiling_for(objective)
        self.tdp = self.player_ceiling
        if self.ceiling < self.tdp - 0.05:
            self._write(self.ceiling, "autopilot-ceiling")
        now = self.clock()
        failures = self.model.floor_failures(key) if self.model else {}
        for point, (tdp, age, n) in failures.items():
            if point.startswith("cap") and point[3:].isdigit():
                left = min(FLOOR_BACKOFF_MAX_S, FLOOR_BACKOFF_S * 2 ** (max(1, n) - 1)) - age
                if left > 0:
                    self.floors[int(point[3:])] = (float(tdp), now + left, max(1, n))
        self._note("governor-start", key=key, objective=objective, ceiling_w=self.ceiling)

    def _top(self) -> float:
        """The highest TDP allowed now: the session ceiling, lowered by heat."""
        return min(x for x in (self.ceiling, self.thermal_ceiling) if x is not None)

    def _ceiling_for(self, objective: str) -> float:
        player = self.player_ceiling or 15.0
        return min(player, AUTOPILOT_MAX_W) if objective == "autopilot" else player

    def _first_level(self, cap: int) -> None:
        """The first TDP at a point: what held last time plus a watt, else the objective's start."""
        if self.objective == "quality" or not self.ceiling:
            return
        learned = self.model.get(f"{self.key}|cap{cap}") if self.model else None
        if learned and learned.get("tdp_w"):
            target, why = float(learned["tdp_w"]) + 1.0, "warm-start"
        elif (self.key, self.objective) not in self.started:
            # A fresh game starts low; later unknown points keep the level the session reached.
            target, why = START_W.get(self.objective, self.ceiling), "start-level"
        else:
            return
        self.started.add((self.key, self.objective))
        floor = self._floor(cap)
        target = max(target, floor) if floor else target
        if target < self.ceiling - 0.05:
            self.probe_from = self.ceiling
            self._write(target, why)

    def _floor(self, cap: int) -> float:
        """The lowest TDP a probe may try at this point (0 = none)."""
        f = self.floors.get(cap)
        if not f or self.clock() >= f[1]:
            return 0.0
        return f[0] + (1.0 + BALANCED_MARGIN_W if self.objective == "balanced" else 1.0)

    def _failed(self, cap: int, tdp: float) -> None:
        """A step to ``tdp`` did not hold: a floor that expires, longer when it repeats."""
        prev = self.floors.get(cap)
        n = prev[2] + 1 if prev and abs(prev[0] - tdp) < 0.55 else 1
        backoff = min(FLOOR_BACKOFF_MAX_S, FLOOR_BACKOFF_S * 2 ** (n - 1))
        self.floors[cap] = (tdp, self.clock() + backoff, n)
        if self.model:
            self.model.record_floor_failure(self.key, f"cap{cap}", tdp, count=n)
        self._note("governor-floor", cap=cap, tdp=tdp, repeats=n, backoff_s=backoff)

    def _write(self, watts: float, why: str) -> bool:
        lim = self._limits()
        ceiling = self._top()
        target = round(max(lim["low"] or MIN_TDP_W, min(ceiling, watts)), 1)
        if self.tdp is not None and abs(target - self.tdp) < 0.05:
            return False
        result = self.actuator.set_tdp_w(target)
        if not result.get("success"):
            state = result.get("state") or {}
            if state.get("external_change"):
                self.owned = False
                self.external_at = self.clock() if self.external_at is None else self.external_at
            else:
                self._note("governor-write-failed", watts=target, error=result.get("error"))
            return False
        self._note("governor-tdp", watts=target, was=self.tdp, why=why)
        self.tdp = target
        self.held_at_tdp = False
        self.changed_at = self.clock()
        self.window = []
        return True

    def _external(self, now: float) -> bool:
        """An outside TDP change: SteamOS's own after a charger change (take over again, its
        value is the new ceiling), else the player's (pause for this game). True while waiting."""
        observed = self.actuator.status().get("observed_tdp_w")
        steamos = (isinstance(observed, (int, float)) and self.player_ceiling is not None
                   and abs(observed - self.player_ceiling) < 0.55)
        if now - self.ac_changed_at <= AC_GRACE_S or steamos:
            # A charger change, or SteamOS putting its own TDP back (after sleep or a game start:
            # the very value it had when the Governor took over), not the player's slider.
            was = self.tdp
            self.external_at = None
            claim = self.actuator.claim()
            if not claim.get("owned"):
                self._pause(claim.get("error") or "TDP control is not available")
                return True
            self.owned = True
            self.player_ceiling = float(self._limits()["ceiling"] or self.player_ceiling or 15.0)
            self.ceiling = self._ceiling_for(self.objective)
            self.tdp = self.player_ceiling
            self._note("governor-reclaimed", reason="steamos-restore" if steamos else "power-source", ac=self.ac,
                       ceiling_w=self.ceiling, was=was)
            if was is not None and was < self.ceiling - 0.05 and self.objective != "quality":
                self._write(was, "power-source")   # keep the level the session had reached
            elif self.ceiling < self.tdp - 0.05:
                self._write(self.ceiling, "autopilot-ceiling")
            self.window, self.window_start = [], now
            return False
        if now - self.external_at < EXTERNAL_WAIT_S:
            return True
        self.external_at = None
        self._pause("TDP changed outside GFG Extreme (Steam's slider?): the Governor stays off for this game")
        return True

    def _pause(self, reason: str) -> None:
        self.paused = reason
        self.owned = False
        self._note("governor-paused", reason=reason)

    # ------------------------------------------------------------------ tick
    def tick(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """One second. sample: key (game|refresh|objective), objective, cap (the locked point,
        0 = none), hold_ceiling, epoch, real, pace, over_budget, ring_miss (per second), temp_c,
        draw_w, experiment (Power Split / GPU clock trying a step), game (bool)."""
        now = self.clock()
        ac = sample.get("ac")
        if isinstance(ac, bool):
            if self.ac is not None and ac != self.ac:
                self.ac_changed_at = now
                self._note("governor-power-source", ac=ac)
            self.ac = ac
        if self.restore_pending:
            self.stop("retry-restore")
            if self.restore_pending:
                return self.status()
        if not self.enabled or not sample.get("game"):
            if self.owned or self.key:
                self.stop("no-game" if self.enabled else "disabled")
            return self.status()
        key = str(sample.get("key") or "")
        objective = sample.get("objective") if sample.get("objective") in OBJECTIVES else "balanced"
        if key != self.key:
            if self.owned:
                self.stop("context-change")
                if self.restore_pending:
                    return self.status()
            self._reset_session()
            self.key = key
            if self.enabled:
                self._start(key, objective)
            self.window_start = now
        if objective != self.objective and self.owned:
            self.objective = objective
            self.ceiling = self._ceiling_for(objective)
            if self.tdp is not None and self.tdp > self.ceiling + 0.05:
                self._write(self.ceiling, "autopilot-ceiling")
            if objective not in WARM_C:
                self.warm, self.warm_cool_since = False, None
            self.window = []
            self.window_start = now
            if objective == "quality":
                self._write(self.ceiling or 15.0, "quality")
            elif self.cap > 0:
                self._first_level(self.cap)
        if self.external_at is None and self.owned and self.actuator.verify_ownership().get("external_change"):
            self.owned = False
            self.external_at = now
        if self.external_at is not None and not self.paused:
            if self._external(now):
                return self.status()
        if self.paused or not self.owned:
            return self.status()

        temp = sample.get("temp_c")
        if self._thermal(now, temp):
            return self.status()
        if sample.get("hold_ceiling"):
            # The pilot measures the game or tries a higher point: full power, no verdicts.
            self.hold = True
            self._write(self.ceiling or 15.0, "pilot-measures")
            self.window, self.window_start, self.healthy_since = [], now, None
            self.recent.clear()
            self.probe_from = None
            return self.status()
        self.hold = False
        cap = int(sample.get("cap") or 0)
        if sample.get("epoch") != self.epoch or cap != self.cap:
            first = cap > 0 and cap != self.cap
            self.epoch = sample.get("epoch")
            self.cap = cap
            self.window = []
            self.window_start = now
            self.healthy_since = None
            self.recent.clear()
            if first:
                self.learned = False
                self._first_level(cap)
        if self.cap <= 0:
            self.window = []
            self.window_start = now
            self.last = {"ok": None, "reason": "no-cap"}
            return self.status()
        real = sample.get("real")
        self.recent.append(None if real is None else float(real))
        if self._fast_guard(now, sample):
            return self.status()
        if self._probing(sample):
            # Its A/B windows need a fixed TDP; our own verdict starts over once it is done.
            self.window, self.window_start = [], now
            return self.status()
        if now - self.changed_at < SETTLE_S:
            self.window_start = now
            return self.status()
        self.window.append(sample)
        if now - self.window_start < (FAST_WINDOW_S if self.fast else WINDOW_S):
            return self.status()
        temp_ok = temp is None or temp < HOT_C
        verdict = healthy(self.window, self.cap, temp_ok, HOLD_RATIO.get(self.objective, 0.97),
                          median=self.objective == "autopilot")
        if len(self.window) < COVERAGE * (now - self.window_start):
            verdict = {"ok": None, "reason": "no-data"}   # missed ticks: too few seconds were seen
        draws = [s["draw_w"] for s in self.window if isinstance(s.get("draw_w"), (int, float))]
        verdict["draw"] = round(statistics.median(draws), 2) if draws else None
        self.window = []
        self.window_start = now
        self.last = verdict
        self._decide(now, verdict, temp, self._probing(sample))
        return self.status()

    def _thermal(self, now: float, temp: Optional[float]) -> bool:
        """True when the temperature decided this second."""
        if temp is None:
            self.cool_since = None
            return False
        if temp >= CRITICAL_C:
            self.thermal_ceiling = self._limits()["low"]
            self.cool_since = None
            self._write(self.thermal_ceiling or MIN_TDP_W, "critical-temperature")
            return True
        warm = WARM_C.get(self.objective)
        if warm is not None:
            if temp >= warm:
                self.warm_cool_since = None
                if not self.warm:
                    self.warm = True
                    self._note("governor-warm", temp_c=temp, tdp_w=self.tdp)
            elif self.warm and temp < WARM_COOL_C:
                if self.warm_cool_since is None:
                    self.warm_cool_since = now
                elif now - self.warm_cool_since >= COOL_S:
                    self.warm, self.warm_cool_since = False, None
                    self._note("governor-cooled", temp_c=temp, warm=True)
            elif temp >= WARM_COOL_C:
                self.warm_cool_since = None
        if temp < COOL_C and self.thermal_ceiling is not None:
            if self.cool_since is None:
                self.cool_since = now
            elif now - self.cool_since >= COOL_S:
                self.thermal_ceiling = None
                self.cool_since = None
                self._note("governor-cooled", temp_c=temp)
                if self.objective == "quality":
                    self._write(self.ceiling or 15.0, "cooled")
        elif temp >= COOL_C:
            self.cool_since = None
        return False

    def _binding(self, draw: Any) -> bool:
        """The limit is what holds the game: the draw sits at it (unknown draw counts as yes)."""
        if not isinstance(draw, (int, float)) or self.tdp is None:
            return True
        return float(draw) >= self.tdp - DRAW_BINDING_W

    @staticmethod
    def _probing(sample: Dict[str, Any]) -> bool:
        """Power Split or the GPU clock ceiling is trying a step: the TDP stays where it is."""
        return bool(sample.get("experiment") or sample.get("probe_active"))

    def _fast_guard(self, now: float, sample: Dict[str, Any]) -> bool:
        """Up fast: the last 3 s short of the cap at a binding limit get watts back at once."""
        n = SUSTAIN_S if self.objective == "autopilot" else 3
        last = list(self.recent)[-n:]
        if self.tdp is None or self.ceiling is None or len(last) < n or None in last:
            return False
        ceiling = self._top()
        if self.tdp >= ceiling - 0.05 or now - self.fast_at < FAST_GAP_S:
            return False
        # Autopilot: the second-best of 6 s (5 of 6 short); the modes: the median of 3 s.
        med = sorted(last)[-2] if n == SUSTAIN_S else statistics.median(last)  # type: ignore[arg-type]
        if med >= SHORT_RATIO.get(self.objective, FAST_SHORT_RATIO) * self.cap or not self._binding(sample.get("draw_w")):
            return False
        severe = med < SEVERE_RATIO * self.cap
        if self.probe_from is not None and now - self.changed_at < 30.0:
            # The step down did not hold: back to where it came from, and a floor at this level.
            self._failed(self.cap, self.tdp)
            target, why = self.probe_from, "fast-restore"
        elif severe:
            target, why = ceiling, "fast-severe"   # a collapse, not a shortfall: full power now
        else:
            target, why = self.tdp + STEP_UP_W, "fast-raise"
        self.fast = False
        self.probe_from = None
        self.fast_at = now
        self.healthy_since = None
        self.recent.clear()
        self._write(target, f"{why}:{med:.0f}/{self.cap}")
        return True

    def _decide(self, now: float, verdict: Dict[str, Any], temp: Optional[float], experiment: bool = False) -> None:
        assert self.tdp is not None and self.ceiling is not None
        if temp is not None and temp >= HOT_C:
            # Too hot: the ceiling comes down a watt per window until it cools.
            self.thermal_ceiling = max(self._limits()["low"] or MIN_TDP_W, (self.thermal_ceiling or self.tdp) - 1.0)
            self._write(self.tdp, "hot")
            return
        if verdict["ok"] is False:
            self.healthy_since = None
            self.fast = False
            if verdict["reason"] in ("below-cap", "pace", "gpu-budget", "ring-miss"):
                severe = verdict.get("real", 0.0) < SEVERE_RATIO * self.cap
                if self.probe_from is not None:
                    # The last step down did not hold a whole window: back up, a floor here.
                    self._failed(self.cap, self.tdp)
                    target = max(self.probe_from, self.tdp + STEP_UP_W)
                else:
                    target = self.tdp + (SEVERE_STEP_W if severe else STEP_UP_W)
                self.probe_from = None
                self._write(target, f"window-failed:{verdict['reason']}" + (":severe" if severe else ""))
            return
        if verdict["ok"] is not True:
            return
        # The level holds a whole window.
        if self.probe_from is not None:
            self.probe_from = None
            prev = self.floors.get(self.cap)
            if prev and self.tdp <= prev[0] and self.model:
                self.model.record_floor_failure(self.key, f"cap{self.cap}", None)  # lighter now
        self.last_good[self.cap] = min(self.last_good.get(self.cap, self.tdp), self.tdp)
        self.lowest_ok = self.tdp if self.lowest_ok is None else min(self.lowest_ok, self.tdp)
        self.held_at_tdp = True
        if self.healthy_since is None:
            self.healthy_since = now
        if not self.learned and now - self.healthy_since >= LEARN_AFTER_S and self.model:
            self.learned = bool(self.model.record(f"{self.key}|cap{self.cap}", "tdp", self.tdp))
        if self.objective == "quality" or experiment:
            return
        dips = verdict.get("p5", self.cap) < P5_RATIO.get(self.objective, 0.90) * self.cap
        if dips != self.dips:
            self.dips = dips
            if dips:
                self._note("governor-dips", tdp_w=self.tdp, p5=verdict.get("p5"), cap=self.cap)
        if dips:
            return
        floor = self._floor(self.cap) or self._limits()["low"] or MIN_TDP_W
        draw = verdict.get("draw")
        step = FAST_STEP_W if self.fast else STEP_DOWN_W
        target = self.tdp - step
        if isinstance(draw, (int, float)) and self.tdp - draw >= DRAW_JUMP_W:
            # The game uses clearly less than the limit: the limit goes to what it draws.
            target = min(target, draw + DRAW_MARGIN_W)
        target = max(target, floor)
        if target > self.tdp - 0.45:
            return
        frm = self.tdp
        if self._write(target, "window-held"):
            self.probe_from = frm
            self.healthy_since = None
            self.learned = False

    def settled(self) -> bool:
        """Holding a point with no TDP step for two windows: other experiments (Power Split)
        may run now without mixing into a Governor trial."""
        return bool(self.owned and not self.paused and not self.hold and self.cap > 0 and self.probe_from is None
                    and self.last.get("ok") is True and self.clock() - self.changed_at >= 2 * WINDOW_S)

    def at_ceiling(self) -> bool:
        """Nothing left to raise: the TDP is at its ceiling, or the Governor does not manage it."""
        if not self.owned or self.paused or self.tdp is None or self.ceiling is None:
            return True
        ceiling = self._top()
        return self.tdp >= ceiling - 0.05

    def status(self) -> Dict[str, Any]:
        act = self.actuator.status() if self.actuator else {}
        return {
            "enabled": self.enabled,
            "owned": self.owned,
            "restore_pending": self.restore_pending,
            "paused": self.paused,
            "objective": self.objective,
            "managing": bool(self.owned and self.cap > 0 and not self.paused),
            "tdp_w": self.tdp,
            "ceiling_w": self.ceiling,
            "thermal_ceiling_w": self.thermal_ceiling,
            "warm": self.warm,
            "floor_fail_w": self.floor_fail.get(self.cap),
            "probing": self.probe_from is not None,
            "dips": self.dips,
            "hold": self.hold,
            "at_ceiling": self.at_ceiling(),
            "settled": self.settled(),
            "cap": self.cap,
            "window": self.last,
            "draw_w": act.get("draw_w"),
            "observed_tdp_w": act.get("observed_tdp_w"),
            "method": act.get("method"),
        }
