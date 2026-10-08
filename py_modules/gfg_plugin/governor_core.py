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
    """Instantaneous effort level, before any smoothing (see ``effort_assessment``)."""
    return effort_assessment(point, real_median, exhausted, tdp_w)[0]


def effort_assessment(
    point: Optional[Dict[str, Any]], real_median: Optional[float], exhausted: bool = False,
    tdp_w: Optional[float] = None, thermal: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Instantaneous effort level and a short reason for it (review 1.1.x: a bare "HARD" left the
    player guessing why).

    Budget mode (``tdp_w`` given) rates the watts the game needs: easy up to 11 W,
    medium 12-15 W, hard above 15 W or x4; nightmare when even that does not hold.
    Otherwise (quality mode): easy native or up to x1.5; medium above x1.5 and
    below x3; hard x3 or reduced render scale; nightmare target not reachable,
    very low real FPS, or x3 *and* reduced scale.  ``thermal`` only colours the reason of a
    medium rating ("low thermal margin"); it never changes the level.
    """
    if exhausted:
        return "nightmare", "target not reachable"
    if point is None:
        return None, None
    mult = float(point.get("multiplier", 1) or 1)
    scale = int(point.get("render_scale_pct", 100) or 100)
    hot = thermal in ("hot", "heating")
    if real_median is not None and real_median < EffortEstimator.NIGHTMARE_REAL_FPS:
        return "nightmare", "very low real FPS"
    if tdp_w is not None:
        if mult >= 4:
            return "hard", "deeper than x3"
        if tdp_w > 15.0 + 1e-6:
            return "hard", "TDP above 15 W"
        if tdp_w <= 11.0 + 1e-6:
            return "easy", "11 W or less"
        return "medium", "low thermal margin" if hot else "TDP 12-15 W"
    if mult >= 3 and scale < 100:
        return "nightmare", "x3 and render scale"
    if mult > 3:
        return "hard", "deeper than x3"
    if mult >= 3:
        return "hard", "x3 required"
    if scale < 100:
        return "hard", "render scale"
    if mult > 1.5:
        return "medium", "low thermal margin" if hot else f"x{mult:g} required"
    # native or up to x1.5: generation fills a minority of frames
    return "easy", "native" if mult <= 1 else "x1.5 or less"


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
        self.reason: Optional[str] = None
        self._reasons: Dict[str, str] = {}  # latest reason seen per raw level
        self._candidate: Optional[str] = None
        self._since = 0.0
        self._changed = 0.0

    def update(self, now: float, raw: Optional[str], reason: Optional[str] = None) -> Optional[str]:
        if raw is None:
            self._candidate = None  # evidence paused; keep what was published
            return self.level
        if reason:
            self._reasons[raw] = reason
        level = self._step(now, raw)
        if level is not None:
            # A single step on the way to ``raw``: its own last reason, else what drives the move.
            self.reason = self._reasons.get(level) or self._reasons.get(raw)
        return level

    def _step(self, now: float, raw: str) -> Optional[str]:
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
        return {"level": self.level, "assessing": self.level is None,
                "reason": self.reason if self.level is not None else None}


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
    bad_windows: int = 0
    good_windows: int = 0
    raised: bool = False
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
        if s.state not in ("optimizing", "locked", "guard") or s.current_tdp_w is None:
            return {"action": "none", "state": s.to_dict()}
        if not isinstance(p5_fps, (int, float)) or not math.isfinite(float(p5_fps)):
            s.reason = "insufficient-fresh-evidence" if s.state == "optimizing" else s.reason
            return {"action": "wait", "state": s.to_dict()}
        target = max(1.0, float(base_target_fps))
        p5 = float(p5_fps)
        healthy = p5 >= target * float(health_ratio) and int(hard_pressure) == 0 and int(misses) == 0
        if s.state != "optimizing":
            return self._watch_locked(healthy, p5 < target * 0.85)

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

    LOCKED_BAD_WINDOWS = 2
    RESEARCH_GOOD_WINDOWS = 6

    def _watch_locked(self, healthy: bool, severe: bool) -> Dict[str, Any]:
        """After the search: a heavier scene gets watts back (up to the user's ceiling), and once
        it is over the search walks down again.

        Without the raise a level found in a menu stayed for the whole session (1.0.7); without
        the walk back down every marginal window ratcheted the cap up to the ceiling (1.0.10).
        At the ceiling a point is handed back only after ``CEILING_CHECKS`` bad windows in a row,
        never on a single hitch, however deep.
        """
        s = self.status
        ceiling = float(s.ceiling_tdp_w if s.ceiling_tdp_w is not None else s.current_tdp_w)
        at_ceiling = float(s.current_tdp_w) >= ceiling - 0.01
        if healthy:
            s.bad_windows = 0
            s.good_windows += 1
            if s.raised and s.good_windows >= self.RESEARCH_GOOD_WINDOWS:
                s.state, s.raised, s.good_windows, s.ceiling_failures = "optimizing", False, 0, 0
                s.last_good_tdp_w = float(s.current_tdp_w)  # a failed step comes back here
                s.reason = "re-searching-lower-power"
            elif s.state == "guard":
                s.state, s.reason = "locked", "minimum-stable-power-found"
            return {"action": "none", "state": s.to_dict()}
        s.good_windows = 0
        s.bad_windows += 1
        needed = max(self.LOCKED_BAD_WINDOWS, self.CEILING_CHECKS) if at_ceiling else self.LOCKED_BAD_WINDOWS
        if s.bad_windows < needed and (at_ceiling or not severe):
            return {"action": "none", "state": s.to_dict()}
        s.bad_windows = 0
        if at_ceiling:
            s.state = "guard"
            s.reason = "point-not-healthy-at-ceiling"
            return {"action": "hold", "state": s.to_dict()}
        result = self.guard_recovery(current_tdp_w=float(s.current_tdp_w), ceiling_tdp_w=ceiling, severe=severe)
        s.state, s.raised = "locked", True  # watching again at the new level
        result["state"] = s.to_dict()
        return result

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
#   >15 W    last resort (only where the device allows it), only while real FPS stays below ~22 for a while
#
# Multipliers 1.0 .. 3.75 in 0.25 steps are normal tools; x4 is a last resort.

BUDGET_MULTIPLIERS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75)
EMERGENCY_MULTIPLIER = 4
REAL_FLOOR_FPS = 24  # below this interpolation smears; deeper points are not offered
EMERGENCY_REAL_FLOOR_FPS = 20  # even the last resort keeps a real cadence that can be watched
START_REAL_FPS = 30  # first point: ~30 real (30x3 at 90 Hz, 30x2 at 60 Hz)


def _point_key(target: int, base: int, multiplier: float) -> str:
    return f"native{target}" if multiplier == 1 else f"{base}x{multiplier:g}"


BALANCED_REAL_FLOOR_FPS = 30   # Balanced never goes below 30 real (x3 at 90 Hz)
BALANCED_START_REAL_FPS = 45   # and starts at x2 at 90 Hz
BALANCED_START_TDP_W = 12.0
BALANCED_IDEAL_MAX_W = 13.0


def budget_points(target_output_fps: int, real_floor: int = REAL_FLOOR_FPS) -> tuple[OperatingPoint, ...]:
    """Cheapest first: x4 emergency, then real ``real_floor`` (24, or 30 in Balanced) .. native."""
    target = int(target_output_fps)
    normal = []
    seen: set[int] = set()
    for m in reversed(BUDGET_MULTIPLIERS):
        base = int(round(target / m))
        if base < real_floor or base in seen:
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


RENDER_SCALE_STEPS = (90, 80)   # live Scaling Engine factors the overlay allows (governor_overlay)
SCALE_ANCHOR_REAL_FPS = 30


def with_render_scale(points: tuple[OperatingPoint, ...]) -> tuple[OperatingPoint, ...]:
    """Battery/Balanced ladder with render-scale rungs.

    Below ~30 real frames the next step used to be a deeper ratio (x3.25 .. x3.75, often not
    available: the renderer's generated-frame capacity tops out at x3) and then more watts.
    Rendering at 90 % / 80 % resolution and upscaling frees GPU time instead: ``30x3@90`` and
    ``30x3@80`` sit right below ``30x3``, so the guard reaches for them before deeper ratios and
    before 12-15 W, and the usual upgrade path (idx + 1) wins full resolution back first.
    They are only usable while the game was launched with the Scaling Engine provisioned.
    """
    anchor = next((i for i, p in enumerate(points) if i > 0 and p.base_target_fps >= SCALE_ANCHOR_REAL_FPS
                   and float(p.multiplier).is_integer() and p.render_scale_pct == 100), None)
    if anchor is None:
        return points
    base = points[anchor]
    scaled = tuple(
        OperatingPoint(f"{base.key}@{pct}", base.target_output_fps, base.base_target_fps, base.multiplier, pct)
        for pct in sorted(RENDER_SCALE_STEPS)        # 80 is cheaper than 90: lower index
    )
    return points[:anchor] + scaled + points[anchor:]


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
      short of its own cap for ``EMERGENCY_SUSTAIN_S``) up to the device maximum.

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
    # A collapse below half the cap is a loading screen far more often than a
    # power level.  It buys one budget step per STALL_ESCALATE_S, and emergency
    # watts only once it has lasted STALL_EMERGENCY_S without a single window
    # above half the cap (no loading screen is that long; a game that is
    # really that slow is the case emergency watts exist for).
    STALL_ESCALATE_S = 120.0
    STALL_EMERGENCY_S = 300.0
    HEALTHY_WINDOWS = 2
    GUARD_WINDOWS = 2
    # Up fast, down carefully, all session long: a starved game gets watts
    # within seconds (fast_check), so a lower-power probe that does not hold
    # costs a short dip, not a 15 s window.  That makes frequent probes cheap.
    REPROBE_S = 45.0
    REPROBE_NO_DRAW_S = 300.0    # without a draw sensor a failed probe costs a whole window
    REPROBE_MAX_S = 300.0
    FAST_STARVED_CHECKS = 2      # consecutive ~1 s checks before a fast raise
    FAST_GAP_S = 3.0             # at most one fast raise per this many seconds
    FAST_STEP_W = 2.0
    WORK_MEMORY_S = 900.0        # how long a level the game needed is remembered
    # Draw this close to the cap: the cap is what limits.  The Deck's draw
    # sensor swings about 1 W around a binding cap (field log: 5.1-6.2 W
    # at a 6 W cap while the game crawled at 13 real).
    DRAW_BINDING_MARGIN_W = 1.2
    EMERGENCY_REPROBE_S = 90.0
    RECOVER_S = 60.0       # giving back what the guard spent is not a new experiment
    RECOVER_MAX_S = 300.0
    REJECT_TTL_S = 600.0
    # A lower level that just failed is not tried again at once, even after a guard raise and a
    # successful walk back down (Field log: 9 W failed nine times in 29 min with this
    # point, each failure a visible dip).  The wait doubles with every repeat at the same level.
    FLOOR_BACKOFF_S = 120.0
    FLOOR_BACKOFF_MAX_S = 600.0
    FAILURE_TTL_S = REJECT_TTL_S  # failures loaded from game memory expire like in-session rejections
    MAX_REQUEST_FAILURES = 4

    def __init__(
        self, *, target_output_fps: int, now: float,
        min_tdp_w: Optional[float] = None, max_tdp_w: Optional[float] = None,
        tdp_control: bool = True, flavor: str = "battery",
    ) -> None:
        self.flavor = "balanced" if flavor == "balanced" else "battery"
        balanced = self.flavor == "balanced"
        self.target_output_fps = int(target_output_fps)
        self.points = with_render_scale(
            budget_points(self.target_output_fps, BALANCED_REAL_FLOOR_FPS if balanced else REAL_FLOOR_FPS))
        # Set by the service every step: the game was launched with the Scaling Engine provisioned
        # (scale-ready launch or the profile's own scaling) and is not CPU-bound.
        self.scale_capable = False
        self.tdp_control = bool(tdp_control)
        hw_min = float(min_tdp_w) if min_tdp_w else 0.0
        hw_max = float(max_tdp_w) if max_tdp_w else self.EMERGENCY_CEILING_W
        self.min_w = max(self.MIN_TDP_W, hw_min)
        self.normal_max_w = min(self.NORMAL_CEILING_W, hw_max)
        self.emergency_max_w = min(self.EMERGENCY_CEILING_W, hw_max)
        start_real = BALANCED_START_REAL_FPS if balanced else START_REAL_FPS
        # Start on an integer ratio: on a Deck they confirmed in ~10 s, while fractional points often
        # ran into the 25 s timeout.  Ties go to the deeper (safer) point.  Fractional ratios stay
        # available for the probes upwards.  (90 Hz: 30x3 / 45x2 as before; 60 Hz Balanced: 30x2.)
        integer = [i for i in range(1, len(self.points)) if float(self.points[i].multiplier).is_integer()
                   and self.points[i].render_scale_pct == 100]
        self.idx = min(integer or range(1, len(self.points)),
                       key=lambda i: (abs(self.points[i].base_target_fps - start_real), self.points[i].base_target_fps))
        self.comfort_idx = self.idx  # deeper than ~30 real only to defend the budget
        self.ideal_max_w = min(BALANCED_IDEAL_MAX_W if balanced else self.IDEAL_MAX_W, self.normal_max_w)
        start_w = BALANCED_START_TDP_W if balanced else self.START_TDP_W
        self.tdp = min(max(start_w, self.min_w), self.normal_max_w) if self.tdp_control else None
        if balanced:
            # No last-resort ratio and no watts beyond the Deck's normal range: Balanced trades
            # some battery for a real-frame floor of 30 and a ceiling it never crosses.
            self.emergency_max_w = self.normal_max_w
        self.phase = "settle"
        self.probe: Optional[str] = None
        self.last_good: Optional[tuple[int, Optional[float]]] = None
        self.prev: Optional[tuple[int, Optional[float]]] = None
        self.good = 0
        self.bad = 0
        self.short_since: Optional[float] = None
        self.stall_since: Optional[float] = None
        self.stall_step_at: Optional[float] = None
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
        self.draw_w: Optional[float] = None   # window median of the measured APU draw
        self.starved_checks = 0
        self.fast_at: Optional[float] = None
        self.held: list[tuple[float, float]] = []   # (time, tdp) of levels that held
        self.last_reason = "budget-start"
        self.not_power_bound_holds = 0
        self.warm_started = False
        # Ceiling of the renderer's current generated-frame resources; updated every step, so it
        # rises again after a swapchain recreation.
        self.current_max_multiplier: Optional[float] = None
        # Point key -> (highest TDP it failed to hold at, when).  Loaded from game memory so a new
        # controller (mode switch, reload) does not repeat a probe that just failed; expires like
        # an in-session rejection, because a lighter scene may hold it later.
        self.known_failures: Dict[str, tuple[float, float]] = {}
        self.new_failures: list[tuple[str, float]] = []  # drained by the service into game memory
        self.verifying: Optional[str] = None  # point inferred from delivered FPS, not yet verified
        # Point index -> (highest TDP a lower-power probe failed at, when, how many times in a row).
        self.floor_failures: Dict[int, tuple[float, float, int]] = {}
        # (point key, TDP or None = cleared, repeats): drained by the service into game memory so a
        # rebuilt controller (mode switch, reload) keeps the remaining back-off (review 1.1.x).
        self.new_floor_failures: list[tuple[str, Optional[float], int]] = []
        self._now = now
        # Host thermal verdict (ok / heating / hot / unknown), set by the service each step.  While
        # the APU heats up, probes towards more real frames (more watts, more heat) wait; probes
        # towards fewer watts continue.  A skipped upgrade is owed and tried once it has cooled.
        self.thermal = "unknown"
        self.thermal_deferred = False
        self._heat_until = -1e9

    def warm_start(self, point_key: str, tdp_w: Optional[float], now: float) -> bool:
        """Start from a remembered point/TDP that held in an earlier session instead of searching.

        Only normal points qualify (never the last-resort point) and the TDP is clamped to what this
        Deck allows without the emergency range.  The usual lock/guard rules still apply: if the
        remembered state does not hold today, the guard escalates exactly as in a fresh search.
        """
        index = next((i for i, p in enumerate(self.points) if p.key == point_key and i > 0), None)
        if index is not None and self.points[index].render_scale_pct != 100 and not self.scale_capable:
            index = None  # remembered at a lower resolution, but this launch cannot scale
        if index is None or self.phase != "settle":
            return False
        self.idx = index
        if self.tdp_control and tdp_w is not None:
            self.tdp = round(min(max(float(tdp_w), self.min_w), self.normal_max_w), 1)
        self.good = self.bad = 0
        self.warm_started = True
        self._lock(now, "warm-start")
        return True

    # ------------------------------------------------------------- targets
    @property
    def point(self) -> OperatingPoint:
        return self.points[self.idx]

    def _usable(self, i: int, now: float) -> bool:
        if not 0 <= i < len(self.points):
            return False
        # Field log: with capacity for 2 generated frames the renderer turned 28x3.25,
        # 26x3.5 and 24x3.75 into a fixed x3 (84/78/72 FPS) and each request timed out.
        if self.current_max_multiplier is not None and float(self.points[i].multiplier) > self.current_max_multiplier + 1e-6:
            return False
        if self.points[i].render_scale_pct != 100 and not self.scale_capable:
            return False
        at = self.rejected.get(self.points[i].key)
        return at is None or now - at >= self.REJECT_TTL_S

    def _move(self, reason: str, *, idx: Optional[int] = None, tdp: Optional[float] = None) -> str:
        self.prev = (self.idx, self.tdp)
        if idx is not None:
            self.idx = idx
        if self.verifying is not None and self.points[self.idx].key != self.verifying:
            self.verifying = None  # left the inferred point before it was verified (a TDP-only move keeps it)
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

    def _binding(self, draw_w: Optional[float]) -> bool:
        return (
            self.tdp is not None and isinstance(draw_w, (int, float))
            and float(draw_w) >= self.tdp - self.DRAW_BINDING_MARGIN_W
        )

    def _remember_held(self, now: float) -> None:
        # Only a level the game actually used: a cap far above the draw says
        # nothing about what the game needs.
        if self.tdp_control and self.tdp is not None and self._binding(self.draw_w):
            self.held = [(t, w) for t, w in self.held if now - t < self.WORK_MEMORY_S]
            self.held.append((now, float(self.tdp)))

    def _work_tdp(self, now: float) -> Optional[float]:
        """The last level the game held at a binding cap: where it goes back after a menu or a pause."""
        recent = [w for t, w in self.held if now - t < self.WORK_MEMORY_S]
        return recent[-1] if recent else None

    def fast_check(self, now: float, real_median: Optional[float], draw_w: Optional[float]) -> str:
        """Called every loop iteration with the last few seconds of real FPS.

        Only ever raises, and only when the measured draw sits at the cap:
        then watts are what the game lacks.  A shortfall with the cap not
        binding (CPU, engine) is the windows' job, which deepen the multiplier
        first.  Up to the ideal budget only; above it the slow path decides.
        """
        self._now = now
        if not (self.tdp_control and self.tdp is not None and not self.cap_ignored):
            self.starved_checks = 0
            return "hold"
        if not isinstance(real_median, (int, float)) or not math.isfinite(float(real_median)):
            return "hold"
        base = float(self.point.base_target_fps)
        short = float(real_median) < base * HOLD_REAL_RATIO
        if not short or not self._binding(draw_w) or self.probe == "up":
            # A fewer-generated-frames probe asks for more real frames on purpose;
            # its own window decides whether the point stays, not extra watts.
            self.starved_checks = 0
            return "hold"
        self.starved_checks += 1
        if self.starved_checks < self.FAST_STARVED_CHECKS:
            return "hold"
        if self.fast_at is not None and now - self.fast_at < self.FAST_GAP_S:
            return "hold"
        return self._fast_raise(now)

    def _fast_raise(self, now: float) -> str:
        if self.probe == "down" and self.last_good is not None:
            # The lower level did not hold: back to the one that did, at once.
            self._note_floor_failure(now)
            idx, tdp = self.last_good
            from_phase = self.phase
            self.probe = None
            self._move("probe-failed:starved", idx=idx, tdp=tdp)
            if from_phase == "search_down":
                self.phase = "upgrade"
                self.good = self.HEALTHY_WINDOWS - 1
            else:
                if from_phase == "probe":  # same back-off as a failed window (_unhealthy)
                    if self.recover is not None:
                        self.recover_interval = min(self.recover_interval * 2.0, self.RECOVER_MAX_S)
                    else:
                        self.reprobe_interval = min(self.reprobe_interval * 2.0, self.REPROBE_MAX_S)
                self._lock(now, "probe-failed:starved")
            self.fast_at, self.starved_checks = now, 0
            return "move"
        ceiling = self.ideal_max_w
        if self.tdp >= ceiling - 1e-6:
            return "hold"   # past the ideal budget the slow path spends multipliers first
        target = max(self._work_tdp(now) or 0.0, self.tdp + self.FAST_STEP_W)
        target = min(target, ceiling)
        self.probe = None
        self._move("fast-raise:starved", tdp=target)
        self.last_good = (self.idx, self.tdp)   # a later failed probe never reverts below this
        self.phase = "locked"
        self.locked_since = now
        self.short_since = self.stall_since = self.stall_step_at = None
        self.fast_at, self.starved_checks = now, 0
        return "move"

    def _probe_delay(self) -> float:
        if self.recover is not None:
            return self.recover_interval
        if self.draw_w is None:
            return max(self.reprobe_interval, self.REPROBE_NO_DRAW_S)
        return self.reprobe_interval

    def _can_lower(self) -> bool:
        # With an ignored cap a "lower" level is fiction: it would hold at any
        # value and walk the label down to the minimum while the APU draws the same.
        return (
            self.tdp_control and not self.cap_ignored
            and self.tdp is not None and self.tdp - 1.0 >= self.min_w - 1e-6
            and not self._floor_blocked(self.tdp - 1.0, self._now)
        )

    def _floor_backoff(self, count: int) -> float:
        return min(self.FLOOR_BACKOFF_S * (2.0 ** max(0, count - 1)), self.FLOOR_BACKOFF_MAX_S)

    def _floor_blocked(self, level: float, now: float) -> bool:
        """``level`` (or a higher one) failed recently with this point: do not probe it yet."""
        known = self.floor_failures.get(self.idx)
        if known is None:
            return False
        failed_w, when, count = known
        if count == 1 and self.draw_w is not None and self.draw_w < level - self.DRAW_BINDING_MARGIN_W:
            # The game now draws clearly less than that level: the scene got lighter.  Only after
            # one failure: a level that failed repeatedly needs more than a (noisy) draw reading.
            return False
        return level <= failed_w + 0.05 and now - when < self._floor_backoff(count)

    def _note_floor_failure(self, now: float) -> None:
        if self.tdp is None:
            return
        previous = self.floor_failures.get(self.idx)
        count = previous[2] + 1 if previous and abs(previous[0] - self.tdp) < 0.05 else 1
        self.floor_failures[self.idx] = (float(self.tdp), now, count)
        self.new_floor_failures.append((self.point.key, float(self.tdp), count))

    def load_floor_failures(self, failures: Dict[str, Any], now: float) -> None:
        """Lower-power failures from game memory: point key -> (tdp, age_s, repeats).

        Anchored at ``now - age`` like ``load_failures``, so the back-off keeps running instead of
        restarting; a point this controller does not have is ignored.
        """
        for key, value in failures.items():
            try:
                tdp, age, count = value
            except (TypeError, ValueError):
                continue
            idx = next((i for i, p in enumerate(self.points) if p.key == key), None)
            if idx is not None:
                self.floor_failures[idx] = (float(tdp), now - float(age), max(1, int(count)))

    @property
    def effective_w(self) -> Optional[float]:
        """Watts the APU actually gets: the cap, or the measured draw when the cap does not bind."""
        if self.cap_ignored and self.draw_w is not None:
            return max(self.tdp or 0.0, self.draw_w)
        return self.tdp

    # ------------------------------------------------------------ evidence
    def observe(self, now: float, verdict: WindowVerdict, real_median: Optional[float] = None) -> str:
        """Feed one fresh window.  Returns ``move`` when the targets changed.

        ``real_median`` is kept for the caller's logs; the decision uses the
        verdict, which measures the real stream against *this point's* cap.  An
        absolute FPS threshold cannot work here: a deep point caps the real
        cadence itself, so it would always look like a power shortage.
        """
        self._now = now
        if verdict.stall:
            # Not evidence about power: neither start nor continue the shortfall clock.
            self.short_since = None
            if self.stall_since is None:
                self.stall_since = self.stall_step_at = now
        else:
            self.stall_since = self.stall_step_at = None
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
        self.verifying = None
        self._remember_held(now)
        self.exhausted = False
        if self.quality_debt is not None and self.idx >= self.quality_debt:
            self.quality_debt = None
        self._clear_recovered()
        was = self.probe
        self.probe = None
        if was == "down" and self.tdp is not None:
            known = self.floor_failures.get(self.idx)
            if known is not None and self.tdp <= known[0] + 0.05:
                del self.floor_failures[self.idx]  # the level holds now: the scene got lighter
                self.new_floor_failures.append((self.point.key, None, 0))
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

    def _upgrade_allowed(self, i: int, now: float) -> bool:
        """A step to fewer generated frames, unless this game already failed it at this TDP or more.

        Field log: 33x2.75 at 10 W was tried three times in one session (each mode
        switch starts a new controller); it never held.
        """
        if not self._usable(i, now):
            return False
        known = self.known_failures.get(self.points[i].key)
        if known is None or now - known[1] >= self.FAILURE_TTL_S:
            return True
        return not (self.tdp is not None and self.tdp <= known[0] + 0.05)

    def _note_failure(self, point: OperatingPoint, now: float) -> None:
        if self.tdp is None:
            return
        previous = self.known_failures.get(point.key)
        worst = max(self.tdp, previous[0]) if previous else self.tdp
        self.known_failures[point.key] = (worst, now)
        self.new_failures.append((point.key, worst))

    def load_failures(self, failures: Dict[str, Any], now: float) -> None:
        """Recent failures of this game from game memory: key -> (tdp, age_s).

        Anchored at ``now - age`` so the original expiry is kept across reloads (PR #40 review:
        re-anchoring at ``now`` turned the TTL into a sliding one).
        """
        for key, value in failures.items():
            tdp, age = value if isinstance(value, (tuple, list)) else (value, 0.0)
            self.known_failures[key] = (float(tdp), now - float(age))

    # The heating verdict comes from a 2-minute temperature slope and flips around its thresholds;
    # once heat has held quality back, the APU must read "ok" for this long before it is released.
    THERMAL_CLEAR_S = 90.0

    def set_thermal(self, state: str, now: float) -> None:
        self.thermal = state
        if state in ("heating", "hot"):
            self._heat_until = now + self.THERMAL_CLEAR_S

    def _heat_word(self) -> str:
        return self.thermal if self.thermal in ("heating", "hot") else "cooling-down"

    @property
    def heat_limited(self) -> bool:
        return self.thermal in ("heating", "hot") or self._now < self._heat_until

    def _upgrade(self, now: float) -> str:
        if self.cap_ignored and self.idx >= self.comfort_idx:
            return self._lock(now, "cap-ignored-quality-held")
        if self._upgrade_allowed(self.idx + 1, now):
            if self.heat_limited:
                self.thermal_deferred = True
                return self._lock(now, f"thermal-quality-held:{self._heat_word()}")
            self.thermal_deferred = False
            self.probe = "up"
            return self._move("testing-fewer-generated-frames", idx=self.idx + 1)
        return self._lock(now, "minimum-power-found")

    def _owed_quality(self) -> bool:
        """Quality was given up to defend watts or a heavy scene and may be won back."""
        return (
            self.idx < self.comfort_idx
            or self.thermal_deferred
            or (self.quality_debt is not None and self.idx < self.quality_debt)
            or (self.recover is not None and self.idx < self.recover[0])
        )

    def _reprobe(self, now: float) -> str:
        # Watts first: try -1 W with the current point.  Upward probes only win
        # back quality that the guard gave up; spare headroom goes to watts.
        kinds = ["down", "up"] if self.next_probe == "down" else ["up", "down"]
        if self.heat_limited:
            kinds = ["down"]  # more real frames would mean more heat
        for kind in kinds:
            if kind == "down" and self._can_lower():
                self.phase, self.probe = "probe", "down"
                self.next_probe = "up" if self._owed_quality() else "down"
                return self._move("reprobe-lower-power", tdp=self.tdp - 1.0)
            if kind == "up" and self._owed_quality() and self._upgrade_allowed(self.idx + 1, now):
                self.phase, self.probe, self.next_probe = "probe", "up", "down"
                self.thermal_deferred = False
                return self._move("reprobe-fewer-generated-frames", idx=self.idx + 1)
        if self.heat_limited and self._owed_quality():
            return self._lock(now, f"thermal-quality-held:{self._heat_word()}")
        return self._lock(now, "budget-point-holds")

    def _unhealthy(self, now: float, verdict: WindowVerdict) -> str:
        self.good = 0
        if self.probe is not None and self.last_good is not None:
            failed = self.points[self.idx]
            if self.probe == "up":
                self.rejected[failed.key] = now
                self._note_failure(failed, now)
            elif self.probe == "down":
                self._note_floor_failure(now)
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
        if verdict.stall:
            # Loading screen / transition: hold, in any phase, until it has lasted
            # long enough to be the game itself.
            if self.stall_step_at is None or now - self.stall_step_at < self.STALL_ESCALATE_S:
                self.last_reason = f"hold-through-stall:{verdict.reason}"
                return "hold"
            self.stall_step_at = now  # one budget step per STALL_ESCALATE_S at most
            return self._escalate(now, verdict)
        self.bad += 1
        if self.phase == "locked" and not verdict.severe and self.bad < self.GUARD_WINDOWS:
            return "hold"
        return self._escalate(now, verdict)

    def _deeper(self, now: float, floor: int = 1) -> Optional[int]:
        """Nearest usable deeper point (>= ``floor``), skipping rejected ones.

        Field log: one rejected neighbour (40x2.25) used to block every deeper point,
        so Balanced sat at 15 W and 80 FPS while 30x3 held 90 FPS at 10 W.
        """
        for i in range(self.idx - 1, floor - 1, -1):
            if self._usable(i, now):
                return i
        return None

    def _escalate(self, now: float, verdict: WindowVerdict) -> str:
        self.bad = 0
        if self.phase != "guard" and self.recover is None:
            # Everything spent from here is a debt to give back when the scene allows.
            self.recover = self.last_good or (self.idx, self.tdp)
        self.phase = "guard"
        self.probe = None
        step = 2.0 if verdict.severe else 1.0
        # Down to ~30 real a deeper multiplier is always cheaper than watts.
        deeper = self._deeper(now, max(1, self.comfort_idx)) if self.idx > self.comfort_idx else None
        if deeper is not None:
            self.quality_debt = max(self.quality_debt or 0, self.idx)
            return self._move(f"guard-deeper-multiplier:{verdict.reason}", idx=deeper)
        # Watts only help a game that uses the watts it has.  A window short of its cap with the
        # measured draw well below the cap (a hitch, streaming, a CPU spike) is not fixed by a
        # higher limit; field log: the guard climbed to 15 W while the APU drew 5-11 W.
        if self._draw_says_not_power_bound(verdict):
            self.last_reason = f"guard-not-power-bound:{verdict.reason}"
            self.not_power_bound_holds += 1  # the service logs each hold (review 1.1.x)
            return "hold"
        # Inside the ideal 9-11 W a watt is cheaper than real FPS below 30.
        if self.tdp_control and self.tdp is not None and self.tdp < self.ideal_max_w - 1e-6:
            return self._move(f"guard-more-power:{verdict.reason}", tdp=min(self.ideal_max_w, self.tdp + step))
        # Defending the 15 W budget: x3.25 .. x3.75 (real 28 .. 24) before more watts.
        deeper = self._deeper(now) if self.idx > 1 else None
        if deeper is not None:
            return self._move(f"guard-deeper-multiplier:{verdict.reason}", idx=deeper)
        if self.tdp_control and self.tdp is not None and self.tdp < self.normal_max_w - 1e-6:
            return self._move(f"guard-more-power:{verdict.reason}", tdp=min(self.normal_max_w, self.tdp + step))
        if self.idx == 1 and self._usable(0, now) and self.flavor != "balanced":
            return self._move(f"guard-emergency-x4:{verdict.reason}", idx=0)
        # Above the normal budget only while the real stream keeps missing the
        # cap of the deepest point there is: that, not an FPS number, is what
        # "the game cannot hold 20-22 real FPS" means.
        if verdict.stall:
            sustained = self.stall_since is not None and now - self.stall_since >= self.STALL_EMERGENCY_S
        else:
            sustained = self.short_since is not None and now - self.short_since >= self.EMERGENCY_SUSTAIN_S
        if (
            sustained and self.tdp_control and self.tdp is not None
            and self.tdp < self.emergency_max_w - 1e-6
        ):
            return self._move(f"guard-emergency-power:{verdict.reason}", tdp=min(self.emergency_max_w, self.tdp + 1.0))
        self.exhausted = True
        self.last_reason = f"budget-exhausted:{verdict.reason}"
        return "hold"

    NOT_POWER_BOUND_MARGIN_W = 2.5

    def _draw_says_not_power_bound(self, verdict: WindowVerdict) -> bool:
        if verdict.stall or not self.tdp_control or self.tdp is None or self.draw_w is None:
            return False
        return float(self.draw_w) < float(self.tdp) - self.NOT_POWER_BOUND_MARGIN_W

    def request_failed(self, now: float, reason: str, observed: Optional[Dict[str, float]] = None) -> None:
        """The renderer never confirmed the requested point: mark it and fall back.

        ``observed`` (real/output medians since the request) covers the case seen on a Deck:
        asked for 40x2.25, the GPU could not feed 40 real, and the adaptive renderer delivered
        the full target at about 30 real (x3).  That is a deeper point holding, not a broken
        renderer: go straight to the point matching what was delivered.
        """
        failed = self.points[self.idx]
        self.rejected[failed.key] = now
        if self.probe == "up":
            self._note_failure(failed, now)  # an upgrade the renderer could not deliver at this TDP
        delivered = self._delivered_point(observed, failed, now)
        if delivered is not None:
            self.request_failures = 0
            self.probe = None
            self.good = self.bad = 0
            # ``prev`` keeps the point that was live before the failed request: if the delivered
            # point is not confirmed either, that is where to fall back (audit 1.0.7), never the
            # point that just failed.
            self.idx = delivered
            # An observation, not a verification: the service requests this point from the
            # renderer (confirmed on fresh samples), and only HEALTHY_WINDOWS fresh windows
            # (real p5, output, misses, hard pressure, pacing) make it a held point.
            self.phase = "guard" if self.phase in ("locked", "probe", "guard") else self.phase
            self.verifying = self.points[delivered].key
            self.last_reason = f"request-failed-use-delivered:{reason}"
            return
        self.request_failures += 1
        self.probe = None
        self.good = self.bad = 0
        self._clear_recovered()
        if self.prev is not None and self.prev[0] != self.idx and self._usable(self.prev[0], now):
            self.idx = self.prev[0]
        else:
            # Nothing applied yet: try the next usable point, cheapest-first from here.
            options = [i for i in range(len(self.points)) if i >= 1 and self._usable(i, now)]
            if options:  # ties go to the deeper (safer) point
                self.idx = min(options, key=lambda i: (abs(i - self.idx), i))
        if self.request_failures >= self.MAX_REQUEST_FAILURES:
            self.exhausted = True
        if self.verifying is not None and self.points[self.idx].key != self.verifying:
            self.verifying = None
        self.phase = "guard" if self.phase in ("locked", "probe", "guard") else self.phase
        self.last_reason = f"request-failed:{reason}"

    def _delivered_point(self, observed: Optional[Dict[str, float]], failed: OperatingPoint,
                         now: float) -> Optional[int]:
        if not observed:
            return None
        real, out = observed.get("real"), observed.get("output")
        if not (isinstance(real, (int, float)) and isinstance(out, (int, float)) and real > 0):
            return None
        if out < 0.94 * self.target_output_fps or real >= 0.95 * failed.base_target_fps:
            return None  # target not delivered, or the cap was reached: a real renderer failure
        options = [i for i in range(1, len(self.points))
                   if self._usable(i, now) and self.points[i].base_target_fps <= real * 1.03]
        return max(options) if options else None

    def status(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "point": self.point.key,
            "tdp_w": self.tdp,
            "tdp_control": self.tdp_control,
            "tier": budget_tier(self.effective_w, self.point),
            "probe": self.probe,
            "last_good": (
                {"point": self.points[self.last_good[0]].key, "tdp_w": self.last_good[1]}
                if self.last_good else None
            ),
            "rejected": sorted(self.rejected),
            "reprobe_interval_s": self._probe_delay(),
            "work_tdp_w": max((w for _, w in self.held), default=None),
            "recovering_to": (
                {"point": self.points[self.recover[0]].key, "tdp_w": self.recover[1]} if self.recover else None
            ),
            "exhausted": self.exhausted,
            "cap_ignored": self.cap_ignored,
            "warm_started": self.warm_started,
            "flavor": self.flavor,
            "verifying": self.verifying,
            "current_max_multiplier": self.current_max_multiplier,
            "thermal": self.thermal,
            "scale_capable": self.scale_capable,
            "thermal_deferred": self.thermal_deferred,
            "heat_limited": self.heat_limited,
            "known_failures": {k: v[0] for k, v in self.known_failures.items()},
            "floor_w": (lambda f: f[0] if f and self._now - f[1] < self._floor_backoff(f[2]) else None)(
                self.floor_failures.get(self.idx)),
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
