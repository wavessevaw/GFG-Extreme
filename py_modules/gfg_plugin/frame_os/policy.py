"""Adaptive Real-Frame Injection and the Render Budget Broker.  (GFG Frame OS, policy.)

The Governor picks a *calm* operating point (e.g. 30 real x3 = 90 at 10 W).  Frame OS bends it
in real time:

* **Injection** — when a real frame matters (fast camera, burst of actions, a scene cut) the real
  cadence is raised to the next level the executor can deliver (30 -> 45 real, output unchanged:
  fewer generated frames exactly where they would smear); when the player is idle it rests.
  "Multiplier" stops being a setting: it is ``output / real`` of the moment.
* **Broker** — energy instead of watts.  Calm play banks the energy left under the calm cap;
  a boost spends it (TDP raised for the boost only).  When the bank is empty a boost is refused,
  so boosts never cost more than what calm play saved.  Rest drops the cap to the floor.

Pure logic with an injected clock; the service feeds 10-20 Hz ticks and writes the decision to
the gfg-pacer control channel and the PPT caps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

BOOST_CAMERA = 0.5          # right-stick intensity that makes real frames matter
BOOST_ACTION = 0.5          # ~2 presses/s
BOOST_HOLD_S = 1.5          # keep a boost this long after its last trigger (no flicker)
SCENE_BOOST_S = 1.0
REST_IDLE_S = 20.0          # no input this long: pause menu, cutscene, AFK
BOOST_PROOF_S = 3.0         # a boost that has not raised the measured real cadence by then ...
BOOST_BACKOFF_S = 120.0     # ... is not paid for again this long (the GPU cannot feed it here)
WAKE_IDLE_S = 0.2


@dataclass
class Decision:
    level: str              # "calm" | "boost" | "rest"
    real_hz: float
    output_hz: float
    tdp_w: Optional[float]
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {"level": self.level, "real_hz": self.real_hz, "output_hz": self.output_hz,
                "tdp_w": self.tdp_w, "reason": self.reason}


def boost_level(output_hz: float, calm_real_hz: float, max_multiplier: float,
                ladder: Sequence[float] = (1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 3.5, 4.0)) -> float:
    """Next real cadence above calm that keeps the output: 90/30 (x3) -> 45 (x2)."""
    candidates = sorted({round(output_hz / m, 3) for m in ladder if m <= max_multiplier + 1e-6})
    above = [r for r in candidates if r > calm_real_hz + 0.5]
    # One step, not a jump to native: x3 -> x2 is the big perceptual win per watt.  Integer
    # ratios first: the renderer switches to them in one frame, fractional ones need adaptive mode.
    big = [r for r in above if r >= calm_real_hz * 1.3]
    integer = [r for r in big if abs(output_hz / r - round(output_hz / r)) < 1e-6 and r <= calm_real_hz * 1.6]
    if integer:
        return integer[0]
    if big:
        return big[0]
    return above[-1] if above else calm_real_hz


@dataclass
class EnergyBroker:
    """Energy bank in joules.  ``calm_w`` is the Governor's cap, ``floor_w`` the hardware minimum."""

    calm_w: float
    floor_w: float = 4.0
    max_bank_s: float = 30.0        # bank at most this many seconds of the calm cap
    boost_extra_w: float = 4.0      # how much above calm a boost may draw
    # Energy the player grants for boosts on top of calm play (0.05 = 5 % of the calm cap).
    # Calm play near its cap saves almost nothing, so without a premium boosts would only be
    # paid by menus and pauses.
    premium: float = 0.05
    bank_j: float = 0.0
    _last: Optional[float] = None

    @property
    def max_bank_j(self) -> float:
        return self.calm_w * self.max_bank_s

    def tick(self, now: float, draw_w: Optional[float], level: str) -> None:
        dt = 0.0 if self._last is None else max(0.0, min(1.0, now - self._last))
        self._last = now
        if draw_w is None or dt <= 0:
            return
        # the bank is the area between the calm cap and what was actually drawn
        income = (self.calm_w * (1.0 + self.premium) - draw_w) * dt
        self.bank_j = max(0.0, min(self.max_bank_j, self.bank_j + income))

    def can_boost(self) -> bool:
        return self.bank_j >= self.boost_extra_w * 0.5     # at least half a second of boost

    def tdp_for(self, level: str) -> float:
        if level == "boost":
            return self.calm_w + self.boost_extra_w
        if level == "rest":
            return max(self.floor_w, self.calm_w * 0.6)
        return self.calm_w


