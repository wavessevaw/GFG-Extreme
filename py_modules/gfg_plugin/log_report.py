"""Turn a recorded log zip into a short plain-language verdict.

Used twice: the recorder appends ``summary.txt`` to every bundle (so the person reading the log sees
the verdict first), and ``tools/gfg_log_report.py`` prints the same report for any bundle.  The
analysis is deliberately conservative: a finding states what the log shows, not a guess about why.
"""
from __future__ import annotations

import json
import re
import statistics
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .governor_telemetry import TelemetryObserver

CURRENT_VERSION = "2.1.6"  # kept in step by scripts/bump_version.py


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return ordered[index]


def _jsonl(text: str) -> List[Dict[str, Any]]:
    rows = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _read(bundle: zipfile.ZipFile, name: str) -> str:
    try:
        return bundle.read(name).decode("utf-8", errors="replace")
    except KeyError:
        return ""


def analyze_diagnostics(text: str) -> Dict[str, Any]:
    """Run the recorded renderer lines through the real parser, exactly as the Governor would see them."""
    clock = {"t": 0.0}
    observer = TelemetryObserver(Path("/nonexistent/gfg-diagnostics.log"), time_fn=lambda: clock["t"])  # parse only
    operations: Counter = Counter()
    capacity_waits: List[Any] = []
    samples = lines = 0
    real: List[float] = []
    output: List[float] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        lines += 1
        fields = TelemetryObserver.parse_fields(raw)
        if fields is None:
            continue
        operations[str(fields.get("operation") or "?")] += 1
        if fields.get("operation") == "runtime-transition-pending" and fields.get("generated_capacity_pending") == "1":
            capacity_waits.append(fields.get("available_generated_capacity"))
        clock["t"] += 0.25
        sample = observer.consume_line(raw, now=clock["t"])
        if sample is not None:
            samples += 1
            real.append(sample.real_fps)
            output.append(sample.output_fps)
    return {
        "lines": lines, "parsed_events": sum(operations.values()), "fps_samples": samples,
        "operations": dict(operations.most_common(12)),
        "delivery_misses": operations["generated-delivery-miss"],
        "acquire_quarantines": operations["ordered-acquire-quarantine"],
        "capacity_waits": len(capacity_waits),
        "available_capacity": capacity_waits[-1] if capacity_waits else None,
        "real_median": statistics.median(real) if real else None,
        "output_median": statistics.median(output) if output else None,
    }


