"""Bounded ordering of an imminent, timer-owned restic or Borg user backup."""
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

TOOLS = {"restic-backup": ("/usr/bin/restic", "backup"),
         "borg-backup": ("/usr/bin/borg", "create")}


def query(command):
    return subprocess.run(command, capture_output=True, text=True, check=True,
                          timeout=2).stdout


def scheduled_backup(manager, tools=TOOLS, clock=time.time):
    timers = [stem + ".timer" for stem in tools if os.path.isfile(tools[stem][0])]
    if not timers:
        return None
    ctl = ["/usr/bin/systemctl", *manager]
    rows = json.loads(query([*ctl, "list-timers", "--output=json", *timers]))
    for row in rows:
        timer = row["unit"]
        if timer not in timers or not isinstance(row.get("next"), int):
            continue
        if not 0 < row["next"] / 1e6 - clock() <= 90:
            continue
        stem = timer[:-6]
        unit = stem + ".service"
        if row["activates"] not in (unit, [unit]):
            continue
        fields = dict(line.split("=", 1) for line in query([
            *ctl, "show", unit, "-p", "Id,ActiveState,Type,TriggeredBy,RequiredBy,WantedBy,BoundBy,RequisiteOf"
        ]).splitlines())
        if (fields.get("Id"), fields.get("ActiveState"), fields.get("Type"), fields.get("TriggeredBy")) != (
                unit, "inactive", "oneshot", timer):
            continue
        if any(fields.get(p, "unknown") for p in ("RequiredBy", "WantedBy", "BoundBy", "RequisiteOf")):
            continue
        obj = "/org/freedesktop/systemd1/unit/" + unit.replace("-", "_2d").replace(".", "_2e")
        def commands(prop):
            reply = json.loads(query(["/usr/bin/busctl", *manager, "--json=short", "get-property",
                                      "org.freedesktop.systemd1", obj,
                                      "org.freedesktop.systemd1.Service", prop]))
            return reply["data"]
        start = commands("ExecStart")
        exe, verb = tools[stem]
        if len(start) != 1 or start[0][0] != exe or start[0][1][:2] != [exe, verb]:
            continue
        if any(commands(prop) for prop in ("ExecStartPre", "ExecStartPost", "ExecCondition")):
            continue
        return unit
    return None


def order_before(manager, unit):
    # A pending oneshot start job delays only later starts ordered after it.
    # EOF releases the job on exit, disable, hot reload or backend death.
    return subprocess.Popen(["/usr/bin/systemd-run", *manager, "--quiet", "--collect",
                             "--unit=gfg-scheduled-backup-window", "--pipe",
                             "--property=Type=oneshot", "--property=TimeoutStartSec=15min",
                             "--property=Before=" + unit, "/usr/bin/cat"],
                            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class BackupWindow:
    def __init__(self, manager):
        self.manager = manager
        self.pool = self.future = self.process = None
        self.next_check = 0
        self.unit = None

    def stop(self):
        if self.process:
            self.process.stdin.close()
            self.process.poll()
            self.process = None
        if self.pool:
            self.pool.shutdown(wait=False, cancel_futures=True)
        self.pool = self.future = self.unit = None
        self.next_check = 0

    def tick(self, now):
        if self.process:
            if self.process.poll() is None:
                return "Scheduling window requested for " + self.unit
            self.process.stdin.close()
            self.process = self.unit = None
        if self.future:
            if self.future.done():
                try:
                    unit = self.future.result()
                    if unit in {s + ".service" for s in TOOLS}:
                        self.process = order_before(self.manager, unit)
                        self.unit = unit
                        self.next_check = now + 960
                except (OSError, subprocess.SubprocessError, TypeError, ValueError, KeyError, IndexError):
                    pass
                self.future = None
            return None
        if now >= self.next_check:
            self.next_check = now + 60
            if any(os.path.isfile(exe) for exe, _ in TOOLS.values()):
                if self.pool is None:
                    self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gfg-timer")
                self.future = self.pool.submit(scheduled_backup, self.manager)
        return None
