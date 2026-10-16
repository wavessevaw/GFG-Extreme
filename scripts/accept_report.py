#!/usr/bin/env python3
"""Render a conservative report from one GFG Native diagnostic capture."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import tarfile


def load_logs(source: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    if source.is_dir():
        for path in source.rglob("*"):
            if path.is_file() and path.stat().st_size <= 32 * 1024 * 1024:
                files[path.name] = path.read_text(errors="replace")
        return files
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe path in diagnostic archive: {member.name}")
            if not member.isfile() or member.size > 32 * 1024 * 1024:
                continue
            stream = archive.extractfile(member)
            if stream is not None:
                files[path.name] = stream.read().decode(errors="replace")
    return files


def render(files: dict[str, str]) -> str:
    stderr = files.get("app.stderr.log", "")
    start = files.get("system-start.txt", "")
    status = files.get("process-status.txt", "unknown")
    active = "yes" if "GPU bridge active:" in stderr else "no / not observed"
    def last(pattern: str, text: str):
        matches = list(re.finditer(pattern, text))
        return matches[-1] if matches else None

    algo_match = last(r"GPU bridge active:.*?\balgo=([^\s]+)", stderr)
    retired = last(
        r"(?:GPU bridge|gpu-bridge) retired real=(\d+) synthetic=(\d+) skipped=(\d+).*?errors=(\d+).*?"
        r"present_path_host_pixel_reads=(\d+) present_path_cpu_waits=(\d+)", stderr)
    stats = last(
        r"gpu stats bridges=(\d+).*?real=(\d+) synthetic=(\d+) skipped=(\d+).*?errors=(\d+)",
        stderr + "\n" + files.get("app.stdout.log", ""))
    count = retired or stats
    present_done = re.findall(r"present_done id=(\d+) kind=([^ ]+) t_ns=(\d+)", stderr)
    intervals_us = []
    for previous, current in zip(present_done, present_done[1:]):
        a, b = int(previous[2]), int(current[2])
        if b > a:
            intervals_us.append((b - a) / 1000.0)
    timings = last(
        r"present_cpu frames=(\d+).*?total_median_us=([0-9.]+).*?total_p95_us=([0-9.]+).*?"
        r"layer_own_median_us=([0-9.]+).*?layer_own_p95_us=([0-9.]+)", stderr)

    lines = [
        "# GFG Native diagnostic report — NOT ACCEPTANCE",
        "",
        "This report summarizes application/WSI instrumentation only. It does not prove physical OLED scanout.",
        "",
        f"- Generator bridge initialized in captured log: **{active}**",
        f"- Algorithm: **{algo_match.group(1) if algo_match else 'not observed'}**",
        f"- Game process exit code: **{status.strip()}**",
        "- Physical display / KMS scanout: **unobserved**",
        "- 30 real → 90 distinct physical FPS acceptance: **false / not established**",
    ]
    if count:
        if retired:
            names = ("real presents", "synthetic presents", "skipped outputs", "errors",
                     "host pixel reads on present path", "CPU waits on present path")
            values = retired.groups()
        else:
            names = ("bridges", "real presents", "synthetic presents", "skipped outputs", "errors")
            values = stats.groups()
        synthetic = int(retired.group(2) if retired else stats.group(3))
        lines.append(f"- Synthetic WSI handoffs observed: **{'yes' if synthetic else 'no — zero generated outputs'}**")
        lines.extend(["", "## Latest captured cumulative counters", "",
                      "Latest process snapshot across swapchain recreations; earlier snapshots are not added again.", ""])
        lines.extend(f"- {name}: {value}" for name, value in zip(names, values))
        if synthetic == 0:
            lines.extend(["", "Bridge initialization succeeded, but generation was not observed. CPU passthrough timings do not measure generation cost."])
    bypass = list(dict.fromkeys(re.findall(r"fg_bypass reason=([^\s]+)", stderr)))
    if bypass:
        lines.extend(["", "## Captured bypass reasons", ""])
        lines.extend(f"- {reason}" for reason in bypass)
    if timings:
        lines.extend([
            "", "## CPU time inside layer", "",
            f"- Samples: {timings.group(1)}",
            f"- Full present call median / p95: {timings.group(2)} / {timings.group(3)} µs",
            f"- Layer-owned CPU median / p95: {timings.group(4)} / {timings.group(5)} µs",
            "- These are API-path CPU timings, not end-to-end display latency.",
        ])
    if len(present_done) > 1 and intervals_us:
        mean = sum(intervals_us) / len(intervals_us)
        fps = 1_000_000.0 / mean if mean else 0.0
        lines.extend([
            "", "## Optional Vulkan present-wait observations", "",
            f"- Completed IDs observed: {len(present_done)}",
            f"- Mean interval between present-wait completions: {mean:.1f} µs ({fps:.2f} completions/s)",
            "- Present-wait completion is not physical panel scanout.",
        ])
    else:
        lines.extend(["", "## Optional Vulkan present-wait observations", "",
                      "- No `present_done` records were captured; completed monitored presents are not established (a monitor may have started without receiving IDs)."])
    lines.extend(["", "## Device snapshot", "", "```text", start.rstrip(), "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path, help="diagnostic directory or .tar.gz archive")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = render(load_logs(args.capture))
    if args.output:
        args.output.write_text(report)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
