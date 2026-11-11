"""Measured TDP sweep. No FPS-to-watts extrapolation and no fixed 15 W ceiling.

The service owns hardware and restores it; this state machine only requests tested
power levels. Samples must contain fresh native frame intervals from Gamescope.
"""
from __future__ import annotations
import math
import statistics


def percentile(values, q):
    a = sorted(values)
    p = (len(a) - 1) * q
    lo = int(p)
    return a[lo] + (a[min(lo + 1, len(a) - 1)] - a[lo]) * (p - lo)


def summarize(samples):
    frames = [v for s in samples for v in s['frame_ms']]
    if len(frames) < 90 or len(samples) < 6:
        raise ValueError('Insufficient fresh frame samples')
    rates = [1000 * len(s['frame_ms']) / sum(s['frame_ms']) for s in samples]
    # Presentation intervals are quantized to refresh (e.g. 40 FPS at 90 Hz).
    # Inverting their median would falsely report 45 FPS and a 30 FPS low.
    fps = statistics.median(rates)
    low = percentile(rates, .10)
    return dict(fps=fps, low_fps=low, p95_ms=percentile(frames, .95),
                p99_ms=percentile(frames, .99), frames=len(frames),
                draw_w=statistics.mean(s['draw_w'] for s in samples),
                draw_error=1.96*statistics.stdev(s['draw_w'] for s in samples)/math.sqrt(len(samples)),
                gpu=statistics.mean(s['gpu'] for s in samples),
                cpu=statistics.mean(s['cpu'] for s in samples),
                temp=max(s['temp'] for s in samples))