def analyze(bundle: zipfile.ZipFile) -> Dict[str, Any]:
    names = bundle.namelist()
    timeline = _jsonl(_read(bundle, "timeline.jsonl"))
    samples = [r for r in timeline if "marker" not in r]
    self_test = []
    try:
        self_test = json.loads(_read(bundle, "self_test.json") or "[]")
    except ValueError:
        pass
    events = _jsonl(_read(bundle, "governor-events.jsonl"))
    diag_text = "".join(_read(bundle, n) for n in names if n.startswith("diagnostics-"))
    diag = analyze_diagnostics(diag_text)

    report: Dict[str, Any] = {"files": len(names), "samples": len(samples), "diagnostics": diag}
    try:
        index = json.loads(_read(bundle,"diagnostics-index.json") or "{}")
        report["diagnostic_export"] = index
    except ValueError:
        report["diagnostic_export"] = {}
    try:
        report["plugin_version"] = json.loads(_read(bundle, "system.json") or "{}").get("plugin_version")
    except (ValueError, AttributeError):
        report["plugin_version"] = None
    if samples:
        t0, t1 = samples[0].get("t"), samples[-1].get("t")
        report["duration_s"] = round(t1 - t0, 1) if isinstance(t0, (int, float)) and isinstance(t1, (int, float)) else None
        report["states"] = dict(Counter(str(r.get("state")) for r in samples).most_common())
        report["reasons"] = dict(Counter(str(r.get("reason")) for r in samples).most_common(8))
        report["points"] = dict(Counter(str(r.get("point")) for r in samples if r.get("point")).most_common(8))
        out = [r["output"] for r in samples if isinstance(r.get("output"), (int, float))]
        real = [r["real"] for r in samples if isinstance(r.get("real"), (int, float))]
        tdp = [r["tdp"] for r in samples if isinstance(r.get("tdp"), (int, float))]
        temps = [(r.get("sensors") or {}).get("temp_c") for r in samples]
        temps = [t for t in temps if isinstance(t, (int, float))]
        report["output"] = {"median": statistics.median(out) if out else None, "p5": _percentile(out, 5)}
        report["real"] = {"median": statistics.median(real) if real else None, "p5": _percentile(real, 5)}
        report["tdp"] = {"min": min(tdp) if tdp else None, "max": max(tdp) if tdp else None}
        report["temp_max_c"] = max(temps) if temps else None
        report["target"] = next((r["target"] for r in samples if r.get("target")), None)
        report["telemetry_available_share"] = round(
            sum(bool((r.get("snapshot") or {}).get("available")) for r in samples) / len(samples), 2)
        report["bottlenecks"] = dict(Counter((r.get("diagnosis") or {}).get("bottleneck") for r in samples if r.get("diagnosis")))
        report["apply_share"] = round(sum(r.get("state") == "APPLY" for r in samples) / len(samples), 2)
        diag_rows = [r.get("diagnosis") or {} for r in samples]
        report["warm_share"] = round(sum(d.get("thermal") in ("hot", "heating") for d in diag_rows) / len(samples), 2)
        report["stutter_share"] = round(sum(d.get("smoothness") == "stuttering" for d in diag_rows) / len(samples), 2)
        report["thermal_holds"] = sum(1 for r in samples if str(r.get("reason") or "").startswith("thermal-quality-held"))
    report["events"] = dict(Counter(str(e.get("event")) for e in events).most_common(12))
    report["rejections_by_reason"] = dict(Counter(str(e.get("reason")) for e in events
                                                  if e.get("event") == "operating-point-rejected"))
    report["mode_switches"] = sum(1 for e in events if e.get("event") == "operating-point-released"
                                  and e.get("reason") == "governor-mode-changed")
    failed_power = Counter()
    for e in events:
        before, after = e.get("before") or {}, e.get("after") or {}
        if (e.get("event") == "budget-step" and str(e.get("reason") or "").startswith("probe-failed")
                and isinstance(before.get("tdp_w"), (int, float)) and isinstance(after.get("tdp_w"), (int, float))
                and after["tdp_w"] > before["tdp_w"]):
            failed_power[before["tdp_w"]] += 1
    report["failed_power_probes"] = {f"{w:g} W": n for w, n in sorted(failed_power.items())}
    not_bound = [e for e in events if e.get("event") == "budget-guard-not-power-bound"]
    draws = [e["draw_w"] for e in not_bound if isinstance(e.get("draw_w"), (int, float))]
    report["not_power_bound_holds"] = {
        "count": len(not_bound),
        "draw_w_median": round(statistics.median(draws), 1) if draws else None,
        "caps_w": sorted({e["cap_w"] for e in not_bound if isinstance(e.get("cap_w"), (int, float))}),
    }
    report["rejected_points"] = sorted({str(e.get("point")) for e in events if e.get("event") == "operating-point-rejected"})
    cadence = []
    for event in events:
        if event.get("event") != "operating-point-rejected":
            continue
        evidence = event.get("cadence") if isinstance(event.get("cadence"), dict) else {}
        delivered_out, delivered_real = evidence.get("delivered_output_fps"), evidence.get("delivered_real_fps")
        if delivered_out is None and delivered_real is None:
            continue
        cadence.append({
            "point": str(event.get("point")),
            "reason": str(event.get("reason") or ""),
            "delivered_output_fps": delivered_out,
            "delivered_real_fps": delivered_real,
            "requested_output_fps": evidence.get("requested_output_fps"),
            "requested_real_fps": evidence.get("requested_real_fps"),
        })
    report["rejection_cadence"] = cadence
    report["failed_checks"] = [c for c in self_test if not c.get("ok")]
    report["overlay_burst_before_exit"] = overlay_burst_before_exit(_jsonl(_read(bundle, "activity.jsonl")))
    report["frame_os"] = frame_os_summary(samples, _read(bundle, "game-processes.json"))
    if report["frame_os"] is not None:
        bursts=[(r.get("frame_os") or {}).get("burst_observations") for r in samples]
        bursts=[b for b in bursts if isinstance(b,dict)]
        report["frame_os"]["short_bursts"]={"available":bool(bursts),**{
            k:max((b.get(k) or 0 for b in bursts),default=0)
            for k in ("windows","accelerated_windows","seconds","peak_real_hz")},"gain_measured":False}
    report["stick_touch_boost"] = stick_touch_boost_summary(samples)
    if report["frame_os"]:
        report["frame_os"]["by_level"] = frame_os_by_level(samples)
        report["frame_os"]["injection"] = dict(Counter(
            f"{e.get('event')}:{e.get('reason')}" for e in events if str(e.get("event", "")).startswith("frame-os-injection")))
    report["power_split"] = power_split_summary(events)
    rows = [r.get("power_split") for r in samples if isinstance(r.get("power_split"), dict)]
    if report["power_split"] and rows:
        report["power_split"]["capped_share"] = round(sum(bool(r.get("cap_khz")) for r in rows) / len(rows), 2)
    report["extreme"] = extreme_summary(samples, events)
    report["render_scale"] = render_scale_summary(events, diag_text)
    report["frame_fusion"] = frame_fusion_summary(samples)
    try:
        identity = json.loads(_read(bundle, "renderer-identity.json") or "{}")
        processes = identity.get("processes", []) if isinstance(identity, dict) else []
        libraries = [lib for process in processes if isinstance(process, dict)
                     for lib in (process.get("renderer_files") or []) if isinstance(lib, dict)]
        report["frame_fusion"]["renderer_identity"] = {
            "available": bool(libraries),
            "matched": sum(lib.get("matches_plugin_manifest") is True for lib in libraries),
            "mismatched": sum(lib.get("matches_plugin_manifest") is False for lib in libraries),
            "unknown": sum(lib.get("matches_plugin_manifest") is None for lib in libraries)}
    except (ValueError, TypeError, AttributeError):
        report["frame_fusion"]["renderer_identity"] = {"available": False}
    actions = _jsonl(_read(bundle, "activity.jsonl"))
    report["frame_fusion"]["enable_requested_in_activity"] = any(
        a.get("kind") == "set_governor_frame_fusion" and isinstance(a.get("args"), dict)
        and a["args"].get("enabled") is True
        for a in actions)
    report["temporal_engine"] = temporal_engine_summary(samples)
    report["temporal_engine"]["renderer_log"] = temporal_engine_log_summary(diag_text)
    report["findings"] = findings(report, names)
    return report


