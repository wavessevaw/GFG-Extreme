"""Read-only cgroup telemetry. Report disjoint subtrees, including system services."""
import os
import re
from collections import deque
from itertools import islice


def sample_groups(roots, previous, now):
    current, rows = {}, []
    for root in roots:
        remaining = 64
        pending = deque([root])
        while remaining and pending:
            parent = pending.popleft()
            try:
                with os.scandir(parent) as entries:
                    for entry in entries:
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        remaining -= 1
                        path = parent / entry.name
                        if entry.name.endswith(".slice"):
                            pending.append(path)
                        elif entry.name.endswith((".service", ".scope")):
                            try:
                                key = (str(path), entry.inode())
                                counters = dict(row.split() for row in (path / "cpu.stat").read_text().splitlines())
                                cpu = int(counters["usage_usec"])
                                devices = {}
                                try:
                                    for line in islice((path / "io.stat").read_text().splitlines(), 32):
                                        dev, *fields = line.split()
                                        io = dict(x.split("=", 1) for x in fields)
                                        devices[dev] = (int(io["rbytes"]), int(io["wbytes"]))
                                except (OSError, ValueError, KeyError):
                                    pass
                                current[key] = (now, cpu, devices)
                                if key in previous:
                                    then, before, old = previous[key]
                                    dt = now - then
                                    if 0 < dt <= 35 and cpu >= before:
                                        rates = {dev: [(new[i]-old[dev][i])/dt for i in (0, 1)]
                                                 for dev, new in devices.items() if dev in old and
                                                 all(new[i] >= old[dev][i] for i in (0, 1))}
                                        rows.append((path, (cpu-before)/(dt*10000), rates))
                            except (ValueError, KeyError, OSError):
                                pass
                        if not remaining:
                            break
            except OSError:
                continue
    return current, rows


def display_role(path, app, verified):
    if path in verified:
        return "Verified background service"
    if "system.slice" in path.parts:
        return "System unit"
    if path.name in {"pipewire.service", "pipewire-pulse.service", "wireplumber.service",
                     "gamescope-session.service", "plasma-kwin_wayland.service"}:
        return "Session infrastructure"
    steam = re.fullmatch(r"app-steam-(\d+)(?:-\d+)?\.scope", path.name)
    if steam and app and steam[1] == str(app):
        return "Active Steam app scope"
    return "Unclassified"


def busiest(rows, app=0, verified=()):
    # Include both CPU-heavy and disk-heavy units. Never add stacked devices together.
    ranked = []
    for path, cpu, devices in rows:
        dev = max(devices, key=lambda d: sum(devices[d]), default=None)
        rd, wr = devices[dev] if dev else (0, 0)
        score = max(cpu, (rd+wr)/1048576)
        if score >= 1:
            ranked.append((score, str(path), dict(unit=path.name, group=str(path), role=display_role(path, app, verified), cpu=round(cpu, 1), device=dev,
                                             read_mib=round(rd/1048576, 2), write_mib=round(wr/1048576, 2))))
    return [item[2] for item in sorted(ranked, key=lambda x: (-x[0], x[1]))[:4]]
