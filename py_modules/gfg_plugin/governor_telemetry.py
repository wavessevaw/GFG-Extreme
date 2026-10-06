"""Incremental renderer telemetry for GFG Governor.

The Governor consumes MAKO present diagnostics exactly once and publishes a
small normalized cache.  UI, planning, stability and power control must read
this cache instead of independently rescanning renderer logs.
"""
from __future__ import annotations

import math
import os
import re
import statistics
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Optional


_DIAGNOSTIC_MARKER = "MAKO Renderer: present diagnostics:"
_FIELD_RE = re.compile(r"(?:^|\s)([A-Za-z0-9_-]+)=([^\s]+)")

MISS_OPERATIONS = frozenset({
    "generated-delivery-miss",
    "render-fence-budget-missed",
    "ordered-acquire-budget-exhausted",
    "generated-admission-pressure",
})
HARD_PRESSURE_OPERATIONS = frozenset({
    "generated-delivery-miss",
    "render-fence-budget-missed",
    "ordered-acquire-budget-exhausted",
})
BYPASS_OPERATIONS = frozenset({
    "pipeline-busy-bypass",
    "ordered-acquire-guard-bypass",
})
APPLICATION_OPERATIONS = frozenset({
    "fixed-plan",
    "adaptive-plan",
    "runtime-state-applied",
    "runtime-transition-pending",
    "runtime-transition-prepared",
    "runtime-transition-applied",
    "runtime-transition-failed",
})