def temporal_engine_summary(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Experimental engine across the recording. GPU times are the engine's own
    timestamp queries; presentation is not observable there and stays unknown."""
    rows = [r["temporal_engine"] for r in samples if isinstance(r.get("temporal_engine"), dict)]
    active = [r for r in rows if r.get("state") in ("generating", "shadow-measuring")]
    last = active[-1] if active else (rows[-1] if rows else None)
    reasons = sorted({x for r in rows for x in (r.get("fallback_reasons") or []) if isinstance(x, str)})
    return {"available": bool(rows), "samples": len(rows),
            "requested_modes": dict(Counter(str(r.get("requested_mode", "off")) for r in rows)),
            "states": dict(Counter(str(r.get("state", "unknown")) for r in rows)),
            "active_samples": len(active), "fallback_reasons": reasons[:8],
            "last_active": last, "presented": None, "verified_on_hardware": False}


def temporal_engine_log_summary(text: str) -> Dict[str, Any]:
    """The engine's own 10 s stats lines in the renderer log (te.3+)."""
    rows = []
    for line in (text or "").splitlines():
        if "Temporal Engine stats " not in line:
            continue
        fields = dict(part.split("=", 1) for part in line.split("Temporal Engine stats ", 1)[1].split() if "=" in part)
        rows.append(fields)
    if not rows:
        return {"available": False}

    def nums(key):
        out = []
        for r in rows:
            try:
                out.append(float(r[key]))
            except (KeyError, ValueError):
                pass
        return out

    def med(key):
        values = nums(key)
        return round(statistics.median(values), 2) if values else None

    orphans = [r.get("orphans", "").split("/") for r in rows]
    orphans = [[float(x) for x in o] for o in orphans if len(o) == 2 and all(x.replace(".", "", 1).isdigit() for x in o)]
    # te.5 (LMC): GPU time of every analysis pass, "a/b/.../h" in lmc_passes order
    passes = []
    for r in rows:
        names, values = r.get("lmc_passes", "").split("/"), r.get("lmc_ms", "").split("/")
        try:
            if len(names) == len(values) > 1:
                passes.append(dict(zip(names, (float(v) for v in values))))
        except ValueError:
            pass
    pass_names = list(passes[0]) if passes else []
    shares = [r.get("shares", "") .split("/") for r in rows]
    shares = [[float(x) for x in s] for s in shares if len(s) == 3 and all(x.replace(".", "", 1).isdigit() for x in s)]
    return {"available": True, "lines": len(rows),
            "levels": dict(Counter(r.get("level", "?") for r in rows)),
            "reasons": dict(Counter(r.get("reason", "?") for r in rows)),
            "holding_share": round(sum(r.get("holding") == "1" for r in rows) / len(rows), 2),
            "cost_holds": max((int(r["cost_holds"]) for r in rows if r.get("cost_holds", "").isdigit()), default=0),
            # te.7 (LMC): cost tiers the generator ran at, and how often it changed tier
            "tiers": dict(Counter(r["tier"] for r in rows if "tier" in r)),
            "tier_steps": max((int(r["tier_steps"]) for r in rows if r.get("tier_steps", "").isdigit()), default=0),
            "fixed_ms_median": med("fixed_ms"), "frame_ms_median": med("frame_ms"),
            "pair_p95_ms_median": med("pair_p95_ms"), "cap_ms": med("cap_ms"),
            "interval_ms_median": med("interval_ms"),
            "shares_median": [round(statistics.median(s[i] for s in shares), 3) for i in range(3)] if shares else None,
            # te.4 (LMC): which generator, the GPU split and what the motion model found
            "algorithms": dict(Counter(r.get("algo", "tiles") for r in rows)),
            "pyramid_ms_median": med("pyramid_ms"), "analyze_ms_median": med("analyze_ms"),
            "fields_ms_median": med("fields_ms"), "layers_median": med("layers"),
            "orphans_median": [round(statistics.median(o[i] for o in orphans), 1) for i in range(2)] if orphans else None,
            "lmc_passes_ms_median": {k: round(statistics.median(p[k] for p in passes if k in p), 3)
                                     for k in pass_names} if passes else None}


def stick_touch_boost_summary(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [(r.get("frame_os") or {}).get("touch_boost") for r in samples
        if isinstance(r.get("frame_os"), dict)]
    rows = [r for r in rows if isinstance(r, dict)]
    return {"available": bool(rows), "samples": len(rows),
        "states": dict(Counter(str(r.get("state", "unknown")) for r in rows)),
        "enabled_samples": sum(r.get("enabled") is True for r in rows),
        "fresh_contact_samples": sum(r.get("signal_fresh") is True and r.get("right_stick_touch") is True for r in rows),
        "requested_samples": sum(r.get("requested") is True for r in rows),
        "submitted_samples": sum(r.get("submitted") is True for r in rows),
        "maximum_touch_requests_snapshot": max((r["touch_requests"] for r in rows
            if type(r.get("touch_requests")) is int and 0 <= r["touch_requests"] < 2**64), default=0),
        "last": rows[-1] if rows else None, "gain_measured": False}


def frame_fusion_summary(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [r["frame_fusion"] for r in samples if isinstance(r.get("frame_fusion"), dict)]
    latest_contexts = next(({"captured_at": r.get("t"), "contexts": r["frame_fusion"]["contexts"]}
        for r in reversed(samples) if isinstance(r.get("frame_fusion"), dict)
        and isinstance(r["frame_fusion"].get("contexts"), list) and r["frame_fusion"]["contexts"]), None)
    return {"available": bool(rows), "samples": len(rows),
        "states": dict(Counter(str(r.get("state", "unknown")) for r in rows)),
        "enabled_samples": sum(r.get("enabled") is True for r in rows),
        "observed_samples": sum(r.get("path_observed") is True for r in rows),
        # Counters are native publication snapshots and reset with contexts.
        # Repeated snapshots must never be summed as a session copy total.
        "maximum_avoided_copies_snapshot": max((
            r.get("avoided_source_copies_at_last_publication", 0) for r in rows
            if type(r.get("avoided_source_copies_at_last_publication")) is int
            and 0 <= r["avoided_source_copies_at_last_publication"] < 2**64), default=0),
        "processing_paths": dict(Counter(str(r.get("processing_path", "legacy")) for r in rows)),
        "maximum_native_transfers_snapshot": max((
            r.get("native_source_transfers_at_last_publication", 0) for r in rows
            if type(r.get("native_source_transfers_at_last_publication")) is int
            and 0 <= r["native_source_transfers_at_last_publication"] < 2**64), default=0),
        "maximum_native_conversion_blits_avoided_snapshot": max((
            r.get("native_conversion_blits_avoided_at_last_publication", 0) for r in rows
            if type(r.get("native_conversion_blits_avoided_at_last_publication")) is int
            and 0 <= r["native_conversion_blits_avoided_at_last_publication"] < 2**64), default=0),
        "last": rows[-1] if rows else None, "last_context_sample": latest_contexts, "gain_measured": False}


def extreme_summary(samples: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Both observed PPT channels, including transitions before a point is confirmed."""
    samples = [r for r in samples if isinstance(r.get("extreme"), dict)]
    if not samples:
        return None
    rows = [r["extreme"] for r in samples]
    ceilings = [(r.get("ceiling") or {}).get("ceiling_w") for r in rows]
    ceilings = [c for c in ceilings if isinstance(c, (int, float))]
    observed, owned = [], []
    above = owned_above = 0
    for sample in samples:
        caps = [sample[k] for k in ("tdp", "tdp_fast")
                if isinstance(sample.get(k), (int, float))]
        observed.extend(caps)
        if sample.get("tdp_owned"):
            owned.extend(caps)
        ceiling = (sample["extreme"].get("ceiling") or {}).get("ceiling_w")
        if caps and isinstance(ceiling, (int, float)) and max(caps) > ceiling + 0.05:
            above += 1
            owned_above += bool(sample.get("tdp_owned"))
    applied = [r.get("applied") or {} for r in rows]
    scales = Counter(str(a.get("render_pct")) for a in applied if a.get("render_pct") is not None)
    return {
        "samples": len(rows),
        "states": dict(Counter(str(r.get("state")) for r in rows)),
        "ceiling_w": min(ceilings) if ceilings else None,
        "max_tdp_w": max(owned) if owned else None,
        "max_observed_tdp_w": max(observed) if observed else None,
        "above_ceiling_samples": above,
        "owned_above_ceiling_samples": owned_above,
        "confirmed_scales": dict(scales),
        "acknowledged": sum(1 for e in events if e.get("event") in ("render-scale-acknowledged", "extreme-scale-acknowledged")),
        "not_acknowledged": sum(1 for e in events if e.get("event") in ("render-scale-not-acknowledged", "extreme-scale-not-acknowledged")),
    }


def render_scale_summary(events: List[Dict[str, Any]], diagnostics: str) -> Optional[Dict[str, Any]]:
    """Did the game really render at a lower resolution?  The renderer's own scaler reports."""
    from .extreme import SWAPCHAIN_POLICY_MARKER, parse_swapchain_policy  # noqa: PLC0415

    policies = [parse_swapchain_policy(line) for line in diagnostics.splitlines() if SWAPCHAIN_POLICY_MARKER in line]
    policies = [p for p in policies if p]
    refused = Counter(str(e.get("reason")) for e in events if e.get("event") == "render-scale-refused")
    acked = sum(1 for e in events if e.get("event") in ("render-scale-acknowledged", "extreme-scale-acknowledged"))
    if not policies and not refused and not acked:
        return None
    last = policies[-1] if policies else {}
    return {"reports": len(policies), "active": sum(1 for p in policies if p.get("active")),
            "last_reason": last.get("reason"), "advertised": last.get("advertised"),
            "actual": last.get("source"), "refused": dict(refused), "acknowledged": acked}


def _wxh(extent: Any) -> str:
    return f"{extent[0]}x{extent[1]}" if isinstance(extent, (list, tuple)) and len(extent) == 2 else "?"


def power_split_summary(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Smart power split (1.5): the CPU clock steps, why the cap came off, and the A/B pairs."""
    steps = [e for e in events if e.get("event") == "power-split"]
    pairs = [e for e in events if e.get("event") == "power-split-ab"]
    if not steps and not pairs:
        return None
    khz = [e["cpu_khz"] for e in steps if isinstance(e.get("cpu_khz"), (int, float))]
    capped = [k for k, e in zip(khz, steps) if e.get("level")]

    def col(key: str) -> List[float]:
        return [float(e[key]) for e in pairs if isinstance(e.get(key), (int, float))]

    from .frame_os.proof import stats  # noqa: PLC0415 - the same interval maths as the Frame OS A/B
    gain = stats(col("gain"))
    mhz, draw, real = col("mhz"), col("draw"), col("real")
    return {
        "reasons": dict(Counter(str(e.get("reason")) for e in steps)),
        "lowest_khz": min(capped) if capped else None,
        "gain": gain,
        "mhz_pct": round(statistics.mean(mhz), 1) if mhz else None,
        "draw_pct": round(statistics.mean(draw), 1) if draw else None,
        "real_delta": round(statistics.mean(real), 2) if real else None,
    }


def frame_os_by_level(samples: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per decision (rest / calm / boost): what the layer measured and what the player got.

    Answers the Act question directly: does boost deliver more real frames and lower freshness,
    and does output smoothness hold while the cadence moves?"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in samples:
        fo = r.get("frame_os")
        if not isinstance(fo, dict) or not fo.get("level"):
            continue
        layer = fo.get("layer") or {}
        if not layer.get("live"):
            continue
        groups.setdefault(str(fo["level"]), []).append({**layer, "_output": r.get("output"), "_tdp": r.get("tdp"),
                                                        "_acting": fo.get("acting")})

    def med(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
        values = [x[key] for x in rows if isinstance(x.get(key), (int, float)) and x[key] > 0]
        return round(statistics.median(values), 2) if values else None

    out: Dict[str, Dict[str, Any]] = {}
    for level, rows in sorted(groups.items()):
        interval = med(rows, "present_interval_p50_ms")
        outputs = [x["_output"] for x in rows if isinstance(x.get("_output"), (int, float))]
        out[level] = {
            "samples": len(rows),
            "acting_share": round(sum(1 for x in rows if x.get("_acting")) / len(rows), 2),
            "real_fps": round(1000.0 / interval, 1) if interval else None,
            "freshness_ms": med(rows, "freshness_ms"),
            "present_hold_ms": med(rows, "present_hold_ms"),
            "interval_p95_ms": med(rows, "present_interval_p95_ms"),
            "output_p5": _percentile(outputs, 5) if outputs else None,
            "tdp_w": med(rows, "_tdp"),
        }
    return out


def frame_os_summary(samples: List[Dict[str, Any]], processes_json: str) -> Optional[Dict[str, Any]]:
    """Frame OS (development): did the layer load and answer, and what it measured."""
    rows = [r["frame_os"] for r in samples if isinstance(r.get("frame_os"), dict)]
    if not rows:
        return None
    layer = [r.get("layer") or {} for r in rows]
    # a sample answers only when the telemetry is live (its writer runs and presented within 1 s)
    answering = [x for x in layer if x.get("live") and (x.get("frames") or 0) > 0]

    def med(key: str) -> Optional[float]:
        values = [x[key] for x in answering if isinstance(x.get(key), (int, float)) and x[key] > 0]
        return round(statistics.median(values), 2) if values else None

    try:
        processes = json.loads(processes_json or "[]")
    except ValueError:
        processes = []
    loaded = [p.get("frame_os_layer_loaded") for p in processes if isinstance(p, dict)]
    not_loaded = [p for p in processes if isinstance(p, dict) and p.get("frame_os_layer_loaded") is False]
    return {
        "modes": dict(Counter(str(r.get("mode")) for r in rows)),
        "layer_installed": any(r.get("layer_installed") for r in rows),
        "layer_errors": sorted({str(r["layer_error"]) for r in rows if r.get("layer_error")}),
        "answering_share": round(len(answering) / len(rows), 2),
        "frames": max((x.get("frames") or 0 for x in answering), default=0),
        "freshness_ms": med("freshness_ms"),
        "present_interval_p50_ms": med("present_interval_p50_ms"),
        "present_interval_p95_ms": med("present_interval_p95_ms"),
        "cost_p50_ms": med("cost_p50_ms"),
        "present_hold_ms": med("present_hold_ms"),
        "acquire_block_ms": med("acquire_block_ms"),
        "engines": sorted({str(x["engine"]) for x in layer if x.get("engine")}),
        "passthrough": any(x.get("passthrough") for x in layer),
        "swapchain_recreations": max((x.get("swapchain_recreations") or 0 for x in layer), default=0),
        "levels": dict(Counter(str(r.get("level")) for r in rows if r.get("level"))),
        "input_sources": dict(Counter(str((r.get("input") or {}).get("source")) for r in rows if r.get("input"))),
        "input_gamepads": max(((r.get("input") or {}).get("gamepads") for r in rows
                              if isinstance((r.get("input") or {}).get("gamepads"), (int, float))), default=None),
        "input_events": max(((r.get("input") or {}).get("events") or 0 for r in rows), default=0),
        # the in-game A/B check: the last sample holds the session's pairs so far
        "ab": next((r.get("proof") for r in reversed(rows) if isinstance(r.get("proof"), dict)), None),
        "ab_control_share": round(sum(1 for r in rows if r.get("ab_control")) / len(rows), 3),
        "loaded_in_game": (any(loaded) if loaded else None),
        "not_loaded_processes": sorted({str(p.get("comm") or p.get("pid")) for p in not_loaded}),
        # The launcher exports the control-file path only when Frame OS was on at game start.
        "started_without_frame_os": bool(not_loaded) and all(
            "GFG_FRAME_OS_SHM" not in (p.get("env") or {}) for p in not_loaded),
    }


def overlay_burst_before_exit(activity: List[Dict[str, Any]], window_s: float = 30.0) -> Optional[int]:
    """Overlay changes in the ``window_s`` before the game exited (None if it did not exit)."""
    exits = [a.get("ts") for a in activity if a.get("kind") == "game-exited" and isinstance(a.get("ts"), (int, float))]
    if not exits:
        return None
    end = exits[-1]
    changes = [a for a in activity if a.get("kind") == "set_governor_hud" and isinstance(a.get("ts"), (int, float))
               and end - window_s <= a["ts"] <= end]
    return len(changes)


def _version(text: Any) -> Optional[tuple]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in match.groups()) if match else None


def findings(report: Dict[str, Any], names: Iterable[str]) -> List[str]:
    out: List[str] = []
    diag = report.get("diagnostics") or {}
    if diag.get("delivery_misses"):
        out.append(f"Renderer delivery misses: {diag['delivery_misses']}; acquire quarantines: {diag.get('acquire_quarantines',0)}. "
                   "Inspect focus/menu transitions and raw diagnostics; these are runtime faults even if setup checks pass.")
    incomplete = [r for r in (report.get("diagnostic_export") or {}).get("files",[]) if r.get("truncated") or r.get("initial_segment_unavailable")]
    if incomplete:
        out.append("Renderer diagnostic export is incomplete: " + ", ".join(r.get("path","?") for r in incomplete) + ". Missing events cannot be ruled out.")
    recorded, current = _version(report.get("plugin_version")), _version(CURRENT_VERSION)
    if recorded and current and recorded < current:
        out.append(f"Recorded with {'.'.join(map(str, recorded))}; this report is from {CURRENT_VERSION}. "
                   "Some of what the log shows may already be fixed (see the release notes).")
    diag = report["diagnostics"]
    for check in report["failed_checks"]:
        out.append(f"Self-test failed: {check.get('check')} ({check.get('detail') or 'no detail'})")
    if report["samples"] == 0:
        out.append("The timeline is empty: the recorder never sampled the Governor (plugin stopped?).")
        return out
    if diag["lines"] == 0:
        out.append("No renderer diagnostics were written during the recording: the game was not started "
                   "with the GFG launch command, the engine did not attach, or diagnostics are off.")
    elif diag["fps_samples"] == 0:
        out.append(f"The renderer wrote {diag['lines']} diagnostic lines but none carried an FPS reading "
                   f"(operations: {', '.join(diag['operations']) or 'none'}): the Governor cannot see the frame rate.")
    if diag.get("capacity_waits"):
        cap = diag.get("available_capacity")
        out.append(f"{diag['capacity_waits']} requests needed more generated frames than the renderer had "
                   f"(capacity {cap}, so at most x{int(cap) + 1 if str(cap).isdigit() else '?'}); "
                   "it fell back to a lower ratio instead.")
    share = report.get("telemetry_available_share")
    if share is not None and share < 0.5 and diag["fps_samples"]:
        out.append(f"Telemetry was usable only {int(share * 100)}% of the time (stale or missing FPS events).")
    states = report.get("states", {})
    touch = report.get("stick_touch_boost") or {}
    if touch.get("enabled_samples"):
        out.append(f"Stick touch Boost: {touch['fresh_contact_samples']} samples with fresh contact, "
                   f"{touch['requested_samples']} requests and {touch['submitted_samples']} acknowledged submissions. "
                   f"States {touch['states']}; maximum touch-request snapshot {touch['maximum_touch_requests_snapshot']}. "
                   "Contact, requests and acknowledgements do not establish increased renderer FPS or energy benefit.")
    if states.get("PAUSED", 0) > 0.3 * report["samples"]:
        top = next(iter(report["reasons"]), "?")
        out.append(f"The Governor was PAUSED for {states['PAUSED']} of {report['samples']} samples; most common reason: {top}.")
    apply_share = report.get("apply_share")
    if apply_share is not None and apply_share > 0.15:
        out.append(f"The Governor spent {int(apply_share * 100)}% of the session waiting for the renderer to confirm "
                   f"a setting (rejections by reason: {report.get('rejections_by_reason')}).")
    if report.get("mode_switches"):
        out.append(f"The mode was switched {report['mode_switches']} times during the recording; each switch starts a new search.")
    temporal = report.get("temporal_engine") or {}
    if temporal.get("available") and set(temporal.get("requested_modes") or {}) - {"off"}:
        last = temporal.get("last_active") or {}
        text = (f"Temporal Engine (experimental): states {temporal['states']}; active in "
                f"{temporal['active_samples']} of {temporal['samples']} samples.")
        if last.get("state") in ("generating", "shadow-measuring"):
            text += (f" Last: shares {last.get('shares')}, GPU ms {last.get('gpu_ms')}, dispatched "
                     f"{last.get('outputs_dispatched')} / GPU-completed {last.get('outputs_gpu_completed')}, "
                     f"dropped {last.get('dropped')}, recommendation {last.get('recommendation')}.")
        tlog = temporal.get("renderer_log") or {}
        if tlog.get("available"):
            text += (f" Renderer log ({tlog['lines']} lines): levels {tlog['levels']}, holding "
                     f"{int(tlog['holding_share'] * 100)}% of the time ({tlog['cost_holds']} cost holds, "
                     f"tiers {tlog.get('tiers') or {}}, {tlog.get('tier_steps', 0)} tier changes), "
                     f"fixed {tlog['fixed_ms_median']} ms + {tlog['frame_ms_median']} ms per generated frame "
                     f"(cap {tlog['cap_ms']} ms), shares reuse/light/full {tlog['shares_median']}.")
        if temporal.get("fallback_reasons"):
            text += " LSFG kept frame generation: " + ", ".join(temporal["fallback_reasons"]) + "."
        out.append(text + " Presentation is not observed by the engine; no FPS, latency or energy gain is implied.")
    fusion = report.get("frame_fusion") or {}
    if fusion.get("available"):
        out.append(f"Frame Fusion: states {fusion['states']}; native direct path observed in "
                   f"{fusion['observed_samples']} of {fusion['samples']} recorded samples; "
                   f"maximum avoided-copy publication snapshot {fusion['maximum_avoided_copies_snapshot']}. "
                   f"Native source transfers snapshot {fusion['maximum_native_transfers_snapshot']}; "
                   f"BGRA conversion blits avoided snapshot {fusion['maximum_native_conversion_blits_avoided_snapshot']}; "
                   f"processing paths {fusion['processing_paths']}. "
                   "Snapshots are not a session copy total or proof of FPS, latency or energy improvement.")
        last = fusion.get("last") or {}
        context_sample = fusion.get("last_context_sample") or {}
        for context in (context_sample.get("contexts") or [])[:3]:
            if not isinstance(context, dict):
                continue
            scaling = context.get("spatial_scaling") or {}
            out.append(f"Last captured Frame Fusion context {context.get('pid')}/{context.get('context')} "
                       f"at {context_sample.get('captured_at')}: "
                       f"{context.get('eligibility', 'unknown')}; "
                       f"source {scaling.get('source_width')}x{scaling.get('source_height')}, "
                       f"presentation {scaling.get('presentation_width')}x{scaling.get('presentation_height')}, "
                       f"pipeline {scaling.get('pipeline')}; native scaling reason "
                       f"{scaling.get('inactive_reason') or scaling.get('constraint_reason') or scaling.get('fallback_reason') or 'none reported'}.")
        identity = fusion.get("renderer_identity") or {}
        if identity.get("available"):
            out.append(f"Mapped renderer file identity: {identity.get('matched', 0)} match the plugin manifest, "
                       f"{identity.get('mismatched', 0)} differ, {identity.get('unknown', 0)} are unconfirmed. "
                       "File identity does not establish GPU completion or a performance gain.")
        if last.get("enabled") is True and not fusion["observed_samples"]:
            out.append("Frame Fusion was enabled but this recording contains no observed direct-path work. "
                       "Check native contexts for restart, scaler eligibility and source/presentation extents.")
    elif fusion.get("enable_requested_in_activity"):
        out.append("Frame Fusion was enabled in the UI, but its native status was not captured. "
                   "This log cannot establish whether Fusion executed.")
    repeated = {w: n for w, n in (report.get("failed_power_probes") or {}).items() if n >= 3}
    if repeated:
        out.append("Lower-power probes failed repeatedly at the same level ("
                   + ", ".join(f"{w} x{n}" for w, n in repeated.items())
                   + "); each failure is a short FPS dip.")
    held = report.get("not_power_bound_holds") or {}
    if held.get("count", 0) >= 3:
        caps = ", ".join(f"{w:g} W" for w in held.get("caps_w") or []) or "?"
        out.append(f"The guard held {held['count']} times without adding watts because the APU drew well under "
                   f"the cap (median draw {held.get('draw_w_median')} W at {caps}): the shortfall was not power "
                   "(CPU, streaming or hitches).")
    if report.get("rejected_points"):
        sentence = ("Operating points the renderer did not confirm or that failed their trial: "
                    + ", ".join(report["rejected_points"]) + ".")
        shown = report.get("rejection_cadence") or []
        if shown:
            bits = [f"{row['point']} delivered output {row['delivered_output_fps']} / real {row['delivered_real_fps']}"
                    f" (asked output {row['requested_output_fps']}, real {row['requested_real_fps']})"
                    for row in shown]
            sentence += " Measured cadence, not the planned multiplier: " + "; ".join(bits) + "."
        out.append(sentence)
    target, out_med = report.get("target"), (report.get("output") or {}).get("median")
    if target and out_med is not None and out_med < 0.9 * target:
        out.append(f"Median output FPS {out_med:.0f} is below the {target} FPS target.")
    elif target and out_med is not None:
        out.append(f"Median output FPS {out_med:.0f} against a {target} FPS target.")
    if report.get("temp_max_c") is not None and report["temp_max_c"] >= 85:
        out.append(f"The APU reached {report['temp_max_c']:.0f} °C.")
    warm = report.get("warm_share")
    if warm and warm >= 0.1:
        held = report.get("thermal_holds") or 0
        out.append(f"The APU was hot or heating up {int(warm * 100)}% of the time"
                   + (f"; quality steps were held back for heat in {held} samples." if held else "."))
    stutter = report.get("stutter_share")
    if stutter and stutter >= 0.1:
        out.append(f"Frametime stutter (spikes over the median) in {int(stutter * 100)}% of the samples.")
    burst = report.get("overlay_burst_before_exit")
    if burst and burst >= 3:
        out.append(f"The game exited within 30 s after {burst} in-game overlay changes "
                   "(MangoHud re-reads its config on every change).")
    if not any(n.startswith("overlay/") for n in names):
        out.append("No overlay files were captured: the in-game overlay was never published (Settings → In-game overlay).")
    fo = report.get("frame_os")
    if fo:
        if fo["layer_errors"]:
            out.append("Frame OS: the layer could not be installed: " + "; ".join(fo["layer_errors"]) + ".")
        elif fo["loaded_in_game"] is False and fo.get("started_without_frame_os"):
            out.append("Frame OS was switched on after the game had started (or was off at launch): it loads "
                       "only at game start. Switch it on, then restart the game.")
        elif fo["loaded_in_game"] is False:
            who = ", ".join(fo.get("not_loaded_processes") or []) or "the game process"
            out.append(f"Frame OS was on, but {who} did not load the Frame OS layer "
                       "(not loaded: 32-bit game? The layer is 64-bit only).")
        elif fo["answering_share"] == 0:
            out.append("Frame OS was on, but the layer never reported live frames (it did not load, it "
                       "could not open the control file, or another process owned it).")
        else:
            if fo.get("passthrough"):
                out.append("Frame OS: the layer hit an internal error and switched to pass-through.")
            out.append(f"Frame OS ({', '.join(fo['modes'])}): the layer reported {fo['frames']} frames; "
                       f"freshness {fo['freshness_ms']} ms, present interval {fo['present_interval_p50_ms']} / "
                       f"{fo['present_interval_p95_ms']} ms (p50 / p95), present hold "
                       f"{fo.get('present_hold_ms')} ms" + (f", engine {', '.join(fo['engines'])}" if fo.get("engines") else "")
                       + ".")
        if fo.get("injection"):
            out.append(f"Frame OS Act executor events: {fo['injection']}.")
        ab = fo.get("ab") or {}
        parts = []
        for metric in ("response", "frames", "energy"):
            r = ab.get(metric) or {}
            if r.get("n") and isinstance(r.get("mean"), (int, float)):
                session_n = r.get("session_n")
                current = r.get("session")
                if isinstance(current, dict) and current.get("n"):
                    shown, scope = current, "current session"
                elif session_n == 0:
                    shown, scope = r, "historical; no pairs in this session"
                elif isinstance(session_n, int) and session_n == r["n"]:
                    shown, scope = r, "current session"
                elif isinstance(session_n, int):
                    shown, scope = r, f"history + current session; {session_n} current pairs"
                else:
                    shown, scope = r, "session provenance unknown"
                interval = f" ({shown['low']}..{shown['high']})" if shown.get("low") is not None else ""
                confidence = "; preliminary" if shown.get("measured") is False else ""
                parts.append(f"{metric} {shown['mean']:+}%{interval} over {shown['n']} "
                             f"pair{'s' if shown['n'] != 1 else ''} [{scope}{confidence}]")
        if parts:
            out.append("Frame OS A/B telemetry (Act vs. control): " + "; ".join(parts)
                       + f"; control windows {round(100 * fo.get('ab_control_share', 0), 1)}% of samples.")
            if (ab.get("response") or {}).get("n"):
                out.append("Frame OS response is an internal pacing/freshness metric, not independently measured input-to-display latency.")
        by_level = fo.get("by_level") or {}
        if by_level:
            parts = []
            for level in ("boost", "calm", "rest"):
                row = by_level.get(level)
                if row:
                    parts.append(f"{level}: {row['samples']} samples, {row['real_fps']} real, freshness "
                                 f"{row['freshness_ms']} ms, output p5 {row['output_p5']}"
                                 + (" (acting)" if row["acting_share"] >= 0.5 else ""))
            out.append("Frame OS by decision — " + "; ".join(parts) + ".")
            boost, calm = by_level.get("boost"), by_level.get("calm")
            if (not (fo.get("short_bursts") or {}).get("available") and boost and calm and boost["acting_share"] >= 0.5 and boost.get("real_fps") and calm.get("real_fps")
                    and boost["real_fps"] < calm["real_fps"] + 5):
                out.append("Frame OS Act: boost did not raise the real frame rate (the renderer or the GPU held it).")
        burst=fo.get("short_bursts") or {}
        if burst.get("available"):
            out.append(f"Short Boost observation snapshots: {burst['windows']} qualified windows, {burst['accelerated_windows']} "
                       f"above the calm cadence; peak {burst['peak_real_hz']} real presents/s. "
                       "Repeated snapshots are not added; long FPS medians cannot judge short pulses. "
                       "Forwarding cadence is not a controlled gain or physical scanout measurement.")
        if fo.get("input_sources"):
            if not fo.get("input_events"):
                out.append(f"Frame OS input sensor saw no gamepad input (sources {fo['input_sources']}, "
                           f"{fo.get('input_gamepads')} gamepads open): real-frame decisions stayed at rest.")
            else:
                out.append(f"Frame OS input sensor: {fo['input_events']} gamepad events from "
                           f"{fo.get('input_gamepads') if fo.get('input_gamepads') is not None else 'unknown number of'} "
                           f"gamepads; decisions {fo.get('levels')}.")
    split = report.get("power_split")
    if split:
        reasons = split.get("reasons") or {}
        text = "Power split: "
        if split.get("lowest_khz"):
            text += f"the CPU clock went down to {split['lowest_khz'] / 1e6:.1f} GHz"
        else:
            text += "no successful full-policy CPU cap was recorded (partial or pending writes are not counted)"
        lifts = [f"{n}× for {why.replace('-', ' ')}" for why, n in reasons.items()
                 if why in ("real-frames-short", "cpu-busy")]
        if split.get("capped_share") is not None:
            text += f" (capped {int(100 * split['capped_share'])}% of the time)"
        text += ("; the cap came off " + ", ".join(lifts) if lifts else "") + "."
        g = split.get("gain") or {}
        if g.get("n"):
            interval = f" ({g['low']}..{g['high']})" if g.get("low") is not None else ""
            text += (f" A/B in game (capped vs. the same moment at full CPU clock): GPU clock per watt "
                     f"{g['mean']:+}%{interval} over {g['n']} pair{'s' if g['n'] != 1 else ''}"
                     + (f"; GPU clock {split['mhz_pct']:+}%, draw {-split['draw_pct']:+}%"
                        if split.get("mhz_pct") is not None and split.get("draw_pct") is not None else "")
                     + (f", real FPS {split['real_delta']:+}" if split.get("real_delta") is not None else "") + ".")
        out.append(text)
    rs = report.get("render_scale")
    if rs and rs.get("reports") and not rs.get("active"):
        text = ("Render scale had no effect: the renderer offered the game "
                f"{_wxh(rs.get('advertised'))} but it rendered at {_wxh(rs.get('actual'))} "
                f"({rs.get('last_reason') or 'scaler inactive'}).")
        if rs.get("last_reason") == "application-extent-override-no-source-presentation-split":
            text += " This game sets its own render size, so render scale (the profile's own included) cannot work here."
        out.append(text)
    elif rs and rs.get("active"):
        out.append(f"Render scale was active in {rs['active']} of {rs['reports']} scaler reports.")
    ext = report.get("extreme")
    if ext:
        text = (f"Extreme: ceiling {ext['ceiling_w']} W" if ext.get("ceiling_w") is not None else "Extreme: ceiling unknown")
        if ext.get("max_tdp_w") is not None:
            text += f", highest cap read while owned {ext['max_tdp_w']} W"
            if ext.get("owned_above_ceiling_samples"):
                text += f" (ABOVE THE CEILING in {ext['owned_above_ceiling_samples']} owned samples)"
        if ext.get("max_observed_tdp_w") is not None:
            text += (f"; highest observed cap {ext['max_observed_tdp_w']} W; "
                     f"{ext['above_ceiling_samples']} samples above their contemporaneous ceiling")
        # Readback alone does not establish who wrote a cap, even while GFG claims ownership.
        scales = ", ".join(f"{k}%" for k in sorted(ext.get("confirmed_scales") or {}, key=lambda k: -float(k)))
        text += f"; render scales confirmed by the renderer: {scales or 'none'}"
        if ext.get("not_acknowledged"):
            text += f"; {ext['not_acknowledged']} scale request(s) the renderer never confirmed"
        out.append(text + ".")
    if not out:
        out.append("Nothing unusual found.")
    return out


def render(report: Dict[str, Any]) -> str:
    lines = ["GFG Extreme log summary", "=" * 24, ""]
    lines += [f"- {f}" for f in report["findings"]]
    lines += ["", f"recorded with: {report.get('plugin_version') or 'unknown version'}"]
    lines += [f"samples: {report['samples']}  duration: {report.get('duration_s')} s  target: {report.get('target')}"]
    if report["samples"]:
        lines.append(f"states: {report.get('states')}")
        lines.append(f"top reasons: {report.get('reasons')}")
        lines.append(f"points used: {report.get('points')}")
        lines.append(f"real FPS: {report.get('real')}  output FPS: {report.get('output')}")
        lines.append(f"TDP: {report.get('tdp')}  max temp: {report.get('temp_max_c')} °C  bottlenecks: {report.get('bottlenecks')}")
    d = report["diagnostics"]
    lines.append(f"renderer diagnostics: {d['lines']} lines, {d['parsed_events']} events, {d['fps_samples']} FPS samples; operations: {d['operations']}")
    lines.append(f"governor events: {report.get('events')}")
    return "\n".join(lines) + "\n"


def summarize_zip(path: str) -> str:
    with zipfile.ZipFile(path) as bundle:
        return render(analyze(bundle))
