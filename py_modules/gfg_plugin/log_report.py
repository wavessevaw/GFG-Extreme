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

CURRENT_VERSION = "2.0.1"  # kept in step by scripts/bump_version.py


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
    report["findings"] = findings(report, names)
    return report


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
    if states.get("PAUSED", 0) > 0.3 * report["samples"]:
        top = next(iter(report["reasons"]), "?")
        out.append(f"The Governor was PAUSED for {states['PAUSED']} of {report['samples']} samples; most common reason: {top}.")
    apply_share = report.get("apply_share")
    if apply_share is not None and apply_share > 0.15:
        out.append(f"The Governor spent {int(apply_share * 100)}% of the session waiting for the renderer to confirm "
                   f"a setting (rejections by reason: {report.get('rejections_by_reason')}).")
    if report.get("mode_switches"):
        out.append(f"The mode was switched {report['mode_switches']} times during the recording; each switch starts a new search.")
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
            if (boost and calm and boost["acting_share"] >= 0.5 and boost.get("real_fps") and calm.get("real_fps")
                    and boost["real_fps"] < calm["real_fps"] + 5):
                out.append("Frame OS Act: boost did not raise the real frame rate (the renderer or the GPU held it).")
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
