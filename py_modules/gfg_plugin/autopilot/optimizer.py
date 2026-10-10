"""Feasibility filter and Pareto choice. No files, actuators or Saved writes.

Axes, higher is better except draw and transition cost. Close points hold.
A small FPS gain does not justify a large power increase. Thresholds live here.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from .contracts import Bottleneck as B, number
from .policy import Action, Knob, Strategy


@dataclass(frozen=True)
class OptimizerConfig:
    min_real_gain: float = 2.0
    max_w_per_real_fps: float = 1.0
    min_draw_save_w: float = 1.0
    min_scale: float = 0.90
    tie_fps: float = 1.0
    tie_w: float = 0.5

    def __post_init__(self):
        values = (self.min_real_gain, self.max_w_per_real_fps, self.min_draw_save_w,
                  self.min_scale, self.tie_fps, self.tie_w)
        if any(number(v) is None or v < 0 for v in values) or not 0 < self.min_scale <= 1:
            raise ValueError("invalid optimizer thresholds")


@dataclass(frozen=True)
class Candidate:
    knob: str
    value: float
    real_delivery: float
    output_stability: float
    render_fidelity: float
    power_draw: float
    transition_cost: float
    measured: bool = True
    requires: Tuple[str, ...] = ()
    evidence_ref: str = ""

    @property
    def tradeoff(self):
        return (self.real_delivery, self.output_stability, self.render_fidelity,
                self.power_draw, self.transition_cost)


def _better(left, right, config):
    """True when left strictly dominates right outside the tie band."""
    if abs(left.real_delivery - right.real_delivery) <= config.tie_fps \
            and abs(left.output_stability - right.output_stability) <= config.tie_fps \
            and abs(left.render_fidelity - right.render_fidelity) <= config.tie_fps \
            and abs(left.power_draw - right.power_draw) <= config.tie_w \
            and abs(left.transition_cost - right.transition_cost) <= config.tie_w:
        return False
    not_worse = (
        left.real_delivery + config.tie_fps >= right.real_delivery
        and left.output_stability + config.tie_fps >= right.output_stability
        and left.render_fidelity + config.tie_fps >= right.render_fidelity
        and left.power_draw <= right.power_draw + config.tie_w
        and left.transition_cost <= right.transition_cost + config.tie_w
    )
    strictly = (
        left.real_delivery > right.real_delivery + config.tie_fps
        or left.output_stability > right.output_stability + config.tie_fps
        or left.render_fidelity > right.render_fidelity + config.tie_fps
        or left.power_draw + config.tie_w < right.power_draw
        or left.transition_cost + config.tie_w < right.transition_cost
    )
    return not_worse and strictly


def feasible(candidate, *, ceiling_w, user_min_scale, allow_scale_80, capabilities,
             user_scale_locked, frame_os_allowed, ack_ok, gpu_bound, cpu_bound):
    if not candidate.measured or number(candidate.real_delivery) is None or number(candidate.output_stability) is None:
        return "unmeasured"
    if candidate.knob == "frame_os_act" and not frame_os_allowed:
        return "frame-os-act-not-consented"
    if candidate.knob not in capabilities:
        return "capability-unavailable"
    if candidate.knob == Knob.POWER_CAP.value and (ceiling_w is None or candidate.value > ceiling_w):
        return "above-power-ceiling"
    if candidate.knob == "render_scale":
        if user_scale_locked:
            return "user-scale-locked"
        if candidate.value < user_min_scale - 1e-9:
            return "below-user-scale"
        if candidate.value <= 0.80 + 1e-9 and not allow_scale_80:
            return "scale-80-not-opted-in"
    if candidate.knob == "fg_ratio" and "renderer-capacity" not in capabilities:
        return "renderer-capacity-unconfirmed"
    if candidate.knob == "cpu_cap" and gpu_bound:
        return "cpu-boost-not-gpu-relevant"
    if candidate.knob == "render_scale" and cpu_bound and candidate.value < 1:
        return "scale-will-not-fix-cpu"
    if not ack_ok and candidate.knob != "current":
        return "renderer-ack-missing"
    if any(need not in capabilities for need in candidate.requires):
        return "requirement-unavailable"
    return None


def select(points, current, *, perception, ceiling_w=None, user_min_scale=0.90,
           allow_scale_80=False, capabilities=(), user_scale_locked=False,
           frame_os_allowed=False, ack_ok=True, config=OptimizerConfig()):
    """Return (action, strategy, chosen, rejected, reason). chosen is None on HOLD."""
    gpu_bound = perception.primary is B.GPU_LIMITED or B.GPU_LIMITED in perception.secondary
    cpu_bound = perception.primary is B.CPU_LIMITED or B.CPU_LIMITED in perception.secondary
    thermal = perception.primary is B.THERMAL_LIMITED or B.THERMAL_LIMITED in perception.secondary
    rejected = []
    allowed = []
    for point in points:
        reason = feasible(point, ceiling_w=ceiling_w, user_min_scale=user_min_scale,
                          allow_scale_80=allow_scale_80, capabilities=set(capabilities),
                          user_scale_locked=user_scale_locked, frame_os_allowed=frame_os_allowed,
                          ack_ok=ack_ok, gpu_bound=gpu_bound, cpu_bound=cpu_bound)
        if reason:
            rejected.append((point.knob, point.value, reason))
            continue
        if thermal and point.power_draw > current.power_draw + config.tie_w:
            rejected.append((point.knob, point.value, "heat-blocks-higher-draw"))
            continue
        allowed.append(point)
    if current.knob != "current":
        raise ValueError("current point must be the held baseline")
    front = [point for point in allowed
             if not any(_better(other, point, config) for other in allowed if other is not point)]
    front.sort(key=lambda point: (point.knob, point.value))
    worthy = []
    for point in front:
        if point.knob == "current":
            worthy.append(point)
            continue
        real_gain = point.real_delivery - current.real_delivery
        extra_w = point.power_draw - current.power_draw
        fidelity_loss = current.render_fidelity - point.render_fidelity
        stability_loss = current.output_stability - point.output_stability
        if fidelity_loss > config.tie_fps or stability_loss > config.tie_fps:
            rejected.append((point.knob, point.value, "quality-or-stability-regression"))
            continue
        if extra_w > config.tie_w and (real_gain < config.min_real_gain
                                       or extra_w > real_gain * config.max_w_per_real_fps):
            rejected.append((point.knob, point.value, "watts-not-worth-the-gain"))
            continue
        if extra_w >= -config.tie_w and real_gain < config.min_real_gain \
                and current.power_draw - point.power_draw < config.min_draw_save_w:
            rejected.append((point.knob, point.value, "gain-below-threshold"))
            continue
        worthy.append(point)
    others = [point for point in worthy if point.knob != "current"]
    if len(others) != 1:
        strategy = Strategy.THERMAL_STABILITY if thermal else Strategy.CRUISE
        return Action.HOLD, strategy, None, tuple(rejected), "tie-or-no-benefit"
    chosen = others[0]
    if chosen.power_draw + config.tie_w < current.power_draw:
        strategy = Strategy.EFFICIENCY
    elif thermal:
        strategy = Strategy.THERMAL_STABILITY
    else:
        strategy = Strategy.EFFICIENCY
    return Action.TRIAL, strategy, chosen, tuple(rejected), "one-nondominated-candidate"
