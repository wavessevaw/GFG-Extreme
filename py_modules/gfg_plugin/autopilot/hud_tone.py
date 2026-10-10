"""Ring colors for Autopilot. Green is a confirmed calm state, not a default."""
from __future__ import annotations

GREEN = (46, 170, 96)
YELLOW = (214, 176, 42)
RED = (214, 64, 54)
GREY = (92, 92, 102)
COLORS = {"green": GREEN, "yellow": YELLOW, "red": RED, "grey": GREY}
HOLD_S = 2.0


def tones(view, critical: bool = False) -> dict:
    def fps():
        if not view.fresh or view.output_fps is None:
            return "grey"
        if view.target_fps and view.output_fps < view.target_fps * 0.85:
            return "yellow"
        return "green"

    def thermal():
        if view.temp_c is None:
            return "grey"
        if view.temp_c >= 90:
            return "red"
        if view.temp_c >= 80:
            return "yellow"
        return "green"

    def frame():
        if not view.fresh or view.frametime_p95_ms is None or not view.target_fps:
            return "grey"
        budget = 1000.0 / view.target_fps
        if view.frametime_p95_ms > budget * 1.8:
            return "red"
        if view.frametime_p95_ms > budget * 1.45:
            return "yellow"
        return "green"

    def gpu():
        if view.gpu_mhz is None and view.gpu_busy is None:
            return "grey"
        if view.fresh and view.target_fps and view.output_fps is not None and view.output_fps < view.target_fps * 0.85:
            if view.gpu_busy is not None and view.gpu_busy >= 95:
                return "yellow"
        return "green" if view.gpu_mhz is not None or view.gpu_busy is not None else "grey"

    def cpu():
        if view.cpu_busy is None:
            return "grey"
        if view.fresh and view.cpu_busy >= 90 and view.target_fps and view.output_fps is not None and view.output_fps < view.target_fps * 0.9:
            return "yellow"
        return "green"

    def battery():
        return "green"

    def energy():
        return "green" if view.fresh else "grey"

    named = {"fps": fps(), "tdp": "green" if view.fresh else "grey",
             "gpu": gpu(), "cpu": cpu(), "temp": thermal(), "frame": frame(),
             "battery": battery() if view.fresh else "grey", "energy": energy()}
    if critical:
        named["temp"] = "red"
    return named


def hold(previous, proposed, now, since, critical_keys=("temp",)):
    """Keep a non-critical color for HOLD_S so one noisy sample does not flash."""
    if previous is None:
        return proposed, now
    kept = {}
    changed = False
    for key, value in proposed.items():
        old = previous.get(key)
        if old == value or value == "red" or key in critical_keys and value == "red":
            kept[key] = value
        elif now - since >= HOLD_S:
            kept[key] = value
            changed = True
        else:
            kept[key] = old
    return kept, now if changed or previous != kept else since
