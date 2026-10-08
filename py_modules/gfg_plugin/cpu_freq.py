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
            if self._closed or not self.owned or not self._verify():
                return False
            if khz == self.cap_khz:
                return True
            wanted = {p: (self.initial[p] if khz is None else
                          max(info["min"], min(int(khz), self.initial[p], info["max"])))
                      for p, info in self._policies.items()}
            self._write_marker(wanted)
            if not self._apply(wanted):
                return False
            self.cap_khz = khz
            self._note("cpu-cap", cap_khz=khz)
            return True

    def restore(self) -> bool:
        """Put the user's values back (when they are still ours).  True if anything was written."""
        with self._lock:
            if not self.owned:
                return False
            if not self._verify():
                return False
            changed = self.cap_khz is not None
            if changed and not self._apply(dict(self.initial)):
                return False
            self.owned, self.cap_khz = False, None
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
            if _read_int(p) != value:
                self.owned, self.external_change, self.cap_khz = False, True, None
                self.error = "CPU clock limit changed outside GFG; power split paused"
                self._clear_marker()
                self._note("cpu-cap-external-change", policy=str(p.parent.name), expected=value,
                           found=_read_int(p))
                return False
        return True

    def _apply(self, wanted: Dict[Path, int]) -> bool:
        for p, value in wanted.items():
            try:
                helper = self._helper()
                if helper is not None:
                    helper.write(p, int(value))
                else:
                    p.write_text(f"{int(value)}\n", encoding="utf-8")
            except (HelperTimeout, OSError) as error:
                self.error = str(error)
            read = _read_int(p)
            if read is not None:
                self.expected[p] = read           # the driver may clamp; what it reads is ours
            if read != value:
                self.error = self.error or f"{p.parent.name}: wrote {value}, reads {read}"
                self._note("cpu-cap-failed", policy=p.parent.name, wanted=value, found=read, error=self.error)
                return False
        self.error = None
        return True

    def _write_marker(self, wanted: Dict[Path, int]) -> None:
        if self.marker is None:
            return
        data = {str(p): {"initial": self.initial[p], "written": wanted[p]} for p in wanted}
        try:
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.marker.with_name(self.marker.name + ".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.replace(tmp, self.marker)
        except OSError:
            pass

    def _clear_marker(self) -> None:
        if self.marker is not None:
            try:
                self.marker.unlink()
            except OSError:
                pass

    def _recover_stale(self) -> None:
        """A crashed session left its cap: put the user's value back where it still reads ours."""
        if self.marker is None or not self.marker.exists():
            return
        try:
            data = json.loads(self.marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        restored = []
        for name, entry in (data.items() if isinstance(data, dict) else ()):
            p = Path(name)
            if p not in self._policies or not isinstance(entry, dict):
                continue
            initial, written = entry.get("initial"), entry.get("written")
            if isinstance(initial, int) and isinstance(written, int) and _read_int(p) == written != initial:
                try:
                    helper = self._helper()
                    if helper is not None:
                        helper.write(p, initial)
                    else:
                        p.write_text(f"{initial}\n", encoding="utf-8")
                    restored.append(p.parent.name)
                except (HelperTimeout, OSError):
                    pass
        self._clear_marker()
        if restored:
            self._note("cpu-cap-recovered", policies=restored)

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal is not None:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {"available": bool(self._policies), "writable": self._writable() if self._policies else False,
                "owned": self.owned, "external_change": self.external_change, "error": self.error,
                "cap_khz": self.cap_khz, "max_khz": self.max_khz or None, "policies": len(self._policies)}
