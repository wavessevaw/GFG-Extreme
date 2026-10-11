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
    multiplier: float | None = None
    multiplier_confirmed: bool = False
    frametime_p99_ms: float | None = None
    frametime_jitter_ms: float | None = None
    battery_pct: float | None = None
    battery_minutes: float | None = None
    external_power: bool | None = None
    tdp_readable: bool = False
    tdp_error: str | None = None
    tdp_external_change: bool = False
    shading_available: bool = False
    shading_consent: bool = False
    shading_enabled: bool = False


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
    # Governor frametime is measured from *real* frames, not generated output.
    # The output FPS goal must never be used as the real-frame time budget.
    multiplier = _num(view.multiplier)
    expected_real = (target / multiplier if view.multiplier_confirmed and multiplier and multiplier > 0
                     and target is not None else real)
    frame_ok = (frame is not None and expected_real is not None and expected_real > 0
                and frame <= (1000.0 / expected_real) * 1.6)
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
        if (gpu is not None and gpu >= 90 and view.shading_consent
                and view.shading_available and not view.shading_enabled):
            return done("OPTIMIZE_SHADING", "gpu-shader-limited", "half-rate-shading",
                        "reduce_gpu_fragment_cost",
                        "Testing Steam Half Rate Shading. Image quality may decrease.")
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


class TargetPolicy:
    """Choose an achievable goal from fresh, non-overlapping evidence windows.

    A lower output goal is a *trial*, not a permanent trap: after sustained
    healthy play at the lower goal, cautiously retry the display goal.
    Rejected retries are backed off to avoid 60/90 flapping.
    """

    RECOVERY_S = 90.0
    RETRY_BACKOFF_S = 240.0
    MIN_GOAL_SPAN_S = 2.0

    def __init__(self) -> None:
        self.target = None
        self.pending = None
        self.pending_n = 0
        self.last_seq = 0
        self.next_recovery_at = 0.0
        self.recovery_attempted = False
        self.display_goal = None
        self._fallback_time = 0.0

    def update(self, display_hz, real_fps, output_fps, preference, fresh,
               *, sample_seq=None, first_sample_seq=None, span_s=None, now=None) -> int:
        # now/seq are passed by Governor in production; the optional arguments
        # keep this pure policy usable from independent unit tests.
        if now is None:
            self._fallback_time += 30.0
            now = self._fallback_time
        hz = 90 if _num(display_hz) and display_hz >= 90 else 60
        if self.display_goal != hz:
            self.display_goal = hz
            self.target = hz
            self.pending = None
            self.pending_n = 0
            self.next_recovery_at = 0.0
            self.recovery_attempted = False
            self.last_seq = 0
        if not fresh:
            self.pending = None
            self.pending_n = 0
            return self.target

        # Ignore a repeated or overlapping sliding window. Three calls on the
        # same sample must never be interpreted as three independent misses.
        if sample_seq is not None:
            if (isinstance(sample_seq, bool) or not isinstance(sample_seq, int)
                    or sample_seq <= self.last_seq
                    or not isinstance(first_sample_seq, int)
                    or first_sample_seq <= self.last_seq
                    or span_s is None or span_s < self.MIN_GOAL_SPAN_S):
                return self.target
            self.last_seq = sample_seq

        real, output = _num(real_fps), _num(output_fps)
        if real is None or output is None or real <= 0:
            self.pending = None
            self.pending_n = 0
            return self.target

        if self.target == hz:
            struggling = real < 28 or output < hz * 0.85
            want = (60 if hz == 90 and struggling
                    and ((preference == "battery") or (preference == "auto" and real < 28))
                    else hz)
        else:
            # At a 60 FPS cap the measured output need not reach 90, even if
            # the game now has headroom. Trial an upgrade only after sustained
            # stability and a long cooldown, not by testing for 90 at a 60 cap.
            stable = output >= self.target * 0.95 and real >= self.target / 3.0
            want = hz if stable and now >= self.next_recovery_at else self.target

        if want == self.target:
            self.pending = None
            self.pending_n = 0
            return self.target
        if self.pending != want:
            self.pending, self.pending_n = want, 1
        else:
            self.pending_n += 1
        if self.pending_n < 3:
            return self.target

        previous = self.target
        self.target, self.pending, self.pending_n = want, None, 0
        if want < previous:
            self.next_recovery_at = now + (
                self.RETRY_BACKOFF_S if self.recovery_attempted else self.RECOVERY_S)
        elif want > previous:
            self.recovery_attempted = True
        return self.target
