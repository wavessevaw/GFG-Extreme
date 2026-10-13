"""Normalize optional native Fusion evidence without equating a request with work."""
from __future__ import annotations
from typing import TypedDict

MAX_DIAGNOSTIC_CONTEXTS = 16


def compact_context(context: dict) -> dict:
    """Copy facts from RuntimeStateService's validated, live contexts only."""
    scaling = context.get("spatial_scaling") or {}
    native = context.get("frame_fusion") or normalize(None)
    if not native.get("supported"):
        eligibility = "renderer-unsupported"
    elif not native.get("requested"):
        eligibility = "disabled-at-launch"
    elif context.get("phase") != "active":
        eligibility = "runtime-transition"
    elif not context.get("frame_generation_active"):
        eligibility = "frame-generation-inactive"
    elif native.get("native_prepared_inputs"):
        eligibility = ("native-path-observed" if native.get("native_source_transfers")
            else "native-prepared-awaiting-submit")
    elif not scaling.get("active"):
        eligibility = native.get("native_fallback_reason") or "scaling-inactive"
    elif scaling.get("active_method") not in (None, "mako"):
        eligibility = "unsupported-scaler"
    elif not native.get("prepared_inputs"):
        eligibility = "direct-inputs-unavailable"
    elif native.get("recorded_frames", 0):
        eligibility = "direct-path-observed"
    else:
        eligibility = "prepared-awaiting-submit"
    bounded = lambda value: value[:240] if isinstance(value, str) else value
    return {k: bounded(context.get(k)) for k in (
        "pid", "process_start_ticks", "context", "role", "updated_unix_ms",
        "state_revision", "phase", "reason", "frame_generation_active", "error")} | {
        "spatial_scaling": {k: bounded(scaling.get(k)) for k in (
            "active", "activation_supported", "requested_method", "active_method", "pipeline",
            "source_width", "source_height", "presentation_width", "presentation_height",
            "inactive_reason", "constraint_reason", "fallback_reason")},
        "frame_fusion": dict(native), "eligibility": eligibility,
        "eligibility_basis": "derived-from-native-state"}

class NativeFusionState(TypedDict):
    supported: bool
    autopilot_scope_supported: bool
    requested: bool
    prepared_inputs: int
    recorded_frames: int
    avoided_source_copies: int
    native_prepared_inputs: int
    native_source_transfers: int
    native_conversion_blits_avoided: int
    native_source_format: int
    native_fallback_reason: str


def normalize(value: object) -> NativeFusionState:
    empty: NativeFusionState = {"supported": False, "autopilot_scope_supported": False, "requested": False,
        "prepared_inputs": 0, "recorded_frames": 0, "avoided_source_copies": 0,
        "native_prepared_inputs": 0, "native_source_transfers": 0,
        "native_conversion_blits_avoided": 0, "native_source_format": 0,
        "native_fallback_reason": ""}
    if value is None:
        return empty
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] not in (1, 2):
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
    native = {k: empty[k] for k in ("native_prepared_inputs", "native_source_transfers",
        "native_conversion_blits_avoided", "native_source_format", "native_fallback_reason")}
    if value["schema"] == 2:
        for key in ("native_prepared_inputs", "native_source_transfers",
                    "native_conversion_blits_avoided", "native_source_format"):
            number = value.get(key)
            if type(number) is not int or not 0 <= number < 2**64:
                raise ValueError("invalid Frame Fusion native counter: " + key)
            native[key] = number
        prepared, transfers = native["native_prepared_inputs"], native["native_source_transfers"]
        conversions, format_ = native["native_conversion_blits_avoided"], native["native_source_format"]
        fallback = value.get("native_fallback_reason")
        if not isinstance(fallback, str) or len(fallback) > 240:
            raise ValueError("invalid Frame Fusion native fallback")
        native["native_fallback_reason"] = fallback
        if prepared not in (0, 2) or (transfers and not prepared) or conversions > transfers:
            raise ValueError("Frame Fusion native counters have no prepared history")
        if prepared and (not requested or fields["prepared_inputs"] or format_ not in (37, 44)):
            raise ValueError("Frame Fusion native source layout is inconsistent")
        if conversions != (transfers if format_ == 44 else 0):
            raise ValueError("Frame Fusion conversion evidence is inconsistent")
    scoped = value.get("autopilot_scope_supported",False)
    if type(scoped) is not bool:
        raise ValueError("invalid Fusion scope capability")
    return {**empty, "supported": True, "autopilot_scope_supported": scoped, "requested": requested, **fields, **native}


def summarize(enabled: bool, contexts: list[dict]) -> dict:
    current = [c for c in contexts if isinstance(c, dict)]
    fusion = [c.get("frame_fusion") or normalize(None) for c in current]
    mismatch = any(f.get("supported") and f.get("requested") is not enabled for f in fusion)
    observed = [c for c in current if enabled and (c.get("frame_fusion") or {}).get("requested") is True and c.get("phase") == "active"
        and c.get("frame_generation_active") is True
        and (((c.get("spatial_scaling") or {}).get("active") is True
              and (c.get("frame_fusion") or {}).get("recorded_frames", 0) > 0)
             or (c.get("frame_fusion") or {}).get("native_source_transfers", 0) > 0)]
    native_prepared = sum(f.get("native_prepared_inputs", 0) for f in fusion)
    prepared = sum(f.get("prepared_inputs", 0) for f in fusion) + native_prepared
    paths = {"native-input" if c["frame_fusion"].get("native_source_transfers", 0) else "spatial-input"
        for c in observed}
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
        "native_prepared_inputs": native_prepared,
        "native_source_transfers_at_last_publication": sum(
            c["frame_fusion"].get("native_source_transfers", 0) for c in observed),
        "native_conversion_blits_avoided_at_last_publication": sum(
            c["frame_fusion"].get("native_conversion_blits_avoided", 0) for c in observed),
        "processing_path": next(iter(paths)) if len(paths) == 1 else "mixed" if paths else "none",
        "gain_measured": False,
        "contexts_total": len(current),
        "contexts_truncated": max(0, len(current) - MAX_DIAGNOSTIC_CONTEXTS),
        "contexts": [compact_context(c) for c in sorted(current,
            key=lambda c: (c not in observed, -c.get("updated_unix_ms", 0)))[:MAX_DIAGNOSTIC_CONTEXTS]]}
