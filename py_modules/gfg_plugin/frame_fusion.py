"""Normalize optional native Fusion evidence without equating a request with work."""
from __future__ import annotations
from typing import TypedDict


class NativeFusionState(TypedDict):
    supported: bool
    requested: bool
    prepared_inputs: int
    recorded_frames: int
    avoided_source_copies: int


def normalize(value: object) -> NativeFusionState:
    empty: NativeFusionState = {"supported": False, "requested": False,
        "prepared_inputs": 0, "recorded_frames": 0, "avoided_source_copies": 0}
    if value is None:
        return empty
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
        raise ValueError("unsupported Frame Fusion evidence")
    requested = value.get("requested", False)
    if type(requested) is not bool:
        raise ValueError("Frame Fusion requested must be boolean")
    fields = {}
    for key in ("prepared_inputs", "recorded_frames", "avoided_source_copies"):
        number = value.get(key)
        if type(number) is not int or not 0 <= number < 2**64:
            raise ValueError("invalid Frame Fusion counter: " + key)
        fields[key] = number
    if fields["prepared_inputs"] > 64 or (
            fields["recorded_frames"] and not fields["prepared_inputs"]):
        raise ValueError("Frame Fusion counters have no prepared inputs")
    if fields["recorded_frames"] != fields["avoided_source_copies"]:
        raise ValueError("Frame Fusion copy evidence is inconsistent")
    return {"supported": True, "requested": requested, **fields}


def summarize(enabled: bool, contexts: list[dict]) -> dict:
    current = [c for c in contexts if isinstance(c, dict)]
    fusion = [c.get("frame_fusion") or normalize(None) for c in current]
    mismatch = any(f.get("supported") and f.get("requested") is not enabled for f in fusion)
    observed = [c for c in current if c.get("phase") == "active"
        and c.get("frame_generation_active") is True
        and (c.get("spatial_scaling") or {}).get("active") is True
        and (c.get("frame_fusion") or {}).get("recorded_frames", 0) > 0]
    prepared = sum(f.get("prepared_inputs", 0) for f in fusion)
    if mismatch:
        state = "restart-required"
    elif observed:
        state = "observed"
    elif not enabled:
        state = "off"
    elif not current:
        state = "waiting-for-game"
    elif not any(f.get("supported") for f in fusion):
        state = "renderer-unsupported"
    elif prepared:
        state = "prepared"
    else:
        state = "pipeline-not-eligible"
    return {"enabled": enabled, "state": state, "restart_required": mismatch,
        "path_observed": bool(observed), "prepared_inputs": prepared,
        "avoided_source_copies_at_last_publication": sum(
            c["frame_fusion"]["avoided_source_copies"] for c in observed),
        "gain_measured": False}
