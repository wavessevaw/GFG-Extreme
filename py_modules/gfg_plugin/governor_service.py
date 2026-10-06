"""Live orchestration service for GFG Governor (v0.0.2).

Observe -> prove -> choose -> apply (runtime overlay) -> confirm -> optimise
power -> lock -> intervene only on fresh evidence.

Hard rules enforced here:

* Saved Profile is never written.  Operating points are applied through a
  per-profile runtime overlay (see ``governor_overlay``).
* Writing the overlay is *not* application.  A point counts as applied only after
  fresh renderer evidence that postdates the write (own request/event
  correlation - ``event_seq`` and ``sample_seq`` are different counters).
* An unconfirmed or unhealthy point is rolled back.
* Disable / unload / profile switch first restore the overlay to the Saved
  projection (verified read-back), then release ownership.
* Power search runs only on a confirmed (or positively adopted) point.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from shared_config import FG_BACKEND_GFG
from .constants import PRESENT_DIAGNOSTICS_LOG_FILENAME
from .governor_core import (
    multiplier_tolerance,
    EffortEstimator, OperatingPoint, OperatingPointPlanner, PowerSearch, TrialLadder, raw_effort,
)
from .governor_battery import BatteryEstimator, read_battery
from .governor_hud import HudWriter, normalize as hud_normalize
from .governor_overlay import (
    OverlayRecord,
    OverlayStore,
    PointNotApplicable,
    base_deltas,
    point_deltas,
)
from .governor_device import detect_model, target_for
from .governor_power import SteamDeckPowerActuator
from .governor_telemetry import TelemetryObserver

APPLIED_OPERATIONS = frozenset({"runtime-state-applied", "runtime-transition-applied"})
FAILED_OPERATIONS = frozenset({"runtime-transition-failed"})
VERSION = "0.0.2"


@dataclass
class Request:
    """One pending Operating Point application (own correlation, not sample_seq)."""

    request_id: int
    point: OperatingPoint
    deltas: Dict[str, Any]
    previous_deltas: Dict[str, Any]
    revision: int
    created: float
    event_mark: int
    generation: int
    external: bool
    stage: str = "confirming"  # confirming -> trial
    confirmation_mode: str = ""
    window_floor_event_seq: int = 0
    confirmed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "point": self.point.key,
            "stage": self.stage,
            "revision": self.revision,
            "event_mark": self.event_mark,
            "confirmation_mode": self.confirmation_mode,
        }


POWER_STATE_NAMES = {"optimizing": "OPTIMIZE_POWER", "locked": "LOCKED", "guard": "GUARD"}


def _power_state_name(state: str) -> str:
    return POWER_STATE_NAMES.get(str(state).lower(), str(state).upper())


class GovernorService:
    LOOP_SECONDS = 1.0
    IDLE_LOOP_SECONDS = 5.0  # nothing enabled: do (almost) nothing
    DISPLAY_REFRESH_SECONDS = 10.0
    LAUNCH_REFRESH_SECONDS = 5.0
    WINDOW_SECONDS = 12.0
    MIN_SAMPLES = 8
    MIN_SAMPLE_SPAN_SECONDS = 4.0
    MAX_SAMPLE_AGE_MS = 2500.0
    CONFIRM_TIMEOUT_SECONDS = 25.0
    TRIAL_MIN_SPAN_SECONDS = 8.0
    TRIAL_TIMEOUT_SECONDS = 60.0
    MULTIPLIER_TOLERANCE = 0.22
    CAP_BOUND_HEALTH_RATIO = 0.97
    UNCAPPED_HEALTH_RATIO = 1.05
    ROLLBACK_RETRY_SECONDS = 5.0

    def __init__(
        self,
        configuration_service: Any,
        gamescope_display_service: Any,
        logger: Any,
        pipeline_inspector: Any = None,
    ) -> None:
        self.configuration = configuration_service
        self.display = gamescope_display_service
        self.log = logger
        self.inspector = pipeline_inspector
        disk = self.configuration.config_dir / PRESENT_DIAGNOSTICS_LOG_FILENAME
        self.observer = TelemetryObserver(disk, Path("/dev/shm/gfg-present-diagnostics.log"))
        self.planner = OperatingPointPlanner()
        self.power = SteamDeckPowerActuator()
        self.search = PowerSearch()
        self.settings_path = self.configuration.config_dir / "gfg-governor.json"
        self.events_path = self.configuration.runtime_state_dir / "governor-events.jsonl"
        self.diagnostics_marker_path = self.configuration.runtime_state_dir / "governor-diagnostics.enabled"
        self._settings = self._load_settings()
        builder = getattr(self.configuration, "build_governor_overlay_text", None)
        self.overlay: Optional[OverlayStore] = (
            OverlayStore(self.configuration.config_dir, builder) if callable(builder) else None
        )
        self.hud = HudWriter(self.configuration.config_dir)
        self._battery = BatteryEstimator()
        self.battery_reader = read_battery
        self._io_lock = threading.RLock()
        self._forced_release: set[str] = set()
        self._restore_pending: Dict[str, str] = {}
        self._status: Dict[str, Any] = self._base_status()
        self._stop = asyncio.Event()
        self._wake: Optional[asyncio.Event] = None
        self._wake_loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None
        self._last_display: Dict[str, Any] = {}
        self._last_display_poll = 0.0
        self._active_profile = ""
        self._evaluation_after_seq = 0
        self._last_event_key = ""
        self._device: Optional[Dict[str, str]] = None
        self._reset_run_state()

    # ------------------------------------------------------------------ state
    def _reset_run_state(self) -> None:
        self._point: Optional[Dict[str, Any]] = None
        self._point_mode = ""
        self._effort = getattr(self, "_effort", None) or EffortEstimator()
        self._effort.reset()
        self._exhausted = False
        self._point_external: Optional[bool] = None
        self._point_deltas: Dict[str, Any] = {}
        self._request: Optional[Request] = None
        self._request_counter = getattr(self, "_request_counter", 0)
        self._ladder: Optional[TrialLadder] = None
        self._rollback_deltas: Optional[Dict[str, Any]] = None
        self._rollback_at = 0.0
        self._generation_seen: Optional[int] = None
        self._launch_key: Any = None
        self._launch: Dict[str, Any] = {}
        self._launch_polled = -1e9
        self._saved_fp: Any = None
        self._record: Optional[OverlayRecord] = None
        self._synced_deltas: Optional[Dict[str, Any]] = None

    def _clock(self) -> float:
        return float(self.observer.time_fn())

    def _base_status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "version": f"{VERSION}",
            "enabled": False,
            "state": "DISABLED",
            "reason": "governor-disabled",
            "profile": "",
            "target_output_fps": None,
            "display": {},
            "telemetry": {},
            "recommended_point": None,
            "recommendation_proven": False,
            "active_point_matches": False,
            "active_point": None,
            "active_point_mode": "",
            "overlay": {"available": self.overlay is not None if hasattr(self, "overlay") else False},
            "request": None,
            "capability": {},
            "ladder": None,
            "power": self.power.status(),
            "power_search": self.search.status.to_dict(),
            "limitations": [
                "Saved profiles are never written; operating points use a runtime overlay",
                "automatic TDP control requires writable Steam Deck fastPPT/slowPPT sysfs controls",
                "a game must be (re)launched after Governor is enabled to use the overlay and diagnostics",
                "Native-FPS points need renderer telemetry that may not exist while FG is off",
            ],
        }

    # --------------------------------------------------------------- settings
    def _load_settings(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("schema") == 1 and isinstance(value.get("profiles"), dict):
                return value
        except (OSError, ValueError, TypeError, UnicodeError):
            pass
        return {"schema": 1, "profiles": {}}

    def _save_settings(self) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.settings_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(self.settings_path)

    def _profile_settings(self, profile: str) -> Dict[str, Any]:
        value = self._settings.get("profiles", {}).get(profile, {})
        return value if isinstance(value, dict) else {}

    def _profile_enabled(self, profile: str) -> bool:
        return bool(self._profile_settings(profile).get("enabled", False))

    def _update_battery(self) -> None:
        try:
            self._status["battery"] = self._battery.update(self.battery_reader())
        except Exception as error:  # sysfs quirks must never break the loop
            self.log.debug("Governor battery read failed: %s", error)

    def _delivering_target(self, telemetry: Dict[str, Any]) -> Optional[str]:
        """'easy'/'medium' when measured output already holds the target (stable game), else None."""
        target = self._status.get("target_output_fps") or ((self._ladder.target_output_fps) if self._ladder else None)
        output = (telemetry.get("output") or {}).get("median")
        real = (telemetry.get("real") or {}).get("median")
        p5 = (telemetry.get("output") or {}).get("p5")
        try:
            if not target or output is None or float(output) < 0.95 * float(target):
                return None
            if p5 is not None and float(p5) < 0.85 * float(target):
                return None
            ratio = float(output) / float(real) if real else 1.0
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return "easy" if ratio <= 1.5 else "medium"

    def _update_effort(self) -> None:
        """Feed the slow effort rating.  Never published while still assessing."""
        status = self._status
        telemetry = status.get("telemetry") or {}
        telemetry = telemetry.get("summary") or telemetry  # service stores {"snapshot", "summary"}
        stable = self._delivering_target(telemetry)
        if not status.get("enabled") or status.get("state") not in ("LOCKED", "OPTIMIZE_POWER", "GUARD", "OBSERVE_ONLY"):
            if self._exhausted and status.get("enabled"):
                # A game that already holds the target is not a nightmare just because
                # no Governor point was accepted.
                raw = stable or "nightmare"
            else:
                raw = None
        else:
            real = (telemetry.get("real") or {}).get("median")
            raw = raw_effort(self._point, real, self._exhausted and not stable)
        self._effort.update(self._clock(), raw)

    def hud_settings(self, profile: str) -> Dict[str, Any]:
        raw = self._profile_settings(profile).get("hud") or {}
        preset, position = hud_normalize(raw.get("preset"), raw.get("position"))
        return {"enabled": bool(raw.get("enabled", False)), "preset": preset, "position": position}

    def set_hud(self, profile: str, enabled: Any = None, preset: Any = None, position: Any = None) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        current = self.hud_settings(profile)
        if enabled is not None:
            current["enabled"] = bool(enabled)
        current["preset"], current["position"] = hud_normalize(
            preset if preset is not None else current["preset"],
            position if position is not None else current["position"],
        )
        self._settings.setdefault("profiles", {}).setdefault(profile, {})["hud"] = current
        self._save_settings()
        self._sync_hud(profile)
        self._poke()
        return {"success": True, "error": None, "hud": current, "relaunch_required": True}

    def _sync_hud(self, profile: str) -> None:
        """Publish/remove the active HUD config and keep the status line fresh."""
        try:
            settings = self.hud_settings(profile)
            if settings["enabled"]:
                self.hud.activate(settings["preset"], settings["position"])
                self.hud.write_status(self._status, settings["preset"])
            else:
                self.hud.deactivate()
        except OSError as error:
            self.log.debug("Governor HUD sync failed: %s", error)

    def _scale_ready(self, profile: str) -> bool:
        return bool(self._profile_settings(profile).get("scale_ready", False))

    def _poke(self) -> None:
        """Wake an idle loop right away (callable from worker threads)."""
        loop, wake = self._wake_loop, self._wake
        if loop is not None and wake is not None:
            try:
                loop.call_soon_threadsafe(wake.set)
            except RuntimeError:
                pass

    def _is_idle(self) -> bool:
        profiles = self._settings.get("profiles", {})
        hud_on = isinstance(profiles, dict) and any(
            isinstance(v, dict) and bool((v.get("hud") or {}).get("enabled", False)) for v in profiles.values()
        )
        return not (self._any_profile_enabled() or hud_on or self._restore_pending or self._forced_release
                    or self._point or self._request)

    def _any_profile_enabled(self) -> bool:
        profiles = self._settings.get("profiles", {})
        return isinstance(profiles, dict) and any(
            isinstance(value, dict) and bool(value.get("enabled", False)) for value in profiles.values()
        )

    def _sync_diagnostics_marker(self) -> None:
        self.diagnostics_marker_path.parent.mkdir(parents=True, exist_ok=True)
        if self._any_profile_enabled():
            temp = self.diagnostics_marker_path.with_suffix(".tmp")
            temp.write_text("enabled\n", encoding="utf-8")
            os.chmod(temp, 0o600)
            temp.replace(self.diagnostics_marker_path)
            return
        try:
            self.diagnostics_marker_path.unlink()
        except FileNotFoundError:
            pass

    # ---------------------------------------------------------- overlay (I/O)
    def _saved_profile_config(self, profile: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.configuration.get_profile_config(profile)
        except Exception as error:  # pragma: no cover - defensive
            self.log.debug("Governor could not read saved profile %s: %s", profile, error)
            return None
        config = response.get("config") if isinstance(response, dict) else None
        return config if isinstance(config, dict) else None

    def _base_for(self, profile: str, saved: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if saved is None:
            return {}
        try:
            return base_deltas(saved, scale_ready=self._scale_ready(profile))
        except PointNotApplicable as error:
            self._status.setdefault("overlay", {})["scale_ready_ignored"] = error.reason
            return {}

    def _write_overlay_sync(
        self, profile: str, deltas: Dict[str, Any], point_key: str, released: bool = False
    ) -> OverlayRecord:
        if self.overlay is None:
            raise OSError("overlay-unsupported")
        with self._io_lock:
            return self.overlay.write(profile, deltas, point_key=point_key, released=released)

    def _restore_overlay_sync(self, profile: str) -> Optional[str]:
        """Restore ``profile``'s overlay to the Saved projection and release the lease.

        Returns an error string, or None when restored and verified.  Nothing
        is removed: a running game keeps a valid (Saved) file to watch.
        """
        if self.overlay is None or not self.overlay.exists(profile):
            return None
        try:
            saved = self._saved_profile_config(profile)
            self._write_overlay_sync(profile, self._base_for(profile, saved), "released", released=True)
        except (OSError, ValueError) as error:
            return str(error)
        return None

    def set_enabled(self, profile: str, enabled: bool) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        profiles = self._settings.setdefault("profiles", {})
        value = profiles.setdefault(profile, {})
        value["enabled"] = bool(enabled)
        self._save_settings()
        try:
            self._sync_diagnostics_marker()
        except OSError as error:
            self.log.warning("Governor could not update diagnostics marker: %s", error)
        overlay_error: Optional[str] = None
        if enabled:
            overlay_error = self._ensure_base_overlay_sync(profile)
        else:
            # Invariant: restore overlay to Saved (verified) BEFORE ownership is
            # released.  The live loop then clears point/power state.
            overlay_error = self._restore_overlay_sync(profile)
            if overlay_error:
                self._restore_pending[profile] = "user-disabled"
            self._forced_release.add(profile)
            if profile == self._active_profile:
                self._status["enabled"] = False
                self._status["state"] = "DISABLING"
                self._status["reason"] = "user-disabled"
        self._poke()
        result: Dict[str, Any] = {"success": True, "error": None, "enabled": bool(enabled), "profile": profile}
        if overlay_error:
            result["overlay_error"] = overlay_error
        return result

    def set_scale_ready(self, profile: str, scale_ready: bool) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        value = self._settings.setdefault("profiles", {}).setdefault(profile, {})
        value["scale_ready"] = bool(scale_ready)
        self._save_settings()
        error = self._ensure_base_overlay_sync(profile) if self._profile_enabled(profile) else None
        return {
            "success": True, "error": None, "scale_ready": bool(scale_ready), "profile": profile,
            "relaunch_required": True, **({"overlay_error": error} if error else {}),
        }

    def _ensure_base_overlay_sync(self, profile: str) -> Optional[str]:
        if self.overlay is None:
            return "overlay-unsupported"
        try:
            saved = self._saved_profile_config(profile)
            if saved is None:
                return "saved-profile-unavailable"
            self._write_overlay_sync(profile, self._base_for(profile, saved), "base")
        except (OSError, ValueError) as error:
            self.log.warning("Governor could not write base overlay for %s: %s", profile, error)
            return str(error)
        return None

    # ----------------------------------------------------------------- events
    def _event(self, event: str, reason: str, **fields: Any) -> None:
        key = json.dumps([event, reason, fields], sort_keys=True, default=str)
        if key == self._last_event_key:
            return
        self._last_event_key = key
        payload = {"ts": time.time(), "event": event, "reason": reason, **fields}
        try:
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
            if self.events_path.stat().st_size > 2 * 1024 * 1024:
                lines = self.events_path.read_text(encoding="utf-8", errors="replace").splitlines()[-1000:]
                temp = self.events_path.with_suffix(".tmp")
                temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
                temp.replace(self.events_path)
        except OSError as error:
            self.log.debug("Governor event journal unavailable: %s", error)

    # -------------------------------------------------------------- lifecycle
    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        try:
            await asyncio.to_thread(self._sync_diagnostics_marker)
        except OSError as error:
            self.log.warning("Governor could not prepare diagnostics marker: %s", error)
        await asyncio.to_thread(self._reconcile_overlays)
        await asyncio.to_thread(self.power.discover)
        self._wake = asyncio.Event()
        self._wake_loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._loop())

    def _reconcile_overlays(self) -> None:
        """After a plugin restart: refresh leases of enabled profiles, restore the rest."""
        if self.overlay is None:
            return
        for profile in list(self._settings.get("profiles", {})):
            if self._profile_enabled(profile):
                error = self._ensure_base_overlay_sync(profile)
            else:
                error = self._restore_overlay_sync(profile)
            if error:
                self._restore_pending[profile] = "startup-reconcile"

    async def stop(self) -> None:
        self._stop.set()
        task = self._task
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            except Exception as error:
                self.log.debug("Governor loop ended with error: %s", error)
        self._task = None
        # Restore overlays to Saved (verified) before power ownership is released.
        for profile in list(self._settings.get("profiles", {})):
            error = await asyncio.to_thread(self._restore_overlay_sync, profile)
            if error:
                self.log.error("Governor could not restore overlay for %s on unload: %s", profile, error)
                self._event("overlay-restore-failed", "plugin-stop", profile=profile, error=error)
        self._reset_run_state()
        try:
            result = await asyncio.to_thread(self.power.restore_if_owned)
            if result.get("restored"):
                self._event("power-restored", "plugin-stop")
        except Exception as error:
            self.log.warning("Governor could not restore owned TDP: %s", error)

    def get_status(self, profile: str = "") -> Dict[str, Any]:
        value = dict(self._status)
        if profile and profile != value.get("profile"):
            value["requested_profile"] = profile
            value["enabled"] = self._profile_enabled(profile)
        value["scale_ready"] = self._scale_ready(profile or value.get("profile", ""))
        value["hud"] = self.hud_settings(profile or value.get("profile", ""))
        value["effort"] = self._effort.status()
        value["power"] = self.power.status()
        value["power_search"] = self.search.status.to_dict()
        value["request"] = self._request.to_dict() if self._request else None
        value["active_point"] = self._point
        value["active_point_mode"] = self._point_mode
        value["ladder"] = self._ladder.status() if self._ladder else None
        if self._restore_pending:
            value["restore_pending"] = dict(self._restore_pending)
        return value

    async def _display_info(self) -> Dict[str, Any]:
        now = time.monotonic()
        if now - self._last_display_poll < self.DISPLAY_REFRESH_SECONDS and self._last_display:
            return self._last_display
        self._last_display_poll = now
        try:
            result = await asyncio.to_thread(self.display.get_active_display_info)
            if isinstance(result, dict) and result.get("success"):
                self._last_display = result
        except Exception as error:
            self.log.debug("Governor display probe unavailable: %s", error)
        return self._last_display

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _matches(point: Dict[str, Any], summary: Dict[str, Any]) -> bool:
        latest = summary.get("latest") or {}
        mult = latest.get("effective_multiplier")
        output = (summary.get("output") or {}).get("median")
        p5 = (summary.get("real") or {}).get("p5")
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (mult, output, p5)):
            return False
        return (
            abs(float(mult) - float(point["multiplier"])) <= multiplier_tolerance(point["multiplier"])
            and float(output) >= float(point["target_output_fps"]) * 0.94
            and float(p5) >= float(point["base_target_fps"]) * 1.05
            and int(point["render_scale_pct"]) == 100
        )

    async def _restore_power(self, reason: str) -> None:
        restored = await asyncio.to_thread(self.power.restore_if_owned)
        if restored.get("restored"):
            self._event("power-restored", reason)
        self.search = PowerSearch()

    def _clear_point_state(self) -> None:
        self._point = None
        self._point_mode = ""
        self._point_external = None
        self._point_deltas = {}
        self._request = None
        self._ladder = None
        self._rollback_deltas = None
        self._synced_deltas = None
        self._evaluation_after_seq = self.observer.sample_seq

    async def _release_point(self, profile: str, reason: str) -> bool:
        """Drop the applied point: overlay back to base (lease kept), power restored."""
        had_runtime = bool(self._point or self._request or self._point_deltas)
        self._clear_point_state()
        await self._restore_power(reason)
        if not had_runtime or self.overlay is None or not self.overlay.exists(profile):
            return True
        saved = await asyncio.to_thread(self._saved_profile_config, profile)
        try:
            await asyncio.to_thread(self._write_overlay_sync, profile, self._base_for(profile, saved), "base")
        except (OSError, ValueError) as error:
            self._rollback_deltas = None
            self._restore_pending[profile] = reason
            self._status.update({"state": "PAUSED", "reason": "overlay-restore-failed", "error": str(error)})
            self._event("overlay-restore-failed", reason, profile=profile, error=str(error))
            return False
        self._event("operating-point-released", reason, profile=profile)
        return True

    async def _release(self, profile: str, reason: str) -> None:
        """Disable/profile-switch/unload path: restore overlay, then release ownership."""
        self._clear_point_state()
        error = await asyncio.to_thread(self._restore_overlay_sync, profile)
        if error:
            self._restore_pending[profile] = reason
            self._status.update({"state": "PAUSED", "reason": "overlay-restore-failed", "error": error})
            self._event("overlay-restore-failed", reason, profile=profile, error=error)
            return  # ownership is NOT released until Saved is restored
        self._restore_pending.pop(profile, None)
        await self._restore_power(reason)
        self._evaluation_after_seq = self.observer.sample_seq
        self._status.update({
            "state": "DISABLED", "reason": reason, "recommended_point": None,
            "recommendation_proven": False, "active_point_matches": False,
        })

    async def _retry_restores(self) -> None:
        for profile, reason in list(self._restore_pending.items()):
            if self._profile_enabled(profile) and reason == "startup-reconcile":
                error = await asyncio.to_thread(self._ensure_base_overlay_sync, profile)
            else:
                error = await asyncio.to_thread(self._restore_overlay_sync, profile)
            if not error:
                self._restore_pending.pop(profile, None)
                self._event("overlay-restore-recovered", reason, profile=profile)

    async def _launch_info(self, profile: str) -> Dict[str, Any]:
        now = self._clock()
        if self.inspector is None:
            return {"running": False, "reason": "no-inspector"}
        if now - self._launch_polled < self.LAUNCH_REFRESH_SECONDS and self._launch:
            return self._launch
        self._launch_polled = now
        try:
            self._launch = await asyncio.to_thread(self.inspector.live_launch, profile)
        except Exception as error:
            self.log.debug("Governor launch probe failed: %s", error)
            self._launch = {"running": False, "reason": "launch-probe-failed"}
        return self._launch

    def _capability(self, profile: str, launch: Dict[str, Any]) -> Dict[str, Any]:
        if self.overlay is None:
            return {"overlay_available": False, "overlay_active": False, "scale_capable": False,
                    "reason": "overlay-unsupported"}
        governor_launch = launch.get("governor_launch") if launch.get("running") else None
        active = bool(governor_launch) and bool(launch.get("renderer_loaded", True))
        scale = bool(active and (governor_launch.get("scaling") == 1 or launch.get("saved_scaling_at_launch")))
        reason = "ok" if active else (
            "relaunch-required-for-governor-overlay" if launch.get("running") else
            ("game-not-running" if self.inspector is not None else "launch-inspector-unavailable")
        )
        return {"overlay_available": True, "overlay_active": active, "scale_capable": scale, "reason": reason}

    # ---------------------------------------------------------- application
    async def _begin_request(
        self, profile: str, saved: Dict[str, Any], point: OperatingPoint, external: bool,
        capability: Dict[str, Any],
    ) -> bool:
        base = self._base_for(profile, saved)
        deltas = point_deltas(
            point.to_dict(), saved,
            scale_capable=bool(capability.get("scale_capable")),
            scale_ready=self._scale_ready(profile),
        )
        full = {**base, **deltas}
        previous = {**base, **self._point_deltas} if self._point_deltas else dict(base)
        await asyncio.to_thread(self.observer.poll)  # absorb backlog: it predates the write
        mark = self.observer.event_seq
        generation = self.observer.session_generation
        try:
            record = await asyncio.to_thread(self._write_overlay_sync, profile, full, point.key)
        except (OSError, ValueError) as error:
            self._status.update({"state": "PAUSED", "reason": "overlay-write-failed", "error": str(error)})
            self._event("overlay-write-failed", "apply", profile=profile, point=point.key, error=str(error))
            return False
        self._request_counter += 1
        self._record = record
        self._ladder.mark_attempt() if self._ladder else None
        self._request = Request(
            request_id=self._request_counter, point=point, deltas=full, previous_deltas=previous,
            revision=record.revision, created=self._clock(), event_mark=mark,
            generation=generation, external=external,
        )
        self._point_deltas_pending = full
        self._event("operating-point-requested", "ladder-trial", profile=profile, point=point.key,
                    revision=record.revision, request_id=self._request_counter)
        self._status.update({"state": "APPLY", "reason": "awaiting-renderer-confirmation"})
        return True

    def _evaluate_confirmation(self, req: Request) -> tuple[str, str]:
        """Return (wait|confirmed|failed, reason).  Never trusts the file write."""
        now = self._clock()
        if self.observer.session_generation != req.generation:
            return "failed", "telemetry-session-changed"
        events = self.observer.application_events_after(req.event_mark)
        if any(event.operation in FAILED_OPERATIONS for event in events):
            return "failed", "renderer-transition-failed"
        applied = [event for event in events if event.operation in APPLIED_OPERATIONS]
        samples = self.observer.samples_after_event(applied[-1].event_seq if applied else req.event_mark)
        want = float(req.point.multiplier)
        tol = multiplier_tolerance(want)
        tail = samples[-self.MIN_SAMPLES:]
        consistent = len(tail) >= self.MIN_SAMPLES and all(
            abs(sample.effective_multiplier - want) <= tol
            or (req.point.multiplier == 1 and sample.effective_multiplier <= 1.12)
            for sample in tail
        )
        if consistent and (tail[-1].monotonic - tail[0].monotonic) >= self.MIN_SAMPLE_SPAN_SECONDS:
            run: list = []
            for sample in reversed(samples):
                if abs(sample.effective_multiplier - want) <= tol or (
                    req.point.multiplier == 1 and sample.effective_multiplier <= 1.12
                ):
                    run.append(sample)
                else:
                    break
            req.window_floor_event_seq = run[-1].event_seq - 1
            req.confirmation_mode = "event+cadence" if applied else "cadence-only"
            req.confirmed_at = now
            return "confirmed", req.confirmation_mode
        if now - req.created > self.CONFIRM_TIMEOUT_SECONDS:
            return "failed", "confirmation-timeout"
        return "wait", "awaiting-fresh-evidence"

    async def _fail_request(self, profile: str, reason: str) -> None:
        req = self._request
        self._request = None
        if req is None:
            return
        if self._ladder is not None:
            self._ladder.reject(req.point.key, reason)
        self._event("operating-point-rejected", reason, profile=profile, point=req.point.key,
                    revision=req.revision, request_id=req.request_id)
        await self._rollback(profile, req.previous_deltas, reason)

    async def _rollback(self, profile: str, deltas: Dict[str, Any], reason: str) -> None:
        try:
            record = await asyncio.to_thread(
                self._write_overlay_sync, profile, deltas, self._point["key"] if self._point else "base"
            )
            self._record = record
            self._rollback_deltas = None
            self._event("overlay-rolled-back", reason, profile=profile, revision=record.revision)
            self._status.update({"state": "PLAN", "reason": f"rolled-back:{reason}"})
        except (OSError, ValueError) as error:
            self._rollback_deltas = dict(deltas)
            self._rollback_at = self._clock()
            self._status.update({"state": "PAUSED", "reason": "rollback-failed", "error": str(error)})
            self._event("overlay-rollback-failed", reason, profile=profile, error=str(error))

    async def _retry_rollback(self, profile: str) -> bool:
        if self._rollback_deltas is None:
            return False
        if self._clock() - self._rollback_at < self.ROLLBACK_RETRY_SECONDS:
            return True
        await self._rollback(profile, self._rollback_deltas, "retry")
        return self._rollback_deltas is not None

    # ------------------------------------------------------------------ loop
    async def _sync_overlay(self, profile: str, saved: Dict[str, Any]) -> None:
        """Keep the overlay equal to Saved + current Governor deltas (lease/saved edits)."""
        if self.overlay is None or self._request is not None or self._rollback_deltas is not None:
            return
        fingerprint = getattr(self.configuration, "saved_config_fingerprint", lambda: None)()
        header = self.overlay.read_header(profile)
        if self._saved_fp is None and header is not None and header.get("owner") == self.overlay.owner_pid:
            self._saved_fp = fingerprint  # first look: overlay was projected at enable/reconcile
            return
        stale = (
            header is None
            or header.get("owner") != self.overlay.owner_pid
            or fingerprint != self._saved_fp
        )
        if not stale:
            return
        base = self._base_for(profile, saved)
        desired = {**base, **self._point_deltas}
        key = self._point["key"] if self._point else "base"
        try:
            self._record = await asyncio.to_thread(self._write_overlay_sync, profile, desired, key)
            self._saved_fp = fingerprint
        except (OSError, ValueError) as error:
            self._status.setdefault("overlay", {})["sync_error"] = str(error)

    async def _iteration(self) -> None:
        await self._iteration_core()
        self._update_effort()
        self._update_battery()
        profile = self._status.get("profile") or ""
        if profile:
            await asyncio.to_thread(self._sync_hud, profile)

    async def _iteration_core(self) -> None:
        profile, response = await asyncio.to_thread(self.configuration.get_current_profile_snapshot)
        config = response.get("config") if isinstance(response, dict) else None
        if not profile or not isinstance(config, dict):
            self._status.update({"state": "PAUSED", "reason": "profile-unavailable", "profile": profile or ""})
            return
        await self._retry_restores()
        for forced in list(self._forced_release):
            self._forced_release.discard(forced)
            if forced == self._active_profile:
                await self._release(forced, "governor-disabled")
        if profile != self._active_profile:
            old = self._active_profile
            if old:
                await self._release(old, "profile-changed")
            else:
                self._clear_point_state()
                await self._restore_power("profile-changed")
            self._active_profile = profile
            self._reset_run_state()
            self._evaluation_after_seq = self.observer.sample_seq
        enabled = self._profile_enabled(profile)
        self._status.update({"profile": profile, "enabled": enabled})
        if not enabled:
            if self.power.state.owned or self._status.get("state") != "DISABLED" or self._point or self._request:
                await self._release(profile, "governor-disabled")
            return
        if config.get("fg_backend", FG_BACKEND_GFG) != FG_BACKEND_GFG:
            if self._point or self._request or self.power.state.owned:
                await self._release_point(profile, "external-fg-backend")
            self._status.update({"state": "OBSERVE_ONLY", "reason": "external-fg-backend"})
            return
        if await self._retry_rollback(profile):
            return
        await self._sync_overlay(profile, config)

        await asyncio.to_thread(self.observer.poll)
        snapshot = self.observer.snapshot()
        summary = self.observer.summary(self.WINDOW_SECONDS)
        display = await self._display_info()
        external = bool(display.get("external", False))
        if self._device is None:
            self._device = await asyncio.to_thread(detect_model)
        policy = target_for(self._device["model"], external=external, valid_rates=display.get("valid_rates"))
        target = int(policy["target"])
        self._status.update({
            "target_output_fps": target,
            "device": {**self._device, "mode": policy["mode"], "target_reason": policy["reason"]},
            "display": {
                "external": external,
                "internal": bool(display.get("internal", not external)),
                "valid_rates": display.get("valid_rates", []),
            },
            "telemetry": {"snapshot": snapshot, "summary": summary},
        })

        # A new telemetry session / launch / display mode invalidates any applied point.
        launch = await self._launch_info(profile)
        launch_key = launch.get("launch_key") if launch.get("running") else None
        generation = snapshot.get("session_generation")
        changed = (
            (self._generation_seen is not None and generation != self._generation_seen)
            or (self._launch_key is not None and launch_key is not None and launch_key != self._launch_key)
            or (self._point_external is not None and external != self._point_external)
        )
        self._generation_seen = generation
        if launch_key is not None:
            self._launch_key = launch_key
        if changed and (self._point or self._request or self._ladder):
            reason = "display-mode-changed" if (
                self._point_external is not None and external != self._point_external
            ) else "new-game-session"
            await self._release_point(profile, reason)
            self._status.update({"state": "PLAN", "reason": reason})
            return

        # Pending application: evaluated before the freshness gate so a silent
        # renderer cannot leave an unconfirmed overlay in place forever.
        req = self._request
        if req is not None:
            verdict, why = self._evaluate_confirmation(req)
            if verdict == "failed":
                await self._fail_request(profile, why)
                return
            if verdict == "wait":
                self._status.update({"state": "APPLY", "reason": why})
                return
            if req.stage == "confirming":
                req.stage = "trial"
                self._event("operating-point-confirmed", req.confirmation_mode, profile=profile,
                            point=req.point.key, revision=req.revision, request_id=req.request_id)
            fresh = self.observer.summary(
                self.WINDOW_SECONDS * 2, after_event_seq=req.window_floor_event_seq,
            )
            if self._ladder is None:  # defensive; requests are only created by the ladder
                self._ladder = TrialLadder(external_display=external, target_output_fps=target)
            outcome = self._ladder.evaluate(
                req.point, fresh, min_samples=self.MIN_SAMPLES, min_span_s=self.TRIAL_MIN_SPAN_SECONDS,
            )
            if outcome.verdict == "wait":
                if self._clock() - req.confirmed_at > self.TRIAL_TIMEOUT_SECONDS:
                    await self._fail_request(profile, "trial-evidence-timeout")
                else:
                    self._status.update({"state": "APPLY", "reason": outcome.reason})
                return
            if outcome.verdict == "reject":
                await self._fail_request(profile, outcome.reason)
                return
            # accepted
            self._point = req.point.to_dict()
            self._point_mode = "applied"
            self._point_external = req.external
            self._point_deltas = {k: v for k, v in req.deltas.items()}
            self._request = None
            self._evaluation_after_seq = self.observer.sample_seq
            self._event("operating-point-applied", outcome.reason, profile=profile, point=self._point,
                        revision=req.revision, confirmation=req.confirmation_mode)
            self.search = PowerSearch()
            self._status.update({"state": "PLAN", "reason": "operating-point-confirmed",
                                 "recommended_point": self._point, "recommendation_proven": True,
                                 "active_point_matches": True})
            return

        if not snapshot.get("available") or (snapshot.get("sample_age_ms") or 10**9) > self.MAX_SAMPLE_AGE_MS:
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            telemetry_reason = "waiting-for-fps-events"
            path = str(snapshot.get("path") or "")
            if snapshot.get("last_poll_error"):
                telemetry_reason = "diagnostics-log-unavailable"
            elif not path:
                telemetry_reason = "diagnostics-path-unavailable"
            elif snapshot.get("event_seq", 0) == 0:
                telemetry_reason = "diagnostics-active-no-events"
            elif snapshot.get("sample_seq", 0) == 0:
                telemetry_reason = "diagnostics-events-no-fps-samples"
            else:
                telemetry_reason = "telemetry-stale"
            self._status.update({"state": "PAUSED", "reason": telemetry_reason})
            return
        if summary.get("samples", 0) < self.MIN_SAMPLES or summary.get("sample_span_s", 0.0) < self.MIN_SAMPLE_SPAN_SECONDS:
            self._status.update({"state": "PROBE", "reason": "collecting-fresh-evidence"})
            return

        if self._point is None:
            decision = self.planner.recommend(
                external_display=external,
                target_output_fps=target,
                observed_p5_fps=(summary.get("real") or {}).get("p5"),
                observed_multiplier=(summary.get("multiplier") or {}).get("median"),
            )
            candidate = decision.point.to_dict() if decision.point else None
            adopt = bool(candidate and decision.proven and self._matches(candidate, summary))
            self._status.update({
                "recommended_point": candidate,
                "recommendation_proven": decision.proven,
                "recommendation_reason": decision.reason,
                "active_point_matches": adopt,
            })
            if adopt:
                # The running cadence already IS a proven point (uncapped
                # headroom evidence): adopt it without touching the overlay.
                self._point = candidate
                self._point_mode = "adopted"
                self._point_external = external
                self._evaluation_after_seq = self.observer.sample_seq
                self._event("operating-point-adopted", decision.reason, profile=profile, point=candidate)
            else:
                await self._plan_trial(profile, config, external, target)
                return

        await self._power_step(profile, summary)

    async def _plan_trial(
        self, profile: str, config: Dict[str, Any], external: bool, target: int,
    ) -> None:
        if self.overlay is None:
            if self._status.get("recommended_point") is None:
                self._status.update({"state": "PLAN", "reason": "target-not-proven-viable"})
            else:
                self._status.update({"state": "PLAN", "reason": "operating-point-recommended-not-yet-applied"})
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            return
        if self.power.state.owned:
            await asyncio.to_thread(self.power.restore_if_owned)
        launch = await self._launch_info(profile)
        capability = self._capability(profile, launch)
        self._status["capability"] = capability
        if not capability["overlay_active"]:
            self._status.update({"state": "PLAN", "reason": capability["reason"]})
            return
        if self._ladder is None:
            self._ladder = TrialLadder(external_display=external, target_output_fps=target)

        saved = await asyncio.to_thread(self._saved_profile_config, profile) or config

        def applicable(point: OperatingPoint) -> Optional[str]:
            try:
                point_deltas(point.to_dict(), saved, scale_capable=bool(capability["scale_capable"]),
                             scale_ready=self._scale_ready(profile))
            except PointNotApplicable as error:
                return error.reason
            return None

        point = self._ladder.next_point(applicable)
        if point is None:
            released = await self._release_point_keep_ladder(profile)
            if released:
                self._status.update({"state": "PLAN", "reason": "target-not-proven-viable"})
            return
        if not await self._begin_request(profile, saved, point, external, capability):
            return

    async def _release_point_keep_ladder(self, profile: str) -> bool:
        ladder = self._ladder
        ok = await self._release_point(profile, "ladder-exhausted")
        self._ladder = ladder  # remember rejections: no re-trial until the session changes
        self._exhausted = True
        return ok

    async def _power_step(self, profile: str, summary: Dict[str, Any]) -> None:
        point = self._point
        assert point is not None
        health_ratio = self.CAP_BOUND_HEALTH_RATIO if self._point_mode == "applied" else self.UNCAPPED_HEALTH_RATIO
        if not self.power.state.available:
            self._status.update({"state": "OBSERVE_ONLY", "reason": "tdp-control-unavailable"})
            return
        if not self.power.state.owned:
            claimed = await asyncio.to_thread(self.power.claim)
            if not claimed.get("owned"):
                self._status.update({"state": "OBSERVE_ONLY", "reason": "tdp-control-unavailable"})
                return
            current = claimed.get("current_tdp_w") or claimed.get("observed_tdp_w")
            minimum = claimed.get("minimum_tdp_w") or 3.0
            ceiling = claimed.get("ceiling_tdp_w") or current
            if not isinstance(current, (int, float)) or not isinstance(ceiling, (int, float)):
                self._status.update({"state": "OBSERVE_ONLY", "reason": "tdp-cap-values-unavailable"})
                return
            self.search.begin(current_tdp_w=float(current), min_tdp_w=float(minimum), ceiling_tdp_w=float(ceiling))
            self._evaluation_after_seq = self.observer.sample_seq
            self._event("power-search-start", "operating-point-confirmed", profile=profile, point=point,
                        mode=self._point_mode)
            self._status.update({"state": "OPTIMIZE_POWER", "reason": "power-search-started"})
            return

        # If another controller changed PPT while Governor was active, release
        # ownership and do not fight it.
        power_status = await asyncio.to_thread(self.power.verify_ownership)
        if power_status.get("external_change"):
            self._status.update({"state": "PAUSED", "reason": "external-tdp-change"})
            return

        fresh = self.observer.summary(self.WINDOW_SECONDS, after_seq=self._evaluation_after_seq)
        if fresh.get("samples", 0) < self.MIN_SAMPLES or fresh.get("sample_span_s", 0.0) < self.MIN_SAMPLE_SPAN_SECONDS:
            self._status.update({"state": _power_state_name(self.search.status.state), "reason": "evaluating-current-power"})
            return
        outcome = self.search.evaluate(
            p5_fps=(fresh.get("real") or {}).get("p5"),
            base_target_fps=float(point["base_target_fps"]),
            hard_pressure=int(fresh.get("hard_pressure") or 0),
            misses=int(fresh.get("misses") or 0),
            health_ratio=health_ratio,
        )
        action = outcome.get("action")
        if action == "set":
            target_w = float(outcome["target_tdp_w"])
            result = await asyncio.to_thread(self.power.set_tdp_w, target_w)
            if not result.get("success"):
                self._status.update({"state": "PAUSED", "reason": "tdp-write-failed"})
                return
            self._evaluation_after_seq = self.observer.sample_seq
            self._event("tdp-set", self.search.status.reason, watts=target_w, profile=profile)
        state = _power_state_name(self.search.status.state)
        self._status.update({"state": state, "reason": self.search.status.reason})
        if state == "LOCKED":
            self._event("operating-point-locked", self.search.status.reason, profile=profile, point=point,
                        tdp_w=self.search.status.current_tdp_w)

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._iteration()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.log.warning("Governor iteration failed: %s", error)
                self._status.update({"state": "PAUSED", "reason": "iteration-error", "error": str(error)})
            timeout = self.IDLE_LOOP_SECONDS if self._is_idle() else self.LOOP_SECONDS
            wake = self._wake
            if wake is not None:
                wake.clear()
            waiters = [asyncio.ensure_future(self._stop.wait())]
            if wake is not None:
                waiters.append(asyncio.ensure_future(wake.wait()))
            try:
                await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for waiter in waiters:
                    waiter.cancel()
