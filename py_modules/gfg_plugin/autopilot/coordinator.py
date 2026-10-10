"""Pure orchestrator. It returns a decision and does not touch an actuator."""
from .contracts import Bottleneck as B, number
from .optimizer import OptimizerConfig, select
from .policy import Action, Decision, Knob, Strategy


class MemoryView:
    """Read-only facts. The coordinator never records an inconclusive trial."""

    def __init__(self, strategy=None, strategy_at=None, last_verified=None, blocked=()):
        self.strategy = strategy
        self.strategy_at = strategy_at
        self.last_verified = last_verified
        self.blocked = tuple(blocked)

    def blocks(self, point):
        return (point.knob, point.value) in self.blocked


def plan(perception, points, current, *, now, restore_pending=False, dwell_s=30.0,
         memory=None, starvation=False, config=OptimizerConfig(), **limits):
    if number(now) is None:
        raise ValueError("finite monotonic time required")
    evidence = perception.evidence_ids
    if restore_pending or perception.reason == "restore-pending":
        return Decision(Action.RESTORE, Strategy.RECOVERY, "restore-pending",
                        evidence_ids=evidence, release_slot=True)
    if perception.reason == "external-backend-observe-only" or perception.primary is B.UNKNOWN or perception.stale:
        return Decision(Action.OBSERVE, Strategy.OBSERVE_ONLY,
                        perception.reason or "insufficient-evidence", evidence_ids=evidence)
    hidden = []
    if memory is not None:
        visible = []
        for point in points:
            if memory.blocks(point):
                hidden.append((point.knob, point.value, "backed-off"))
            else:
                visible.append(point)
        points = tuple(visible)
    verified = None if memory is None else memory.last_verified
    if verified is not None and current.output_stability + config.tie_fps < verified.output_stability:
        return Decision(Action.RECOVER, Strategy.RECOVERY, "delivery-below-last-verified",
                        evidence_ids=evidence, candidate_value=verified.value, release_slot=True)
    action, strategy, chosen, rejected, reason = select(
        points, current, perception=perception, config=config, **limits)
    rejected = hidden + list(rejected)
    if memory is not None and memory.strategy is not None and not starvation \
            and perception.primary is not B.THERMAL_LIMITED \
            and number(memory.strategy_at) is not None and 0 <= now - memory.strategy_at < dwell_s \
            and strategy is not memory.strategy and action is not Action.RECOVER:
        return Decision(Action.HOLD, memory.strategy, "hysteresis", evidence_ids=evidence, rejected=rejected)
    knob = None
    if chosen is not None:
        try:
            knob = Knob(chosen.knob)
        except ValueError:
            knob = None
    return Decision(action, strategy, reason, knob=knob, confidence=perception.confidence,
                    evidence_ids=evidence, candidate_value=None if chosen is None else chosen.value,
                    rejected=rejected)
