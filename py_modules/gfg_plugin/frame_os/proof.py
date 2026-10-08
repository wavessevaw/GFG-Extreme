"""A/B proof: Frame OS measures its own effect inside the game.

The benefit rings start as model estimates.  In Act this module replaces them with measurements:
now and then a short *control* window runs with one Act effect switched off, and the windows right
before and after it (effect on) are the comparison.  A-B-A pairs cancel slow drift (heat, a scene
getting heavier); only pairs where the moment stayed the same (same Frame OS level, live pacer, no
gap) count.

Which effect a window tests follows the moment it starts in:

* calm  -> **response**: just-in-time start shaping off, same real cadence and pacing.  Metric:
  frame age at present (pacer ``freshness_ms``).  Positive = Act frames are younger.
* boost -> **frames**: the boost is held at the calm cadence.  Metric: real cadence (pacer present
  interval).  Positive = more real frames with Act.
* rest  -> **energy**: the rest is held at calm.  Metric: measured APU draw.  Positive = less power.

A metric counts as *measured* after ``MIN_PAIRS`` pairs; the summary gives the mean and a 95 %
interval over the pairs.  Control windows are rare (one every ``GAP_S``, longer apart once every
metric is measured) and short, so the game barely notices them.

Pure logic with an injected clock; the runner calls ``observe`` and then ``control`` every tick.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

MIN_PAIRS = 3
SETTLED_PAIRS = 6           # every metric at least this many pairs: tests get rarer
GAP_S = 20.0                # between control windows while learning
SETTLED_GAP_S = 90.0
MIN_FILL = 0.6              # a window needs samples for this share of its length
# T quantiles (95 %, two-sided) for 1..9 degrees of freedom; 2.0 beyond.
_T95 = (12.71, 4.30, 3.18, 2.78, 2.57, 2.45, 2.36, 2.31, 2.26)


@dataclass(frozen=True)
class Test:
    metric: str             # response | frames | energy
    level: str              # the Frame OS level it runs in
    control: str            # no-shaping | hold-calm
    window_s: float
    settle_s: float


TESTS = {
    "calm": Test("response", "calm", "no-shaping", 4.0, 1.0),
    "boost": Test("frames", "boost", "hold-calm", 2.5, 0.7),
    "rest": Test("energy", "rest", "hold-calm", 5.0, 1.5),
}
METRICS = ("response", "frames", "energy")


def _value(test: Test, telemetry: Dict[str, Any], draw_w: Optional[float]) -> Optional[float]:
    if test.metric == "response":
        v = telemetry.get("freshness_ms")
    elif test.metric == "frames":
        iv = telemetry.get("present_interval_p50_ms")
        v = 1000.0 / iv if isinstance(iv, (int, float)) and iv > 0 else None
    else:
        v = draw_w
    return float(v) if isinstance(v, (int, float)) and math.isfinite(v) and v > 0 else None


def _gain(test: Test, a: float, b: float) -> float:
    """Act's benefit in percent of the control value; positive is better for every metric."""
    if test.metric == "frames":
        return 100.0 * (a - b) / b
    return 100.0 * (b - a) / b       # younger frames, lower draw


class Window:
    def __init__(self, start: float, test: Test) -> None:
        self.start, self.test = start, test
        self.sum = 0.0
        self.n = 0
        self.covered = 0.0

    def add(self, value: Optional[float], dt: float) -> None:
        if value is not None:
            self.sum += value * dt
            self.covered += dt

    @property
    def mean(self) -> Optional[float]:
        return self.sum / self.covered if self.covered > 0 else None


