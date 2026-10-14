"""GFG Temporal Engine: setting, native status files and their summary.

The engine runs inside the renderer's frame-generation backend and writes one
status file per context under ``<runtime-state>/temporal``.  This module never
infers work from the setting: requested, applied (a live engine context),
dispatched, GPU-completed and presented are separate facts, and "presented"
is reported as unknown because the backend cannot observe presentation.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

MODES = ("off", "observe", "shadow", "experimental")
MARKER_NAME = "temporal-engine.mode"
STATUS_DIRNAME = "temporal"
MAX_FILES = 32
_ROLES = ("engine", "observer", "fallback")


def normalize_mode(value: object) -> str:
    return value if isinstance(value, str) and value in MODES else "off"


def _int(value: object, field: str) -> int:
    if type(value) is not int or value < 0 or value >= 2 ** 63:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _num(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return float(value)


def _str(value: object, field: str, limit: int = 240) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value[:limit]


def normalize_status(raw: object) -> Dict[str, Any]:
    """Validate one engine status record (schema 1); raises ValueError."""
    if not isinstance(raw, dict) or raw.get("schema") != 1 or raw.get("engine") != "gfg-temporal":
        raise ValueError("unsupported Temporal Engine status")
    mode = raw.get("mode")
    role = raw.get("role")
    if mode not in MODES[1:] or role not in _ROLES:
        raise ValueError("invalid mode or role")
    active = raw.get("active")
    if type(active) is not bool:
        raise ValueError("active must be boolean")
    out: Dict[str, Any] = {
        "version": _str(raw.get("version"), "version", 40),
        "pid": _int(raw.get("pid"), "pid"),
        "process_start_ticks": _int(raw.get("process_start_ticks"), "process_start_ticks"),
        "context": _int(raw.get("context"), "context"),
        "updated_unix_ms": _int(raw.get("updated_unix_ms"), "updated_unix_ms"),
        "mode": mode, "role": role, "active": active,
        "device": _str(raw.get("device"), "device", 120),
        "width": _int(raw.get("width"), "width"), "height": _int(raw.get("height"), "height"),
    }
    if not active:
        eligible = raw.get("eligible")
        if type(eligible) is not bool:
            raise ValueError("eligible must be boolean")
        out["eligible"] = eligible
        out["fallback_reason"] = _str(raw.get("fallback_reason"), "fallback_reason")
        return out
    counters = raw.get("counters")
    gpu = raw.get("gpu_ms")
    shares = raw.get("shares")
    sched = raw.get("scheduler")
    if not all(isinstance(v, dict) for v in (counters, gpu, shares, sched)):
        raise ValueError("engine sections missing")
    out["outputs_capacity"] = _int(raw.get("outputs_capacity"), "outputs_capacity")
    out["vram_bytes"] = _int(raw.get("vram_bytes"), "vram_bytes")
    out["real_interval_ms"] = _num(raw.get("real_interval_ms"), "real_interval_ms")
    out["counters"] = {k: _int(counters.get(k), k) for k in (
        "pairs_submitted", "history_frames", "outputs_dispatched", "outputs_gpu_completed", "dropped",
        "scene_cuts", "promoted_tiles")}
    if counters.get("presented") is not None:
        raise ValueError("presented is not observable in the backend")
    out["counters"]["presented"] = None
    if out["counters"]["outputs_gpu_completed"] > out["counters"]["outputs_dispatched"]:
        raise ValueError("more outputs completed than dispatched")
    out["gpu_ms"] = {k: _num(gpu.get(k), "gpu_ms." + k) for k in (
        "pyramid", "analyze", "classify", "lists", "reuse", "light", "full", "merge", "frame",
        "pair_p50", "pair_p95", "pair_p99")}
    timed = gpu.get("timed")
    if type(timed) is not bool:
        raise ValueError("gpu_ms.timed must be boolean")
    out["gpu_ms"]["timed"] = timed
    out["shares"] = {k: _num(shares.get(k), "shares." + k) for k in ("reuse", "light", "full")}
    if any(v > 1.0001 for v in out["shares"].values()):
        raise ValueError("shares must be fractions")
    out["confidence"] = _num(raw.get("confidence"), "confidence")
    recommendation = sched.get("recommendation")
    if recommendation not in ("keep", "fewer-outputs", "fallback"):
        raise ValueError("invalid recommendation")
    out["scheduler"] = {
        "level": _int(sched.get("level"), "level"),
        "light_scale": _num(sched.get("light_scale"), "light_scale"),
        "force_full": _int(sched.get("force_full"), "force_full"),
        "budget_ms": _num(sched.get("budget_ms"), "budget_ms"),
        "predicted_ms": _num(sched.get("predicted_ms"), "predicted_ms"),
        "recommended_outputs": _int(sched.get("recommended_outputs"), "recommended_outputs"),
        "recommendation": recommendation,
        "reason": _str(sched.get("reason"), "reason", 40),
        "misses": _int(sched.get("misses"), "misses"),
        "gpu_busy_known": sched.get("gpu_busy_known") is True,
    }
    out["last_error"] = _str(raw.get("last_error"), "last_error")
    return out


def _process_start_ticks(pid: int) -> Optional[int]:
    try:
        line = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        fields = line[line.rfind(")") + 2:].split()
        return int(fields[19]) if len(fields) >= 20 else None
    except (OSError, UnicodeError, ValueError):
        return None


def read_contexts(folders: Iterable[Path], live_check=_process_start_ticks) -> List[Dict[str, Any]]:
    """Live, valid status records from the given ``temporal`` folders (newest first)."""
    found: Dict[tuple, Dict[str, Any]] = {}
    for folder in folders:
        try:
            paths = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_FILES]
        except OSError:
            continue
        for path in paths:
            try:
                flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(path, flags)
                try:
                    data = os.read(fd, 65536)
                finally:
                    os.close(fd)
                record = normalize_status(json.loads(data.decode("utf-8")))
            except (OSError, UnicodeError, ValueError):
                continue
            if live_check(record["pid"]) != record["process_start_ticks"]:
                continue
            key = (record["pid"], record["process_start_ticks"], record["context"])
            if key not in found or record["updated_unix_ms"] > found[key]["updated_unix_ms"]:
                found[key] = record
    return sorted(found.values(), key=lambda r: r["updated_unix_ms"], reverse=True)


def summarize(requested_mode: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One status block for the UI, the session log and Autopilot."""
    mode = normalize_mode(requested_mode)
    engines = [c for c in contexts if c["active"]]
    passive = [c for c in contexts if not c["active"]]
    fallback = [c.get("fallback_reason") for c in passive if c.get("fallback_reason")]
    out: Dict[str, Any] = {
        "requested_mode": mode,
        "applied": bool(engines) or (mode == "observe" and bool(passive)),
        "contexts": len(contexts),
        "engine_contexts": len(engines),
        "fallback_reasons": sorted(set(fallback))[:6],
        "fallback_contexts": sum(1 for c in passive if c["role"] == "fallback"),
        "eligible": any(c.get("eligible") for c in passive) or bool(engines),
        "presented": None,
        "presented_basis": "not-observable-in-backend",
        "performance_basis": "gpu-timestamp-queries" if engines else "none",
        "verified_on_hardware": False,
    }
    if mode == "off":
        out["state"] = "off"
    elif not contexts:
        out["state"] = "waiting-for-game"
    elif engines:
        out["state"] = "shadow-measuring" if engines[0]["mode"] == "shadow" else "generating"
    elif fallback:
        out["state"] = "fallback"
    else:
        out["state"] = "observing"
    if engines:
        e = engines[0]
        c = e["counters"]
        out.update(
            mode=e["mode"], version=e["version"], device=e["device"],
            width=e["width"], height=e["height"], outputs_capacity=e["outputs_capacity"],
            real_interval_ms=round(e["real_interval_ms"], 3),
            real_fps=round(1000.0 / e["real_interval_ms"], 2) if e["real_interval_ms"] > 0 else None,
            pairs_submitted=c["pairs_submitted"], outputs_dispatched=c["outputs_dispatched"],
            outputs_gpu_completed=c["outputs_gpu_completed"], dropped=c["dropped"],
            scene_cuts=c["scene_cuts"], promoted_tiles=c["promoted_tiles"],
            gpu_ms={k: round(v, 4) if isinstance(v, float) else v for k, v in e["gpu_ms"].items()},
            shares={k: round(v, 4) for k, v in e["shares"].items()},
            confidence=round(e["confidence"], 4), scheduler=dict(e["scheduler"]),
            vram_mb=round(e["vram_bytes"] / (1024 * 1024), 1), last_error=e["last_error"])
        dispatched = c["outputs_dispatched"]
        out["completion_ratio"] = round(c["outputs_gpu_completed"] / dispatched, 4) if dispatched else None
        total = c["pairs_submitted"] + c["dropped"]
        out["drop_rate"] = round(c["dropped"] / total, 4) if total else 0.0
    return out


def compact(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Few fields per timeline sample of the session recorder."""
    keys = ("requested_mode", "state", "applied", "engine_contexts", "fallback_reasons", "real_fps",
            "outputs_dispatched", "outputs_gpu_completed", "dropped", "shares", "confidence")
    out = {k: summary.get(k) for k in keys if k in summary}
    gpu = summary.get("gpu_ms") or {}
    if gpu:
        out["gpu_ms"] = {k: gpu.get(k) for k in ("analyze", "frame", "pair_p95") if k in gpu}
    sched = summary.get("scheduler") or {}
    if sched:
        out["level"] = sched.get("level")
        out["recommendation"] = sched.get("recommendation")
    return out


def blocks_experiments(summary: Dict[str, Any]) -> bool:
    """While the engine runs (shadow or generating), resource trials would confound its measurements."""
    return summary.get("state") in ("shadow-measuring", "generating")