def _number(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _first_number(fields: Dict[str, str], names: Iterable[str]) -> Optional[float]:
    for name in names:
        value = _number(fields.get(name))
        if value is not None:
            return value
    return None


def _percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    p = max(0.0, min(100.0, float(percentile))) / 100.0
    pos = p * (len(ordered) - 1)
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    weight = pos - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def robust_stats(values: Iterable[float]) -> Dict[str, Optional[float]]:
    vals = [float(value) for value in values if _number(value) is not None]
    if not vals:
        return {"p1": None, "p5": None, "median": None, "mad": None}
    median = statistics.median(vals)
    mad = statistics.median(abs(value - median) for value in vals)
    return {
        "p1": round(float(_percentile(vals, 1.0)), 3),
        "p5": round(float(_percentile(vals, 5.0)), 3),
        "median": round(float(median), 3),
        "mad": round(float(mad), 3),
    }


@dataclass(frozen=True)
class FpsSample:
    seq: int
    event_seq: int
    monotonic: float
    operation: str
    real_fps: float
    output_fps: float
    generated_fps: float
    effective_multiplier: float
    output_source: str
    target_fps: Optional[float] = None
    refresh_hz: Optional[float] = None
    source_interval_stddev_ms: Optional[float] = None
    requested_interval_stddev_ms: Optional[float] = None
    source_interval_p95_ms: Optional[float] = None
    requested_interval_p95_ms: Optional[float] = None


@dataclass(frozen=True)
class TelemetryEvent:
    event_seq: int
    monotonic: float
    operation: str


class TelemetryObserver:
    """Incrementally tail the renderer diagnostics and cache fresh evidence."""

    MAX_READ_BYTES = 1024 * 1024
    MAX_SAMPLES = 900
    MAX_EVENTS = 1800

    def __init__(
        self,
        disk_log_path: Path,
        ram_log_path: Optional[Path] = None,
        *,
        time_fn=time.monotonic,
    ) -> None:
        self.disk_log_path = Path(disk_log_path)
        self.ram_log_path = Path(ram_log_path) if ram_log_path else None
        self.time_fn = time_fn
        self._path: Optional[Path] = None
        self._inode: Optional[tuple[int, int]] = None
        self._offset = 0
        self._partial = b""
        self._event_seq = 0
        self._sample_seq = 0
        self._samples: Deque[FpsSample] = deque(maxlen=self.MAX_SAMPLES)
        self._events: Deque[TelemetryEvent] = deque(maxlen=self.MAX_EVENTS)
        self._last_fields: Dict[str, str] = {}
        self._last_application: Dict[str, Any] = {}
        self._last_poll_error: Optional[str] = None
        self._session_generation = 0

    @property
    def sample_seq(self) -> int:
        return self._sample_seq

    @property
    def event_seq(self) -> int:
        return self._event_seq

    def _select_path(self) -> Path:
        candidates = [self.disk_log_path]
        if self.ram_log_path is not None:
            candidates.insert(0, self.ram_log_path)
        existing: list[Path] = []
        for path in candidates:
            try:
                if path.is_file():
                    existing.append(path)
            except OSError:
                continue
        if not existing:
            return self.disk_log_path
        def mtime(path: Path) -> int:
            try:
                return path.stat().st_mtime_ns
            except OSError:
                return -1
        return max(existing, key=mtime)

    def _reset_session(self, *, keep_offset: int = 0) -> None:
        self._offset = max(0, int(keep_offset))
        self._partial = b""
        self._samples.clear()
        self._events.clear()
        self._last_fields = {}
        self._last_application = {}
        self._session_generation += 1

    @staticmethod
    def parse_fields(line: str) -> Optional[Dict[str, str]]:
        if _DIAGNOSTIC_MARKER not in line:
            return None
        return {match.group(1): match.group(2) for match in _FIELD_RE.finditer(line)}

    def consume_line(self, line: str, *, now: Optional[float] = None) -> Optional[FpsSample]:
        fields = self.parse_fields(line)
        if fields is None:
            return None
        now_mono = self.time_fn() if now is None else float(now)
        self._event_seq += 1
        operation = str(fields.get("operation") or "")
        self._last_fields = dict(fields)
        self._events.append(TelemetryEvent(self._event_seq, now_mono, operation))
        if operation in APPLICATION_OPERATIONS:
            self._last_application = {
                "event_seq": self._event_seq,
                "monotonic": now_mono,
                "operation": operation,
                "fields": dict(fields),
            }

        base = _first_number(fields, (
            "current_base_fps",
            "measured_base_fps",
            "instantaneous_base_fps",
            "base_fps",
        ))
        source_interval = _first_number(fields, ("source_interval_mean_ms",))
        requested_interval = _first_number(fields, ("requested_interval_mean_ms",))
        interval_real: Optional[float] = None
        interval_output: Optional[float] = None
        interval_multiplier: Optional[float] = None
        if (
            source_interval is not None and source_interval > 0
            and requested_interval is not None and requested_interval > 0
        ):
            interval_real = 1000.0 / source_interval
            interval_output = 1000.0 / requested_interval
            interval_multiplier = source_interval / requested_interval

        generated_count = _first_number(fields, (
            "generated",
            "generated_limit",
            "requested_generated_limit",
            "configured_generated_limit",
            "generated_per_real",
        ))
        planned_output: Optional[float] = None
        if base is not None and base > 0 and generated_count is not None and generated_count >= 0:
            planned_output = base * max(1.0, generated_count + 1.0)

        measured_output = _first_number(fields, (
            "current_output_fps",
            "observed_output_fps",
            "previous_output_fps",
        ))
        real = interval_real if interval_real is not None else base
        if measured_output is not None and measured_output > 0:
            output = measured_output
            output_source = "measured"
        elif interval_output is not None:
            output = interval_output
            output_source = "scheduler_interval"
        else:
            output = planned_output
            output_source = "instant_plan"

        if real is None or output is None or real <= 0 or output <= 0:
            return None

        if output_source == "scheduler_interval" and interval_multiplier is not None:
            effective = max(1.0, interval_multiplier)
        else:
            effective = max(1.0, output / real)
        generated_fps = max(0.0, output - real)
        target = _first_number(fields, (
            "target_fps",
            "requested_target_fps",
            "current_target_fps",
            "configured_adaptive_target_fps",
        ))
        refresh = _first_number(fields, ("refresh_hz", "gamescope_refresh_hz"))
        self._sample_seq += 1
        sample = FpsSample(
            seq=self._sample_seq,
            event_seq=self._event_seq,
            monotonic=now_mono,
            operation=operation,
            real_fps=float(real),
            output_fps=float(output),
            generated_fps=float(generated_fps),
            effective_multiplier=float(effective),
            output_source=output_source,
            target_fps=target,
            refresh_hz=refresh,
            source_interval_stddev_ms=_first_number(fields, ("source_interval_stddev_ms",)),
            requested_interval_stddev_ms=_first_number(fields, ("requested_interval_stddev_ms",)),
            source_interval_p95_ms=_first_number(fields, ("source_interval_p95_ms",)),
            requested_interval_p95_ms=_first_number(fields, ("requested_interval_p95_ms",)),
        )
        self._samples.append(sample)
        return sample

    def _consume_bytes(self, data: bytes, *, now: Optional[float] = None) -> int:
        lines = (self._partial + data).split(b"\n")
        self._partial = lines.pop()
        samples = 0
        for raw in lines:
            if self.consume_line(raw.decode("utf-8", errors="ignore"), now=now) is not None:
                samples += 1
        return samples

    def poll(self) -> Dict[str, Any]:
        """Read only newly appended diagnostics bytes.

        On first attachment to an already-existing log, old backlog is skipped:
        it is historical evidence and must not acknowledge a new Governor run.
        A newly rotated/truncated log is read from its beginning.
        """
        path = self._select_path()
        try:
            stat = path.stat()
        except OSError as error:
            self._last_poll_error = str(error)
            return self.snapshot()

        inode = (stat.st_dev, stat.st_ino)
        if self._inode is None:
            self._path = path
            self._inode = inode
            self._reset_session(keep_offset=stat.st_size)
            self._last_poll_error = None
            return self.snapshot()
        if self._path != path or self._inode != inode:
            self._path = path
            self._inode = inode
            self._reset_session(keep_offset=0)
        elif stat.st_size < self._offset:
            self._reset_session(keep_offset=0)

        available = max(0, stat.st_size - self._offset)
        if available <= 0:
            self._last_poll_error = None
            return self.snapshot()
        read_size = min(available, self.MAX_READ_BYTES)
        try:
            with open(path, "rb") as handle:
                handle.seek(self._offset)
                data = handle.read(read_size)
        except OSError as error:
            self._last_poll_error = str(error)
            return self.snapshot()
        if data:
            self._offset += len(data)
            self._consume_bytes(data)
        self._last_poll_error = None
        return self.snapshot()

    def _events_since(self, cutoff: float) -> list[TelemetryEvent]:
        return [event for event in self._events if event.monotonic >= cutoff]

    def samples_since(self, cutoff: float, *, after_seq: int = 0) -> list[FpsSample]:
        return [
            sample for sample in self._samples
            if sample.monotonic >= cutoff and sample.seq > int(after_seq)
        ]

    def summary(
        self,
        window_seconds: float = 12.0,
        *,
        after_seq: int = 0,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        now_mono = self.time_fn() if now is None else float(now)
        cutoff = now_mono - max(0.1, float(window_seconds))
        samples = self.samples_since(cutoff, after_seq=after_seq)
        real_stats = robust_stats(sample.real_fps for sample in samples)
        output_stats = robust_stats(sample.output_fps for sample in samples)
        multiplier_stats = robust_stats(sample.effective_multiplier for sample in samples)
        events = self._events_since(cutoff)
        if after_seq:
            # A new TDP candidate must be evaluated only with events emitted
            # alongside fresh samples from that candidate. Old pressure from
            # the previous power level must not poison the next window.
            if samples:
                first_event_seq = samples[0].event_seq
                events = [event for event in events if event.event_seq >= first_event_seq]
            else:
                events = []
        operations = [event.operation for event in events]
        latest = samples[-1] if samples else (self._samples[-1] if self._samples else None)
        span = (samples[-1].monotonic - samples[0].monotonic) if len(samples) >= 2 else 0.0
        return {
            "samples": len(samples),
            "sample_span_s": round(max(0.0, span), 3),
            "first_sample_seq": samples[0].seq if samples else None,
            "last_sample_seq": samples[-1].seq if samples else self._sample_seq,
            "real": real_stats,
            "output": output_stats,
            "multiplier": multiplier_stats,
            "misses": sum(operation in MISS_OPERATIONS for operation in operations),
            "hard_pressure": sum(operation in HARD_PRESSURE_OPERATIONS for operation in operations),
            "bypasses": sum(operation in BYPASS_OPERATIONS for operation in operations),
            "latest": asdict(latest) if latest else None,
        }

    def snapshot(self, *, now: Optional[float] = None) -> Dict[str, Any]:
        now_mono = self.time_fn() if now is None else float(now)
        latest = self._samples[-1] if self._samples else None
        age_ms = None if latest is None else max(0.0, (now_mono - latest.monotonic) * 1000.0)
        application_age_ms = None
        if self._last_application:
            application_age_ms = max(
                0.0,
                (now_mono - float(self._last_application["monotonic"])) * 1000.0,
            )
        return {
            "available": latest is not None,
            "path": str(self._path or self._select_path()),
            "sample_seq": self._sample_seq,
            "event_seq": self._event_seq,
            "sample_age_ms": round(age_ms, 1) if age_ms is not None else None,
            "latest": asdict(latest) if latest else None,
            "last_application": {
                **self._last_application,
                "age_ms": round(application_age_ms, 1) if application_age_ms is not None else None,
            } if self._last_application else None,
            "last_poll_error": self._last_poll_error,
            "session_generation": self._session_generation,
        }
