"""Immutable observation contracts. Times are monotonic receipt/acquisition times."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Optional, Tuple


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if isfinite(result) and result >= 0 else None


class Bottleneck(str, Enum):
    GPU_LIMITED = "GPU_LIMITED"
    CPU_LIMITED = "CPU_LIMITED"
    POWER_LIMITED = "POWER_LIMITED"
    THERMAL_LIMITED = "THERMAL_LIMITED"
    FG_LIMITED = "FG_LIMITED"
    PRESENTATION_LIMITED = "PRESENTATION_LIMITED"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Config:
    max_age_s: float = 2.5
    window_s: float = 12.0
    min_span_s: float = 6.0
    min_samples: int = 5
    max_gap_s: float = 2.5
    delivery_ratio: float = .97
    busy_pct: float = 95.0
    other_idle_pct: float = 80.0
    pressure_events: int = 3

    def __post_init__(self):
        values = (self.max_age_s, self.window_s, self.min_span_s, self.max_gap_s)
        if any(number(v) is None or v <= 0 for v in values):
            raise ValueError("positive finite time limits required")
        if not 2 <= self.min_samples <= 64 or self.min_span_s > self.window_s:
            raise ValueError("invalid evidence window")
        if not 0 < self.delivery_ratio <= 1 or not 0 <= self.other_idle_pct < self.busy_pct <= 100:
            raise ValueError("invalid inference thresholds")
        if self.pressure_events < 1:
            raise ValueError("positive pressure count required")


@dataclass(frozen=True)
class Sample:
    seq: int
    timestamp_mono: float
    context: str
    real_fps: Optional[float]
    output_fps: Optional[float]
    # These are reported measurements, not a target/ratio reconstruction.
    source: str = "renderer-log-receipt"
    units: str = "fps"


@dataclass(frozen=True)
class Host:
    timestamp_mono: float
    seq: int
    gpu_busy_pct: Optional[float] = None
    cpu_top_core_pct: Optional[float] = None
    temp_c: Optional[float] = None
    # Populated only by a future adapter with verified sensor/limit provenance.
    thermal_limit_c: Optional[float] = None
    apu_draw_w: Optional[float] = None
    verified_cap_w: Optional[float] = None
    source: str = "host-sensors"


@dataclass(frozen=True)
class Snapshot:
    session_key: str
    timestamp_mono: float
    samples: Tuple[Sample, ...] = ()
    host: Optional[Host] = None
    pressure: Tuple[Tuple[int, float, str], ...] = ()
    target_fps: Optional[float] = None
    blocked_reason: str = ""
    backend: str = "gfg"
    context: str = ""


@dataclass(frozen=True)
class Perception:
    primary: Bottleneck
    secondary: Tuple[Bottleneck, ...]
    confidence: float
    evidence_ids: Tuple[str, ...]
    missing: Tuple[str, ...]
    reason: str
    since: float
    expires_at: float
    session_key: str
    stale: bool = False
