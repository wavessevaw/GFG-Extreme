"""Pure C2 decisions. No files, actuators or Saved writes.

The two tools this slice may name are the power cap and flow scale. Naming one
is not permission to apply it: arming stays off until a later adapter exists.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .contracts import Bottleneck as B, Perception, number


class Action(str, Enum):
    HOLD = "HOLD"
    OBSERVE = "OBSERVE"
    RESTORE = "RESTORE"
    TRIAL = "TRIAL"
    RECOVER = "RECOVER"


class Strategy(str, Enum):
    CRUISE = "CRUISE"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    EFFICIENCY = "EFFICIENCY"
    RECOVERY = "RECOVERY"
    THERMAL_STABILITY = "THERMAL_STABILITY"


class Knob(str, Enum):
    POWER_CAP = "power_cap"
    FLOW_SCALE = "flow_scale"


@dataclass(frozen=True)
class Decision:
    action: Action
    strategy: Strategy
    reason: str
    knob: Optional[Knob] = None
    confidence: float = 0.0
    evidence_ids: Tuple[str, ...] = ()
    armed: bool = False
    release_slot: bool = False

    def public(self):
        return {
            "stage": "C2", "action": self.action.value, "strategy": self.strategy.value,
            "reason": self.reason, "knob": None if self.knob is None else self.knob.value,
            "confidence": self.confidence, "evidence_ids": list(self.evidence_ids),
            "armed": False, "control_enabled": False, "release_slot": self.release_slot,
            "tools": ["power_cap", "flow_scale"],
            "limitation": "Decision only. Actuators are not connected, so a trial cannot start.",
        }


def choose(candidates):
    """One feasible tool, or none. A tie keeps the current point."""
    unique = tuple(dict.fromkeys(candidates))
    if len(unique) != 1:
        return None
    return unique[0]


def decide(perception: Perception, *, now, restore_pending=False, flow_available=False,
           power_ceiling_w=None, slot_busy=False, slot_knob=None):
    if number(now) is None:
        raise ValueError("finite monotonic time required")
    evidence = perception.evidence_ids
    if restore_pending or perception.reason == "restore-pending":
        return Decision(Action.RESTORE, Strategy.RECOVERY, "restore-pending",
                        evidence_ids=evidence, release_slot=True)
    if slot_busy:
        knob = slot_knob if slot_knob in (Knob.POWER_CAP, Knob.FLOW_SCALE) else None
        if perception.stale or perception.primary is B.UNKNOWN:
            return Decision(Action.OBSERVE, Strategy.OBSERVE_ONLY, "evidence-lost",
                            knob=knob, evidence_ids=evidence, release_slot=True)
        return Decision(Action.TRIAL, Strategy.EFFICIENCY, "single-flight-in-progress",
                        knob=knob, confidence=perception.confidence, evidence_ids=evidence)
    if (perception.stale or perception.primary is B.UNKNOWN
            or perception.reason in ("external-backend-observe-only", "snapshot-stale")):
        return Decision(Action.OBSERVE, Strategy.OBSERVE_ONLY,
                        perception.reason or "insufficient-evidence", evidence_ids=evidence)
    if perception.primary is B.THERMAL_LIMITED or B.THERMAL_LIMITED in perception.secondary:
        return Decision(Action.HOLD, Strategy.THERMAL_STABILITY, "heat-blocks-trials",
                        confidence=perception.confidence, evidence_ids=evidence)
    if perception.primary is B.STABLE:
        return Decision(Action.HOLD, Strategy.CRUISE, "delivery-held",
                        confidence=perception.confidence, evidence_ids=evidence)
    candidates = []
    causes = (perception.primary,) + tuple(perception.secondary)
    if B.GPU_LIMITED in causes and flow_available:
        candidates.append(Knob.FLOW_SCALE)
    ceiling = number(power_ceiling_w)
    if B.POWER_LIMITED in causes and ceiling is not None and ceiling > 0:
        candidates.append(Knob.POWER_CAP)
    # CPU-bound is not treated by lowering render scale or by a CPU boost.
    knob = choose(candidates)
    if knob is None:
        reason = "cpu-bound-no-scale-or-boost" if perception.primary is B.CPU_LIMITED else "no-single-safe-tool"
        return Decision(Action.HOLD, Strategy.CRUISE, reason,
                        confidence=perception.confidence, evidence_ids=evidence)
    return Decision(Action.TRIAL, Strategy.EFFICIENCY, "candidate-not-armed", knob=knob,
                    confidence=perception.confidence, evidence_ids=evidence)
