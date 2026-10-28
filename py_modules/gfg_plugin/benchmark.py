"""Benchmark (3.3.0): 20 seconds in game at the 15 W ceiling with generation off.

The medians of the game's own frame rate, GPU and CPU load, power and temperature give a
starting strategy (base cap, multiplier, expected watts). Accepted, it is stored per game: the
next launches start there and Autopilot uses it as its compass, still adapting to heavier and
lighter scenes. Declined, Autopilot keeps searching as usual.

The run is cancelled by the Steam menu, a paused game (no frames), a game change or leaving the
game: those seconds are not the game's medians.
"""
from __future__ import annotations

import statistics
import time
from typing import Any, Callable, Dict, List, Optional

from .pilot import BAND_MAX_W, TRIAL_RATIO, capped, ladder, lowest_point, mult_label

DURATION_S = 20.0
SETTLE_S = 3.0          # after the Quick Access menu closes and the TDP reaches the ceiling
SETTLE_MAX_S = 10.0     # the ceiling not reached by then (a TDP GFG does not manage): measure anyway
WAIT_MAX_S = 60.0       # the Quick Access menu still open after this: the run is called off
NO_FRAMES_S = 5.0       # no reading of the game's frame rate this long while measuring
DONE_SHOW_S = 5.0       # the in-game "done" panel
FG_COST = 0.92          # the game keeps about 92 % of its frame rate with generation on
PAUSED_FPS = 3.0
IDLE_W = 4.0            # Deck draw with the game near idle, for the watts estimate


def _median(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if isinstance(x, (int, float))]
    return float(statistics.median(xs)) if xs else None


class Benchmark:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.reset()

    def reset(self) -> None:
        # idle | waiting (for the Quick Access menu to close; nothing changes yet) | settling
        # (generation off, TDP to the ceiling) | running | done | cancelled
        self.state = "idle"
        self.app: Optional[int] = None
        self.refresh = 90
        self.since = 0.0
        self.ended = 0.0
        self.samples: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.reason = ""
        self.seen = 0.0

    # ------------------------------------------------------------------ control
    def start(self, app: Optional[int], game: bool) -> Dict[str, Any]:
        if not game or not app:
            return {"ok": False, "error": "Start a game first: the benchmark measures it in game."}
        self.reset()
        self.state, self.app, self.since = "waiting", app, self.clock()
        return {"ok": True}

    def answer(self, accept: bool) -> Optional[Dict[str, Any]]:
        """The result to store when accepted (None when declined or nothing to answer). Declining
        also cancels a run that has not finished."""
        if self.state != "done" or not self.result:
            if not accept:
                self.reset()
            return None
        res = self.result if accept else None
        self.reset()
        return res

    @property
    def measuring(self) -> bool:
        """The plugin holds generation off and the TDP at the ceiling (not while it waits for the
        Quick Access menu: the game keeps the player's settings until the run really starts)."""
        return self.state in ("settling", "running")

    @property
    def busy(self) -> bool:
        return self.state in ("waiting", "settling", "running")

    # ------------------------------------------------------------------ tick
    def tick(self, s: Dict[str, Any]) -> None:
        """s: app, game, steam_ui, real (game fps), gpu, cpu, draw_w, temp_c, at_ceiling, refresh,
        dock, above_x3."""
        now = self.clock()
        if self.state == "cancelled" and now - self.ended > DONE_SHOW_S:
            self.reset()
        if not self.busy:
            return
        if not s.get("game") or s.get("app") != self.app:
            return self._cancel("the game was closed or changed")
        if self.state == "waiting":
            if s.get("steam_ui"):
                if now - self.since >= WAIT_MAX_S:
                    return self._cancel("the Steam menu stayed open")
                return
            self.state, self.since = "settling", now
            return
        if s.get("steam_ui"):
            return self._cancel("the Steam menu opened")
        if self.state == "settling":
            settled = now - self.since >= SETTLE_S and s.get("at_ceiling", True)
            if settled or now - self.since >= SETTLE_MAX_S:
                self.state, self.since, self.samples, self.seen = "running", now, [], now
            return
        real = s.get("real")
        if isinstance(real, (int, float)):
            if real < PAUSED_FPS:
                return self._cancel("the game was paused")
            self.seen = now
        elif now - self.seen >= NO_FRAMES_S:
            return self._cancel("no game frames were measured")
        self.samples.append(s)
        if now - self.since >= DURATION_S:
            self._finish(s)

    def _cancel(self, why: str) -> None:
        self.state, self.reason, self.ended = "cancelled", why, self.clock()

    def _finish(self, s: Dict[str, Any]) -> None:
        med = {k: _median([x.get(k) for x in self.samples]) for k in ("real", "gpu", "cpu", "draw_w", "temp_c")}
        if med["real"] is None:
            return self._cancel("no game frames were measured")
        self.refresh = refresh = int(s.get("refresh") or 90)
        self.result = {"app": self.app, "refresh": refresh, "dock": bool(s.get("dock")),
                       "medians": {k: (round(v, 1) if v is not None else None) for k, v in med.items()},
                       **strategy(med["real"], med["draw_w"], refresh, bool(s.get("above_x3")),
                                  bool(s.get("dock")))}
        self.state, self.ended = "done", self.clock()

    # ------------------------------------------------------------------ view
    def view(self) -> Dict[str, Any]:
        now = self.clock()
        left = max(0.0, DURATION_S - (now - self.since)) if self.state == "running" else DURATION_S
        return {"state": self.state, "seconds_left": round(left), "reason": self.reason,
                "result": self.result,
                "live": {k: _median([x.get(k) for x in self.samples[-5:]]) for k in ("real", "gpu", "cpu", "draw_w", "temp_c")}
                if self.samples else None,
                "panel": self.panel(now)}

    def panel(self, now: Optional[float] = None) -> Optional[str]:
        """What the in-game centre panel shows: measuring, done (a few seconds) or nothing."""
        now = self.clock() if now is None else now
        if self.state in ("settling", "running"):
            return "measuring"
        if self.state == "done" and now - self.ended < DONE_SHOW_S:
            return "done"
        if self.state == "cancelled" and now - self.ended < DONE_SHOW_S:
            return "cancelled"
        return None


def strategy(fps: float, draw_w: Optional[float], refresh: int, above_x3: bool, dock: bool) -> Dict[str, Any]:
    """The highest point the game should hold with generation on (it keeps about FG_COST of its
    frame rate), within Autopilot's ladder; the multiplier follows from it."""
    steps = [c for c in capped(ladder(refresh), refresh, above_x3)
             if c >= lowest_point(refresh, "autopilot", dock=dock)]
    held = fps * FG_COST
    fit = [c for c in steps if TRIAL_RATIO * c <= held]
    point = fit[-1] if fit else steps[0]
    watts = None
    if isinstance(draw_w, (int, float)) and fps > 0:
        share = min(1.0, point / held) if held > 0 else 1.0
        watts = round(min(BAND_MAX_W + 0.5, IDLE_W + (draw_w - IDLE_W) * share))
    return {"point": point, "multiplier": mult_label(refresh, point), "watts": watts,
            "holds": bool(fit)}
