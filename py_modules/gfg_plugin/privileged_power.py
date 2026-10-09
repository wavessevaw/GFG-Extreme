"""Root-only PPT cap writer, everything else as the desktop user.

Steam Deck fastPPT/slowPPT hwmon caps are writable by root only, so the plugin
is loaded with Decky's ``root`` flag.  Running the whole plugin as root would
leave root-owned files (wrapper, configs, logs) in the user's home, which the
game and later non-root plugin versions cannot rewrite.  Instead, at import the
root process forks a tiny helper that keeps root and can do exactly one thing,
write an integer to a hwmon ``power*_cap`` file (or, for the smart power split, a cpufreq
``scaling_max_freq``), and then the plugin process
drops to the owner of ``DECKY_USER_HOME`` for good.  Without root nothing
changes: no helper, and the caps are written directly if permitted.
"""
from __future__ import annotations

import os
import re
import select
import signal
import threading
import time
from pathlib import Path
from typing import Optional

_CAP_RE = re.compile(r"^/sys/devices/[A-Za-z0-9_.:/-]+/hwmon/hwmon[0-9]+/power[0-9]+_cap$")
_MAX_UW = 100_000_000
_CPU_RE = re.compile(r"^/sys/devices/system/cpu/cpufreq/policy[0-9]+/scaling_max_freq$")
_CPU_KHZ = (100_000, 10_000_000)


def allowed_cap_path(path: str) -> Optional[str]:
    """Resolved hwmon PPT cap path, or None for anything else."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return None
    return real if _CAP_RE.match(real) else None


def allowed_cpu_path(path: str) -> Optional[str]:
    """Resolved cpufreq ``scaling_max_freq`` path, or None for anything else."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return None
    return real if _CPU_RE.match(real) else None


