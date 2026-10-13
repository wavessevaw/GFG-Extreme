"""Scoped Extreme resources: game priority/OOM preference and OEM fan ownership.

Only GFG-marked game processes of the Deck user are eligible. No global VM,
swap, realtime scheduler or arbitrary system-file writes are exposed.
The root helper owns these leases and restores them on EOF or heartbeat expiry.
"""
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

LEASE_S = 20.0
MAX_PROCESSES = 16
MAX_THREADS = 256


def start_ticks(path: Path) -> Optional[int]:
    try:
        with (path / "stat").open(encoding="utf-8") as stream:
            text = stream.read(8193)
        if len(text) > 8192:
            return None
        value = int(text.rpartition(")")[2].split()[19])
        return value if value > 0 else None
    except (OSError, ValueError, IndexError):
        return None


def managed_process(proc: Path, pid: int, ticks: int, uid: Optional[int]) -> bool:
    if uid is None or pid <= 1 or ticks <= 0:
        return False
    path = proc / str(pid)
    try:
        if path.stat().st_uid != uid or start_ticks(path) != ticks:
            return False
        with (path / "environ").open("rb") as stream:
            environment = stream.read(65537)
        return len(environment) <= 65536 and b"GFG_MANAGED_GAME=1" in environment.split(b"\0")
    except OSError:
        return False


