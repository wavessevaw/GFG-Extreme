"""Fast measured TDP sweep.

A 15-second *budget* for the entire benchmark, not 15 seconds per TDP.
Coarse descending steps, no returns to the ceiling. Every proposed wattage
has been visited; two independent samples at the chosen level are required
before a result may be applied. This is a quick estimate, not a laboratory
measurement or a fabricated FPS-to-watts extrapolation.
"""
from __future__ import annotations
import math
import statistics


def percentile(values, q):
    a = sorted(values)
    if not a:
        raise ValueError("No frame samples")
    p = (len(a) - 1) * q
    lo = int(p)
    return a[lo] + (a[min(lo + 1, len(a) - 1)] - a[lo]) * (p - lo)


def summarize(samples, min_samples=6, min_frames=90):
    frames = [v for s in samples for v in s["frame_ms"]]
    if len(frames) < min_frames or len(samples) < min_samples:
        raise ValueError("Insufficient fresh frame samples")
    rates = [1000 * len(s["frame_ms"]) / sum(s["frame_ms"]) for s in samples]
    draws = [s["draw_w"] for s in samples]
    return dict(
        fps=statistics.median(rates),
        low_fps=percentile(rates, .10),
        p95_ms=percentile(frames, .95),
        p99_ms=percentile(frames, .99),
        frames=len(frames),
        draw_w=statistics.mean(draws),
        draw_error=(1.96 * statistics.stdev(draws) / math.sqrt(len(draws))
                    if len(draws) > 1 else 0.0),
        gpu=statistics.mean(s["gpu"] for s in samples),
        cpu=statistics.mean(s["cpu"] for s in samples),
        temp=max(s["temp"] for s in samples),
    )


