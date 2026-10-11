"""Conservative dynamic SteamOS Half Rate Shading (RADV VRS 2x2).

Steam's gamescope session exports RADV_FORCE_VRS_CONFIG_FILE into the game.
Mesa/RADV observes changes to that file using inotify. This adapter only
touches that *existing* config file (never game launch arguments or Mesa).

The setting is visibly lossy. Autopilot may trial it only after explicit
per-profile consent, with one resource experiment at a time and rollback.
File writes are never an assertion that the game actually used VRS.
"""
from __future__ import annotations

import json
import os
import re
import stat
import time
from pathlib import Path

_VAR = b"RADV_FORCE_VRS_CONFIG_FILE="
_FILENAME = re.compile(r"^radv_vrs\.[A-Za-z0-9]+$")


class SteamVrsBackend:
    def __init__(self, *, proc_root: Path = Path("/proc"), fixed_path: Path | None = None):
        self.proc_root = Path(proc_root)
        self.fixed_path = Path(fixed_path) if fixed_path is not None else None
        self._found: Path | None = None
        self._owner: int | None = None
        self._missing_at = -1e10

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

    def path(self) -> Path | None:
        return self._discover()

    def _discover(self) -> Path | None:
        if self.fixed_path is not None:
            return self._checked(self.fixed_path)
        if self._found is not None and self._checked(self._found, self._owner):
            return self._found
        self._found = None
        # A negative /proc sweep can be expensive when the Steam client is
        # absent. Cache misses briefly, but never cache a positive stale inode.
        now = time.monotonic()
        if now - self._missing_at < 4:
            return None
        self._missing_at = now
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
                    self._missing_at = -1e10
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
        flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 16
                    or (self._owner is not None and info.st_uid != self._owner)):
                raise OSError("Steam VRS file changed during acquisition")
            os.ftruncate(fd, 0)
            written = os.write(fd, value.encode("ascii"))
            if written != 3:
                raise OSError("short VRS write")
            os.fsync(fd)
        finally:
            os.close(fd)


class HalfRateShading:
    def __init__(self, backend=None, receipt_path: Path | None = None) -> None:
        self.backend = backend if backend is not None else SteamVrsBackend()
        self.receipt_path = Path(receipt_path) if receipt_path else None
        self.original: str | None = None
        self.phase = "idle"
        self.reason = "not-tested"
        self._owned_path: str | None = None
        self._load()

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
        self._owned_path = str(self.backend.path()) if hasattr(self.backend, "path") else None
        self.phase = "partial"
        self._save()
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
        self._save()
        return {"applied": True, "reason": self.reason}

    def restore(self) -> dict:
        if not self.owned:
            return {"restored": True, "reason": "not-owned"}
        # Restore only the Steam config file we captured when the trial began.
        # A game/session switch can replace it with a new QAM file containing
        # the user's OWN shading value. Never write our saved value there.
        current_path = (str(self.backend.path()) if hasattr(self.backend, "path") else None)
        if self._owned_path is not None and current_path != self._owned_path:
            self._clear("steam-session-changed")
            return {"restored": False, "yielded": True, "reason": self.reason}
        current = self.backend.read()
        if current is None:
            # The temporary Gamescope session file has disappeared: we cannot
            # and must not write to a different session's file.
            if (self._owned_path and hasattr(self.backend, "path")
                    and str(self.backend.path()) != self._owned_path):
                self._clear("old-steam-session-ended")
                return {"restored": False, "yielded": True, "reason": self.reason}
            self.phase = "restore-pending"
            self.reason = "vrs-unavailable"
            self._save()
            return {"restored": False, "reason": self.reason}
        if self.phase == "owned" and current != "2x2":
            # User/QAM took control. Never change their own setting.
            self._clear("external-change")
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
            self._save()
            return {"restored": False, "reason": self.reason}
        self._clear("restored")
        return {"restored": True, "reason": self.reason}

    def _clear(self, reason: str) -> None:
        self.phase, self.original, self.reason, self._owned_path = "idle", None, reason, None
        self._save()

    def _save(self) -> None:
        if self.receipt_path is None:
            return
        if self.phase == "idle":
            self.receipt_path.unlink(missing_ok=True)
            return
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        path = self.receipt_path.with_suffix(".tmp")
        path.write_text(json.dumps({"phase": self.phase, "original": self.original,
                                    "session_path": self._owned_path}), encoding="utf-8")
        os.replace(path, self.receipt_path)

    def _load(self) -> None:
        if self.receipt_path is None or not self.receipt_path.is_file():
            return
        try:
            saved = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(saved, dict) or saved.get("original") != "1x1":
            return
        expected = saved.get("session_path")
        actual = str(self.backend.path()) if hasattr(self.backend, "path") else None
        if not expected or expected != actual:
            # A reboot creates a *new* RADV file. Never apply the old receipt
            # to another Steam game session.
            self._clear("previous-steam-session")
            return
        self.original, self._owned_path = "1x1", expected
        if self.backend.read() == "2x2":
            self.phase, self.reason = "restore-pending", "unclosed-trial-recovered"
        else:
            self._clear("already-reset")
