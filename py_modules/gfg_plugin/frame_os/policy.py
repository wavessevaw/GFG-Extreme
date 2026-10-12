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
import math
from typing import Any, Dict, List, Optional, Sequence
from .input_sensor import STICK_DEADZONE

BOOST_CAMERA = 0.5          # right-stick intensity that makes real frames matter
BOOST_ACTION = 0.5          # ~2 presses/s
BOOST_HOLD_S = 1.5          # keep a boost this long after its last trigger (no flicker)
BOOST_MAX_BURST_S = 1.5     # hard limit, even under continuous input
BOOST_RECOVERY_S = 0.5      # return to the calm cadence before another burst
BOOST_REARM_S = 0.15        # camera/action must become quiet before a new onset
SCENE_BOOST_S = 1.0
REST_IDLE_S = 20.0          # no input this long: pause menu, cutscene, AFK
BOOST_PROOF_S = 3.0         # a boost that has not raised the measured real cadence by then ...
BOOST_BACKOFF_S = 120.0     # ... is not paid for again this long (the GPU cannot feed it here)
WAKE_IDLE_S = 0.2
# Predictive boost: a camera swing is announced by the stick before it is fast.  A deflection
# rising this quickly (intensity per second) from this level starts the boost on the onset, about
# one real frame earlier than the plain threshold, so the first fast frames are already real.
ONSET_CAMERA = 0.25
ONSET_RATE = 2.0
HISTORY_KEEP = 200
TOUCH_PREBOOST_S = 0.5
TOUCH_RELEASE_S = 0.2
TOUCH_REARM_S = 0.15
TOUCH_GYRO_DPS = 15.0


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

    def tdp_for(self, level: str, cadence_drop: bool = True) -> float:
        if level == "boost":
            return self.calm_w + self.boost_extra_w
        if level == "rest":
            # with fewer real frames (x4) the GPU needs much less; at the calm cadence only a
            # little headroom can go, or the output drops in the pause
            return max(self.floor_w, self.calm_w * (0.6 if cadence_drop else 0.85))
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
    _boost_missing_s: float = 0.0
    _delivery_at: Optional[float] = None
    _last_boost_miss_at: Optional[float] = None
    # per game (Frame OS memory): effects the A/B proof ruled out in this game
    boost_allowed: bool = True
    rest_allowed: bool = True
    _cam_prev: Optional[float] = None
    _cam_prev_t: Optional[float] = None
    continuous_boost_enabled: bool = False
    touch_boost_enabled: bool = False
    _touch_seen: Optional[int] = None
    _touch_until: float = -1e9
    _touch_rearm_at: float = -1e9
    _touch_contact: bool = False
    touch_requests: int = 0
    touch_intent: bool = False
    _burst_started: Optional[float] = None
    _burst_recovery_until: float = -1e9
    _input_armed: bool = True
    _quiet_since: Optional[float] = None
    _touch_motion_armed: bool = False

    def cancel_boost(self) -> None:
        """A scope exit cannot leave any camera, scene or contact contribution alive."""
        self._boost_until = self._touch_until = -1e9
        self._burst_started = None
        self._boost_since = None
        self._touch_contact = self.touch_intent = False
        self._touch_motion_armed = False
        self._input_armed = False
        self._quiet_since = None
        self.level = "calm"

    def configure_continuous_boost(self, enabled: bool) -> None:
        if self.continuous_boost_enabled != enabled:
            self.cancel_boost()
            self._burst_recovery_until = -1e9
        self.continuous_boost_enabled = enabled is True

    def configure_touch_boost(self, enabled: bool) -> None:
        if self.touch_boost_enabled != enabled:
            self._touch_until = -1e9
            self._touch_contact = self.touch_intent = False
        self.touch_boost_enabled = enabled

    def _touch_trigger(self, now: float, inp: Dict[str, Any], focused: Optional[bool]) -> Optional[str]:
        contact = inp.get("right_stick_touch") if inp.get("touch_signal_fresh") is True else None
        generation = inp.get("touch_generation")
        edge = type(generation) is int and generation >= 0 and generation != self._touch_seen
        if edge:
            self._touch_seen = generation
        self.touch_intent = False
        if not self.touch_boost_enabled or focused is False or contact is None:
            self._touch_until = -1e9
            self._touch_contact = False
            self._touch_motion_armed = False
            return None
        reason = "stick-touch"
        if edge and contact is True and now >= self._touch_rearm_at:
            self._touch_until = now + TOUCH_PREBOOST_S
            self._touch_rearm_at = now + TOUCH_REARM_S
            self.touch_requests += 1
            self._touch_motion_armed = now >= self._burst_recovery_until
        gyro, stick = inp.get("gyro_dps"), inp.get("right_stick_deflection")
        moving = (type(gyro) in (int, float) and math.isfinite(gyro) and gyro >= TOUCH_GYRO_DPS) or (
            type(stick) in (int, float) and math.isfinite(stick) and stick > STICK_DEADZONE)
        if contact is True and moving and self._touch_motion_armed:
            self._touch_until = max(self._touch_until, now + TOUCH_RELEASE_S)
            reason = "stick-touch-motion"
        elif contact is False and self._touch_contact:
            self._touch_until = min(self._touch_until, now + TOUCH_RELEASE_S)
        self._touch_contact = contact is True
        self.touch_intent = now < self._touch_until
        return reason if self.touch_intent else None

    def _note(self, entry: str) -> None:
        self.history.append(entry)
        del self.history[:-HISTORY_KEEP]       # a whole session of camera-onset boosts stays bounded

    def note_delivered(self, now: float, real_fps: Optional[float], *, short_window: bool = False,
                       exposure_s: Optional[float] = None) -> None:
        """Measured real cadence while acting.  A boost the GPU cannot deliver is a waste of the
        energy bank: stop boosting for a while instead of paying watts for nothing."""
        dt = 0.0 if self._delivery_at is None else max(0.0, min(0.2, now - self._delivery_at))
        self._delivery_at = now
        if self.level != "boost" and not short_window:
            self._boost_since = None
            return
        if (isinstance(real_fps, bool) or not isinstance(real_fps, (int, float))
                or not math.isfinite(real_fps)):
            self._boost_since = None
            return  # unavailable cadence is not evidence of failed delivery
        delivered_floor = (self.calm_real_hz + max(1.0,self.calm_real_hz*0.05)
                           if short_window and not self.continuous_boost_enabled else 0.9*self.boost_real_hz)
        if real_fps is not None and real_fps >= delivered_floor:
            self._boost_since = None          # delivered
            self._boost_missing_s = 0.0
            self._last_boost_miss_at = None
            return
        if self._last_boost_miss_at is not None and now - self._last_boost_miss_at > BOOST_BACKOFF_S:
            self._boost_missing_s = 0.0
        self._last_boost_miss_at = now
        if short_window:
            # The caller supplies a fresh generation-specific window clipped to the pulse.
            # Count its final window too, even when this tick has just returned to calm.
            exposure = dt if exposure_s is None else max(0.0,min(0.5,float(exposure_s)))
            self._boost_missing_s += exposure
            self._boost_since = None
        elif self._boost_since is None:
            self._boost_since = now
        elif not short_window and now - self._boost_since >= 1.3:
            # Ignore the pacer's interval-ring transition, then accumulate
            # unsuccessful burst exposure too. Short camera swings must not
            # reset the proof timer forever (2.0.0 field log: boost stayed at 30).
            self._boost_missing_s += dt
        if (not short_window and self._boost_since is not None and now - self._boost_since >= BOOST_PROOF_S
                or self._boost_missing_s >= BOOST_PROOF_S):
            self._boost_blocked_until = now + BOOST_BACKOFF_S
            self._boost_since = None
            self._boost_missing_s = 0.0
            self._note(f"{now:.1f}:boost-ineffective")

    @property
    def boost_real_hz(self) -> float:
        return boost_level(self.output_hz, self.calm_real_hz, self.max_multiplier)

    @property
    def rest_real_hz(self) -> float:
        """Idle (menus, cutscenes, AFK): x4 saves energy on a scene that barely moves; the
        renderer fills the output.  Never below 20 real, never above calm."""
        # deepest ratio the renderer can generate right now (field log: capacity x3 refused x4 and
        # the output dropped to 60)
        deepest = max(1.0, min(4.0, float(int(self.max_multiplier + 1e-6))))
        rest = self.output_hz / deepest
        return rest if 20.0 <= rest < self.calm_real_hz - 1e-6 else self.calm_real_hz

    def tick(self, now: float, inp: Dict[str, Any], scene_change: bool = False,
             draw_w: Optional[float] = None, focused: Optional[bool] = None) -> Decision:
        camera, action = float(inp.get("camera", 0.0)), float(inp.get("action", 0.0))
        idle = float(inp.get("idle_s", float("inf")))
        trigger = None
        rising = 0.0
        if self._cam_prev is not None and self._cam_prev_t is not None and now > self._cam_prev_t:
            rising = (camera - self._cam_prev) / (now - self._cam_prev_t)
        self._cam_prev, self._cam_prev_t = camera, now
        if camera >= BOOST_CAMERA:
            trigger = "camera"
        elif camera >= ONSET_CAMERA and rising >= ONSET_RATE:
            trigger = "camera-onset"
        elif action >= BOOST_ACTION:
            trigger = "action"
        if not trigger:
            if self._quiet_since is None:
                self._quiet_since = now
            if now - self._quiet_since >= BOOST_REARM_S:
                self._input_armed = True
        else:
            self._quiet_since = None
        if trigger and self._input_armed and now >= self._burst_recovery_until:
            self._boost_until = max(self._boost_until, now + BOOST_HOLD_S)
            self._input_armed = False
        if scene_change and now >= self._burst_recovery_until:
            self._boost_until = max(self._boost_until, now + SCENE_BOOST_S)
            trigger = trigger or "scene-change"
        touch_trigger = self._touch_trigger(now, inp, focused)
        trigger = trigger or touch_trigger
        boost_until = max(self._boost_until, self._touch_until)
        if self.continuous_boost_enabled:
            boost_until = now + 1.0
            trigger = "continuous-boost"

        if focused is False:
            self.cancel_boost()
            boost_until = -1e9
        if not self.continuous_boost_enabled and self._burst_started is not None and now - self._burst_started >= BOOST_MAX_BURST_S:
            self._boost_until = self._touch_until = -1e9
            self._burst_recovery_until = now + BOOST_RECOVERY_S
            self._burst_started = None
            self._touch_motion_armed = False
            boost_until = -1e9

        if focused is False and self.rest_allowed:
            level, reason = "rest", "steam-ui"      # Steam's menu covers the game: rest at once
        elif idle >= REST_IDLE_S and self.rest_allowed and idle != float("inf") and inp.get("idle_verified") is True:
            # Gamepad silence cannot prove the player is idle in a keyboard/mouse game.
            # Require a future sensor with whole-session input coverage, not raw evdev silence.
            level, reason = "rest", "idle-verified"
        elif now < self._burst_recovery_until:
            level, reason = "calm", "boost-recovery"
        elif now < boost_until and not self.boost_allowed:
            level, reason = "calm", "boost-off-for-game"     # measured useless or harmful here
        elif now < boost_until and now < self._boost_blocked_until:
            level, reason = "calm", "boost-ineffective"
        elif now < boost_until and self.boost_real_hz > self.calm_real_hz:
            # Explicit sustained mode spends power directly within the service's
            # normal ceiling; its duration must not depend on a finite pulse bank.
            affordable = self.continuous_boost_enabled or self.broker is None or self.broker.can_boost() or self.level == "boost"
            level, reason = ("boost", trigger or self._reason) if affordable else ("calm", "energy-bank-empty")
        else:
            level, reason = "calm", "steady"
        if self.broker is not None:
            self.broker.tick(now, draw_w, level)
            if level == "boost" and not self.continuous_boost_enabled and self.broker.bank_j <= 0.0:
                level, reason = "calm", "energy-bank-empty"
        if level != self.level:
            self._note(f"{now:.1f}:{self.level}->{level}:{reason}")
        if level == "boost" and self.level != "boost":
            self._burst_started = now
        elif level != "boost" and self.level == "boost":
            self._boost_since = None
            self._burst_recovery_until = max(self._burst_recovery_until, now + BOOST_RECOVERY_S)
            self._burst_started = None
            self._boost_until = self._touch_until = -1e9
            self._touch_motion_armed = False
        self.level, self._reason = level, reason
        real = {"boost": self.boost_real_hz, "rest": self.rest_real_hz}.get(level, self.calm_real_hz)
        tdp = self.broker.tdp_for(level, cadence_drop=self.rest_real_hz < self.calm_real_hz) \
            if self.broker is not None else None
        return Decision(level, real, self.output_hz, tdp, reason)