@dataclass
class InjectionPolicy:
    output_hz: float
    calm_real_hz: float
    max_multiplier: float = 3.0
    broker: Optional[EnergyBroker] = None
    level: str = "calm"
    _boost_until: float = -1e9
    _reason: str = "start"
    history: List[str] = field(default_factory=list)
    _boost_since: Optional[float] = None
    _boost_blocked_until: float = -1e9

    def note_delivered(self, now: float, real_fps: Optional[float]) -> None:
        """Measured real cadence while acting.  A boost the GPU cannot deliver is a waste of the
        energy bank: stop boosting for a while instead of paying watts for nothing."""
        if self.level != "boost":
            self._boost_since = None
            return
        if real_fps is not None and real_fps >= 0.9 * self.boost_real_hz:
            self._boost_since = None          # delivered
            return
        if self._boost_since is None:
            self._boost_since = now
        elif now - self._boost_since >= BOOST_PROOF_S:
            self._boost_blocked_until = now + BOOST_BACKOFF_S
            self._boost_since = None
            self.history.append(f"{now:.1f}:boost-ineffective")

    @property
    def boost_real_hz(self) -> float:
        return boost_level(self.output_hz, self.calm_real_hz, self.max_multiplier)

    @property
    def rest_real_hz(self) -> float:
        """Idle (menus, cutscenes, AFK): x4 saves energy on a scene that barely moves; the
        renderer fills the output.  Never below 20 real, never above calm."""
        rest = self.output_hz / 4.0
        return rest if 20.0 <= rest < self.calm_real_hz else self.calm_real_hz

    def tick(self, now: float, inp: Dict[str, float], scene_change: bool = False,
             draw_w: Optional[float] = None, focused: Optional[bool] = None) -> Decision:
        camera, action = float(inp.get("camera", 0.0)), float(inp.get("action", 0.0))
        idle = float(inp.get("idle_s", float("inf")))
        trigger = None
        if camera >= BOOST_CAMERA:
            trigger = "camera"
        elif action >= BOOST_ACTION:
            trigger = "action"
        if trigger:
            self._boost_until = max(self._boost_until, now + BOOST_HOLD_S)
        if scene_change:
            self._boost_until = max(self._boost_until, now + SCENE_BOOST_S)
            trigger = trigger or "scene-change"

        if focused is False:
            level, reason = "rest", "steam-ui"      # Steam's menu covers the game: rest at once
        elif idle >= REST_IDLE_S and idle != float("inf"):
            level, reason = "rest", "idle"     # never before any input was seen (no pad, no reader)
        elif now < self._boost_until and now < self._boost_blocked_until:
            level, reason = "calm", "boost-ineffective"
        elif now < self._boost_until and self.boost_real_hz > self.calm_real_hz:
            affordable = self.broker is None or self.broker.can_boost() or self.level == "boost"
            level, reason = ("boost", trigger or self._reason) if affordable else ("calm", "energy-bank-empty")
        else:
            level, reason = "calm", "steady"
        if self.broker is not None:
            self.broker.tick(now, draw_w, level)
            if level == "boost" and self.broker.bank_j <= 0.0:
                level, reason = "calm", "energy-bank-empty"
        if level != self.level:
            self.history.append(f"{now:.1f}:{self.level}->{level}:{reason}")
        self.level, self._reason = level, reason
        real = {"boost": self.boost_real_hz, "rest": self.rest_real_hz}.get(level, self.calm_real_hz)
        tdp = self.broker.tdp_for(level) if self.broker is not None else None
        return Decision(level, real, self.output_hz, tdp, reason)