class AdaptiveBenchmark:
    SETTLE = 3.0
    WINDOW = 6
    MAX_RETRIES = 2

    def __init__(self):
        self.phase = 'idle'
        self.result = None
        self.reason = ''
        self.points = []
        self.last_seq = None

    @property
    def active(self):
        return self.phase in ('settle', 'measure')

    def start(self, *, context, mode, ceiling, floor, ladder, now):
        if self.active or self.phase == 'result':
            raise ValueError('Benchmark already active')
        if mode not in ('quality', 'balanced', 'battery', 'autopilot'):
            raise ValueError('Unknown performance mode')
        if not (math.isfinite(ceiling) and math.isfinite(floor) and 0 < floor <= ceiling <= 60):
            raise ValueError('Unknown power limits')
        self.__init__()
        self.context, self.mode = context, mode
        self.ceiling, self.floor = ceiling, floor
        self.ladder = sorted(set(float(v) for v in ladder if 0 < v <= context['refresh']))
        self.baseline = None
        self.target = 0
        self.candidate = None
        self.steps = 0
        self.retries = 0
        self._begin(ceiling, 'baseline', now)
        return self.watts

    def _begin(self, watts, purpose, now):
        self.watts, self.purpose = watts, purpose
        self.phase, self.ready_at = 'settle', now + self.SETTLE
        self.samples, self.windows = [], []
        self.last_seq = None
        self.deadline = now + 60

    def abort(self, reason):
        self.phase, self.reason = 'aborted', reason
        self.result = None

    def _holds(self, p):
        return p['fps'] >= self.target * .99 and p['low_fps'] >= self.target * .93 and p['p99_ms'] <= 2000 / max(1, self.target)

    def _comparable(self, a, b):
        # At identical power, a changed scene invalidates the comparison.
        return abs(a['fps'] / b['fps'] - 1) <= .07 and abs(a['low_fps'] / b['low_fps'] - 1) <= .12 and abs(a['gpu'] - b['gpu']) <= 20 and abs(a['cpu'] - b['cpu']) <= 20

    def feed(self, sample, *, context, now):
        """Return a new requested power level, or None. Caller confirms readback."""
        if not self.active:
            return None
        if context != self.context:
            self.abort('Game, display, power source or image settings changed')
            return None
        if sample.get('menu') or not sample.get('fresh'):
            self.abort('Game lost focus or compositor status became stale')
            return None
        if sample.get('temp', 100) >= 85 or sample.get('throttled'):
            self.abort('Thermal limit or throttling detected')
            return None
        if abs(sample.get('tdp', -100) - self.watts) > .25:
            self.abort('Power limit changed externally')
            return None
        if now > self.deadline:
            self.abort('Insufficient stable measurements')
            return None
        if now < self.ready_at:
            return None
        self.phase = 'measure'
        if sample.get('seq') == self.last_seq:
            return None
        self.last_seq = sample.get('seq')
        values = sample.get('frame_ms', [])
        if not values or not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 < v < 2000 for v in values):
            return None
        if not all(isinstance(sample.get(k), (int, float)) and math.isfinite(sample[k]) for k in ('draw_w', 'gpu', 'cpu', 'temp')) or sample['draw_w'] <= 0:
            return None
        self.latest = sample
        self.samples.append(sample)
        if len(self.samples) < self.WINDOW:
            return None
        try:
            window = summarize(self.samples)
        except ValueError:
            return None
        self.samples = []
        self.windows.append(window)
        if len(self.windows) < 2:
            return None
        a, b = self.windows[-2:]
        if not self._comparable(a, b):
            self.retries += 1
            self.windows = [b]
            if self.retries > self.MAX_RETRIES:
                self.abort('Scene load is not repeatable')
            return None
        p = {k: (a[k] + b[k]) / 2 for k in a}
        p['tdp'] = self.watts
        self.points.append(dict(p, purpose=self.purpose))
        self.retries = 0
        if self.purpose == 'baseline':
            self.baseline = p
            hz = self.context['refresh']
            if self.mode == 'quality':
                self.target = p['fps'] * .97
            elif self.mode == 'battery':
                self.target = hz / (3 if hz >= 85 else 2)
            elif self.mode == 'balanced':
                self.target = min(hz / 2, max(35, min(40, p["low_fps"] / .93)))
            else:
                viable = [v for v in self.ladder if v <= p['low_fps'] / .93]
                self.target = max(viable) if viable else min(self.ladder)
            if not self._holds(p):
                self.candidate = p
                return self._verify(now)
            self.candidate = p
            return self._lower(now)
        if self.purpose == 'control':
            if not self._comparable(self.baseline, p):
                self.abort('Baseline changed during sweep; repeat in a stable scene')
                return None
            self._begin(self.next_watts, 'sweep', now)
            return self.watts
        if self.purpose == 'verify':
            passed = self._holds(p) and self._comparable(self.candidate, p)
            self.result = dict(mode=self.mode, context=self.context, target=self.target,
                               tdp=self.watts, measured=p, points=self.points.copy(),
                               passed=passed, confidence='repeated' if passed else 'insufficient',
                               reason='' if passed else 'Target or repeatability not achieved')
            self.phase = 'result'
            return None
        if self._holds(p):
            # Avoid choosing nominal lower caps without measured power savings.
            if p['draw_w'] + p['draw_error'] < self.candidate['draw_w'] * .98 - self.candidate['draw_error']:
                self.candidate = p
            return self._lower(now)
        if self.mode == 'autopilot':
            viable = [v for v in self.ladder if v < self.target and v <= p['low_fps'] / .93]
            if viable and p['draw_w'] / max(viable) < self.candidate['draw_w'] / self.target * .95:
                self.target = max(viable)
                self.candidate = p
                return self._lower(now)
        return self._verify(now)

    def _lower(self, now):
        if self.watts <= self.floor:
            return self._verify(now)
        target = max(self.floor, self.watts - 1)
        self.steps += 1
        if self.steps % 2 == 0:
            self.next_watts = target
            self._begin(self.ceiling, 'control', now)
        else:
            self._begin(target, 'sweep', now)
        return self.watts

    def _verify(self, now):
        self._begin(self.candidate['tdp'], 'verify', now)
        return self.watts

    def status(self):
        return dict(phase=self.phase, reason=self.reason, result=self.result,
                    tdp=getattr(self, 'watts', None), target=getattr(self, 'target', None),
                    purpose=getattr(self, 'purpose', ''), tested=len(self.points),
                    windows=len(getattr(self, 'windows', [])),
                    native_fps=(1000*len(self.latest['frame_ms'])/sum(self.latest['frame_ms'])) if hasattr(self,'latest') else None,
                    draw_w=getattr(self,'latest',{}).get('draw_w'),
                    loss_pct=(100*(1-1000*len(self.latest['frame_ms'])/sum(self.latest['frame_ms'])/self.baseline['fps'])) if hasattr(self,'latest') and self.baseline else None)
