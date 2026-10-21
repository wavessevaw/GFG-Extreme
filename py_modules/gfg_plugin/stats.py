"""Mean and t-interval of A/B measurements (Power Split's evidence), as in GFG Extreme 2.x."""
from __future__ import annotations

import math
from typing import Any, Dict, List

MIN_PAIRS = 3
_T95 = (12.71, 4.30, 3.18, 2.78, 2.57, 2.45, 2.36, 2.31, 2.26)
_T99 = (63.66, 9.92, 5.84, 4.60, 4.03, 3.71, 3.50, 3.36, 3.25)


def stats(values: List[float], confidence: float = 0.95) -> Dict[str, Any]:
    # Corrupt/legacy A/B records must never leak NaN/Infinity to the HUD,
    # JSON settings or per-game verdicts. Percentages outside any physical
    # plausibility window are malformed provenance, not useful samples.
    values = [float(v) for v in values if isinstance(v, (int, float))
              and not isinstance(v, bool) and math.isfinite(float(v))
              and abs(float(v)) <= 10_000]
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "low": None, "high": None, "measured": False}
    mean = sum(values) / n
    table, beyond = (_T99, 2.6) if confidence >= 0.99 else (_T95, 2.0)
    if n > 1:
        sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
        half = (table[n - 2] if n - 1 <= len(table) else beyond) * sd / math.sqrt(n)
    else:
        half = None
    return {"n": n, "mean": round(mean, 1),
            "low": round(mean - half, 1) if half is not None else None,
            "high": round(mean + half, 1) if half is not None else None,
            "measured": n >= MIN_PAIRS}