class ProcessResources:
    """Helper-side undo for modest game priority and OOM preference.

    Nice is per thread on Linux. Newly created threads are discovered on renewal.
    Outside changes are preserved; a reused PID/TID is never restored.
    """
    def __init__(self, uid: Optional[int], *, proc: Path = Path("/proc"),
                 get_nice: Callable = None, set_nice: Callable = None,
                 clock: Callable = time.monotonic, marker: Optional[Path] = None) -> None:
        self.uid, self.proc, self.clock = uid, Path(proc), clock
        self.get_nice = get_nice or (lambda tid: os.getpriority(os.PRIO_PROCESS, tid))
        self.set_nice = set_nice or (lambda tid, value: os.setpriority(os.PRIO_PROCESS, tid, value))
        self.nice: Dict[tuple, Tuple[int, int]] = {}
        self.oom: Dict[tuple, Tuple[int, int]] = {}
        self.deadlines: Dict[tuple, float] = {}
        self.blocked: set = set()
        self.marker = marker
        self._saved = None
        self.baselines: Dict[tuple, int] = {}
        self.recover()

    def _save(self) -> None:
        if self.marker is None:
            return
        record = {"schema": 1, "uid": self.uid,
                  "nice": [[*key, *value] for key, value in self.nice.items()],
                  "oom": [[*key, *value] for key, value in self.oom.items()]}
        text = json.dumps(record, sort_keys=True)
        if text == self._saved:
            return
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.marker.with_name(self.marker.name + f".tmp.{os.getpid()}")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.marker)
            self._saved = text
        finally:
            temporary.unlink(missing_ok=True)

    def recover(self) -> None:
        if self.marker is None:
            return
        try:
            info = self.marker.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_size > 1048576:
                raise OSError("process-undo-not-trusted")
            record = json.loads(self.marker.read_text())
            if record.get("schema") != 1 or record.get("uid") != self.uid:
                raise OSError("process-undo-invalid")
            nice, oom = record.get("nice"), record.get("oom")
            if not isinstance(nice, list) or not isinstance(oom, list) or len(nice) > MAX_PROCESSES * MAX_THREADS or len(oom) > MAX_PROCESSES:
                raise OSError("process-undo-invalid")
            for row in nice:
                if (not isinstance(row, list) or len(row) != 6
                        or not all(type(v) is int for v in row) or min(row[:4]) <= 0
                        or not -20 <= row[4] <= 19 or not -20 <= row[5] <= 19):
                    raise OSError("process-undo-invalid")
            for row in oom:
                if (not isinstance(row, list) or len(row) != 4
                        or not all(type(v) is int for v in row) or min(row[:2]) <= 0
                        or not -1000 <= row[2] <= 1000 or not -1000 <= row[3] <= 1000):
                    raise OSError("process-undo-invalid")
            self.nice = {tuple(r[:4]): tuple(r[4:]) for r in nice}
            self.oom = {tuple(r[:2]): tuple(r[2:]) for r in oom}
            self.deadlines = {key[:2]: 0.0 for key in self.nice}
            self.deadlines.update({key: 0.0 for key in self.oom})
            self.expire(force=True)
        except FileNotFoundError:
            return
        except (ValueError, TypeError, KeyError) as error:
            raise OSError("process-undo-invalid") from error

    def _valid(self, owner: tuple) -> bool:
        return managed_process(self.proc, owner[0], owner[1], self.uid)

    def _oom_read(self, pid: int) -> int:
        return int((self.proc / str(pid) / "oom_score_adj").read_text().strip())

    def _oom_write(self, pid: int, value: int) -> None:
        (self.proc / str(pid) / "oom_score_adj").write_text(str(value) + "\n")

    def _restore_nice(self, key: tuple) -> bool:
        original, last = self.nice[key]
        owner, tid, ticks = key[:2], key[2], key[3]
        if not self._valid(owner) or start_ticks(self.proc / str(owner[0]) / "task" / str(tid)) != ticks:
            self.nice.pop(key, None)
            return True
        try:
            current = self.get_nice(tid)
            if current == last:
                self.set_nice(tid, original)
                if self.get_nice(tid) != original:
                    return False
            self.nice.pop(key, None)
            return True
        except OSError:
            return False

    def _restore_oom(self, owner: tuple) -> bool:
        original, last = self.oom[owner]
        if not self._valid(owner):
            self.oom.pop(owner, None)
            return True
        try:
            if self._oom_read(owner[0]) == last:
                self._oom_write(owner[0], original)
                if self._oom_read(owner[0]) != original:
                    return False
            self.oom.pop(owner, None)
            return True
        except (OSError, ValueError):
            return False

    def restore(self, owner: tuple, *, priority: bool = True, memory: bool = True) -> bool:
        ok = True
        if priority:
            for key in list(self.nice):
                if key[:2] == owner:
                    ok = self._restore_nice(key) and ok
        if memory and owner in self.oom:
            ok = self._restore_oom(owner) and ok
        if not any(k[:2] == owner for k in self.nice) and owner not in self.oom:
            self.deadlines.pop(owner, None)
        self._save()
        return ok

    def apply(self, pid: int, ticks: int, priority: bool, memory: bool) -> None:
        owner = (pid, ticks)
        if not self._valid(owner):
            raise OSError("game-identity-not-confirmed")
        if owner not in self.deadlines and len(self.deadlines) >= MAX_PROCESSES:
            raise OSError("game-resource-limit")
        self.deadlines[owner] = self.clock() + LEASE_S
        if not self.restore(owner, priority=not priority, memory=not memory):
            raise OSError("process-restore-pending")
        self.deadlines[owner] = self.clock() + LEASE_S
        if priority:
            tasks = sorted((self.proc / str(pid) / "task").iterdir(), key=lambda p: p.name)[:MAX_THREADS]
            plan = []
            initial = owner not in self.baselines
            first_values = []
            for task in tasks:
                if not task.name.isdecimal():
                    continue
                tid, tid_ticks = int(task.name), start_ticks(task)
                if tid_ticks is None or not self._valid(owner):
                    continue
                key = (*owner, tid, tid_ticks)
                current = self.get_nice(tid)
                first_values.append(current)
                previous = self.nice.get(key)
                if key in self.blocked or (previous and current != previous[1]):
                    self.blocked.add(key)
                    self.nice.pop(key, None)
                    continue
                original = previous[0] if previous else current
                if not initial and not previous and current == min(self.baselines[owner], -5):
                    original = self.baselines[owner]
                target = min(original, -5)
                if current != target or original != target:
                    self.nice[key] = (original, target)
                    plan.append((key, current, target))
            if initial and first_values:
                self.baselines[owner] = min(first_values)
            self._save()
            for key, before, target in plan:
                if (not self._valid(owner) or start_ticks(self.proc / str(pid) / "task" / str(key[2])) != key[3]):
                    continue
                current = self.get_nice(key[2])
                if current != before:
                    self.blocked.add(key)
                    self.nice.pop(key, None)
                    continue
                if current != target:
                    self.set_nice(key[2], target)
                if self.get_nice(key[2]) != target:
                    raise OSError("game-priority-not-confirmed")
        if memory:
            current = self._oom_read(pid)
            previous = self.oom.get(owner)
            key = (*owner, "oom")
            if key in self.blocked or (previous and current != previous[1]):
                self.blocked.add(key)
                self.oom.pop(owner, None)
                self._save()
                raise OSError("game-memory-priority-changed-externally")
            original = previous[0] if previous else current
            target = min(original, -100)  # preference, never make a game immune to OOM
            if current != target:
                self.oom[owner] = (original, target)
                self._save()
                self._oom_write(pid, target)
                if self._oom_read(pid) != target:
                    raise OSError("game-memory-priority-not-confirmed")
        self._save()

    def expire(self, force: bool = False) -> None:
        now = self.clock()
        for owner, deadline in list(self.deadlines.items()):
            if force or now >= deadline:
                self.restore(owner)
        # Ended identities and their external-change guards are bounded by the live leases.
        self.blocked = {k for k in self.blocked if k[:2] in self.deadlines}
        self.baselines = {k: v for k, v in self.baselines.items() if k in self.deadlines}