class ProofMeter:
    """The A-B-A state machine: ``wait -> before -> control -> after -> wait``."""

    def __init__(self) -> None:
        self.enabled = True
        self.prior: Dict[str, List[float]] = {m: [] for m in METRICS}   # this game's earlier sessions
        self.skip: set = set()          # metrics whose effect is off for this game: nothing to test
        self.reset()

    def reset(self) -> None:
        self.phase = "wait"
        self.test: Optional[Test] = None
        self.window: Optional[Window] = None
        self.before: Optional[float] = None
        self.control_mean: Optional[float] = None
        self.pairs: Dict[str, List[float]] = {m: [] for m in METRICS}
        self.aborted = 0
        self.next_at: Optional[float] = None
        self._last: Optional[float] = None
        self._since: Optional[float] = None       # the current level holds since
        self._level: Optional[str] = None

    # ------------------------------------------------------------------ runner side
    def observe(self, now: float, *, eligible: bool, level: Optional[str], telemetry: Dict[str, Any],
                draw_w: Optional[float]) -> None:
        """One tick of what the game did under the control in effect since the last tick."""
        dt = 0.0 if self._last is None else max(0.0, min(1.0, now - self._last))
        self._last = now
        if level != self._level:
            self._level, self._since = level, now
        if not self.enabled or not eligible:
            self._abort(now, waiting=True)
            return
        if self.next_at is None:
            self.next_at = now + GAP_S
        if self.phase == "wait":
            return
        test = self.test
        assert test is not None and self.window is not None
        if level != test.level:
            self._abort(now)                     # the moment changed: no fair comparison
            return
        if now - self.window.start >= (test.settle_s if self.phase != "before" else 0.0):
            self.window.add(_value(test, telemetry, draw_w), dt)
        if now - self.window.start < test.window_s + (test.settle_s if self.phase != "before" else 0.0):
            return
        mean = self.window.mean if self.window.covered >= MIN_FILL * test.window_s else None
        if mean is None:
            self._abort(now)
            return
        if self.phase == "before":
            self.before, self.phase, self.window = mean, "control", Window(now, test)
        elif self.phase == "control":
            self.control_mean, self.phase, self.window = mean, "after", Window(now, test)
        else:
            a = (self.before + mean) / 2.0       # type: ignore[operator]
            b = self.control_mean
            if b and b > 0:
                self.pairs[test.metric].append(round(_gain(test, a, b), 2))
            self._finish(now)

    def control(self, now: float, level: Optional[str]) -> Optional[str]:
        """What to switch off right now: None, ``"no-shaping"`` or ``"hold-calm"``."""
        if not self.enabled or self._level is None:
            return None
        if self.phase == "wait" and self.next_at is not None and now >= self.next_at:
            test = TESTS.get(level or "")
            if test is not None and test.metric in self.skip:
                test = None
            # the level must already hold for a full window: the "before" window is all one moment
            if test is not None and self._since is not None and now - self._since >= 0.5:
                self.test, self.phase, self.window = test, "before", Window(now, test)
        return self.test.control if self.phase == "control" and self.test else None

    # ------------------------------------------------------------------ results
    def summary(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"enabled": self.enabled, "phase": self.phase,
                               "testing": self.test.metric if self.phase != "wait" and self.test else None,
                               "aborted": self.aborted}
        for metric in METRICS:
            out[metric] = stats(self.prior[metric] + self.pairs[metric])
            out[metric]["session_n"] = len(self.pairs[metric])
        return out

    def load(self, prior: Dict[str, List[float]], skip: Optional[set] = None) -> None:
        """What earlier sessions measured in this game (the rings start measured) and the metrics
        not to test because their effect is off here."""
        self.prior = {m: [float(v) for v in prior.get(m) or []] for m in METRICS}
        self.skip = set(skip or ())

    # ------------------------------------------------------------------ internals
    def _finish(self, now: float) -> None:
        # the moment just tested decides the gap: a settled calm-play metric gets rare even when
        # rests (pauses) are too rare to ever settle the energy metric
        metric = self.test.metric if self.test else None
        settled = metric is not None and len(self.prior[metric]) + len(self.pairs[metric]) >= SETTLED_PAIRS
        self.phase, self.test, self.window = "wait", None, None
        self.before = self.control_mean = None
        self.next_at = now + (SETTLED_GAP_S if settled else GAP_S)

    def _abort(self, now: float, waiting: bool = False) -> None:
        if self.phase != "wait":
            self.aborted += 1
            self.phase, self.test, self.window = "wait", None, None
            self.before = self.control_mean = None
            self.next_at = now + GAP_S / 2.0     # try again soon, in a steadier moment
        elif waiting:
            self.next_at = None                  # the gap starts when Act runs again


def stats(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "low": None, "high": None, "measured": False}
    mean = sum(values) / n
    if n > 1:
        sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
        half = (_T95[n - 2] if n - 1 <= len(_T95) else 2.0) * sd / math.sqrt(n)
    else:
        half = None
    return {"n": n, "mean": round(mean, 1),
            "low": round(mean - half, 1) if half is not None else None,
            "high": round(mean + half, 1) if half is not None else None,
            "measured": n >= MIN_PAIRS}
