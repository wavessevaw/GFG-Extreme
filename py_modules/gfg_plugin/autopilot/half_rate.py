"""Conservative dynamic SteamOS Half Rate Shading (RADV VRS 2x2).

Steam's gamescope session exports RADV_FORCE_VRS_CONFIG_FILE into the game.
Mesa/RADV observes changes to that file using inotify. This adapter only
touches that *existing* config file (never game launch arguments or Mesa).

The setting is visibly lossy. Autopilot may trial it only after explicit
per-profile consent, with one resource experiment at a time and rollback.
File writes are never an assertion that the game actually used VRS.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path

_VAR = b"RADV_FORCE_VRS_CONFIG_FILE="
_FILENAME = re.compile(r"^radv_vrs\.[A-Za-z0-9]+$")


class SteamVrsBackend:
    def __init__(self, *, proc_root: Path = Path("/proc"), fixed_path: Path | None = None):
        self.proc_root = Path(proc_root)
        self.fixed_path = Path(fixed_path) if fixed_path is not None else None
        self._found: Path | None = None
        self._owner: int | None = None

    def _checked(self, path: Path, uid: int | None = None) -> Path | None:
        # Steam creates /tmp/radv_vrs.XXXXXXXX and exports its exact name.
        # Do not follow symlinks or write arbitrary paths from game processes.
        if path.parent != Path("/tmp") or not _FILENAME.fullmatch(path.name):
            # Fixed paths are used exclusively by injected tests.
            if self.fixed_path is None or path != self.fixed_path:
                return None
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or (uid is not None and info.st_uid != uid):
                return None
            if info.st_mode & 0o022:
                return None  # other users must not be able to mutate it
            if info.st_size > 16:
                return None
        except OSError:
            return None
        return path

    def _discover(self) -> Path | None:
        if self.fixed_path is not None:
            return self._checked(self.fixed_path)
        if self._found is not None and self._checked(self._found, self._owner):
            return self._found
        self._found = None
        try:
            processes = list(self.proc_root.iterdir())
        except OSError:
            return None
        for pid in processes:
            if not pid.name.isdigit():
                continue
            try:
                comm = (pid / "comm").read_text(errors="replace").strip().lower()
                if not (comm.startswith("steam") or "gamescope" in comm):
                    continue
                procstat = (pid / "status").read_text(errors="replace")
                uid_line = next(line for line in procstat.splitlines() if line.startswith("Uid:"))
                uid = int(uid_line.split()[1])
                raw = (pid / "environ").read_bytes()
            except (OSError, StopIteration, ValueError):
                continue
            for entry in raw.split(b"\0"):
                if not entry.startswith(_VAR):
                    continue
                try:
                    path = Path(os.fsdecode(entry[len(_VAR):]))
                except (UnicodeError, ValueError):
                    continue
                if self._checked(path, uid):
                    self._owner, self._found = uid, path
                    return path
        return None

    def read(self) -> str | None:
        path = self._discover()
        if path is None:
            return None
        try:
            value = path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            return None
        return value if value in ("1x1", "2x2", "2x1", "1x2") else None

    def write(self, value: str) -> None:
        if value not in ("1x1", "2x2"):
            raise OSError("invalid VRS mode")
        path = self._discover()
        if path is None:
            raise OSError("Steam RADV VRS file unavailable")
        # In-place write is deliberate: Mesa watches the existing inode using
        # inotify, so os.replace() risks disconnecting the live game notifier.
        flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            os.write(fd, value.encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)


class HalfRateShading:
    def __init__(self, backend=None) -> None:
        self.backend = backend if backend is not None else SteamVrsBackend()
        self.original: str | None = None
        self.phase = "idle"
        self.reason = "not-tested"

    @property
    def owned(self) -> bool:
        return self.phase in ("owned", "partial", "restore-pending")

    def status(self) -> dict:
        value = self.backend.read()
        return {"available": value in ("1x1", "2x2"), "mode": value,
                "enabled": value == "2x2", "owned": self.owned,
                "phase": self.phase, "reason": self.reason}

    def enable_trial(self) -> dict:
        if self.owned:
            return {"applied": False, "reason": "already-owned"}
        original = self.backend.read()
        if original != "1x1":
            return {"applied": False, "reason": "already-on-or-unavailable"}
        self.original = original
        self.phase = "partial"
        try:
            self.backend.write("2x2")
            if self.backend.read() != "2x2":
                raise OSError("VRS readback failed")
        except OSError:
            self.reason = "write-or-readback-failed"
            restored = self.restore()
            return {"applied": False, "reason": self.reason,
                    "restored": restored.get("restored", False)}
        self.phase = "owned"
        self.reason = "trial-enabled"
        return {"applied": True, "reason": self.reason}

    def restore(self) -> dict:
        if not self.owned:
            return {"restored": True, "reason": "not-owned"}
        current = self.backend.read()
        if current is None:
            self.phase = "restore-pending"
            self.reason = "vrs-unavailable"
            return {"restored": False, "reason": self.reason}
        if self.phase == "owned" and current != "2x2":
            # User/QAM took control. Never change their own setting.
            self.phase = "idle"
            self.reason = "external-change"
            self.original = None
            return {"restored": False, "yielded": True, "reason": self.reason}
        if self.original is None:
            self.phase = "restore-pending"
            return {"restored": False, "reason": "original-not-known"}
        try:
            if current != self.original:
                self.backend.write(self.original)
            if self.backend.read() != self.original:
                raise OSError("VRS restore not confirmed")
        except OSError:
            self.phase = "restore-pending"
            self.reason = "restore-unconfirmed"
            return {"restored": False, "reason": self.reason}
        self.phase, self.original, self.reason = "idle", None, "restored"
        return {"restored": True, "reason": self.reason}
