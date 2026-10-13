"""CPU maximum-clock actuator for the smart power split (``power_split.py``).

Writes ``scaling_max_freq`` of every cpufreq policy, with the same rules as the TDP actuator:

* the values found at claim time are the user's and come back on release, game exit and unload;
* a value changed by another tool (PowerTools, a script) is theirs: control pauses, nothing is
  restored over it;
* the cap never goes above the user's own limit.

Crash safety: the values in force are noted in a small marker file before every write; the next
start puts the user's values back if they still read what GFG wrote.  The root helper does the
same when the plugin process dies (``privileged_power``).
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .privileged_power import HelperTimeout, allowed_cpu_path, writer as privileged_writer


def _read_int(path: Path) -> Optional[int]:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError, UnicodeError):
        return None


class CpuFreqActuator:
    def __init__(self, *, root: Path = Path("/sys/devices/system/cpu/cpufreq"),
                 helper: Callable[[], Any] = privileged_writer, access: Any = os.access,
                 marker: Optional[Path] = None) -> None:
        self.root = Path(root)
        self._helper = helper
        self._access = access
        self.marker = marker
        self.journal: Optional[Callable[..., None]] = None
        self._lock = threading.RLock()
        self._policies: Dict[Path, Dict[str, int]] = {}    # scaling_max_freq -> cpuinfo min/max
        self.initial: Dict[Path, int] = {}
        self.expected: Dict[Path, int] = {}
        self.owned = False
        self.external_change = False
        self.error: Optional[str] = None
        self.cap_khz: Optional[int] = None
        self._discovered = False
        self._closed = False
        self.restore_pending = False
        self._pending_targets: Dict[Path, int] = {}

    # ------------------------------------------------------------------ discovery
    def discover(self) -> bool:
        with self._lock:
            if self._discovered:
                return bool(self._policies)
            self._discovered = True
            try:
                dirs = sorted(self.root.glob("policy[0-9]*"))
            except OSError:
                dirs = []
            for d in dirs:
                top, low = _read_int(d / "cpuinfo_max_freq"), _read_int(d / "cpuinfo_min_freq")
                if top and (d / "scaling_max_freq").exists():
                    self._policies[d / "scaling_max_freq"] = {"max": top, "min": low or 0}
            self._recover_stale()
            return bool(self._policies)

    @property
    def available(self) -> bool:
        return bool(self._policies) and self._writable()

    @property
    def max_khz(self) -> int:
        """The highest clock GFG may use: the hardware's, or the user's own lower limit."""
        tops = [min(info["max"], self.initial.get(p) or _read_int(p) or info["max"])
                for p, info in self._policies.items()]
        return min(tops) if tops else 0

    @property
    def min_khz(self) -> int:
        return max((info["min"] for info in self._policies.values()), default=0)

    def _writable(self) -> bool:
        if self._helper() is not None:
            return all(allowed_cpu_path(str(p)) for p in self._policies)
        return all(self._access(p, os.W_OK) for p in self._policies)

    # ------------------------------------------------------------------ control
    def claim(self) -> bool:
        with self._lock:
            if self._closed or not self.discover() or not self._writable():
                return False
            if self.restore_pending:
                if self.owned:
                    self.restore()
                else:
                    self._recover_stale()
                if self.restore_pending:
                    return False
            if self.owned:
                return True
            values = {p: _read_int(p) for p in self._policies}
            if any(v is None for v in values.values()):
                self.error = "could not read scaling_max_freq"
                return False
            self.initial = {p: int(v) for p, v in values.items() if v is not None}
            self.expected = dict(self.initial)
            self.owned, self.external_change, self.error, self.cap_khz = True, False, None, None
            return True

    def set_cap_khz(self, khz: Optional[int]) -> bool:
        """Cap every policy at ``khz`` (None: the user's own values).  False when not in control."""
        with self._lock:
            if self._closed or not self.owned:
                return False
            if self.restore_pending:
                self.restore()
                return False  # resolve the failed transaction before another optimization
            if not self._verify():
                return False
            if khz == self.cap_khz:
                return True
            wanted = {p: (self.initial[p] if khz is None else
                          max(info["min"], min(int(khz), self.initial[p], info["max"])))
                      for p, info in self._policies.items()}
            if not self._write_marker(wanted):
                return False
            if not self._apply(wanted, restoring=khz is None):
                self.restore_pending = True
                return False
            # Commit readback: a completed cap no longer needs the previous-value
            # candidate that only protected a crash during the partial write.
            if not self._write_marker(wanted):
                self.restore_pending = True
                return False
            self.cap_khz = khz
            self._note("cpu-cap", cap_khz=khz)
            return True

    def restore(self) -> bool:
        """Put the user's values back (when they are still ours).  True if anything was written."""
        with self._lock:
            if not self.owned:
                return self._recover_stale() if self.restore_pending else False
            if not self._verify():
                return False
            # A failed multi-policy write may have changed clocks before cap_khz was
            # committed. Late helper writes also require an explicit ordered undo.
            changed = bool(self._pending_targets) or any(
                self.expected.get(p) != value for p, value in self.initial.items())
            if changed and not self._apply(dict(self.initial), restoring=True):
                self.restore_pending = True
                return False
            self.owned, self.cap_khz = False, None
            self.restore_pending = False
            self._pending_targets.clear()
            self._clear_marker()
            if changed:
                self._note("cpu-cap-restored")
            return changed

    def shutdown(self) -> bool:
        with self._lock:
            restored = self.restore()
            self._closed = True
            return restored

    def reopen(self) -> None:
        with self._lock:
            self._closed = False

    def release_external(self) -> None:
        """A new game: an outside change from the last one does not block this one."""
        with self._lock:
            if not self.owned:
                self.external_change = False

    # ------------------------------------------------------------------ internals
    def _verify(self) -> bool:
        for p, value in self.expected.items():
            found = _read_int(p)
            if found != value and p in self._pending_targets and found == self._pending_targets[p]:
                self.expected[p] = found  # an accepted/timed-out write landed; it is still ours
                self._note("cpu-cap-delayed-applied", policy=p.parent.name, found=found)
                continue
            if found != value:
                self.owned, self.external_change, self.cap_khz = False, True, None
                # One outside policy must not strand our caps on the other policies.
                # The journal restores each value only while it still matches ours.
                self._recover_stale(trusted_expected=self.expected)
                self.error = self.error or "CPU clock limit changed outside GFG; power split paused"
                self._note("cpu-cap-external-change", policy=str(p.parent.name), expected=value,
                           found=found)
                return False
        return True

    def _apply(self, wanted: Dict[Path, int], *, restoring: bool = False) -> bool:
        for p, value in wanted.items():
            try:
                helper = self._helper()
                if helper is not None:
                    write = getattr(helper, "restore_cpu", helper.write) if restoring else helper.write
                    self._pending_targets[p] = value
                    write(p, int(value))
                else:
                    p.write_text(f"{int(value)}\n", encoding="utf-8")
            except HelperTimeout as error:
                self._pending_targets[p] = value
                self.error = str(error)
                return False
            except OSError as error:
                self.error = str(error)
            read = _read_int(p)
            if read is not None:
                self.expected[p] = read           # the driver may clamp; what it reads is ours
            if read != value:
                # A successful helper reply is not synchronous sysfs readback.
                # Retain the accepted target so its late arrival remains ours.
                if helper is not None:
                    self._pending_targets[p] = value
                self.error = self.error or f"{p.parent.name}: wrote {value}, reads {read}"
                self._note("cpu-cap-failed", policy=p.parent.name, wanted=value, found=read, error=self.error)
                return False
            self._pending_targets.pop(p, None)
        self.error = None
        return True

    def _write_marker(self, wanted: Dict[Path, int]) -> bool:
        data = {str(p): {"initial": self.initial[p], "written": wanted[p],
                         "previous": self.expected[p]} for p in wanted}
        return self._save_marker(data)

    def _save_marker(self, data: Dict[str, Any]) -> bool:
        if self.marker is None:
            return True
        try:
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.marker.with_name(self.marker.name + ".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.replace(tmp, self.marker)
            return True
        except OSError as error:
            self.error = f"CPU recovery marker could not be saved: {error}"
            return False  # no sysfs write without its undo record

    def _clear_marker(self) -> None:
        if self.marker is not None:
            try:
                self.marker.unlink()
            except OSError:
                pass

    def _recover_stale(self, *, trusted_expected: Optional[Dict[Path, int]] = None) -> bool:
        """Restore owned policies; keep failed/read-unverified undo entries for retry."""
        if self.marker is None or not self.marker.exists():
            return False
        try:
            data = json.loads(self.marker.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("expected a policy map")
        except (OSError, ValueError, UnicodeError) as error:
            self.restore_pending = True
            self.error = f"CPU recovery marker unreadable: {error}"
            return False

        restored, remaining = [], {}
        for name, entry in data.items():
            p = Path(name)
            if p not in self._policies or not isinstance(entry, dict):
                continue
            initial, written = entry.get("initial"), entry.get("written")
            previous = entry.get("previous", written)  # older journals have only written
            if (not isinstance(initial, int) or isinstance(initial, bool) or initial <= 0
                    or not isinstance(written, int) or isinstance(written, bool) or written <= 0
                    or not isinstance(previous, int) or isinstance(previous, bool) or previous <= 0):
                self.restore_pending = True
                self.error = f"CPU recovery marker invalid for {p.parent.name}"
                return False
            found = _read_int(p)
            if found is None:
                remaining[name] = entry
                continue
            if found == initial:
                continue
            if trusted_expected is not None:
                if found != trusted_expected.get(p) and found != self._pending_targets.get(p):
                    continue  # live ownership is stronger than an uncommitted journal candidate
            elif found not in (written, previous):
                continue  # a different tool owns this policy
            try:
                helper = self._helper()
                if helper is not None:
                    getattr(helper, "restore_cpu", helper.write)(p, initial)
                else:
                    p.write_text(f"{initial}\n", encoding="utf-8")
            except (HelperTimeout, OSError) as error:
                self.error = str(error)
            if _read_int(p) == initial:
                restored.append(p.parent.name)
                self._pending_targets.pop(p, None)
            else:
                remaining[name] = entry
                self.initial[p] = initial  # never learn a leftover GFG cap as the user's limit

        self.restore_pending = bool(remaining)
        if remaining:
            self.error = self.error or "CPU clock restore did not verify; recovery pending"
            # Even if this rewrite fails, the older full journal still carries undo.
            self._save_marker(remaining)
        else:
            self._clear_marker()
            self.error = None
        if restored:
            self._note("cpu-cap-recovered", policies=restored)
        return bool(restored)

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal is not None:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {"available": bool(self._policies), "writable": self._writable() if self._policies else False,
                "owned": self.owned, "external_change": self.external_change, "error": self.error,
                "restore_pending": self.restore_pending,
                "cap_khz": self.cap_khz, "max_khz": self.max_khz or None, "policies": len(self._policies),
                "observed_policy_caps_khz": {p.parent.name: _read_int(p) for p in self._policies},
                "pending_policy_caps_khz": {p.parent.name: value for p, value in self._pending_targets.items()}}
