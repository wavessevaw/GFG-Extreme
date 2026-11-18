"""Bounded CPU-weight trials for isolated desktop background services on cgroup v2."""
from itertools import islice
import json
import os
import pwd
import statistics
import subprocess
import sys
import time
from pathlib import Path

UNIT = "gfg-baloo-weight"
# Fixed paths beneath the desktop user's manager. Never accept a path from the UI.
SERVICES = {
    "baloo": ("background.slice/kde-baloo.service", {"/usr/lib/baloo_file", "/usr/lib/baloo_file_extractor"}),
    "syncthing": ("app.slice/syncthing.service", {"/usr/bin/syncthing"}),
    "syncthing-background": ("background.slice/syncthing.service", {"/usr/bin/syncthing"}),
}


def group_path(uid, role="baloo"):
    return Path(f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service") / SERVICES[role][0]


def eligible(group, uid, proc=Path("/proc"), role="baloo"):
    # Never affect descendants or mixed services. Recheck inside the helper.
    if any(entry.is_dir() for entry in group.iterdir()):
        return False
    pids = (group / "cgroup.procs").read_text().split()
    if not 0 < len(pids) <= 8:
        return False
    return all((proc / pid).stat().st_uid == uid and
               os.readlink(proc / pid / "exe") in SERVICES[role][1] for pid in pids)


def lease(action, uid=None, group=None, receipt=None, role="baloo"):
    uid = os.getuid() if uid is None else uid
    if uid < 1000:
        raise ValueError("A desktop user is required")
    group = group or group_path(uid, role)
    receipt = receipt or Path(f"/run/user/{uid}/gfg-{role}-weight.json")
    if action == "restore" and not receipt.exists():
        return
    try:
        fd = os.open(group, os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        if action == "restore":
            receipt.unlink(missing_ok=True)
            return
        raise
    try:
        identity = [Path("/proc/sys/kernel/random/boot_id").read_text().strip(), os.fstat(fd).st_ino]
        weight = Path(f"/proc/self/fd/{fd}/cpu.weight")
        quota = Path(f"/proc/self/fd/{fd}/cpu.max")
        if action == "restore":
            record = json.loads(receipt.read_text())
            if record.get("action") == "limit":
                if record["identity"] == identity and quota.read_text().strip() == "25000 100000":
                    quota.write_text("max 100000")
                    if quota.read_text().strip() != "max 100000":
                        raise OSError("Quota restore readback failed")
                receipt.unlink()
                return
            if record["identity"] == identity and weight.read_text().strip() == "50":
                weight.write_text("100")
                if weight.read_text().strip() != "100":
                    raise OSError("Restore readback failed")
            receipt.unlink()
            return
        if receipt.exists():
            lease("restore", uid, group, receipt, role)
        if not eligible(Path(f"/proc/self/fd/{fd}"), uid, role=role) or weight.read_text().strip() != "100":
            raise ValueError("Service changed or already managed")
        if action == "limit":
            if role != "baloo" or quota.read_text().strip() != "max 100000":
                raise ValueError("CPU quota already managed or service unsuitable")
            control, original, trial = quota, "max 100000", "25000 100000"
        else:
            control, original, trial = weight, "100", "50"
        with receipt.open("x") as f:
            json.dump(dict(identity=identity, action=action, original=original, trial=trial), f)
            f.flush()
            os.fsync(f.fileno())
        control.write_text(trial)
        if control.read_text().strip() != trial:
            raise OSError("Weight readback failed")
        time.sleep(30)
    finally:
        os.close(fd)


def pressures(root=Path("/proc/pressure")):
    result = {}
    for name in ("cpu", "memory", "io"):
        try:
            fields = (root / name).read_text().splitlines()[0].split()
            result[name] = float(dict(v.split("=") for v in fields[1:])["avg10"])
        except (OSError, ValueError, KeyError, IndexError):
            result[name] = None
    return result


def service_usage(root, previous, now):
    """Read-only attribution for direct user services. Never use these paths for writes."""
    current, loads = {}, []
    for name in ("app.slice", "background.slice"):
        try:
            with os.scandir(root / name) as entries:
                for entry in islice(entries, 64):
                    if not entry.name.endswith(".service") or not entry.is_dir(follow_symlinks=False):
                        continue
                    try:
                        group = Path(entry.path)
                        stats = dict(line.split() for line in (group / "cpu.stat").read_text().splitlines())
                        key = (entry.path, entry.inode())
                        used = int(stats["usage_usec"])
                    except (ValueError, OSError, KeyError):
                        continue
                    current[key] = (now, used)
                    if key in previous:
                        then, before = previous[key]
                        if 0 < now - then <= 10 and used > before:
                            pct = (used - before) / ((now - then) * 10000)
                            loads.append((pct, entry.name))
        except OSError:
            continue
    top = sorted(loads, reverse=True)[:3]
    return current, ", ".join(f"{name}: {pct:.1f}%" for pct, name in top if pct >= 1)


class Optimizer:
    def __init__(self, uid):
        self.uid = uid
        self.service_root = group_path(uid).parent.parent
        self.observed = {}
        self.control = "cpu.weight"
        self.groups = {role: group_path(uid, role) for role in SERVICES}
        self.active = None
        self.app = 0
        self.previous = {}
        self.hits = {}
        self.next_sample = self.cooldown = self.until = self.settle = 0
        self.status = dict(state="Inactive", tasks=0, result="Waiting for game")
        self.manager = ["--user", "--machine=" + pwd.getpwuid(uid).pw_name + "@.host"]

    def stop(self):
        if self.until:
            subprocess.run(["/usr/bin/systemctl", *self.manager, "stop", UNIT + ".service"],
                           timeout=4, check=False, capture_output=True)
        self.until = self.app = 0
        self.active = None
        self.hits.clear()
        self.previous = {}
        self.observed.clear()
        self.status = dict(state="Inactive", tasks=0, result="Waiting for game")

    def tick(self, app, now, frames, target, *, sample=True, inactive_reason="Waiting for game"):
        if app != self.app:
            self.stop()
            self.app = app
            self.next_sample = 0
            if app:
                self.status.update(state="Auto", result="Game active. Monitoring background services")
        if not app:
            self.status.update(state="Inactive", tasks=0, result=inactive_reason)
            return
        if not sample:
            self.observed.clear()
            self.previous.clear()
            self.hits.clear()
            if not self.active or now >= self.until:
                self.status.update(state="Auto", tasks=0, result="Game active. Waiting for gameplay telemetry")
            return
        if now < self.next_sample:
            return
        self.next_sample = now + 5
        pressure = pressures()
        self.status.update(state="Auto", tasks=0, pressure=pressure, result="Game active. Monitoring background services")
        self.observed, top = service_usage(self.service_root, self.observed, now)
        self.status["services"] = f"User services (% of one CPU): {top}" if top else "No measured user service above 1% of one CPU"
        samples = sorted(x for x in frames if isinstance(x, (float, int)) and 0 < x < 2000)
        budget = 1000 / target if target and target > 0 else (statistics.median(samples) if samples else 0)
        p95 = samples[int(.95 * (len(samples) - 1))] if len(samples) >= 10 else 0
        late = p95 > 1.25 * budget
        if self.active and now < self.until:
            role = self.active
            group = self.groups[role]
            try:
                expected = "25000 100000" if self.control == "cpu.max" else "50"
                confirmed = eligible(group, self.uid, role=role) and (group / self.control).read_text().strip() == expected
            except OSError:
                confirmed = False
            if confirmed and not (late and (not self.before or p95 > self.before * 1.25)):
                self.status.update(state="Optimizing", tasks=1, result=f"{group.name}: {self.control} = {expected} confirmed")
            else:
                self.stop()
                self.status["result"] = "Trial ended after service or frame times changed"
            return

        self.active = None
        self.until = 0
        candidates = []
        for role, group in self.groups.items():
            try:
                if not eligible(group, self.uid, role=role):
                    raise ValueError("Ineligible service")
                ident = group.stat().st_ino
                stats = dict(row.split() for row in (group / "cpu.stat").read_text().splitlines())
                cpu = int(stats["usage_usec"])
                if group.stat().st_ino != ident or (group / "cpu.weight").read_text().strip() != "100":
                    raise ValueError("Service changed or already managed")
            except (OSError, ValueError, KeyError):
                self.previous.pop(role, None)
                self.hits.pop(role, None)
                self.hits.pop(role + ":quota", None)
                continue
            old = self.previous.get(role)
            self.previous[role] = (ident, now, cpu)
            load = 0
            if old and ident == old[0] and 0 < now - old[1] <= 10:
                load = (cpu - old[2]) / (1000000 * (now - old[1]))
            competing = late and load >= .25 and (pressure["cpu"] or 0) >= 5
            # The standalone file indexer can defer heavy indexing before frame times suffer.
            heavy_indexing = role == "baloo" and load >= .5 and (pressure["cpu"] or 0) >= 5
            quota_available = False
            if heavy_indexing:
                try:
                    quota_available = (group / "cpu.max").read_text().strip() == "max 100000"
                except OSError:
                    pass
            self.hits[role] = self.hits.get(role, 0) + 1 if competing or quota_available else 0
            quota_key = role + ":quota"
            self.hits[quota_key] = self.hits.get(quota_key, 0) + 1 if quota_available else 0
            if self.hits[role] >= 3:
                if competing or self.hits[quota_key] >= 3:
                    candidates.append((load, role))
        if not candidates or now < self.cooldown:
            return
        _, role = max(candidates)
        action = "limit" if self.hits.get(role + ":quota", 0) >= 3 else "apply"
        self.control = "cpu.max" if action == "limit" else "cpu.weight"
        self.cooldown = now + 120
        self.hits.clear()
        script = str(Path(__file__).resolve())
        cmd = ["/usr/bin/systemd-run", *self.manager, "--collect", "--unit="+UNIT,
               "--property=Type=exec", "--property=RuntimeMaxSec=35",
               "--property=ExecStopPost=/usr/bin/python3 -I "+script+" restore "+role,
               "/usr/bin/python3", "-I", script, action, role]
        try:
            subprocess.run(cmd, check=True, timeout=4, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            self.status["result"] = "Desktop manager could not start the trial"
            return
        self.before = p95
        self.active = role
        self.until = now + 35
        self.settle = now + 10
        self.status["result"] = f"Started CPU trial for {self.groups[role].name}"


if __name__ == "__main__":
    args = sys.argv[1:]
    # Retain the old helper invocation for an outstanding Baloo cleanup.
    if len(args) == 1:
        args.append("baloo")
    if len(args) != 2 or args[0] not in ("apply", "limit", "restore") or args[1] not in SERVICES:
        sys.exit(2)
    lease(args[0], role=args[1])