class FanResources:
    """OEM BIOS/OS controller selection, never a raw RPM or fan-stop command.

    The root-owned undo file survives helper/plugin crashes. Restore only our
    BIOS selection; an outside return to OS control is kept.
    """
    def __init__(self, manager: Any, marker: Optional[Path], clock: Callable = time.monotonic) -> None:
        self.manager, self.marker, self.clock = manager, marker, clock
        self.original: Optional[int] = None
        self.deadline = 0.0
        self.pending = False
        self.blocked = False
        self.recover()

    def _save(self, original: int) -> None:
        if self.marker is None:
            raise OSError("fan-undo-storage-unavailable")
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.marker.with_name(self.marker.name + f".tmp.{os.getpid()}")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump({"schema": 1, "original": original, "written": 0}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.marker)
        finally:
            temporary.unlink(missing_ok=True)

    def recover(self) -> None:
        if self.marker is None:
            return
        try:
            info = self.marker.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_size > 4096:
                self.pending = True
                return
            record = json.loads(self.marker.read_text())
            if record.get("schema") != 1 or record.get("original") not in (0, 1) or record.get("written") != 0:
                self.pending = True
                return
            self.original = int(record["original"])
            self.pending = True
            self.restore()
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError):
            self.pending = True

    def apply(self) -> None:
        if self.blocked:
            raise OSError("fan-controller-changed-externally")
        if self.pending and not self.restore():
            raise OSError("fan-restore-pending")
        current = self.manager.query()
        if current not in (0, 1):
            raise OSError("oem-fan-interface-unavailable")
        if self.original is not None and current != 0:
            # The player changed controller: release and do not immediately fight it.
            self.original = None
            self.blocked = True
            if self.marker:
                self.marker.unlink(missing_ok=True)
            raise OSError("fan-controller-changed-externally")
        if self.original is None and current != 0:
            self._save(current)
            self.original = current
        self.deadline = self.clock() + LEASE_S
        if current != 0:
            self.pending = True  # a timeout may still land
            ok, _ = self.manager.set(0)
            if not ok or self.manager.query() != 0:
                raise OSError("fan-controller-not-confirmed")
            self.pending = False

    def restore(self) -> bool:
        if self.original is None:
            return not self.pending
        current = self.manager.query()
        if current not in (0, 1):
            self.pending = True
            return False
        if current == 0 and current != self.original:
            ok, _ = self.manager.set(self.original)
            if not ok or self.manager.query() != self.original:
                self.pending = True
                return False
        if self.marker:
            try:
                self.marker.unlink(missing_ok=True)
            except OSError:
                self.pending = True
                return False
        self.original, self.pending = None, False
        return True

    def expire(self, force: bool = False) -> None:
        if self.pending or (self.original is not None and (force or self.clock() >= self.deadline)):
            self.restore()
