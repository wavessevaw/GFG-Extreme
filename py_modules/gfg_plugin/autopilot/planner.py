"""Choose one strategy from the Governor's own telemetry.

The planner never writes TDP, clocks or overlays. A missing measurement stays
missing: a target FPS is not a measured Real FPS.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class View:
    real_fps: float | None
    output_fps: float | None
    frametime_p95_ms: float | None
    target_fps: float | None
    gpu_busy: float | None
    cpu_busy: float | None
    gpu_mhz: float | None
    temp_c: float | None
    draw_w: float | None
    ceiling_w: float | None
    fresh: bool
    samples: int
    gpu_clock_available: bool
    preference: str = "auto"


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    tool: str
    expected_effect: str
    confidence: float
    message: str
    measured_real_fps: float | None
    measured_output_fps: float | None


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def decide(view: View) -> Decision:
    real, output = _num(view.real_fps), _num(view.output_fps)
    target = _num(view.target_fps)
    confidence = 0.9 if view.fresh and view.samples >= 8 else 0.55

    def done(action, reason, tool, effect, message):
        return Decision(action, reason, tool, effect, confidence, message, real, output)

    if not view.fresh or real is None or output is None or view.samples < 5:
        return done("PAUSE", "telemetry-not-fresh", "none", "none",
                    "Lost reliable telemetry. Optimization is paused.")
    temp = _num(view.temp_c)
    if temp is not None and temp >= 90:
        return done("PAUSE", "thermal-limited", "none", "protect",
                    "Temperature is critical. Experiments are stopped.")
    if temp is not None and temp >= 85:
        return done("HOLD", "thermal-watch", "none", "protect",
                    "Temperature is high. Holding the current configuration.")

    meeting = target is None or output >= target * 0.92
    frame = _num(view.frametime_p95_ms)
    frame_ok = frame is None or target is None or target <= 0 or frame <= (1000.0 / target) * 1.6
    cpu, gpu = _num(view.cpu_busy), _num(view.gpu_busy)
    ceiling, draw = _num(view.ceiling_w), _num(view.draw_w)
    power_bound = ceiling is not None and draw is not None and draw >= ceiling - 1.2

    if meeting and frame_ok and view.preference == "smoothness":
        return done("HOLD", "smoothness-held", "none", "hold",
                    "Stable frame rate. Keeping it smooth.")
    if meeting and frame_ok and view.preference == "auto" and not _has_power_headroom(draw, ceiling):
        return done("HOLD", "already-efficient", "none", "hold",
                    "Stable frame rate. No change is justified.")
    if not meeting:
        if cpu is not None and gpu is not None and cpu >= 85 and gpu <= 70 and view.gpu_clock_available:
            return done("OPTIMIZE_GPU_CLOCK", "probable-cpu-bottleneck", "gpu-clock",
                        "increase_real_fps", "CPU looks limiting. Checking one lower GPU clock ceiling.")
        if power_bound or (gpu is not None and gpu >= 90):
            return done("OPTIMIZE_POWER", "power-or-gpu-limited", "budget",
                        "increase_real_fps", "The GPU needs the power Governor can safely give.")
        return done("HOLD", "bottleneck-unknown", "none", "hold",
                    "The limit is not clear. Holding the current configuration.")
    if view.preference == "battery" or _has_power_headroom(draw, ceiling):
        return done("OPTIMIZE_POWER", "save-power", "budget",
                    "reduce_power", "Stable frame rate. Looking for a lower power point.")
    return done("HOLD", "already-efficient", "none", "hold",
                "Working configuration confirmed.")


def _has_power_headroom(draw, ceiling):
    return draw is not None and ceiling is not None and draw + 2 <= ceiling
