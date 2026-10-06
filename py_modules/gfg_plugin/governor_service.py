"""Live orchestration service for GFG Governor v0.0.1 Beta."""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from shared_config import FG_BACKEND_GFG
from .constants import PRESENT_DIAGNOSTICS_LOG_FILENAME
from .governor_core import OperatingPointPlanner, PowerSearch
from .governor_power import SteamDeckPowerActuator
from .governor_telemetry import TelemetryObserver


class GovernorService:
    """Observe, prove, plan, optimize TDP, then lock.

    v0.0.1 Beta deliberately does not rewrite saved multiplier/scale/profile
    fields.  Automatic TDP optimization is allowed only when the *observed*
    running cadence already matches the planner's proven operating point.
    """

    LOOP_SECONDS = 1.0
    DISPLAY_REFRESH_SECONDS = 10.0
    WINDOW_SECONDS = 12.0
    MIN_SAMPLES = 8
    MIN_SAMPLE_SPAN_SECONDS = 4.0
    MAX_SAMPLE_AGE_MS = 2500.0

    def __init__(self, configuration_service: Any, gamescope_display_service: Any, logger: Any) -> None:
        self.configuration = configuration_service
        self.display = gamescope_display_service
        self.log = logger
        disk = self.configuration.config_dir / PRESENT_DIAGNOSTICS_LOG_FILENAME
        self.observer = TelemetryObserver(
            disk,
            Path("/dev/shm/gfg-present-diagnostics.log"),
        )
        self.planner = OperatingPointPlanner()
        self.power = SteamDeckPowerActuator()
        self.search = PowerSearch()
        self.settings_path = self.configuration.config_dir / "gfg-governor.json"
        self.events_path = self.configuration.runtime_state_dir / "governor-events.jsonl"
        self.diagnostics_marker_path = self.configuration.runtime_state_dir / "governor-diagnostics.enabled"
        self._settings = self._load_settings()
        self._status: Dict[str, Any] = self._base_status()
        self._stop = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_display: Dict[str, Any] = {}
        self._last_display_poll = 0.0
        self._active_profile = ""
        self._evaluation_after_seq = 0
        self._last_event_key = ""

    def _base_status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "version": "0.0.1-beta.2",
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
            "power": self.power.status(),
            "power_search": self.search.status.to_dict(),
            "limitations": [
                "v0.0.1 Beta.2 keeps saved profiles separate from Governor runtime decisions",
                "automatic TDP control requires writable Steam Deck fastPPT/slowPPT sysfs controls",
                "enabling Governor diagnostics takes effect for a newly launched managed game",
            ],
        }

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

    def _profile_enabled(self, profile: str) -> bool:
        value = self._settings.get("profiles", {}).get(profile, {})
        return bool(value.get("enabled", False)) if isinstance(value, dict) else False

    def _any_profile_enabled(self) -> bool:
        profiles = self._settings.get("profiles", {})
        return isinstance(profiles, dict) and any(
            isinstance(value, dict) and bool(value.get("enabled", False))
            for value in profiles.values()
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
        if not enabled and profile == self._active_profile:
            # Live task will restore owned TDP on the next iteration.  The RPC
            # never races a sysfs write from a background to_thread operation.
            self._status["enabled"] = False
            self._status["state"] = "DISABLING"
            self._status["reason"] = "user-disabled"
        return {"success": True, "error": None, "enabled": bool(enabled), "profile": profile}

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
            # Cheap bounded journal: trim only after 2 MiB.
            if self.events_path.stat().st_size > 2 * 1024 * 1024:
                lines = self.events_path.read_text(encoding="utf-8", errors="replace").splitlines()[-1000:]
                temp = self.events_path.with_suffix(".tmp")
                temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
                temp.replace(self.events_path)
        except OSError as error:
            self.log.debug("Governor event journal unavailable: %s", error)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        try:
            await asyncio.to_thread(self._sync_diagnostics_marker)
        except OSError as error:
            self.log.warning("Governor could not prepare diagnostics marker: %s", error)
        await asyncio.to_thread(self.power.discover)
        self._task = asyncio.create_task(self._loop())

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
        value["power"] = self.power.status()
        value["power_search"] = self.search.status.to_dict()
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

    @staticmethod
    def _matches(point: Dict[str, Any], summary: Dict[str, Any]) -> bool:
        latest = summary.get("latest") or {}
        mult = latest.get("effective_multiplier")
        output = (summary.get("output") or {}).get("median")
        p5 = (summary.get("real") or {}).get("p5")
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (mult, output, p5)):
            return False
        return (
            abs(float(mult) - float(point["multiplier"])) <= 0.22
            and float(output) >= float(point["target_output_fps"]) * 0.94
            and float(p5) >= float(point["base_target_fps"]) * 1.05
            and int(point["render_scale_pct"]) == 100
        )

    async def _disable_current(self, reason: str) -> None:
        restored = await asyncio.to_thread(self.power.restore_if_owned)
        if restored.get("restored"):
            self._event("power-restored", reason)
        self.search = PowerSearch()
        self._evaluation_after_seq = self.observer.sample_seq
        self._status.update({
            "state": "DISABLED",
            "reason": reason,
            "recommended_point": None,
            "recommendation_proven": False,
            "active_point_matches": False,
        })

    async def _iteration(self) -> None:
        profile, response = await asyncio.to_thread(self.configuration.get_current_profile_snapshot)
        config = response.get("config") if isinstance(response, dict) else None
        if not profile or not isinstance(config, dict):
            self._status.update({"state": "PAUSED", "reason": "profile-unavailable", "profile": profile or ""})
            return
        if profile != self._active_profile:
            await self._disable_current("profile-changed")
            self._active_profile = profile
            self._evaluation_after_seq = self.observer.sample_seq
        enabled = self._profile_enabled(profile)
        self._status.update({"profile": profile, "enabled": enabled})
        if not enabled:
            if self.power.state.owned or self._status.get("state") != "DISABLED":
                await self._disable_current("governor-disabled")
            return
        if config.get("fg_backend", FG_BACKEND_GFG) != FG_BACKEND_GFG:
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            self._status.update({"state": "OBSERVE_ONLY", "reason": "external-fg-backend"})
            return

        await asyncio.to_thread(self.observer.poll)
        snapshot = self.observer.snapshot()
        summary = self.observer.summary(self.WINDOW_SECONDS)
        display = await self._display_info()
        external = bool(display.get("external", False))
        target = 60 if external else 90
        self._status.update({
            "target_output_fps": target,
            "display": {
                "external": external,
                "internal": bool(display.get("internal", not external)),
                "valid_rates": display.get("valid_rates", []),
            },
            "telemetry": {"snapshot": snapshot, "summary": summary},
        })
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

        decision = self.planner.recommend(
            external_display=external,
            observed_p5_fps=(summary.get("real") or {}).get("p5"),
            observed_multiplier=(summary.get("multiplier") or {}).get("median"),
        )
        point = decision.point.to_dict() if decision.point else None
        matches = bool(point and decision.proven and self._matches(point, summary))
        self._status.update({
            "recommended_point": point,
            "recommendation_proven": decision.proven,
            "recommendation_reason": decision.reason,
            "active_point_matches": matches,
        })
        if point is None:
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            self._status.update({"state": "PLAN", "reason": "target-not-proven-viable"})
            return
        if not matches:
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            self._status.update({"state": "PLAN", "reason": "operating-point-recommended-not-yet-applied"})
            return

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
            self._event("power-search-start", "operating-point-confirmed", profile=profile, point=point)
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
            self._status.update({"state": self.search.status.state.upper(), "reason": "evaluating-current-power"})
            return
        outcome = self.search.evaluate(
            p5_fps=(fresh.get("real") or {}).get("p5"),
            base_target_fps=float(point["base_target_fps"]),
            hard_pressure=int(fresh.get("hard_pressure") or 0),
            misses=int(fresh.get("misses") or 0),
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
        state = self.search.status.state.upper()
        self._status.update({"state": state, "reason": self.search.status.reason})
        if state == "LOCKED":
            self._event("operating-point-locked", self.search.status.reason, profile=profile, point=point, tdp_w=self.search.status.current_tdp_w)

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._iteration()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.log.warning("Governor iteration failed: %s", error)
                self._status.update({"state": "PAUSED", "reason": "iteration-error", "error": str(error)})
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.LOOP_SECONDS)
            except asyncio.TimeoutError:
                pass
