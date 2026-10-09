"""Bounded flow-resolution trials; Saved profiles and generator models are unchanged.

One A/B/A trial per stable context. Each resource change requires a fresh
frame-generation ACK from the same renderer context. Benefits are local window
comparisons, never input-to-display latency or a universal FPS promise.
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Optional


def number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


class FlowTrial:
    STABLE_S = 30.0
    WINDOW_S = 8.0
    MIN_SAMPLES = 8
    SETTLE_S = 3.0
    ACK_S = 15.0
    PHASE_S = 30.0

    def __init__(self):
        self.reset()

    def reset(self):
        self.context = None
        self.mode = ""
        self.phase = "idle"
        self.reason = "waiting-for-stable-context"
        self.since = None
        self.started = 0.0
        self.attempted = False
        self.original = None
        self.candidate = None
        self.wanted = None
        self.actual = None
        self.mark = 0
        self.last_seq = -1
        self.samples = []
        self.windows = {}
        self.proof = None
        self.pending_accept = False

    @property
    def busy(self):
        return self.phase in {"a1", "wait-b", "b", "wait-a", "a2", "wait-accept", "wait-restore"}

    def status(self):
        return {"phase": self.phase, "reason": self.reason, "requested": self.wanted,
                "confirmed": self.actual, "original": self.original, "candidate": self.candidate,
                "samples": len(self.samples), "comparison": self.proof,
                "accepted": self.phase == "held"}

    def _request(self, value, phase, now, event_seq):
        self.wanted = value
        self.phase = phase
        self.started = now
        self.mark = event_seq
        self.samples = []
        return value

    def _abort(self, now, event_seq, reason):
        self.reason = reason
        self.pending_accept = False
        self.proof = None
        if self.wanted is not None and (self.wanted != self.original
                                        or self.actual is None or abs(self.actual - self.original) >= .005):
            return self._request(self.original, "wait-restore", now, event_seq)
        self.phase = "done"
        self.wanted = None
        self.attempted = True
        return None

    @staticmethod
    def _window(samples):
        def median(key):
            vals = [s[key] for s in samples if number(s.get(key)) is not None]
            return statistics.median(vals) if len(vals) >= FlowTrial.MIN_SAMPLES else None
        return {"n": len(samples), "real": min(s["real"] for s in samples),
                "output": min(s["output"] for s in samples),
                "draw": median("draw"), "gpu": median("gpu"),
                "p95": max((s["p95"] for s in samples if number(s.get("p95")) is not None), default=None),
                "temp": median("temp")}

    def _judge(self, target):
        a, b, c = self.windows["a1"], self.windows["b"], self.windows["a2"]
        # Reject moving scenes or changing load. Compare B to both adjacent A windows.
        for key in ("real", "output", "draw", "gpu"):
            if a[key] is not None and c[key] is not None:
                if abs(a[key] - c[key]) > max(1.0, .1 * max(a[key], c[key])):
                    return False, "control-window-drift"
        if a["temp"] is not None and c["temp"] is not None and abs(a["temp"] - c["temp"]) > 3:
            return False, "control-temperature-drift"
        real_floor = max(a["real"], c["real"])
        output_floor = max(a["output"], c["output"])
        healthy = (b["real"] >= .97 * real_floor and b["output"] >= .97 * output_floor
                   and b["output"] >= .94 * target)
        p95 = [a["p95"], c["p95"]]
        if b["p95"] is not None and all(v is not None for v in p95):
            healthy = healthy and b["p95"] <= 1.1 * min(p95)
        if not healthy:
            return False, "cadence-regression"
        draws = [a["draw"], c["draw"]]
        energy = (100 * (1 - b["draw"] / min(draws))
                  if all(v is not None and v > 0 for v in draws) and b["draw"] is not None else None)
        gpu = (min(a["gpu"], c["gpu"]) - b["gpu"]
               if all(v is not None for v in (a["gpu"], b["gpu"], c["gpu"])) else None)
        real_gain = 100 * (b["real"] / real_floor - 1) if real_floor > 0 else 0
        output_gain = 100 * (b["output"] / output_floor - 1) if output_floor > 0 else 0
        if self.mode == "quality":
            accepted = energy is not None and energy >= -10
            reason = "higher-flow-resolution-held"
        elif self.mode == "budget":
            accepted = energy is not None and energy >= 5
            reason = "lower-draw-held"
        elif self.mode == "balanced":
            accepted = (energy is not None and energy >= 7) or output_gain >= 5
            reason = "cadence-or-draw-held"
        else:
            accepted = (real_gain >= 5 or output_gain >= 5
                        or (gpu is not None and gpu >= 5 and energy is not None and energy >= 0))
            reason = "generation-headroom-held"
        if accepted:
            self.proof = {"basis": "same-context-a-b-a-windows", "real_floor_change_pct": round(real_gain, 1),
                          "output_floor_change_pct": round(output_gain, 1),
                          "apu_draw_change_pct": round(-energy, 1) if energy is not None else None,
                          "gpu_busy_drop_pp": round(gpu, 1) if gpu is not None else None,
                          "samples_per_window": {name: window["n"] for name, window in self.windows.items()}}
        return accepted, reason if accepted else "no-useful-benefit"

    def step(self, *, now, context, mode, eligible, saved_flow, actual_flow, ack_seq,
             event_seq, sample, target, base_target):
        actual = number(actual_flow)
        if actual is not None:
            self.actual = actual
        if context != self.context:
            # The caller restores Saved before changing profile/point/session.
            self.reset()
            self.context = context
            self.mode = mode
            self.since = now
            self.actual = actual
        if not eligible and self.phase != "wait-restore":
            self.since = None
            if self.busy or self.phase == "held":
                return self._abort(now, event_seq, "context-not-eligible")
            self.reason = "waiting-for-eligible-context"
            return None
        if self.since is None:
            self.since = now
        if self.phase in {"done", "held"}:
            return None
        if (self.busy and self.phase != "wait-restore" and sample is not None
                and sample.get("seq") != self.last_seq):
            # Resource recreation must not hide starvation behind the ACK or
            # settling grace. Return Saved immediately on a fresh severe dip.
            if any(number(sample.get(k)) is None for k in ("real", "output")):
                return self._abort(now, event_seq, "invalid-frame-evidence")
            if sample["real"] < .85 * base_target or sample["output"] < .85 * target:
                return self._abort(now, event_seq, "output-starved")
        if self.phase.startswith("wait-"):
            if actual is not None and ack_seq > self.mark and abs(actual - self.wanted) < .005:
                if self.phase in {"wait-restore", "wait-accept"}:
                    self.phase = "held" if self.phase == "wait-accept" else "done"
                    self.attempted = True
                    if self.phase == "done":
                        self.wanted = None
                    return None
                self.phase = "b" if self.phase == "wait-b" else "a2"
                self.started = now
                self.samples = []
            elif now - self.started > self.ACK_S:
                if self.phase == "wait-restore" and (actual is None or abs(actual - self.original) >= .005):
                    self.reason = "restore-not-confirmed"
                    return self._request(self.original, "wait-restore", now, event_seq)
                if self.phase == "wait-restore":
                    self.phase = "done"
                    self.wanted = None
                    self.reason = "restore-not-confirmed"
                    self.attempted = True
                    return None
                return self._abort(now, event_seq, "flow-change-not-confirmed")
            else:
                return None
        if self.phase == "idle":
            saved = number(saved_flow)
            if (self.attempted or now - self.since < self.STABLE_S or saved is None or actual is None
                    or not .25 <= saved <= 1 or abs(saved - actual) > .005):
                return None
            if sample is None or number(sample.get("gpu")) is None:
                return None
            if mode == "quality":
                if sample["gpu"] > 75:
                    return None
                candidate = min(1.0, round(saved + .1, 2))
            else:
                if mode in {"extreme", "balanced"} and sample["gpu"] < 90:
                    return None
                floor = {"budget": .65, "extreme": .60, "balanced": .70}.get(mode, saved)
                candidate = max(floor, round(saved - .1, 2))
            if abs(candidate - saved) < .005 or (mode != "quality" and candidate >= saved):
                self.reason = "saved-flow-at-policy-bound"
                self.attempted = True
                return None
            self.original, self.candidate = saved, candidate
            self.phase = "a1"
            self.started = now - self.SETTLE_S
            self.samples = []
            self.reason = "testing-generation-workload"
        if now - self.started > self.PHASE_S:
            return self._abort(now, event_seq, "flow-window-timeout")
        if sample is None or sample.get("seq") == self.last_seq or now - self.started < self.SETTLE_S:
            return None
        self.last_seq = sample.get("seq")
        if any(number(sample.get(k)) is None or sample[k] < 0 for k in ("real", "output")):
            return self._abort(now, event_seq, "invalid-frame-evidence")
        if sample["real"] < .85 * base_target or sample["output"] < .85 * target:
            return self._abort(now, event_seq, "output-starved")
        self.samples.append(dict(sample, at=now))
        if len(self.samples) < self.MIN_SAMPLES or now - self.samples[0]["at"] < self.WINDOW_S:
            return None
        self.windows[self.phase] = self._window(self.samples)
        if self.phase == "a1":
            return self._request(self.candidate, "wait-b", now, event_seq)
        if self.phase == "b":
            return self._request(self.original, "wait-a", now, event_seq)
        accepted, self.reason = self._judge(target)
        self.pending_accept = accepted
        if accepted:
            return self._request(self.candidate, "wait-accept", now, event_seq)
        self.phase = "done"
        self.wanted = None
        self.attempted = True
        return None
