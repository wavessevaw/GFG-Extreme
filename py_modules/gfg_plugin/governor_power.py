"""Steam Deck power-cap actuator for GFG Governor.

The actuator is deliberately conservative.  It discovers the amdgpu hwmon PPT
controls, snapshots the user's current caps as the session ceiling, preserves
fast/slow PPT proportion within an explicit ceiling, and refuses to overwrite caps that changed outside
Governor ownership.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from .privileged_power import HelperTimeout, allowed_cap_path, writer as privileged_writer


_FAST_LABELS = {"fastppt", "ppt1", "fast ppt"}
_SLOW_LABELS = {"slowppt", "ppt", "slow ppt"}


def _norm_label(value: str) -> str:
    return " ".join(value.strip().casefold().replace("_", " ").split())


def _read_int(path: Path) -> Optional[int]:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError, UnicodeError):
        return None


@dataclass
class PowerControlState:
    available: bool = False
    writable: bool = False
    owned: bool = False
    external_change: bool = False
    error: Optional[str] = None
    hwmon_path: Optional[str] = None
    fast_cap_path: Optional[str] = None
    slow_cap_path: Optional[str] = None
    initial_fast_uw: Optional[int] = None
    initial_slow_uw: Optional[int] = None
    expected_fast_uw: Optional[int] = None
    expected_slow_uw: Optional[int] = None
    fast_min_uw: Optional[int] = None
    slow_min_uw: Optional[int] = None
    fast_max_uw: Optional[int] = None
    slow_max_uw: Optional[int] = None
    ceiling_override_uw: Optional[int] = None
    strict_ceiling: bool = False
    method: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["current_tdp_w"] = (
            round(self.expected_slow_uw / 1_000_000.0, 3)
            if self.expected_slow_uw is not None else None
        )
        ceiling = self.ceiling_override_uw if self.ceiling_override_uw is not None else self.initial_slow_uw
        value["ceiling_tdp_w"] = round(ceiling / 1_000_000.0, 3) if ceiling is not None else None
        # The user's own limit before GFG took over (the ceiling may be a Battery-mode override).
        value["initial_tdp_w"] = (
            round(self.initial_slow_uw / 1_000_000.0, 3) if self.initial_slow_uw is not None else None
        )
        value["maximum_tdp_w"] = (
            round(self.slow_max_uw / 1_000_000.0, 3) if self.slow_max_uw is not None else None
        )
        value["minimum_tdp_w"] = (
            round(self.slow_min_uw / 1_000_000.0, 3)
            if self.slow_min_uw is not None else None
        )
        return value


class SteamDeckPowerActuator:
    """Ownership-aware writer for Steam Deck fastPPT/slowPPT hwmon caps."""

    def __init__(
        self,
        *,
        drm_root: Path = Path("/sys/class/drm"),
        hwmon_root: Path = Path("/sys/class/hwmon"),
        access: Any = os.access,
        helper: Any = privileged_writer,
        manager: Any = None,
        verify_seconds: float = 1.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        # steamos-manager (Steam's own TDP path) when present; direct hwmon writes otherwise.
        self.manager = manager
        self._verify_seconds = verify_seconds
        self._sleep = sleep
        self.drm_root = Path(drm_root)
        self.hwmon_root = Path(hwmon_root)
        self._access = access
        self._helper = helper
        self.journal: Optional[Callable[..., None]] = None
        self.state = PowerControlState()
        self._fast_path: Optional[Path] = None
        self._slow_path: Optional[Path] = None
        self._draw_path: Optional[Path] = None
        self._keep_initial = False
        # One writer at a time: an unload restore must not be overtaken by a slow write that was
        # already running in a worker thread (audit 1.0.8).  ``_closed`` refuses writes after it.
        self._lock = threading.RLock()
        self._closed = False
        self._unverified_caps: set = set()

    def reopen(self) -> None:
        with self._lock:
            self._closed = False

    def shutdown(self) -> Dict[str, Any]:
        """Plugin stop: wait for any write in flight, put the user's caps back, refuse later writes."""
        with self._lock:
            self._closed = True
            return self.restore_if_owned()

    @staticmethod
    def _candidate_hwmons(drm_root: Path, hwmon_root: Path) -> Iterable[Path]:
        seen: set[str] = set()
        patterns = (
            (drm_root, "card*/device/hwmon/hwmon*"),
            (hwmon_root, "hwmon*"),
        )
        for root, pattern in patterns:
            try:
                paths = sorted(root.glob(pattern))
            except OSError:
                paths = []
            for path in paths:
                try:
                    key = str(path.resolve())
                except OSError:
                    key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                yield path

    @staticmethod
    def _power_channels(hwmon: Path) -> Dict[str, Path]:
        result: Dict[str, Path] = {}
        try:
            labels = sorted(hwmon.glob("power*_label"))
        except OSError:
            return result
        for label_path in labels:
            try:
                label = _norm_label(label_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError):
                continue
            stem = label_path.name[:-6]  # remove _label
            cap = hwmon / f"{stem}_cap"
            if not cap.exists():
                continue
            if label.replace(" ", "") in {v.replace(" ", "") for v in _FAST_LABELS}:
                result["fast"] = cap
            if label.replace(" ", "") in {v.replace(" ", "") for v in _SLOW_LABELS}:
                result["slow"] = cap
        return result

    @staticmethod
    def _limits(cap_path: Path) -> tuple[Optional[int], Optional[int]]:
        stem = cap_path.name[:-4]  # powerN
        minimum = _read_int(cap_path.parent / f"{stem}_cap_min")
        maximum = _read_int(cap_path.parent / f"{stem}_cap_max")
        return minimum, maximum

    @staticmethod
    def _draw_sensor(hwmon: Path, slow_cap: Path) -> Optional[Path]:
        """Measured APU power: the cap only says what was allowed, this says what was used."""
        stem = slow_cap.name[:-4]
        preferred = [hwmon / f"{stem}_average", hwmon / f"{stem}_input"]
        try:
            preferred += sorted(hwmon.glob("power*_average")) + sorted(hwmon.glob("power*_input"))
        except OSError:
            pass
        for path in preferred:
            if _read_int(path) is not None:
                return path
        return None

    def discover(self) -> Dict[str, Any]:
        for hwmon in self._candidate_hwmons(self.drm_root, self.hwmon_root):
            channels = self._power_channels(hwmon)
            fast = channels.get("fast")
            slow = channels.get("slow")
            if fast is None or slow is None:
                continue
            fast_value = _read_int(fast)
            slow_value = _read_int(slow)
            if not fast_value or not slow_value:
                continue
            fast_min, fast_max = self._limits(fast)
            slow_min, slow_max = self._limits(slow)
            # hwmon caps are root-only: a plugin running as the desktop user can
            # read them but every write fails.  Report that up front instead of
            # claiming control that cannot work.
            helper = self._helper()
            if helper is not None:
                direct = bool(allowed_cap_path(str(fast)) and allowed_cap_path(str(slow)))
            else:
                direct = bool(self._access(fast, os.W_OK) and self._access(slow, os.W_OK))
            via_manager = False
            if self.manager is not None:
                try:
                    via_manager = bool(self.manager.probe())
                except Exception:
                    via_manager = False
            writable = via_manager or direct
            mgr_range = getattr(self.manager, "range", None) if via_manager else None
            if mgr_range and not direct:
                # Only Steam's path is available: its range is the real limit.
                low_uw, high_uw = int(mgr_range[0]) * 1_000_000, int(mgr_range[1]) * 1_000_000
                slow_min = max(slow_min or 0, low_uw) or None
                slow_max = min(slow_max, high_uw) if slow_max else high_uw
            method = "steamos-manager" if via_manager else ("sysfs" if direct else None)
            self._fast_path = fast
            self._slow_path = slow
            self._draw_path = self._draw_sensor(hwmon, slow)
            self.state = PowerControlState(
                available=writable,
                writable=writable,
                error=None if writable else "Steam Deck fastPPT/slowPPT caps are not writable by the plugin",
                hwmon_path=str(hwmon),
                fast_cap_path=str(fast),
                slow_cap_path=str(slow),
                fast_min_uw=fast_min,
                slow_min_uw=slow_min,
                fast_max_uw=fast_max,
                slow_max_uw=slow_max,
                method=method,
            )
            return self.status()
        self._fast_path = None
        self._slow_path = None
        self._draw_path = None
        self.state = PowerControlState(
            available=False,
            error="Steam Deck fastPPT/slowPPT controls were not found",
        )
        return self.status()

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal is not None:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def claim(self) -> Dict[str, Any]:
        with self._lock:
            if self._closed:
                return self.status()
            result = self._claim()
        self._note("tdp-claim", owned=result.get("owned"), available=result.get("available"),
                   writable=result.get("writable"), current_w=result.get("current_tdp_w"),
                   error=result.get("error"))
        return result

    def claim_at_ceiling_w(self, watts: float) -> Dict[str, Any]:
        """Claim and lower both caps before handing an Extreme session to the controller.

        Keep the player's originals for exit; inherited caps must not remain above
        the stock/user ceiling during a renderer trial.
        """
        with self._lock:
            if self._closed:
                return {**self.status(), "success": False}
            self.set_strict_ceiling_w(watts)
            result = self._claim()
            if not result.get("owned"):
                return {**result, "success": False}
            initial = min(self.state.initial_slow_uw, self.state.initial_fast_uw) / 1e6
            target = min(float(watts), initial)
            self.set_strict_ceiling_w(target)
            result = self._set_tdp_w(target)
            return {**self.status(), "success": bool(result.get("success"))}

    def _claim(self) -> Dict[str, Any]:
        if not self.state.available:
            self.discover()
        if not self.state.available or self._fast_path is None or self._slow_path is None:
            return self.status()
        fast = _read_int(self._fast_path)
        slow = _read_int(self._slow_path)
        if not fast or not slow:
            self.state.error = "Could not read current PPT caps"
            return self.status()
        if not (self._keep_initial and self.state.initial_fast_uw and self.state.initial_slow_uw):
            self.state.initial_fast_uw = fast
            self.state.initial_slow_uw = slow
        self._keep_initial = False
        self.state.expected_fast_uw = fast
        self.state.expected_slow_uw = slow
        self.state.owned = True
        self.state.external_change = False
        self.state.error = None
        return self.status()

    def _verify_ownership(self) -> bool:
        if not self.state.owned or self._fast_path is None or self._slow_path is None:
            return False
        fast = _read_int(self._fast_path)
        slow = _read_int(self._slow_path)
        if fast != self.state.expected_fast_uw or slow != self.state.expected_slow_uw:
            self.state.external_change = True
            self.state.owned = False
            self._keep_initial = False
            self.state.error = "PPT caps changed outside GFG Governor; automatic power control paused"
            self._note("tdp-external-change", expected_slow_uw=self.state.expected_slow_uw, found_slow_uw=slow,
                       expected_fast_uw=self.state.expected_fast_uw, found_fast_uw=fast)
            return False
        return True

    @staticmethod
    def _clamp(value: int, minimum: Optional[int], maximum: Optional[int]) -> int:
        if minimum is not None:
            value = max(value, minimum)
        if maximum is not None:
            value = min(value, maximum)
        return value

    def _write_value(self, path: Path, value: int) -> None:
        helper = self._helper()
        if helper is not None:
            helper.write(path, int(value))
        else:
            path.write_text(f"{int(value)}\n", encoding="utf-8")

    def _direct_possible(self) -> bool:
        if self._fast_path is None or self._slow_path is None:
            return False
        if self._helper() is not None:
            return bool(allowed_cap_path(str(self._slow_path)) and allowed_cap_path(str(self._fast_path)))
        return bool(self._access(self._slow_path, os.W_OK) and self._access(self._fast_path, os.W_OK))

    def _apply(self, slow: int, fast: int, *, exact: bool = False) -> Optional[tuple[str, str]]:
        """Put the caps at slow/fast; returns (kind, message) on failure, None on success.

        Kinds: ``unverified`` (a write was accepted but the cap reads something
        else, or the root helper timed out and the write may still land) and
        ``write-failed``.  Updates the expected caps on success.
        ``exact`` (restore) prefers the direct write, which keeps fast != slow.
        """
        assert self._fast_path is not None and self._slow_path is not None
        manager = self.manager if self.state.method == "steamos-manager" else None
        direct = self._direct_possible()
        if manager is not None and not exact and self.state.strict_ceiling:
            # Steam's integer TdpLimit API does not promise the fastPPT cap. A strict
            # ceiling requires control of both channels, without a transient overshoot.
            if not direct:
                return "write-failed", "Explicit PPT ceiling requires writable fast/slow caps"
            manager = None
        if manager is not None and exact and direct:
            # Put Steam's own TdpLimit back too, so a later re-apply by Steam
            # (sleep, game change) does not bring our last value back.
            low, high = getattr(manager, "range", None) or (1, 60)
            try:
                manager.set(max(low, min(high, int(round(slow / 1_000_000.0)))))
            except Exception:
                pass
        if manager is not None and not (exact and direct):
            watts = max(1, int(round(slow / 1_000_000.0)))
            low, high = getattr(manager, "range", None) or (watts, watts)
            if exact:
                if slow != fast or slow % 1_000_000 or not low <= slow // 1_000_000 <= high:
                    return "write-failed", "Exact PPT restore requires writable fast/slow caps"
            else:
                ceiling = self.state.ceiling_override_uw
                slow_limits = [v for v in (self.state.slow_max_uw,
                              ceiling if ceiling is not None else self.state.initial_slow_uw) if v is not None]
                fast_limits = [v for v in (self.state.fast_max_uw,
                              ceiling if ceiling is not None else self.state.initial_fast_uw) if v is not None]
                safe_max = min(slow_limits + fast_limits) if slow_limits or fast_limits else slow
                if (watts > high or watts < low or watts * 1_000_000 > safe_max) and direct:
                    manager = None  # preserve fractional limits through the verified pair writer
                else:
                    watts = min(watts, high, safe_max // 1_000_000)
                    if (watts < low or watts < 1
                            or any(v is not None and watts * 1_000_000 < v
                                   for v in (self.state.slow_min_uw, self.state.fast_min_uw))):
                        return "write-failed", "No SteamOS Manager watt step fits the PPT limits"
        if manager is not None and not (exact and direct):
            ok, message = manager.set(watts)
            if ok:
                deadline = time.monotonic() + self._verify_seconds
                while True:
                    read_slow = _read_int(self._slow_path)
                    read_fast = _read_int(self._fast_path)
                    # The manager promises an equal pair. Reading slow alone can
                    # accept a half-applied write or leave a high short-duration cap.
                    if read_slow == read_fast == watts * 1_000_000:
                        self.state.expected_slow_uw = read_slow
                        self.state.expected_fast_uw = read_fast
                        return None
                    if time.monotonic() >= deadline:
                        break
                    self._sleep(0.1)
                return "unverified", f"steamos-manager accepted {watts} W but the cap reads slow={read_slow}, fast={read_fast}"
            self._note("tdp-manager-failed", error=message, requested_w=watts)
            if not direct:
                return "write-failed", f"steamos-manager: {message}"
        try:
            self._write_value(self._slow_path, slow)
            self._write_value(self._fast_path, fast)
        except HelperTimeout as error:
            # A late write is ours, not an outside change: keep the restore path open.
            return "unverified", str(error)
        except OSError as error:
            return "write-failed", str(error)
        read_slow = _read_int(self._slow_path)
        read_fast = _read_int(self._fast_path)
        if read_slow != slow or read_fast != fast:
            return "unverified", "PPT write did not verify"
        self.state.expected_slow_uw = slow
        self.state.expected_fast_uw = fast
        return None

    def set_ceiling_w(self, watts: Optional[float], *, strict: bool = False) -> None:
        """Budget ceiling; strict (Extreme) requires verified control of both PPT caps."""
        with self._lock:
            self.state.strict_ceiling = bool(strict and watts is not None)
            if watts is None:
                self.state.ceiling_override_uw = None
                return
            value = int(round(float(watts) * 1_000_000.0))
            if self.state.slow_max_uw is not None:
                value = min(value, self.state.slow_max_uw)
            self.state.ceiling_override_uw = value

    def set_strict_ceiling_w(self, watts: float) -> None:
        """Extreme's stock-power contract, separate from manager-compatible budgets."""
        self.set_ceiling_w(watts, strict=True)

    def set_tdp_w(self, watts: float) -> Dict[str, Any]:
        with self._lock:
            if self._closed:
                return {"success": False, "error": "power control closed", "state": self.status()}
            result = self._set_tdp_w(watts)
        state = result.get("state") or {}
        self._note("tdp-write", requested_w=watts, success=result.get("success"), error=result.get("error"),
                   observed_w=state.get("observed_tdp_w"), observed_fast_w=state.get("observed_fast_w"),
                   draw_w=state.get("draw_w"), cap_path=self.state.slow_cap_path, method=self.state.method)
        return result

    def _set_tdp_w(self, watts: float) -> Dict[str, Any]:
        if not self.state.owned:
            return {"success": False, "error": self.state.error or "Power control is not owned", "state": self.status()}
        if not self._verify_ownership():
            return {"success": False, "error": self.state.error, "state": self.status()}
        assert self._fast_path is not None and self._slow_path is not None
        assert self.state.initial_fast_uw is not None and self.state.initial_slow_uw is not None
        requested_slow = int(round(float(watts) * 1_000_000.0))
        ratio = self.state.initial_fast_uw / max(1, self.state.initial_slow_uw)
        requested_fast = int(round(requested_slow * ratio))
        slow = self._clamp(requested_slow, self.state.slow_min_uw, self.state.slow_max_uw)
        fast = self._clamp(requested_fast, self.state.fast_min_uw, self.state.fast_max_uw)
        # Default session ceiling: whatever the user/QAM had selected when
        # Governor claimed the controls.  Budget mode sets an explicit ceiling
        # (at most the hardware maximum) because it may need to go above it.
        if self.state.ceiling_override_uw is None:
            slow = min(slow, self.state.initial_slow_uw)
            fast = min(fast, self.state.initial_fast_uw)
        else:
            slow = min(slow, self.state.ceiling_override_uw)
            fast = min(fast, self.state.ceiling_override_uw)
        if ((self.state.slow_min_uw is not None and slow < self.state.slow_min_uw)
                or (self.state.fast_min_uw is not None and fast < self.state.fast_min_uw)):
            return {"success": False, "error": "PPT ceiling is below the hardware minimum", "state": self.status()}
        failure = self._apply(slow, fast)
        if failure is not None:
            kind, error = failure
            self.state.error = error
            if kind == "write-failed":
                # A half-done write (slow written, fast refused) is still ours: track what the caps
                # read now, so the next check does not call it an outside change and skip restore.
                self.state.expected_slow_uw = _read_int(self._slow_path)
                self.state.expected_fast_uw = _read_int(self._fast_path)
            if kind == "unverified":
                # What the caps may read if our write did land (late or rounded): restore only
                # from these, never over a value another tool wrote meanwhile.
                self._unverified_caps = {(_read_int(self._slow_path), _read_int(self._fast_path)),
                                         (slow, fast), (slow, self.state.expected_fast_uw),
                                         (self.state.expected_slow_uw, self.state.expected_fast_uw)}
                self.state.owned = False
                # Our own write failed, nobody else touched the caps: a re-claim in
                # this session must keep the user's original values for restore.
                self._keep_initial = True
            return {"success": False, "error": error, "state": self.status()}
        self.state.error = None
        return {"success": True, "error": None, "state": self.status()}

    def restore_if_owned(self) -> Dict[str, Any]:
        with self._lock:
            result = self._restore_if_owned()
        if result.get("restored") or not result.get("success", True):
            self._note("tdp-restore", restored=result.get("restored"), reason=result.get("reason"),
                       error=result.get("error"), observed_w=(result.get("state") or {}).get("observed_tdp_w"))
        return result

    def _restore_if_owned(self) -> Dict[str, Any]:
        if not self.state.owned:
            # Our own write did not verify (ownership dropped, nobody else touched the caps):
            # the user's values must still come back (audit 1.0.8).
            if not (self._keep_initial and self.state.initial_slow_uw and self.state.initial_fast_uw
                    and self._fast_path is not None and self._slow_path is not None):
                return {"success": True, "restored": False, "reason": "not-owned", "state": self.status()}
            now_caps = (_read_int(self._slow_path), _read_int(self._fast_path))
            if now_caps not in self._unverified_caps:
                # Someone else set the caps after our write failed: theirs stay (review 1.0.10).
                self._keep_initial = False
                return {"success": True, "restored": False, "reason": "external-change", "state": self.status()}
        elif not self._verify_ownership():
            return {"success": True, "restored": False, "reason": "external-change", "state": self.status()}
        assert self._fast_path is not None and self._slow_path is not None
        assert self.state.initial_fast_uw is not None and self.state.initial_slow_uw is not None
        failure = self._apply(self.state.initial_slow_uw, self.state.initial_fast_uw, exact=True)
        if failure is not None:
            self.state.error = failure[1]
            return {"success": False, "restored": False, "error": failure[1], "state": self.status()}
        self._keep_initial = False
        self.state.expected_fast_uw = self.state.initial_fast_uw
        self.state.expected_slow_uw = self.state.initial_slow_uw
        self.state.owned = False
        self.state.error = None
        return {"success": True, "restored": True, "reason": "restored", "state": self.status()}

    def verify_ownership(self) -> Dict[str, Any]:
        """Check that external Steam/QAM tooling has not changed our caps."""
        with self._lock:
            if self.state.owned:
                self._verify_ownership()
            return self.status()

    def status(self) -> Dict[str, Any]:
        value = self.state.to_dict()
        if self._fast_path is not None and self._slow_path is not None:
            current_fast = _read_int(self._fast_path)
            current_slow = _read_int(self._slow_path)
            value["observed_fast_uw"] = current_fast
            value["observed_slow_uw"] = current_slow
            value["observed_tdp_w"] = round(current_slow / 1_000_000.0, 3) if current_slow else None
            value["observed_fast_w"] = round(current_fast / 1_000_000.0, 3) if current_fast else None
        draw = _read_int(self._draw_path) if self._draw_path is not None else None
        value["draw_w"] = round(draw / 1_000_000.0, 2) if draw is not None else None
        return value
