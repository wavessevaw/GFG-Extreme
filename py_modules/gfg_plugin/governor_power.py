"""Steam Deck power-cap actuator for GFG Governor.

The actuator is deliberately conservative.  It discovers the amdgpu hwmon PPT
controls, snapshots the user's current caps as the session ceiling, preserves
fast/slow PPT proportion, and refuses to overwrite caps that changed outside
Governor ownership.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from .privileged_power import allowed_cap_path, writer as privileged_writer


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

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["current_tdp_w"] = (
            round(self.expected_slow_uw / 1_000_000.0, 3)
            if self.expected_slow_uw is not None else None
        )
        value["ceiling_tdp_w"] = (
            round(self.initial_slow_uw / 1_000_000.0, 3)
            if self.initial_slow_uw is not None else None
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
    ) -> None:
        self.drm_root = Path(drm_root)
        self.hwmon_root = Path(hwmon_root)
        self._access = access
        self._helper = helper
        self.journal: Optional[Callable[..., None]] = None
        self.state = PowerControlState()
        self._fast_path: Optional[Path] = None
        self._slow_path: Optional[Path] = None
        self._draw_path: Optional[Path] = None

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
                writable = bool(allowed_cap_path(str(fast)) and allowed_cap_path(str(slow)))
            else:
                writable = bool(self._access(fast, os.W_OK) and self._access(slow, os.W_OK))
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
        result = self._claim()
        self._note("tdp-claim", owned=result.get("owned"), available=result.get("available"),
                   writable=result.get("writable"), current_w=result.get("current_tdp_w"),
                   error=result.get("error"))
        return result

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
        self.state.initial_fast_uw = fast
        self.state.initial_slow_uw = slow
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

    def set_tdp_w(self, watts: float) -> Dict[str, Any]:
        result = self._set_tdp_w(watts)
        state = result.get("state") or {}
        self._note("tdp-write", requested_w=watts, success=result.get("success"), error=result.get("error"),
                   observed_w=state.get("observed_tdp_w"), observed_fast_w=state.get("observed_fast_w"),
                   draw_w=state.get("draw_w"), cap_path=self.state.slow_cap_path)
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
        # The session ceiling is whatever the user/QAM had selected when
        # Governor claimed the controls. Governor never raises beyond it.
        slow = min(slow, self.state.initial_slow_uw)
        fast = min(fast, self.state.initial_fast_uw)
        try:
            self._write_value(self._slow_path, slow)
            self._write_value(self._fast_path, fast)
        except OSError as error:
            self.state.error = str(error)
            return {"success": False, "error": str(error), "state": self.status()}
        read_slow = _read_int(self._slow_path)
        read_fast = _read_int(self._fast_path)
        if read_slow != slow or read_fast != fast:
            self.state.error = "PPT write did not verify"
            self.state.owned = False
            return {"success": False, "error": self.state.error, "state": self.status()}
        self.state.expected_slow_uw = slow
        self.state.expected_fast_uw = fast
        self.state.error = None
        return {"success": True, "error": None, "state": self.status()}

    def restore_if_owned(self) -> Dict[str, Any]:
        result = self._restore_if_owned()
        if result.get("restored") or not result.get("success", True):
            self._note("tdp-restore", restored=result.get("restored"), reason=result.get("reason"),
                       error=result.get("error"), observed_w=(result.get("state") or {}).get("observed_tdp_w"))
        return result

    def _restore_if_owned(self) -> Dict[str, Any]:
        if not self.state.owned:
            return {"success": True, "restored": False, "reason": "not-owned", "state": self.status()}
        if not self._verify_ownership():
            return {"success": True, "restored": False, "reason": "external-change", "state": self.status()}
        assert self._fast_path is not None and self._slow_path is not None
        assert self.state.initial_fast_uw is not None and self.state.initial_slow_uw is not None
        try:
            self._write_value(self._slow_path, self.state.initial_slow_uw)
            self._write_value(self._fast_path, self.state.initial_fast_uw)
        except OSError as error:
            self.state.error = str(error)
            return {"success": False, "restored": False, "error": str(error), "state": self.status()}
        self.state.expected_fast_uw = self.state.initial_fast_uw
        self.state.expected_slow_uw = self.state.initial_slow_uw
        self.state.owned = False
        self.state.error = None
        return {"success": True, "restored": True, "reason": "restored", "state": self.status()}

    def verify_ownership(self) -> Dict[str, Any]:
        """Check that external Steam/QAM tooling has not changed our caps."""
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
