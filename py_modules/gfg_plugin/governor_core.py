"""Pure planning and power-search primitives for GFG Governor.

No Decky imports live here.  The same code is used by the live service and the
offline replay tests so policy changes remain reproducible.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class OperatingPoint:
    key: str
    target_output_fps: int
    base_target_fps: int
    multiplier: float
    render_scale_pct: int
    degraded: bool = False
    requires_scale_validation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannerDecision:
    point: Optional[OperatingPoint]
    proven: bool
    reason: str
    observed_p5_fps: Optional[float]
    required_p5_fps: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point": self.point.to_dict() if self.point else None,
            "proven": self.proven,
            "reason": self.reason,
            "observed_p5_fps": self.observed_p5_fps,
            "required_p5_fps": self.required_p5_fps,
        }


class OperatingPointPlanner:
    """Small deterministic operating-point planner.

    This planner only makes positive capacity claims from observed FPS.  It does
    not interpret a capped 30 FPS source as proof that 45 FPS is impossible.
    Scaled points are suggestions requiring validation because the current
    renderer diagnostics cannot prove performance at a scale that has not yet
    been applied.
    """

    HEADROOM_RATIO = 1.05

    @classmethod
    def candidates(
        cls, *, external_display: bool = False, target_output_fps: Optional[int] = None,
    ) -> tuple[OperatingPoint, ...]:
        """Ladder for a 60 FPS target (Dock / Deck LCD) or a 90 FPS target (Deck OLED)."""
        sixty = (int(target_output_fps) == 60) if target_output_fps else bool(external_display)
        target = 60 if sixty else 90
        ladder = cls.fg_ladder(target)
        base2 = int(round(target / 2))
        # Render scale is a tool of its own: before pushing generation to x2.75/x3
        # (more artefacts, more latency) try x2 with a reduced render scale, which
        # frees GPU time for the real frames instead.
        mid = (
            OperatingPoint(f"{base2}x2-s90", target, base2, 2, 90, requires_scale_validation=True),
            OperatingPoint(f"{base2}x2-s80", target, base2, 2, 80, requires_scale_validation=True),
        )
        head = tuple(p for p in ladder if p.multiplier <= 2.5)
        rest = tuple(p for p in ladder if p.multiplier > 2.5)
        if sixty:
            tail = (OperatingPoint("20x3-degraded", 60, 20, 3, 100, degraded=True),)
        else:
            tail = (
                OperatingPoint("30x3-s90", 90, 30, 3, 90, requires_scale_validation=True),
                OperatingPoint("30x3-s80", 90, 30, 3, 80, requires_scale_validation=True),
            )
        return head + mid + rest + tail

    # Automatic multipliers: native, then quarter steps up to x3.  x4/x5 are
    # never chosen automatically.
    MULTIPLIER_GRID = (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0)

    @classmethod
    def fg_ladder(cls, target: int) -> tuple[OperatingPoint, ...]:
        """Highest quality (lowest multiplier, highest real FPS) first."""
        points = []
        for m in cls.MULTIPLIER_GRID:
            base = int(round(target / m))
            if m == 1.0:
                key = f"native{target}"
            else:
                key = f"{base}x{m:g}"
            if target == 60 and m == 3.0:
                continue  # 20x3 only exists as the degraded last resort
            points.append(OperatingPoint(key, target, base, m if m != int(m) else int(m), 100))
        return tuple(points)

    @classmethod
    def required_p5(cls, point: OperatingPoint) -> float:
        return float(point.base_target_fps) * cls.HEADROOM_RATIO

    def recommend(
        self,
        *,
        external_display: bool = False,
        observed_p5_fps: Optional[float],
        observed_multiplier: Optional[float],
        target_output_fps: Optional[int] = None,
    ) -> PlannerDecision:
        if not isinstance(observed_p5_fps, (int, float)) or not math.isfinite(float(observed_p5_fps)):
            return PlannerDecision(None, False, "insufficient-capacity-evidence", None, None)
        p5 = float(observed_p5_fps)
        multiplier = (
            float(observed_multiplier)
            if isinstance(observed_multiplier, (int, float)) and math.isfinite(float(observed_multiplier))
            else None
        )
        candidates = self.candidates(external_display=external_display, target_output_fps=target_output_fps)

        # Native capacity is only positively proven while the observed cadence
        # is effectively native.  An active 2x/3x scheduler can intentionally
        # cap base FPS and therefore cannot prove or disprove native 90/60.
        native = candidates[0]
        if multiplier is not None and multiplier <= 1.12 and p5 >= self.required_p5(native):
            return PlannerDecision(native, True, "native-capacity-confirmed", p5, self.required_p5(native))

        # Prefer the highest-quality unscaled FG point that the observed source
        # cadence positively proves.  x4/x5 do not exist in this candidate set.
        for point in candidates[1:]:
            if point.render_scale_pct != 100:
                continue
            required = self.required_p5(point)
            if p5 >= required:
                return PlannerDecision(point, True, "base-capacity-confirmed", p5, required)

        # A scale change cannot be proven before it is applied.  Return at most
        # a bounded trial recommendation when the source is close enough that
        # the requested scale reduction could plausibly bridge the gap.
        base_fg = next((p for p in candidates if p.multiplier > 1 and not p.degraded), None)
        if base_fg is not None:
            for scale in (90, 80):
                point = next((p for p in candidates if p.render_scale_pct == scale), None)
                if point is None:
                    continue
                # Scaling linearity is not assumed as a performance model.  The
                # threshold only decides whether a *trial* is reasonable.
                trial_floor = self.required_p5(point) * (scale / 100.0)
                if p5 >= trial_floor:
                    return PlannerDecision(
                        point,
                        False,
                        "scale-trial-requires-validation",
                        p5,
                        self.required_p5(point),
                    )

        return PlannerDecision(None, False, "target-non-viable-from-observed-capacity", p5, None)


@dataclass(frozen=True)
class TrialVerdict:
    verdict: str  # "accept" | "reject" | "wait"
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TrialLadder:
    """Bounded, highest-quality-first exploration of operating points.

    Rationale: once Governor caps the real cadence at an operating point's base
    target, the renderer can no longer reveal headroom, so capacity cannot be
    *inferred* for the next rung - it must be *tried* and judged on fresh
    evidence.  The ladder never tries a rejected point twice in a session and
    never exceeds ``MAX_ATTEMPTS`` applications, so it cannot oscillate.
    """

    MAX_ATTEMPTS = 12
    # Cap-bound health: the real cadence sits on the cap, so require it to hold
    # within 5 % of the cap, with output close to the display target and no
    # delivery pressure.  (Uncapped headroom evidence is impossible here.)
    REAL_P5_RATIO = 0.95
    OUTPUT_MEDIAN_RATIO = 0.94
    MAX_MISSES = 1

    def __init__(self, *, external_display: bool = False, target_output_fps: Optional[int] = None) -> None:
        self.external_display = bool(external_display)
        self.target_output_fps = int(target_output_fps) if target_output_fps else (60 if external_display else 90)
        self.rejected: Dict[str, str] = {}
        self._reject_until: Dict[str, float] = {}
        self.skipped: Dict[str, str] = {}
        self.predicted: Dict[str, str] = {}
        self.native_capacity: Optional[float] = None
        self.attempts = 0

    CAPACITY_SLACK = 1.10

    def observe_native_capacity(self, real_median: Any, multiplier: Any) -> None:
        """Remember uncapped native cadence; it is an upper bound for every FG point's real FPS.

        Only evidence taken while no generation was active counts (``multiplier`` <= 1.12).
        """
        try:
            real, mult = float(real_median), float(multiplier)
        except (TypeError, ValueError):
            return
        if math.isfinite(real) and real > 0 and mult <= 1.12:
            self.native_capacity = max(self.native_capacity or 0.0, real)

    def candidates(self) -> tuple[OperatingPoint, ...]:
        return OperatingPointPlanner.candidates(
            external_display=self.external_display, target_output_fps=self.target_output_fps,
        )

    def next_point(self, applicable: Any, now: Optional[float] = None) -> Optional[OperatingPoint]:
        """First unrejected point for which ``applicable(point)`` returns None.

        ``applicable`` returns a reason string when a point cannot currently be
        expressed (for example a scaled point on a process launched without the
        Scaling Engine); such points are skipped and reported, not rejected.
        """
        if now is not None:
            for key, until in list(self._reject_until.items()):
                if now >= until:
                    self._reject_until.pop(key)
                    self.rejected.pop(key, None)
        if self.attempts >= self.MAX_ATTEMPTS:
            return None
        self.skipped = {}
        self.predicted = {}
        for point in self.candidates():
            if point.key in self.rejected:
                continue
            # Predictive skip: generation cannot make the real stream faster than native,
            # so a point whose real-frame budget exceeds the native capacity cannot hold.
            # Not a rejection: stale evidence must not poison the session.
            if (
                self.native_capacity is not None
                and point.base_target_fps > self.native_capacity * self.CAPACITY_SLACK
            ):
                self.predicted[point.key] = f"native-capacity-{self.native_capacity:.0f}-below-base-{point.base_target_fps}"
                continue
            reason = applicable(point)
            if reason:
                self.skipped[point.key] = str(reason)
                continue
            return point
        return None

    def mark_attempt(self) -> None:
        self.attempts += 1

    def reject(self, point_key: str, reason: str, until: Optional[float] = None) -> None:
        """Permanent for the session, or until ``until`` (service clock) for transient evidence."""
        self.rejected[point_key] = reason
        if until is None:
            self._reject_until.pop(point_key, None)
        else:
            self._reject_until[point_key] = float(until)

    def evaluate(
        self,
        point: OperatingPoint,
        summary: Dict[str, Any],
        *,
        min_samples: int,
        min_span_s: float,
    ) -> TrialVerdict:
        if (
            int(summary.get("samples") or 0) < int(min_samples)
            or float(summary.get("sample_span_s") or 0.0) < float(min_span_s)
        ):
            return TrialVerdict("wait", "collecting-trial-evidence")
        real_p5 = (summary.get("real") or {}).get("p5")
        output_median = (summary.get("output") or {}).get("median")
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (real_p5, output_median)):
            return TrialVerdict("reject", "trial-evidence-incomplete")
        if int(summary.get("hard_pressure") or 0) > 0:
            return TrialVerdict("reject", "hard-pressure-during-trial")
        if int(summary.get("misses") or 0) > self.MAX_MISSES:
            return TrialVerdict("reject", "delivery-misses-during-trial")
        if float(real_p5) < point.base_target_fps * self.REAL_P5_RATIO:
            return TrialVerdict("reject", "real-cadence-below-cap")
        if float(output_median) < point.target_output_fps * self.OUTPUT_MEDIAN_RATIO:
            return TrialVerdict("reject", "output-below-target")
        return TrialVerdict("accept", "trial-healthy")

    def status(self) -> Dict[str, Any]:
        return {
            "external_display": self.external_display,
            "target_output_fps": self.target_output_fps,
            "attempts": self.attempts,
            "max_attempts": self.MAX_ATTEMPTS,
            "rejected": dict(self.rejected),
            "skipped": dict(self.skipped),
            "predicted_infeasible": dict(self.predicted),
            "native_capacity": self.native_capacity,
        }


def multiplier_tolerance(multiplier: float) -> float:
    """Fractional neighbours are 0.25 apart, so they need a tighter match than integers."""
    m = float(multiplier)
    return 0.22 if m == int(m) else 0.12


EFFORT_LEVELS = ("easy", "medium", "hard", "nightmare")


def raw_effort(
    point: Optional[Dict[str, Any]], real_median: Optional[float], exhausted: bool = False,
    tdp_w: Optional[float] = None,
) -> Optional[str]:
    """Instantaneous effort level, before any smoothing.

    Budget mode (``tdp_w`` given) rates the watts the game needs: easy up to 11 W,
    medium 12-15 W, hard above 15 W or x4; nightmare when even that does not hold.
    Otherwise (quality mode): easy native or up to x1.5; medium above x1.5 and
    below x3; hard x3 or reduced render scale; nightmare target not reachable,
    very low real FPS, or x3 *and* reduced scale.
    """
    if exhausted:
        return "nightmare"
    if point is None:
        return None
    if tdp_w is not None:
        if real_median is not None and real_median < EffortEstimator.NIGHTMARE_REAL_FPS:
            return "nightmare"
        if float(point.get("multiplier", 1) or 1) >= 4 or tdp_w > 15.0 + 1e-6:
            return "hard"
        return "easy" if tdp_w <= 11.0 + 1e-6 else "medium"
    mult = float(point.get("multiplier", 1) or 1)
    scale = int(point.get("render_scale_pct", 100) or 100)
    if real_median is not None and real_median < EffortEstimator.NIGHTMARE_REAL_FPS:
        return "nightmare"
    if mult >= 3 and scale < 100:
        return "nightmare"
    if mult >= 3 or scale < 100:
        return "hard"
    if mult > 1.5:
        return "medium"
    return "easy"  # native or up to x1.5: generation fills a minority of frames


class EffortEstimator:
    """Slow, hysteretic 'GFG effort' rating: Easy / Medium / Hard / Nightmare.

    Nothing is published until the same raw level has held for ``INITIAL_DWELL``
    seconds, so the rating never flickers while the Governor is still trying
    operating points.  Afterwards a *harder* level needs ``UP_DWELL`` seconds,
    an *easier* one ``DOWN_DWELL`` and moves a single step at a time; changes
    are at least ``MIN_HOLD`` seconds apart.
    """

    INITIAL_DWELL = 45.0
    UP_DWELL = 20.0
    DOWN_DWELL = 60.0
    MIN_HOLD = 30.0
    NIGHTMARE_REAL_FPS = 18.0

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.level: Optional[str] = None
        self._candidate: Optional[str] = None
        self._since = 0.0
        self._changed = 0.0

    def update(self, now: float, raw: Optional[str]) -> Optional[str]:
        if raw is None:
            self._candidate = None  # evidence paused; keep what was published
            return self.level
        if raw != self._candidate:
            self._candidate, self._since = raw, now
        held = now - self._since
        if self.level is None:
            if held >= self.INITIAL_DWELL:
                self.level, self._changed = raw, now
            return self.level
        if raw == self.level:
            return self.level
        order = EFFORT_LEVELS.index
        harder = order(raw) > order(self.level)
        need = self.UP_DWELL if harder else self.DOWN_DWELL
        if held >= need and now - self._changed >= self.MIN_HOLD:
            step = order(self.level) + (1 if harder else -1)
            if harder and raw == "nightmare":
                step = order(raw)  # unreachable target is reported at once
            self.level, self._changed = EFFORT_LEVELS[step], now
            if self.level != raw:
                self._since = now  # next single step needs its own dwell
        return self.level

    def status(self) -> Dict[str, Any]:
        return {"level": self.level, "assessing": self.level is None}


class CostModel:
    """Transparent relative cost model used for rare point comparisons."""

    SCALE_PENALTY = {100: 0.0, 90: 2.0, 80: 6.0}

    @staticmethod
    def multiplier_penalty(multiplier: float) -> float:
        """Piecewise linear: x1 0, x2 1, x3 4 (x1.5 0.5, x2.5 2.5); anything else is steep."""
        m = float(multiplier)
        if 1.0 <= m <= 2.0:
            return (m - 1.0) * 1.0
        if 2.0 < m <= 3.0:
            return 1.0 + (m - 2.0) * 3.0
        return 20.0

    def score(
        self,
        point: OperatingPoint,
        *,
        estimated_power_w: float,
        instability_penalty: float = 0.0,
        current_point_key: str = "",
    ) -> float:
        transition = 0.0 if not current_point_key or point.key == current_point_key else 5.0
        degraded = 4.0 if point.degraded else 0.0
        return (
            max(0.0, float(estimated_power_w))
            + self.multiplier_penalty(point.multiplier)
            + self.SCALE_PENALTY.get(point.render_scale_pct, 20.0)
            + max(0.0, float(instability_penalty))
            + transition
            + degraded
        )


@dataclass
class PowerSearchState:
    state: str = "idle"
    current_tdp_w: Optional[float] = None
    last_good_tdp_w: Optional[float] = None
    recovery_tdp_w: Optional[float] = None
    min_tdp_w: Optional[float] = None
    ceiling_tdp_w: Optional[float] = None
    ceiling_failures: int = 0
    reason: str = "not-started"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PowerSearch:
    """Coarse-to-fine, non-oscillating TDP search.

    The service evaluates one power level using fresh evidence, calls
    ``evaluate`` once, applies the returned cap, then starts a new evidence
    window.  A failed lower candidate restores the last known-good level and
    locks.  This is intentionally not a continuously hunting PID controller.
    """

    # One bad window at the ceiling (a hitch, a camera turn) must not end the
    # search for the whole session: re-check before giving up on the point.
    CEILING_CHECKS = 2

    def __init__(self) -> None:
        self.status = PowerSearchState()

    def begin(self, *, current_tdp_w: float, min_tdp_w: float, ceiling_tdp_w: float) -> None:
        current = min(max(float(current_tdp_w), float(min_tdp_w)), float(ceiling_tdp_w))
        self.status = PowerSearchState(
            state="optimizing",
            current_tdp_w=current,
            last_good_tdp_w=None,
            recovery_tdp_w=None,
            min_tdp_w=float(min_tdp_w),
            ceiling_tdp_w=float(ceiling_tdp_w),
            reason="power-search-started",
        )

    @staticmethod
    def _step_for_headroom(headroom_ratio: float) -> float:
        if headroom_ratio >= 0.25:
            return 4.0
        if headroom_ratio >= 0.15:
            return 2.0
        return 1.0

    def evaluate(
        self,
        *,
        p5_fps: Optional[float],
        base_target_fps: float,
        hard_pressure: int = 0,
        misses: int = 0,
        health_ratio: float = 1.05,
    ) -> Dict[str, Any]:
        """Evaluate one fresh evidence window at the current power level.

        ``health_ratio`` is the p5/target ratio that counts as healthy.  The
        default 1.05 needs uncapped headroom evidence.  When Governor itself
        caps the real cadence at the target (runtime overlay), headroom above
        the cap is unobservable, so callers pass a cap-bound ratio (< 1.0).
        """
        s = self.status
        if s.state != "optimizing" or s.current_tdp_w is None:
            return {"action": "none", "state": s.to_dict()}
        if not isinstance(p5_fps, (int, float)) or not math.isfinite(float(p5_fps)):
            s.reason = "insufficient-fresh-evidence"
            return {"action": "wait", "state": s.to_dict()}
        target = max(1.0, float(base_target_fps))
        p5 = float(p5_fps)
        healthy = p5 >= target * float(health_ratio) and int(hard_pressure) == 0 and int(misses) == 0

        if not healthy:
            if s.last_good_tdp_w is None:
                # The selected point is not healthy even at the initial/user
                # ceiling.  Never exceed that ceiling automatically.
                s.ceiling_failures += 1
                if s.ceiling_failures < self.CEILING_CHECKS:
                    s.reason = "rechecking-at-ceiling"
                    return {"action": "wait", "state": s.to_dict()}
                s.state = "guard"
                s.reason = "point-not-healthy-at-ceiling"
                return {"action": "hold", "state": s.to_dict()}
            restore = float(s.last_good_tdp_w)
            s.current_tdp_w = restore
            s.state = "locked"
            s.reason = "minimum-stable-power-found"
            return {"action": "set", "target_tdp_w": restore, "state": s.to_dict()}

        current = float(s.current_tdp_w)
        s.last_good_tdp_w = current
        headroom = max(0.0, p5 / target - 1.0)
        step = self._step_for_headroom(headroom)
        minimum = float(s.min_tdp_w if s.min_tdp_w is not None else current)
        candidate = max(minimum, current - step)
        if candidate >= current - 0.01:
            s.state = "locked"
            s.reason = "minimum-hardware-cap-reached"
            return {"action": "lock", "state": s.to_dict()}
        s.recovery_tdp_w = current
        s.current_tdp_w = candidate
        s.reason = "testing-lower-power"
        return {"action": "set", "target_tdp_w": candidate, "state": s.to_dict()}

    def guard_recovery(self, *, current_tdp_w: float, ceiling_tdp_w: float, severe: bool = False) -> Dict[str, Any]:
        current = float(current_tdp_w)
        ceiling = float(ceiling_tdp_w)
        step = 3.0 if severe else 2.0
        target = min(ceiling, current + step)
        if target <= current + 0.01:
            self.status.state = "guard"
            self.status.reason = "guard-at-user-ceiling"
            return {"action": "hold", "state": self.status.to_dict()}
        self.status.current_tdp_w = target
        self.status.last_good_tdp_w = target
        self.status.state = "guard"
        self.status.reason = "guard-restoring-headroom"
        return {"action": "set", "target_tdp_w": target, "state": self.status.to_dict()}


# ------------------------------------------------------------------ budget mode
#
# Battery-first policy (v0.0.6).  Every watt saved is battery life, so the
# Governor looks for the *lowest TDP* at which the real stream holds, and only
# then spends the remaining headroom on fewer generated frames.
#
#   9-11 W   ideal
#   12-15 W  heavy / poorly optimised game
#   16-20 W  last resort, only while real FPS stays below ~22 for a while
#
# Multipliers 1.0 .. 3.75 in 0.25 steps are normal tools; x4 is a last resort.

BUDGET_MULTIPLIERS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75)
EMERGENCY_MULTIPLIER = 4
REAL_FLOOR_FPS = 24  # below this interpolation smears; deeper points are not offered
EMERGENCY_REAL_FLOOR_FPS = 20  # even the last resort keeps a real cadence that can be watched
START_REAL_FPS = 30  # first point: ~30 real (30x3 at 90 Hz, 30x2 at 60 Hz)


def _point_key(target: int, base: int, multiplier: float) -> str:
    return f"native{target}" if multiplier == 1 else f"{base}x{multiplier:g}"


def budget_points(target_output_fps: int) -> tuple[OperatingPoint, ...]:
    """Cheapest first: x4 emergency, then real 24 .. native."""
    target = int(target_output_fps)
    normal = []
    seen: set[int] = set()
    for m in reversed(BUDGET_MULTIPLIERS):
        base = int(round(target / m))
        if base < REAL_FLOOR_FPS or base in seen:
            continue
        seen.add(base)
        mult = int(m) if m == int(m) else m
        normal.append(OperatingPoint(_point_key(target, base, m), target, base, mult, 100))
    # Last resort: as deep as x4 allows, but the real cadence stays >= 20 and the
    # ratio is taken from the target, so the output still lands on the display
    # rate (90/23 = 3.91, not 22x4 = 88 on a 90 Hz panel).
    base4 = max(math.ceil(target / EMERGENCY_MULTIPLIER), EMERGENCY_REAL_FLOOR_FPS)
    mult4 = round(target / base4, 3)
    mult4 = int(mult4) if mult4 == int(mult4) else mult4
    emergency = OperatingPoint(_point_key(target, base4, mult4), target, base4, mult4, 100, degraded=True)
    return (emergency,) + tuple(normal)


@dataclass(frozen=True)
class WindowVerdict:
    healthy: bool
    severe: bool
    reason: str
    short: bool = False   # the real stream did not reach this point's own cap
    stall: bool = False   # real collapsed (loading screen / transition), not a power level

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# One definition of "the point holds", used for every decision in budget mode.
HOLD_REAL_RATIO = 0.95       # real p5 vs the real-frame cap
HOLD_OUTPUT_RATIO = 0.94     # output median vs the display target
SEVERE_REAL_RATIO = 0.85
STALL_REAL_RATIO = 0.5       # below half the cap looks like a loading screen, not a power level
MAX_WINDOW_MISSES = 1
PACING_P95_RATIO = 1.35      # p95 real frame interval vs the cap's frame time


def window_verdict(summary: Dict[str, Any], point: OperatingPoint) -> WindowVerdict:
    real_p5 = (summary.get("real") or {}).get("p5")
    output_median = (summary.get("output") or {}).get("median")
    if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (real_p5, output_median)):
        return WindowVerdict(False, True, "evidence-incomplete")
    hard = int(summary.get("hard_pressure") or 0)
    misses = int(summary.get("misses") or 0)
    base = float(point.base_target_fps)
    short = float(real_p5) < base * HOLD_REAL_RATIO
    severe = float(real_p5) < base * SEVERE_REAL_RATIO or hard >= 3
    real_median = (summary.get("real") or {}).get("median")
    reference = float(real_median) if isinstance(real_median, (int, float)) and math.isfinite(
        float(real_median)) else float(real_p5)
    stall = reference < base * STALL_REAL_RATIO
    flags = {"short": short, "stall": stall}
    if hard > 0:
        return WindowVerdict(False, severe, "hard-pressure", **flags)
    if misses > MAX_WINDOW_MISSES:
        return WindowVerdict(False, severe, "delivery-misses", **flags)
    if short:
        return WindowVerdict(False, severe, "real-below-cap", **flags)
    if float(output_median) < point.target_output_fps * HOLD_OUTPUT_RATIO:
        return WindowVerdict(False, severe, "output-below-target", **flags)
    p95 = summary.get("real_interval_p95_ms")
    if isinstance(p95, (int, float)) and math.isfinite(float(p95)) and base > 0:
        if float(p95) > PACING_P95_RATIO * 1000.0 / base:
            return WindowVerdict(False, False, "uneven-pacing", **flags)
    return WindowVerdict(True, False, "holds")


class BudgetController:
    """Watts first, quality second.  Pure state machine; the service applies its targets.

    The service feeds one *non-overlapping* evidence window at a time through
    ``observe``.  Phases:

    * ``settle``      first point (~30 real) at ``START_TDP_W``.
    * ``search_down`` -1 W per success while the point holds.  A failure
      restores the last good level (edge + 1 W, never the failing level).
    * ``upgrade``     at the found TDP try one step fewer generated frames at a
      time; stop at the first failure.
    * ``locked``      keep watching.  Two bad windows (one if severe) start the
      guard.  After ``REPROBE_S`` of clean play try -1 W or one quality step
      again (alternating), backing off on failure.
    * ``guard``       escalation, cheapest first: deeper multiplier down to ~30
      real, +1 W up to 11 W, x3.25 .. x3.75 (real 28 .. 24), +1 W up to 15 W,
      the last-resort point, then (only while the real stream keeps falling
      short of its own cap for ``EMERGENCY_SUSTAIN_S``) up to 20 W.

    Everything the guard spends is a debt: the state the point held before the
    guard is remembered and walked back to on a short ``RECOVER_S`` timer, so a
    loading screen every few minutes cannot ratchet the budget upwards for the
    rest of the session.

    A TDP or point change is accepted only after ``HEALTHY_WINDOWS``
    consecutive clean windows.
    """

    START_TDP_W = 10.0
    MIN_TDP_W = 6.0
    IDEAL_MAX_W = 11.0
    NORMAL_CEILING_W = 15.0
    EMERGENCY_CEILING_W = 20.0
    EMERGENCY_SUSTAIN_S = 60.0
    HEALTHY_WINDOWS = 2
    GUARD_WINDOWS = 2
    REPROBE_S = 300.0
    REPROBE_MAX_S = 1200.0
    EMERGENCY_REPROBE_S = 90.0
    RECOVER_S = 60.0       # giving back what the guard spent is not a new experiment
    RECOVER_MAX_S = 300.0
    REJECT_TTL_S = 600.0
    MAX_REQUEST_FAILURES = 4

    def __init__(
        self, *, target_output_fps: int, now: float,
        min_tdp_w: Optional[float] = None, max_tdp_w: Optional[float] = None,
        tdp_control: bool = True,
    ) -> None:
        self.target_output_fps = int(target_output_fps)
        self.points = budget_points(self.target_output_fps)
        self.tdp_control = bool(tdp_control)
        hw_min = float(min_tdp_w) if min_tdp_w else 0.0
        hw_max = float(max_tdp_w) if max_tdp_w else self.EMERGENCY_CEILING_W
        self.min_w = max(self.MIN_TDP_W, hw_min)
        self.normal_max_w = min(self.NORMAL_CEILING_W, hw_max)
        self.emergency_max_w = min(self.EMERGENCY_CEILING_W, hw_max)
        self.idx = min(
            range(1, len(self.points)),
            key=lambda i: abs(self.points[i].base_target_fps - START_REAL_FPS),
        )
        self.comfort_idx = self.idx  # deeper than ~30 real only to defend the budget
        self.ideal_max_w = min(self.IDEAL_MAX_W, self.normal_max_w)
        self.tdp = min(max(self.START_TDP_W, self.min_w), self.normal_max_w) if self.tdp_control else None
        self.phase = "settle"
        self.probe: Optional[str] = None
        self.last_good: Optional[tuple[int, Optional[float]]] = None
        self.prev: Optional[tuple[int, Optional[float]]] = None
        self.good = 0
        self.bad = 0
        self.short_since: Optional[float] = None
        self.recover: Optional[tuple[int, Optional[float]]] = None
        self.recover_interval = self.RECOVER_S
        self.rejected: Dict[str, float] = {}
        self.locked_since = now
        self.reprobe_interval = self.REPROBE_S
        self.next_probe = "down"
        self.exhausted = False
        self.request_failures = 0
        self.quality_debt: Optional[int] = None
        # Set when the measured draw shows our cap does not bind (another tool
        # raised the limit through the SMU).  A lower cap is then fiction, so
        # spare "headroom" must not be spent on more real frames.
        self.cap_ignored = False
        self.last_reason = "budget-start"

    # ------------------------------------------------------------- targets
    @property
    def point(self) -> OperatingPoint:
        return self.points[self.idx]

    def _usable(self, i: int, now: float) -> bool:
        if not 0 <= i < len(self.points):
            return False
        at = self.rejected.get(self.points[i].key)
        return at is None or now - at >= self.REJECT_TTL_S

    def _move(self, reason: str, *, idx: Optional[int] = None, tdp: Optional[float] = None) -> str:
        self.prev = (self.idx, self.tdp)
        if idx is not None:
            self.idx = idx
        if tdp is not None and self.tdp_control:
            self.tdp = round(float(tdp), 1)
        self.good = self.bad = 0
        self.last_reason = reason
        return "move"

    def _lock(self, now: float, reason: str) -> str:
        self.phase = "locked"
        self.probe = None
        self.locked_since = now
        self.exhausted = False
        self._clear_recovered()
        self.reprobe_interval = (
            self.EMERGENCY_REPROBE_S if self.tdp_control and self.tdp is not None and self.tdp > self.normal_max_w
            else max(self.reprobe_interval, self.REPROBE_S)
        )
        self.last_reason = reason
        return "hold"

    def _at_least(self, state: tuple[int, Optional[float]]) -> bool:
        """Back at (or better than) ``state``: same quality and no more watts."""
        idx, tdp = state
        if self.idx < idx:
            return False
        return not (self.tdp_control and tdp is not None and self.tdp is not None and self.tdp > tdp + 1e-6)

    def _clear_recovered(self) -> None:
        if self.recover is not None and self._at_least(self.recover):
            self.recover = None
            self.recover_interval = self.RECOVER_S

    def _probe_delay(self) -> float:
        return self.recover_interval if self.recover is not None else self.reprobe_interval

    def _can_lower(self) -> bool:
        return self.tdp_control and self.tdp is not None and self.tdp - 1.0 >= self.min_w - 1e-6

    # ------------------------------------------------------------ evidence
    def observe(self, now: float, verdict: WindowVerdict, real_median: Optional[float] = None) -> str:
        """Feed one fresh window.  Returns ``move`` when the targets changed.

        ``real_median`` is kept for the caller's logs; the decision uses the
        verdict, which measures the real stream against *this point's* cap.  An
        absolute FPS threshold cannot work here: a deep point caps the real
        cadence itself, so it would always look like a power shortage.
        """
        if verdict.healthy or not verdict.short:
            self.short_since = None
        elif self.short_since is None:
            self.short_since = now
        if verdict.healthy:
            return self._healthy(now)
        return self._unhealthy(now, verdict)

    def _healthy(self, now: float) -> str:
        self.bad = 0
        self.good += 1
        self.request_failures = 0
        if self.phase == "locked":
            if now - self.locked_since < self._probe_delay():
                return "hold"
            return self._reprobe(now)
        if self.good < self.HEALTHY_WINDOWS:
            return "hold"
        self.last_good = (self.idx, self.tdp)
        self.exhausted = False
        if self.quality_debt is not None and self.idx >= self.quality_debt:
            self.quality_debt = None
        self._clear_recovered()
        was = self.probe
        self.probe = None
        if self.phase == "probe":
            # The scene got lighter: keep going the same way until it fails.
            self.reprobe_interval = self.REPROBE_S
            self.phase = "search_down" if was == "down" else "upgrade"
        if self.phase in ("settle", "search_down"):
            if self._can_lower():
                self.phase = "search_down"
                self.probe = "down"
                return self._move("testing-lower-power", tdp=self.tdp - 1.0)
            self.phase = "upgrade"
        if self.phase == "upgrade":
            return self._upgrade(now)
        return self._lock(now, "budget-point-holds")

    def _upgrade(self, now: float) -> str:
        if self.cap_ignored and self.idx >= self.comfort_idx:
            return self._lock(now, "cap-ignored-quality-held")
        if self._usable(self.idx + 1, now):
            self.probe = "up"
            return self._move("testing-fewer-generated-frames", idx=self.idx + 1)
        return self._lock(now, "minimum-power-found")

    def _owed_quality(self) -> bool:
        """Quality was given up to defend watts or a heavy scene and may be won back."""
        return (
            self.idx < self.comfort_idx
            or (self.quality_debt is not None and self.idx < self.quality_debt)
            or (self.recover is not None and self.idx < self.recover[0])
        )

    def _reprobe(self, now: float) -> str:
        # Watts first: try -1 W with the current point.  Upward probes only win
        # back quality that the guard gave up; spare headroom goes to watts.
        kinds = ["down", "up"] if self.next_probe == "down" else ["up", "down"]
        for kind in kinds:
            if kind == "down" and self._can_lower():
                self.phase, self.probe = "probe", "down"
                self.next_probe = "up" if self._owed_quality() else "down"
                return self._move("reprobe-lower-power", tdp=self.tdp - 1.0)
            if kind == "up" and self._owed_quality() and self._usable(self.idx + 1, now):
                self.phase, self.probe, self.next_probe = "probe", "up", "down"
                return self._move("reprobe-fewer-generated-frames", idx=self.idx + 1)
        return self._lock(now, "budget-point-holds")

    def _unhealthy(self, now: float, verdict: WindowVerdict) -> str:
        self.good = 0
        if self.probe is not None and self.last_good is not None:
            failed = self.points[self.idx]
            if self.probe == "up":
                self.rejected[failed.key] = now
            idx, tdp = self.last_good
            from_phase = self.phase
            self.probe = None
            self._move(f"probe-failed:{verdict.reason}", idx=idx, tdp=tdp)
            if from_phase == "search_down":
                self.phase = "upgrade"
                self.good = self.HEALTHY_WINDOWS - 1  # the restored level already held
            else:
                if from_phase == "probe":
                    if self.recover is not None:
                        self.recover_interval = min(self.recover_interval * 2.0, self.RECOVER_MAX_S)
                    else:
                        self.reprobe_interval = min(self.reprobe_interval * 2.0, self.REPROBE_MAX_S)
                self._lock(now, f"probe-failed:{verdict.reason}")
            return "move"
        self.bad += 1
        # A collapse to half the cap is a loading screen or a transition far more
        # often than a power level, so it never escalates on a single window.
        immediate = verdict.severe and not verdict.stall
        if self.phase == "locked" and not immediate and self.bad < self.GUARD_WINDOWS:
            return "hold"
        return self._escalate(now, verdict)

    def _escalate(self, now: float, verdict: WindowVerdict) -> str:
        self.bad = 0
        if self.phase != "guard" and self.recover is None:
            # Everything spent from here is a debt to give back when the scene allows.
            self.recover = self.last_good or (self.idx, self.tdp)
        self.phase = "guard"
        self.probe = None
        step = 2.0 if verdict.severe else 1.0
        # Down to ~30 real a deeper multiplier is always cheaper than watts.
        if self.idx > self.comfort_idx and self._usable(self.idx - 1, now):
            self.quality_debt = max(self.quality_debt or 0, self.idx)
            return self._move(f"guard-deeper-multiplier:{verdict.reason}", idx=self.idx - 1)
        # Inside the ideal 9-11 W a watt is cheaper than real FPS below 30.
        if self.tdp_control and self.tdp is not None and self.tdp < self.ideal_max_w - 1e-6:
            return self._move(f"guard-more-power:{verdict.reason}", tdp=min(self.ideal_max_w, self.tdp + step))
        # Defending the 15 W budget: x3.25 .. x3.75 (real 28 .. 24) before more watts.
        if self.idx > 1 and self._usable(self.idx - 1, now):
            return self._move(f"guard-deeper-multiplier:{verdict.reason}", idx=self.idx - 1)
        if self.tdp_control and self.tdp is not None and self.tdp < self.normal_max_w - 1e-6:
            return self._move(f"guard-more-power:{verdict.reason}", tdp=min(self.normal_max_w, self.tdp + step))
        if self.idx == 1 and self._usable(0, now):
            return self._move(f"guard-emergency-x4:{verdict.reason}", idx=0)
        # Above the normal budget only while the real stream keeps missing the
        # cap of the deepest point there is: that, not an FPS number, is what
        # "the game cannot hold 20-22 real FPS" means.
        sustained = self.short_since is not None and now - self.short_since >= self.EMERGENCY_SUSTAIN_S
        if (
            sustained and self.tdp_control and self.tdp is not None
            and self.tdp < self.emergency_max_w - 1e-6
        ):
            return self._move(f"guard-emergency-power:{verdict.reason}", tdp=min(self.emergency_max_w, self.tdp + 1.0))
        self.exhausted = True
        self.last_reason = f"budget-exhausted:{verdict.reason}"
        return "hold"

    def request_failed(self, now: float, reason: str) -> None:
        """The renderer never confirmed the requested point: mark it and fall back."""
        failed = self.points[self.idx]
        self.rejected[failed.key] = now
        self.request_failures += 1
        self.probe = None
        self.good = self.bad = 0
        self._clear_recovered()
        if self.prev is not None and self.prev[0] != self.idx:
            self.idx = self.prev[0]
        else:
            # Nothing applied yet: try the next usable point, cheapest-first from here.
            options = [i for i in range(len(self.points)) if i >= 1 and self._usable(i, now)]
            if options:
                self.idx = min(options, key=lambda i: abs(i - self.idx))
        if self.request_failures >= self.MAX_REQUEST_FAILURES:
            self.exhausted = True
        self.phase = "guard" if self.phase in ("locked", "probe", "guard") else self.phase
        self.last_reason = f"request-failed:{reason}"

    def status(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "point": self.point.key,
            "tdp_w": self.tdp,
            "tdp_control": self.tdp_control,
            "tier": budget_tier(self.tdp, self.point),
            "probe": self.probe,
            "last_good": (
                {"point": self.points[self.last_good[0]].key, "tdp_w": self.last_good[1]}
                if self.last_good else None
            ),
            "rejected": sorted(self.rejected),
            "reprobe_interval_s": self._probe_delay(),
            "recovering_to": (
                {"point": self.points[self.recover[0]].key, "tdp_w": self.recover[1]} if self.recover else None
            ),
            "exhausted": self.exhausted,
            "cap_ignored": self.cap_ignored,
            "reason": self.last_reason,
            "limits_w": {"min": self.min_w, "normal": self.normal_max_w, "emergency": self.emergency_max_w},
        }


def budget_tier(tdp_w: Optional[float], point: Optional[OperatingPoint] = None) -> str:
    """ideal (<=11 W), heavy (12-15 W), emergency (>15 W or x4)."""
    if point is not None and point.degraded:
        return "emergency"
    if tdp_w is None:
        return "unknown"
    if tdp_w <= 11.0 + 1e-6:
        return "ideal"
    if tdp_w <= 15.0 + 1e-6:
        return "heavy"
    return "emergency"
