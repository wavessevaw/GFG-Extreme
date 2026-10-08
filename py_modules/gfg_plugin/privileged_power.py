"""Root-only PPT cap writer, everything else as the desktop user.

Steam Deck fastPPT/slowPPT hwmon caps are writable by root only, so the plugin
is loaded with Decky's ``root`` flag.  Running the whole plugin as root would
leave root-owned files (wrapper, configs, logs) in the user's home, which the
game and later non-root plugin versions cannot rewrite.  Instead, at import the
root process forks a tiny helper that keeps root and can do exactly one thing,
write an integer to a hwmon ``power*_cap`` file, and then the plugin process
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


def allowed_cap_path(path: str) -> Optional[str]:
    """Resolved hwmon PPT cap path, or None for anything else."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return None
    return real if _CAP_RE.match(real) else None


def _serve(requests: int, replies: int) -> None:  # pragma: no cover - runs in the forked root child
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
                raw_path, raw_value = line.decode("utf-8").rsplit(" ", 1)
                value = int(raw_value)
                path = allowed_cap_path(raw_path)
                if path is None:
                    reply = b"err path-not-allowed\n"
                elif not 0 < value <= _MAX_UW:
                    reply = b"err value-out-of-range\n"
                else:
                    fd = os.open(path, os.O_WRONLY)
                    try:
                        os.write(fd, f"{value}\n".encode())
                    finally:
                        os.close(fd)
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

    def write(self, path: Path, value: int) -> None:
        with self._lock:
            self._drain_stale()
            os.write(self._requests, f"{path} {int(value)}\n".encode())
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