def _read_value(path: str) -> Optional[int]:
    try:
        with open(path, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _write_value(path: str, value: int) -> None:
    fd = os.open(path, os.O_WRONLY)
    try:
        os.write(fd, f"{value}\n".encode())
    finally:
        os.close(fd)


def restore_cpu_caps(written: dict, read=_read_value, write=_write_value) -> list:
    """The plugin is gone: put each CPU clock limit back that still reads what we wrote.

    ``written`` maps a path to (the value found before our first write, our last write)."""
    restored = []
    for path, (original, last) in written.items():
        if original is not None and last != original and read(path) == last:
            try:
                write(path, original)
                restored.append(path)
            except OSError:
                pass
    return restored


def _serve(requests: int, replies: int) -> None:  # pragma: no cover - runs in the forked root child
    cpu_written: dict = {}
    try:
        _serve_loop(requests, replies, cpu_written)
    finally:
        restore_cpu_caps(cpu_written)


def _serve_loop(requests: int, replies: int, cpu_written: dict) -> None:  # pragma: no cover - root child
    buffer = b""
    while True:
        try:
            chunk = os.read(requests, 4096)
        except OSError:
            break
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            reply = b"err bad-request\n"
            try:
                request = line.decode("utf-8")
                restoring_cpu = request.startswith("restore-cpu ")
                if restoring_cpu:
                    request = request[len("restore-cpu "):]
                raw_path, raw_value = request.rsplit(" ", 1)
                value = int(raw_value)
                path = allowed_cap_path(raw_path)
                cpu = None if path else allowed_cpu_path(raw_path)
                if (path is None and cpu is None) or (restoring_cpu and cpu is None):
                    reply = b"err path-not-allowed\n"
                elif path is not None and not 0 < value <= _MAX_UW:
                    reply = b"err value-out-of-range\n"
                elif cpu is not None and not _CPU_KHZ[0] <= value <= _CPU_KHZ[1]:
                    reply = b"err value-out-of-range\n"
                elif cpu is not None:
                    before = _read_value(cpu)
                    prior = cpu_written.get(cpu)
                    # An outside tool (or a new ownership session) changed this policy.
                    # Rebase undo; never restore a previous game's higher CPU limit.
                    original = prior[0] if prior and before == prior[1] else before
                    if restoring_cpu and prior and before != prior[1]:
                        reply = b"err external-cpu-change\n"
                    else:
                        _write_value(cpu, value)
                        if restoring_cpu:
                            # Undo is complete: helper exit must not undo the undo,
                            # especially after replaying an older plugin's crash journal.
                            cpu_written.pop(cpu, None)
                        else:
                            cpu_written[cpu] = (original, value)
                        reply = b"ok\n"
                else:
                    _write_value(path, value)
                    reply = b"ok\n"
            except OSError as error:
                reply = f"err {error.strerror or error}\n".replace("\n", " ").strip().encode() + b"\n"
            except (ValueError, UnicodeError):
                pass
            try:
                os.write(replies, reply)
            except OSError:
                return


class HelperTimeout(OSError):
    """The helper did not answer in time: the write may still land later."""


class PrivilegedCapWriter:
    """Client side of the root helper (one request at a time)."""

    # review 1.1.x: a helper stuck in a sysfs write used to block the Governor loop forever (os.read
    # without a timeout) and plugin unload with it (blocking waitpid).
    REPLY_TIMEOUT_S = 3.0
    CLOSE_TIMEOUT_S = 2.0

    def __init__(self, requests: int, replies: int, pid: int) -> None:
        self._requests = requests
        self._replies = replies
        self.pid = pid
        self._lock = threading.Lock()

    def _drain_stale(self) -> None:
        """Drop a late reply to a request that already timed out, so it is not taken for this one."""
        while select.select([self._replies], [], [], 0)[0]:
            if not os.read(self._replies, 256):
                raise OSError("TDP helper exited")

    def restore_cpu(self, path: Path, value: int) -> None:
        self.write(path, value, restore_cpu=True)

    def write(self, path: Path, value: int, *, restore_cpu: bool = False) -> None:
        with self._lock:
            self._drain_stale()
            prefix = "restore-cpu " if restore_cpu else ""
            os.write(self._requests, f"{prefix}{path} {int(value)}\n".encode())
            data = b""
            deadline = time.monotonic() + self.REPLY_TIMEOUT_S
            while not data.endswith(b"\n"):
                left = deadline - time.monotonic()
                if left <= 0 or not select.select([self._replies], [], [], left)[0]:
                    raise HelperTimeout(f"TDP helper did not answer within {self.REPLY_TIMEOUT_S:g} s")
                chunk = os.read(self._replies, 256)
                if not chunk:
                    raise OSError("TDP helper exited")
                data += chunk
        text = data.decode("utf-8", "replace").strip()
        if text != "ok":
            raise OSError(f"TDP helper: {text}")

    def close(self) -> None:
        for fd in (self._requests, self._replies):
            try:
                os.close(fd)
            except OSError:
                pass
        # EOF on its pipe ends the helper; one stuck in a write gets a bounded wait, then SIGKILL
        # (refused once this process has dropped root: it is then left to exit on its own).
        deadline = time.monotonic() + self.CLOSE_TIMEOUT_S
        while True:
            try:
                done, _ = os.waitpid(self.pid, os.WNOHANG)
            except OSError:
                return  # already reaped / not our child
            if done:
                return
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
        try:
            os.kill(self.pid, signal.SIGKILL)
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if os.waitpid(self.pid, os.WNOHANG)[0]:
                    return
                time.sleep(0.02)
        except OSError:
            pass


_writer: Optional[PrivilegedCapWriter] = None


def writer() -> Optional[PrivilegedCapWriter]:
    return _writer


def _target_ids(home: Path) -> Optional[tuple[int, int]]:
    try:
        st = home.stat()
    except OSError:
        return None
    if st.st_uid == 0:
        return None
    return st.st_uid, st.st_gid


def start_and_drop_privileges(user_home: Optional[str]) -> bool:
    """Fork the root helper and drop this process to the home owner. Idempotent."""
    global _writer
    if _writer is not None or os.geteuid() != 0 or not user_home:
        return False
    if not os.environ.get("DECKY_PLUGIN_DIR"):
        return False  # only inside a real Decky plugin process, never in tests/tools
    ids = _target_ids(Path(user_home))
    if ids is None:
        return False
    uid, gid = ids
    helper = spawn_helper()
    try:  # Frame OS input sensor: gamepad events only, from a second root child (input_relay.py)
        from .frame_os import input_relay
        from .constants import CONFIG_DIR, RUNTIME_STATE_DIRNAME
        marker = Path(user_home) / CONFIG_DIR / RUNTIME_STATE_DIRNAME / "frame-os.enabled"
        input_relay.set_relay_fd(input_relay.spawn_relay(marker))
    except Exception:
        pass
    import pwd

    try:
        name = pwd.getpwuid(uid).pw_name
        os.initgroups(name, gid)
    except (KeyError, OSError):
        name = None
        os.setgroups([gid])
    os.setgid(gid)
    os.setuid(uid)
    os.environ["HOME"] = str(user_home)
    if name:
        os.environ["USER"] = os.environ["LOGNAME"] = name
    _writer = helper
    return True


def spawn_helper() -> PrivilegedCapWriter:
    """Fork the cap-writer helper; it keeps this process's privileges and exits on EOF."""
    req_r, req_w = os.pipe()
    rep_r, rep_w = os.pipe()
    pid = os.fork()
    if pid == 0:  # pragma: no cover - runs in the forked helper
        try:
            os.close(req_w)
            os.close(rep_r)
            # Hold nothing of the plugin (Decky sockets, logs) but our two pipes.
            keep = sorted((req_r, rep_w))
            os.closerange(3, keep[0])
            os.closerange(keep[0] + 1, keep[1])
            os.closerange(keep[1] + 1, 65536)
            _serve(req_r, rep_w)
        finally:
            os._exit(0)
    os.close(req_r)
    os.close(rep_w)
    return PrivilegedCapWriter(req_w, rep_r, pid)
