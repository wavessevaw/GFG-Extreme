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
    multiplier: int
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
        if sixty:
            return (
                OperatingPoint("native60", 60, 60, 1, 100),
                OperatingPoint("30x2", 60, 30, 2, 100),
                OperatingPoint("30x2-s90", 60, 30, 2, 90, requires_scale_validation=True),
                OperatingPoint("30x2-s80", 60, 30, 2, 80, requires_scale_validation=True),
                OperatingPoint("20x3-degraded", 60, 20, 3, 100, degraded=True),
            )
        return (
            OperatingPoint("native90", 90, 90, 1, 100),
            OperatingPoint("45x2", 90, 45, 2, 100),
            OperatingPoint("30x3", 90, 30, 3, 100),
            OperatingPoint("30x3-s90", 90, 30, 3, 90, requires_scale_validation=True),
            OperatingPoint("30x3-s80", 90, 30, 3, 80, requires_scale_validation=True),
        )

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

    MAX_ATTEMPTS = 6
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
        self.skipped: Dict[str, str] = {}
        self.attempts = 0

    def candidates(self) -> tuple[OperatingPoint, ...]:
        return OperatingPointPlanner.candidates(
            external_display=self.external_display, target_output_fps=self.target_output_fps,
        )

    def next_point(self, applicable: Any) -> Optional[OperatingPoint]:
        """First unrejected point for which ``applicable(point)`` returns None.

        ``applicable`` returns a reason string when a point cannot currently be
        expressed (for example a scaled point on a process launched without the
        Scaling Engine); such points are skipped and reported, not rejected.
        """
        if self.attempts >= self.MAX_ATTEMPTS:
            return None
        self.skipped = {}
        for point in self.candidates():
            if point.key in self.rejected:
                continue
            reason = applicable(point)
            if reason:
                self.skipped[point.key] = str(reason)
                continue
            return point
        return None

    def mark_attempt(self) -> None:
        self.attempts += 1

    def reject(self, point_key: str, reason: str) -> None:
        self.rejected[point_key] = reason

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
        }


EFFORT_LEVELS = ("easy", "medium", "hard", "nightmare")


def raw_effort(point: Optional[Dict[str, Any]], real_median: Optional[float], exhausted: bool = False) -> Optional[str]:
    """Instantaneous effort level, before any smoothing.

    easy: no generation needed; medium: x2; hard: x3 or reduced render scale;
    nightmare: target not reachable, very low real FPS, or x3 *and* reduced scale.
    """
    if exhausted:
        return "nightmare"
    if point is None:
        return None
    mult = int(point.get("multiplier", 1) or 1)
    scale = int(point.get("render_scale_pct", 100) or 100)
    if real_median is not None and real_median < EffortEstimator.NIGHTMARE_REAL_FPS:
        return "nightmare"
    if mult >= 3 and scale < 100:
        return "nightmare"
    if mult >= 3 or scale < 100:
        return "hard"
    if mult == 2:
        return "medium"
    return "easy"


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

    MULTIPLIER_PENALTY = {1: 0.0, 2: 1.0, 3: 4.0}
    SCALE_PENALTY = {100: 0.0, 90: 2.0, 80: 6.0}

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
            + self.MULTIPLIER_PENALTY.get(point.multiplier, 20.0)
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
