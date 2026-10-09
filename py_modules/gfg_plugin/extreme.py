"""GFG Extreme (1.6): the stock-power contract and the render scale + sharpening policy.

First stage (P0) of ``docs/EXTREME_FOUNDATION.md``.  Pure functions; ``governor_service`` owns the
lifecycle.  The rules this module encodes:

* **One power ceiling.**  ``min(15 W, the player's own lower limit, the hardware maximum)``.  Extreme
  never raises a player's 10-12 W to 15 and never goes above 15 W, overclocked BIOS or not.  Every
  TDP write (the Governor's, Frame OS Act boosts, recovery) is clamped to it by the power actuator.
* **Scale + sharpening are one logical point.**  The ladder is 100 -> 90 -> 80 % render scale (75 / 70
  follow after on-Deck validation of the native reference); the scaler's sharpening starts from
  ``CAS_START`` plus the player's own correction.  Saved is never written: everything goes through
  the temporary Governor overlay.
* **A request is not an application.**  A scaled point counts only after the renderer reports the
  game's real render extent (``swapchain-context-create``: application vs presented size) or its
  spatial scaler (``spatial scaling active: source=...; sharpness=...``).  No acknowledgement, no
  "render 80 %" on screen and no learning.
* **Honest capabilities.**  A direction without a verified mechanism is listed as unavailable with
  its reason, and a setting that needs a new launch says RESTART_REQUIRED.
* **No promised gain.**  The gain against Balanced is shown only after a same-scene A-B-A proof,
  which this version does not run yet; nothing is estimated from pixel counts.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional

EXTREME_CEILING_W = 15.0
# Starting hypothesis for calibration (EXTREME_FOUNDATION.md), not a quality verdict.
CAS_START: Dict[int, float] = {100: 0.0, 90: 0.15, 80: 0.30, 75: 0.40, 70: 0.50}
AUTO_SCALE_STEPS = (90, 80)
SHARPNESS_OFFSET_LIMIT = 0.3
SCALE_ACK_TIMEOUT_S = 20.0
SCALE_ACK_TOLERANCE_PCT = 3.0
SHARPNESS_ACK_TOLERANCE = 0.011
MAX_SCALE_ACK_FAILURES = 2

STATES = ("OFF", "DISCOVER", "BASELINE", "APPLY", "VERIFY", "TUNE", "ACTIVE",
          "RESTART_REQUIRED", "PAUSED", "RESTORING", "RESTORE_PENDING", "FAILED")

SPATIAL_ACTIVE_MARKER = "MAKO Renderer: spatial scaling active:"
_EXTENT_RE = re.compile(r"(\d{2,5})x(\d{2,5})")


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


# ---------------------------------------------------------------------------- power ceiling
def power_ceiling(user_w: Any, hardware_max_w: Any = None) -> Dict[str, Any]:
    """The one ceiling of every Extreme power write, and where it comes from."""
    options = [(EXTREME_CEILING_W, "stock-limit")]
    user = _finite(user_w)
    if user is not None and user > 0:
        options.append((round(user, 1), "your-limit"))
    hardware = _finite(hardware_max_w)
    if hardware is not None and hardware > 0:
        options.append((round(hardware, 1), "hardware"))
    ceiling, source = min(options, key=lambda option: option[0])  # ties: the first (stock) wins
    return {"ceiling_w": ceiling, "source": source, "user_w": round(user, 1) if user else None}


# ---------------------------------------------------------------------------- sharpening
def clamp_offset(value: Any) -> float:
    number = _finite(value)
    if number is None:
        return 0.0
    return round(max(-SHARPNESS_OFFSET_LIMIT, min(SHARPNESS_OFFSET_LIMIT, number)), 2)


def user_scaling(saved: Dict[str, Any]) -> bool:
    """The profile scales on its own: its factor and sharpness are the player's, not Extreme's."""
    return bool(saved.get("scaling_enabled"))


def vkbasalt_sharpening(saved: Dict[str, Any]) -> bool:
    """vkBasalt (Filters) runs and sharpens: its CAS/DLS is on only with the layer selected."""
    return (str(saved.get("external_vulkan_layer") or "").lower() == "vkbasalt"
            and str(saved.get("vkbasalt_sharpening") or "none").lower() in ("cas", "dls"))


def sharpness_for(pct: int, saved: Dict[str, Any], offset: Any = 0.0) -> tuple[Optional[float], str]:
    """Scaler sharpening for a render scale: (value or None to leave Saved's, reason)."""
    if user_scaling(saved):
        return None, "profile-scaling"
    if int(pct) >= 100:
        return None, "native"
    if vkbasalt_sharpening(saved):
        return 0.0, "vkbasalt-sharpening"        # never sharpen twice
    base = CAS_START.get(int(pct))
    if base is None:
        return None, "scale-not-allowed"
    return round(max(0.0, min(1.0, base + clamp_offset(offset))), 2), "table"


# ---------------------------------------------------------------------------- renderer evidence
def parse_spatial_active(line: str) -> Optional[Dict[str, Any]]:
    """``MAKO Renderer: spatial scaling active: source=WxH; factor=..; ...; sharpness=..; ...``."""
    at = line.find(SPATIAL_ACTIVE_MARKER)
    if at < 0:
        return None
    fields: Dict[str, str] = {}
    for part in line[at + len(SPATIAL_ACTIVE_MARKER):].split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key:
            fields[key.strip()] = value.strip()
    extents = _EXTENT_RE.findall(fields.get("source", ""))
    source = (int(extents[0][0]), int(extents[0][1])) if extents else None
    output = (int(extents[1][0]), int(extents[1][1])) if len(extents) > 1 else None
    return {
        "kind": "spatial-active",
        "source": source,
        "output": output,
        "factor": _finite(fields.get("factor")),
        "effective_factor": _finite(fields.get("effective_factor")),
        "sharpness": _finite(fields.get("sharpness")),
        "method": fields.get("active_method") or fields.get("requested_method"),
    }


def swapchain_extent(fields: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """``swapchain-context-create``: the size the game renders vs the size that is presented."""
    try:
        source = (int(fields["application_width"]), int(fields["application_height"]))
        output = (int(fields["width"]), int(fields["height"]))
    except (KeyError, TypeError, ValueError):
        return None
    if min(source + output) <= 0:
        return None
    return {"kind": "swapchain", "source": source, "output": output, "factor": None,
            "effective_factor": None, "sharpness": None, "method": None,
            "pipeline": fields.get("spatial_pipeline")}


RUNTIME_STATE_DIRNAME = "runtime-state"   # next to the renderer's config file (MAKO_CONFIG)
RUNTIME_STATE_MAX_FILES = 32
RUNTIME_STATE_MAX_BYTES = 64 * 1024


def _int(value: Any) -> Optional[int]:
    number = _finite(value)
    return int(number) if number is not None and number > 0 else None


def runtime_state_evidence(doc: Any) -> Optional[Dict[str, Any]]:
    """The renderer's runtime-state JSON (schema 5): its ``spatial_scaling`` block as evidence.

    Fields seen in the bundled renderer: pid, process_start_ticks, role, updated_unix_ms and
    spatial_scaling {active, source_width/height, presentation_width/height, effective_factor,
    active_method}.  Only an *active* scaler with both extents counts.
    """
    if not isinstance(doc, dict):
        return None
    spatial = doc.get("spatial_scaling")
    if not isinstance(spatial, dict):
        return None
    source = (_int(spatial.get("source_width")), _int(spatial.get("source_height")))
    output = (_int(spatial.get("presentation_width")), _int(spatial.get("presentation_height")))
    return {
        "kind": "runtime-state",
        "active": spatial.get("active") is True or spatial.get("active") == 1,
        "source": source if None not in source else None,
        "output": output if None not in output else None,
        "factor": None,
        "effective_factor": _finite(spatial.get("effective_factor")),
        "sharpness": None,
        "method": spatial.get("active_method") or spatial.get("requested_method"),
        "pid": _int(doc.get("pid")),
        "updated_unix_ms": _finite(doc.get("updated_unix_ms")),
        "reason": spatial.get("inactive_reason") or spatial.get("fallback_reason"),
    }


def read_runtime_states(dirs: Iterable[Any], pids: Iterable[int], since_unix_s: float = 0.0) -> List[Dict[str, Any]]:
    """Runtime-state records of the game's processes written after ``since_unix_s``, oldest first.

    Bounded: at most RUNTIME_STATE_MAX_FILES files of RUNTIME_STATE_MAX_BYTES each; anything
    unreadable or malformed is skipped.  A record from another process never counts.
    """
    import json
    from pathlib import Path

    wanted = {int(p) for p in pids if isinstance(p, int) or str(p).isdigit()}
    out: List[Dict[str, Any]] = []
    for base in dirs:
        folder = Path(base) / RUNTIME_STATE_DIRNAME
        try:
            files = sorted(folder.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:RUNTIME_STATE_MAX_FILES]
        except OSError:
            continue
        for path in files:
            try:
                if path.stat().st_size > RUNTIME_STATE_MAX_BYTES:
                    continue
                record = runtime_state_evidence(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, UnicodeError):
                continue
            if record is None or (wanted and record.get("pid") not in wanted):
                continue
            updated = record.get("updated_unix_ms")
            if since_unix_s and (updated is None or updated / 1000.0 < since_unix_s):
                continue
            out.append(record)
    out.sort(key=lambda r: r.get("updated_unix_ms") or 0.0)
    return out


def render_pct(evidence: Dict[str, Any]) -> Optional[float]:
    """Render scale (share of the presented width) an evidence record proves, or None."""
    source, output = evidence.get("source"), evidence.get("output")
    if source and output and output[0] > 0 and output[1] > 0:
        width, height = 100.0 * source[0] / output[0], 100.0 * source[1] / output[1]
        if abs(width - height) > SCALE_ACK_TOLERANCE_PCT:
            return None                             # not a uniform scale: no proof of anything
        return round((width + height) / 2.0, 1)
    factor = evidence.get("effective_factor")
    if isinstance(factor, (int, float)) and factor >= 1.0:
        return round(100.0 / float(factor), 1)
    return None


def scale_acknowledged(evidence: Iterable[Dict[str, Any]], pct: int) -> Optional[Dict[str, Any]]:
    """The newest evidence record that shows the game rendering at ``pct`` %."""
    for record in reversed(list(evidence)):
        if record.get("kind") == "runtime-state" and not record.get("active"):
            return record if float(pct) >= 100 else None  # the newest report: the scaler is off
        seen = render_pct(record)
        if seen is not None:
            return record if abs(seen - float(pct)) <= SCALE_ACK_TOLERANCE_PCT else None
    return None


def sharpness_acknowledged(evidence: Iterable[Dict[str, Any]], value: Optional[float]) -> Optional[bool]:
    """True/False from the newest scaler report, None when the renderer has not reported it."""
    if value is None:
        return None
    for record in reversed(list(evidence)):
        seen = record.get("sharpness")
        if record.get("kind") == "spatial-active" and isinstance(seen, (int, float)):
            return abs(float(seen) - float(value)) <= SHARPNESS_ACK_TOLERANCE
    return None


# ---------------------------------------------------------------------------- capabilities
BOOSTERS = ("upscale", "quiet", "split", "cooling", "act", "memory", "latency", "shield", "instant")


def _cap(ident: str, state: str, reason: str, **extra: Any) -> Dict[str, Any]:
    return {"id": ident, "state": state, "reason": reason, **extra}


def booster_states(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The nine Extreme directions with what each does in this session, honestly.

    ``state``: active, ready, waiting, restart_required, off or unavailable.  Directions without a
    verified mechanism stay unavailable with a reason instead of an imitation.
    """
    running = bool(facts.get("running"))
    out: List[Dict[str, Any]] = []

    # 1. Render scale + sharpening (P0)
    pct, ack = facts.get("scale_pct"), facts.get("scale_ack")
    if not running:
        out.append(_cap("upscale", "waiting", "game-not-running"))
    elif facts.get("scale_blocked"):
        out.append(_cap("upscale", "unavailable", str(facts["scale_blocked"])))
    elif not facts.get("scale_provisioned"):
        out.append(_cap("upscale", "restart_required", "scaler-not-provisioned-at-launch"))
    elif facts.get("cpu_bound"):
        out.append(_cap("upscale", "ready", "cpu-bound-full-resolution"))
    elif isinstance(pct, int) and pct < 100 and ack:
        out.append(_cap("upscale", "active", "render-scale-confirmed", render_pct=pct,
                        sharpness=facts.get("sharpness") if facts.get("sharpness_ack") else None,
                        sharpness_reason=facts.get("sharpness_reason")))
    elif isinstance(pct, int) and pct < 100:
        out.append(_cap("upscale", "waiting", "awaiting-renderer-acknowledgement", render_pct=pct))
    else:
        out.append(_cap("upscale", "ready", "full-resolution-holds", render_pct=100))

    # 2. Quiet background (P2): needs a supported per-job Steam API; never SIGSTOP Steam.
    out.append(_cap("quiet", "unavailable", "no-supported-steam-job-api"))

    # 3. CPU <-> GPU power split: the GPU-bound direction is the existing Smart Power Split.
    split = facts.get("split") or {}
    if not split.get("setting", True):
        out.append(_cap("split", "off", "power-split-setting-off"))
    elif not split.get("available", True):
        out.append(_cap("split", "unavailable", "cpu-clock-control-unavailable"))
    elif split.get("cap_khz"):
        out.append(_cap("split", "active", "gpu-bound-cpu-capped", cap_khz=split["cap_khz"]))
    else:
        out.append(_cap("split", "ready", "cpu-at-full-clock"))

    # 4. Cooling ahead (P3): only through a verified OEM fan interface.
    out.append(_cap("cooling", "unavailable", "no-verified-fan-api"))

    # 5. Frame OS Act through the existing consent.
    act = facts.get("act") or {}
    if act.get("consent") is False:
        out.append(_cap("act", "off", "declined"))
    elif not act.get("enabled"):
        out.append(_cap("act", "off", "act-not-enabled"))
    elif running and not act.get("pacer_live"):
        out.append(_cap("act", "restart_required", "pacer-not-loaded-at-launch"))
    elif act.get("injecting"):
        out.append(_cap("act", "active", "boosting-real-frames"))
    else:
        out.append(_cap("act", "waiting", "waits-for-settled-watts"))

    # 6. Memory (P4): no global VM tweaks without pressure/OOM/recovery tests.
    out.append(_cap("memory", "unavailable", "global-memory-tweaks-not-applied"))
    # 7. Low latency (P3): a software proxy is not input-to-photon; no Reflex claims.
    out.append(_cap("latency", "unavailable", "latency-not-measured-on-hardware"))
    # 8. Stutter shield (P3): needs p99 / max-gap acceptance on a Deck.
    out.append(_cap("shield", "unavailable", "not-validated-on-hardware"))

    # 9. Instant start: a remembered point of this game, verified again before it counts.
    if facts.get("warm_started"):
        out.append(_cap("instant", "active", "remembered-point-verified-again"))
    else:
        out.append(_cap("instant", "waiting", "learning-this-game"))
    return out


def gain_unavailable() -> Dict[str, Any]:
    """Gain contract: no number before a same-scene A-B-A proof against Balanced."""
    return {"kind": "unavailable", "percent": None, "uncertainty": None, "metric": "real_fps",
            "baseline": "balanced", "samples": 0, "reason": "aba-proof-not-in-this-version"}


def session_state(*, enabled: bool, running: bool, overlay_active: bool, paused: bool,
                  request: bool, verifying_scale: bool, phase: Optional[str],
                  restart_required: bool) -> str:
    """Coarse Extreme state for the HUD and log (see STATES)."""
    if not enabled:
        return "OFF"
    if not running:
        return "DISCOVER"
    if not overlay_active or restart_required:
        return "RESTART_REQUIRED"
    if paused:
        return "PAUSED"
    if verifying_scale:
        return "VERIFY"
    if request:
        return "APPLY"
    if phase in (None, "settle"):
        return "BASELINE"
    if phase == "locked":
        return "ACTIVE"
    return "TUNE"
