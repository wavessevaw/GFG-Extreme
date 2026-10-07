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

CURRENT_VERSION = "1.1.0"  # kept in step by scripts/bump_version.py


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
    report["failed_checks"] = [c for c in self_test if not c.get("ok")]
    report["overlay_burst_before_exit"] = overlay_burst_before_exit(_jsonl(_read(bundle, "activity.jsonl")))
    report["frame_os"] = frame_os_summary(samples, _read(bundle, "game-processes.json"))
    report["findings"] = findings(report, names)
    return report


def frame_os_summary(samples: List[Dict[str, Any]], processes_json: str) -> Optional[Dict[str, Any]]:
    """Frame OS (development): did the layer load and answer, and what it measured."""
    rows = [r["frame_os"] for r in samples if isinstance(r.get("frame_os"), dict)]
    if not rows:
        return None
    layer = [r.get("layer") or {} for r in rows]
    answering = [x for x in layer if (x.get("frames") or 0) > 0]

    def med(key: str) -> Optional[float]:
        values = [x[key] for x in answering if isinstance(x.get(key), (int, float)) and x[key] > 0]
        return round(statistics.median(values), 2) if values else None

    try:
        processes = json.loads(processes_json or "[]")
    except ValueError:
        processes = []
    loaded = [p.get("frame_os_layer_loaded") for p in processes if isinstance(p, dict)]
    return {
        "modes": dict(Counter(str(r.get("mode")) for r in rows)),
        "layer_installed": any(r.get("layer_installed") for r in rows),
        "layer_errors": sorted({str(r["layer_error"]) for r in rows if r.get("layer_error")}),
        "answering_share": round(len(answering) / len(rows), 2),
        "frames": max((x.get("frames") or 0 for x in layer), default=0),
        "freshness_ms": med("freshness_ms"),
        "present_interval_p50_ms": med("present_interval_p50_ms"),
        "present_interval_p95_ms": med("present_interval_p95_ms"),
        "cost_p50_ms": med("cost_p50_ms"),
        "swapchain_recreations": max((x.get("swapchain_recreations") or 0 for x in layer), default=0),
        "levels": dict(Counter(str(r.get("level")) for r in rows if r.get("level"))),
        "loaded_in_game": (any(loaded) if loaded else None),
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
        out.append("Operating points the renderer did not confirm or that failed their trial: "
                   + ", ".join(report["rejected_points"]) + ".")
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
        elif fo["loaded_in_game"] is False:
            out.append("Frame OS was on, but the game process did not load the Frame OS layer.")
        elif fo["answering_share"] == 0:
            out.append("Frame OS was on, but the layer never reported frames (it did not load, or it "
                       "could not open the control file).")
        else:
            out.append(f"Frame OS ({', '.join(fo['modes'])}): the layer reported {fo['frames']} frames; "
                       f"freshness {fo['freshness_ms']} ms, present interval {fo['present_interval_p50_ms']} / "
                       f"{fo['present_interval_p95_ms']} ms (p50 / p95).")
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
