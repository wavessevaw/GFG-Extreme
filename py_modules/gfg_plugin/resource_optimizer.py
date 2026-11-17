"""Bounded CPU-weight trials for the KDE file indexer on cgroup v2."""
import json
import os
import pwd
import statistics
import subprocess
import sys
import time
from pathlib import Path

UNIT = "gfg-baloo-weight"
GROUP = "kde-baloo.service"
BINARIES = {"/usr/lib/baloo_file", "/usr/lib/baloo_file_extractor"}


def group_path(uid):
    return Path(f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service/background.slice") / GROUP


def eligible(group, uid, proc=Path("/proc")):
    # Never affect descendants or mixed services. Recheck inside the helper.
    if any(entry.is_dir() for entry in group.iterdir()):
        return False
    pids = (group / "cgroup.procs").read_text().split()
    if not 0 < len(pids) <= 8:
        return False
    return all((proc / pid).stat().st_uid == uid and
               os.readlink(proc / pid / "exe") in BINARIES for pid in pids)


def lease(action, uid=None, group=None, receipt=None):
    uid = os.getuid() if uid is None else uid
    if uid < 1000:
        raise ValueError("A desktop user is required")
    group = group or group_path(uid)
    receipt = receipt or Path(f"/run/user/{uid}/gfg-baloo-weight.json")
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
        if action == "restore":
            record = json.loads(receipt.read_text())
            if record["identity"] == identity and weight.read_text().strip() == "50":
                weight.write_text("100")
                if weight.read_text().strip() != "100":
                    raise OSError("Restore readback failed")
            receipt.unlink()
            return
        if receipt.exists():
            lease("restore", uid, group, receipt)
        if not eligible(Path(f"/proc/self/fd/{fd}"), uid) or weight.read_text().strip() != "100":
            raise ValueError("Service changed or already managed")
        with receipt.open("x") as f:
            json.dump(dict(identity=identity, original=100, trial=50), f)
            f.flush()
            os.fsync(f.fileno())
        weight.write_text("50")
        if weight.read_text().strip() != "50":
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


class Optimizer:
    def __init__(self, uid):
        self.uid = uid
        self.group = group_path(uid)
        self.app = 0
        self.previous = None
        self.hits = 0
        self.next_sample = self.cooldown = self.until = self.settle = 0
        self.status = dict(state="Inactive", tasks=0, result="Waiting for game")
        self.manager = ["--user", "--machine=" + pwd.getpwuid(uid).pw_name + "@.host"]

    def stop(self):
        if self.until:
            subprocess.run(["/usr/bin/systemctl", *self.manager, "stop", UNIT + ".service"],
                           timeout=4, check=False, capture_output=True)
        self.until = self.hits = self.app = 0
        self.previous = None
        self.status.update(state="Inactive", tasks=0)

    def tick(self, app, now, frames, target):
        if app != self.app:
            self.stop()
            self.app = app
            self.next_sample = 0
        if not app or now < self.next_sample:
            return
        self.next_sample = now + 5
        pressure = pressures()
        self.status.update(state="Auto", tasks=0, pressure=pressure)
        try:
            if not eligible(self.group, self.uid):
                raise ValueError("No eligible indexing service")
            cpu = int(dict(row.split() for row in (self.group / "cpu.stat").read_text().splitlines())["usage_usec"])
            ident = self.group.stat().st_ino
            old, self.previous = self.previous, (ident, now, cpu)
            busy = old and old[0] == ident and (cpu-old[2]) >= 250000*(now-old[1])
            samples = sorted(x for x in frames if isinstance(x,(float,int)) and 0 < x < 2000)
            budget = 1000 / target if target and target > 0 else (statistics.median(samples) if samples else 0)
            late = len(samples)>=10 and samples[int(.95*(len(samples)-1))] > 1.25 * budget
            if self.until and now < self.until:
                if (self.group / "cpu.weight").read_text().strip()=="50":
                    self.status.update(state="Optimizing",tasks=1,result="CPU weight 50 confirmed")
                if late and samples[int(.95*(len(samples)-1))] > self.before*1.25:
                    self.stop()
                    self.status["result"]="Trial ended after frame times worsened"
                return
            self.until = 0
            self.hits = self.hits+1 if busy and late and (pressure["cpu"] or 0)>=5 else 0
            if self.hits < 3 or now < self.cooldown:
                return
            self.cooldown = now+120
            self.hits = 0
            script = str(Path(__file__).resolve())
            cmd = ["/usr/bin/systemd-run", *self.manager, "--collect", "--unit="+UNIT,
                   "--property=Type=exec", "--property=RuntimeMaxSec=35",
                   "--property=ExecStopPost=/usr/bin/python3 -I "+script+" restore",
                   "/usr/bin/python3","-I",script,"apply"]
            subprocess.run(cmd,check=True,timeout=4,capture_output=True)
            self.before=samples[int(.95*(len(samples)-1))]
            self.until=now+35
            self.settle=now+10
            self.status["result"]="Started bounded CPU-weight trial"
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            self.hits=0
            self.previous=None
            self.status["result"]="Observation only"


if __name__ == "__main__" and sys.argv[1:] in (["apply"], ["restore"]):
    lease(sys.argv[1])