class AdaptiveBenchmark:
    MAX_SECONDS = 15.0
    SEARCH_SECONDS = 9.0   # reserve time for final recheck and FG validation
    SETTLE = .70           # next 1 Hz compositor report after a TDP write
    BASE_SAMPLES = 2
    VERIFY_SAMPLES = 2
    STEP_W = 2.0

    def __init__(self):
        self.phase = "idle"
        self.result = None
        self.reason = ""
        self.points = []
        self.last_seq = None

    @property
    def active(self):
        return self.phase in ("settle", "measure")

    def start(self, *, context, mode, ceiling, floor, ladder, now):
        if self.active or self.phase == "result":
            raise ValueError("Benchmark already active")
        if mode not in ("quality", "balanced", "battery", "autopilot"):
            raise ValueError("Unknown performance mode")
        if not (math.isfinite(ceiling) and math.isfinite(floor)
                and 0 < floor <= ceiling <= 60):
            raise ValueError("Unknown power limits")
        self.__init__()
        self.context, self.mode = context, mode
        self.ceiling, self.floor = ceiling, floor
        self.ladder = sorted(set(float(v) for v in ladder
                                 if 0 < v <= context["refresh"]))
        self.started_at = now
        self.deadline = now + self.MAX_SECONDS
        self.baseline = None
        self.candidate = None
        self.target = 0.0
        self._begin(ceiling, "baseline", now)
        return self.watts

    def _begin(self, watts, purpose, now):
        self.watts = float(watts)
        self.purpose = purpose
        self.ready_at = now + self.SETTLE
        self.phase = "settle"
        self.samples = []
        self.last_seq = None

    def abort(self, reason):
        self.phase, self.reason = "aborted", reason
        self.result = None

    def _holds(self, p):
        return (self.target > 0 and
                p["fps"] >= self.target * .98 and
                p["low_fps"] >= self.target * .92 and
                p["p99_ms"] <= 2000 / self.target)

    @staticmethod
    def _comparable(a, b):
        return (a["fps"] > 0 and a["low_fps"] > 0 and
                abs(a["fps"] / b["fps"] - 1) <= .10 and
                abs(a["low_fps"] / b["low_fps"] - 1) <= .15 and
                abs(a["gpu"] - b["gpu"]) <= 25 and
                abs(a["cpu"] - b["cpu"]) <= 25)

    def _finish(self, measured, passed, reason):
        self.result = dict(
            mode=self.mode, context=self.context, target=self.target,
            tdp=self.candidate["tdp"] if self.candidate else self.ceiling,
            measured=measured or self.candidate or self.baseline or {},
            points=self.points.copy(), passed=bool(passed),
            confidence="quick-verified" if passed else "insufficient",
            reason=reason)
        self.phase = "result"

    def _verify(self, now):
        if self.candidate is None:
            self._finish(self.baseline, False,
                         "Target was not achieved at the available power")
            return None
        self._begin(self.candidate["tdp"], "verify", now)
        return self.watts

    def _next(self, now):
        # Never bounce to the ceiling: only lower power until a target fails.
        if self.watts <= self.floor + .01 or now - self.started_at >= self.SEARCH_SECONDS:
            return self._verify(now)
        nxt = max(self.floor, self.watts - self.STEP_W)
        if nxt >= self.watts - .01:
            return self._verify(now)
        self._begin(nxt, "sweep", now)
        return self.watts

    def _valid(self, sample):
        frames = sample.get("frame_ms") or []
        if not isinstance(frames, (list, tuple)) or len(frames) < 12:
            return False
        if not all(isinstance(v, (int, float)) and math.isfinite(v)
                   and 0 < v < 2000 for v in frames):
            return False
        for k in ("draw_w", "gpu", "cpu", "temp"):
            v = sample.get(k)
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                return False
        return sample["draw_w"] > 0

    def feed(self, sample, *, context, now):
        """Return next TDP or None. Caller writes and confirms readback."""
        if not self.active:
            return None
        if context != self.context:
            self.abort("Game or benchmark conditions changed")
            return None
        if sample.get("menu"):
            self.abort("Steam menu opened")
            return None
        # One stale compositor report is not a user cancellation.
        if not sample.get("fresh"):
            return None
        if sample.get("throttled") or (
                isinstance(sample.get("temp"), (int, float))
                and sample["temp"] >= 85):
            self.abort("Thermal protection")
            return None
        tdp = sample.get("tdp")
        if isinstance(tdp, (int, float)) and math.isfinite(tdp):
            if abs(tdp - self.watts) > .25:
                self.abort("TDP changed outside Benchmark")
                return None
        if now >= self.deadline:
            self._finish(self.candidate, False,
                         "15-second budget elapsed without a confirmed result")
            return None
        if now < self.ready_at:
            return None
        self.phase = "measure"
        seq = sample.get("seq")
        if seq is None or seq == self.last_seq:
            return None
        self.last_seq = seq
        if not self._valid(sample):
            return None
        self.latest = sample
        self.samples.append(sample)
        needed = self.BASE_SAMPLES if self.purpose == "baseline" else (
            self.VERIFY_SAMPLES if self.purpose == "verify" else 1)
        if len(self.samples) < needed:
            return None
        p = summarize(self.samples, min_samples=needed, min_frames=12)
        p["tdp"] = self.watts
        self.points.append(dict(p, purpose=self.purpose))
        self.samples = []

        if self.purpose == "baseline":
            self.baseline = p
            hz = self.context["refresh"]
            if self.mode == "quality":
                self.target = p["fps"] * .97
            elif self.mode == "battery":
                self.target = hz / (3 if hz >= 85 else 2)
            elif self.mode == "balanced":
                self.target = min(hz / 2, max(35, min(40, p["low_fps"] * .97)))
            else:
                viable = [v for v in self.ladder if v <= p["low_fps"] * .97]
                self.target = max(viable) if viable else min(self.ladder or [hz/3])
            if not self._holds(p):
                return self._verify(now)
            self.candidate = p
            return self._next(now)

        if self.purpose == "verify":
            passed = self._holds(p) and self._comparable(self.candidate, p)
            self._finish(p, passed, "" if passed else
                         "Final FPS or scene repeatability was not confirmed")
            return None

        # Single quick sample for discovery only. No result is accepted on it.
        if self._holds(p):
            if (self.candidate is None or
                    p["draw_w"] <= self.candidate["draw_w"] + .3):
                self.candidate = p
            return self._next(now)
        return self._verify(now)

    def status(self):
        progress = len(self.points) / 9
        latest = getattr(self, "latest", {})
        frames = latest.get("frame_ms") or []
        native = 1000 * len(frames) / sum(frames) if frames else None
        return dict(
            phase=self.phase, reason=self.reason, result=self.result,
            tdp=getattr(self, "watts", None),
            target=getattr(self, "target", None),
            purpose=getattr(self, "purpose", ""),
            tested=len(self.points), windows=len(getattr(self, "samples", [])),
            window_progress=min(1.0, max(0.0, progress)),
            gpu=latest.get("gpu"), cpu=latest.get("cpu"),
            temp=latest.get("temp"), native_fps=native,
            draw_w=latest.get("draw_w"),
            loss_pct=(100 * (1 - native / self.baseline["fps"])
                      if native is not None and self.baseline else None))
