"""
Main plugin class for the GFG Extreme Loader plugin.

This plugin provides services for installing and managing the GFG Engine
Vulkan layer for frame generation and scaling on SteamOS.
"""

import os
import asyncio
import hashlib
import shlex
import json
from typing import Dict, Any, Optional
from pathlib import Path

import decky

from .installation import InstallationService
from .dll_detection import DllDetectionService
from .configuration import ConfigurationService
from .runtime_state import RuntimeStateService
from .pipeline_inspector import PipelineInspectorService
from .gamescope_display import GamescopeDisplayService
from .governor_service import GovernorService
from .session_recorder import SessionRecorder
from .config_schema import ConfigurationManager, DEFAULT_PROFILE_NAME
from shared_config import FG_BACKEND_GFG
from .config_schema_generated import ConfigurationPatch
from .flatpak_service import (
    FlatpakAppInfo,
    FlatpakExtensionStatus,
    FlatpakOverrideResponse,
    FlatpakService,
)
from .types import (
    ConfigSchemaResponse,
    ConfigurationResponse,
    DllDetectionResponse,
    DllStatsResponse,
    FgmodCheckResponse,
    FileContentResponse,
    InstallationCheckResponse,
    InstallationResult,
    LaunchOptionResponse,
    ProfileResponse,
    ProfilesResponse,
    RuntimeStatusResponse,
    ModelStatusResponse,
)


class Plugin:
    """
    Main plugin class for GFG Extreme and GFG Engine management.

    This class provides a unified interface for installation, configuration,
    and DLL detection services. It implements the Decky Loader plugin lifecycle
    methods (_main, _unload, and _uninstall).
    """

    def __init__(self):
        """Initialize the plugin with all necessary services"""
        self.installation_service = InstallationService()
        self.dll_detection_service = DllDetectionService()
        self.configuration_service = ConfigurationService()
        self.runtime_state_service = RuntimeStateService()
        self.pipeline_inspector_service = PipelineInspectorService(self.configuration_service)
        self.flatpak_service = FlatpakService()
        self.gamescope_display_service = GamescopeDisplayService()
        self.governor_service = GovernorService(
            self.configuration_service, self.gamescope_display_service, decky.logger,
            self.pipeline_inspector_service,
        )
        self.session_recorder = self._build_session_recorder()
        self._display_sync_task = None
        self._dock_monitor_task = None
        self._display_io_lock = asyncio.Lock()
        self._dock_policy_lock = asyncio.Lock()
        self._dock_stop_event = asyncio.Event()
        self._dock_state_path = (
            self.configuration_service.config_dir / "gfg-extreme-dock-state.json"
        )
        legacy_dock_state_path = (
            self.configuration_service.config_dir / "mako-extreme-dock-state.json"
        )
        if legacy_dock_state_path.is_file() and not self._dock_state_path.exists():
            try:
                legacy_dock_state_path.replace(self._dock_state_path)
                decky.logger.info("Migrated legacy Dock state to GFG Extreme")
            except OSError as error:
                decky.logger.warning("Could not migrate legacy Dock state: %s", error)

    async def _run_display_call(self, function, *args):
        """Serialize Gamescope/Xwayland calls and keep them off the event loop."""
        async with self._display_io_lock:
            return await asyncio.to_thread(function, *args)

    def _schedule_target_refresh_sync(
            self, target_fps: Any, profile_name: Optional[str] = None
    ) -> None:
        """Debounce Target FPS -> display refresh writes while a slider is moving."""
        try:
            target = int(target_fps)
        except (TypeError, ValueError):
            return

        task = self._display_sync_task
        if task is not None and not task.done():
            task.cancel()

        async def apply_after_slider_settles() -> None:
            try:
                await asyncio.sleep(0.55)
                if profile_name is not None:
                    current_profile, _response = await asyncio.to_thread(
                        self.configuration_service.get_current_profile_snapshot
                    )
                    if current_profile != profile_name:
                        decky.logger.debug(
                            "Target FPS display sync skipped for inactive profile %s",
                            profile_name,
                        )
                        return
                dock_state = await asyncio.to_thread(self._read_dock_state)
                if dock_state is not None:
                    decky.logger.debug(
                        "Target FPS display sync deferred while Automatic Dock owns the display"
                    )
                    return
                worker = asyncio.create_task(
                    self._run_display_call(
                        self.gamescope_display_service.sync_target_fps, target
                    )
                )
                try:
                    result = await asyncio.shield(worker)
                except asyncio.CancelledError:
                    # A thread cannot be force-cancelled. Wait for the bounded
                    # Gamescope operation so unload/restore cannot be followed
                    # by a late modeset from a detached worker.
                    try:
                        await worker
                    except Exception as error:
                        decky.logger.debug(
                            "Cancelled Target FPS sync finished with error: %s",
                            error,
                        )
                    return
                if not result.get("success"):
                    decky.logger.debug(
                        "Target FPS display sync unavailable: %s",
                        result.get("error", "unknown error"),
                    )
                elif not result.get("applied"):
                    decky.logger.info(
                        "Target FPS display sync skipped: target=%s reason=%s",
                        target,
                        result.get("reason", "display mode not eligible"),
                    )
            except asyncio.CancelledError:
                return
            except Exception as error:
                decky.logger.warning("Target FPS display sync failed: %s", error)

        self._display_sync_task = asyncio.create_task(apply_after_slider_settles())

    def _schedule_refresh_from_config_response(
            self, result: ConfigurationResponse, profile_name: Optional[str] = None
    ) -> None:
        if not result.get("success"):
            return
        config = result.get("config")
        if isinstance(config, dict) and "target_fps" in config:
            self._schedule_target_refresh_sync(
                config["target_fps"], profile_name=profile_name
            )

    _DOCK_MANAGED_FIELDS = (
        "frame_generation_enabled",
        "frame_generation_refresh_threshold",
        "base_fps_cap",
        "multiplier",
        "adaptive",
        "adaptive_auto_base_fps_cap",
        "adaptive_fractional_real_frame_priority",
        "target_fps",
        "adaptive_max_multiplier",
        "adaptive_stable_cadence",
        "gamescope_vrr_mode",
        "dynamic_cadence_recovery",
    )

    def _read_dock_state(self) -> Optional[Dict[str, Any]]:
        try:
            if not self._dock_state_path.is_file():
                return None
            value = json.loads(self._dock_state_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema") != 1:
                return None
            if not isinstance(value.get("profile"), str):
                return None
            if not isinstance(value.get("original"), dict):
                return None
            return value
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _write_dock_state(self, state: Dict[str, Any]) -> None:
        self._dock_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._dock_state_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.replace(self._dock_state_path)

    def _clear_dock_state(self) -> None:
        try:
            self._dock_state_path.unlink(missing_ok=True)
        except OSError as error:
            decky.logger.debug("Could not clear Dock state: %s", error)

    async def _restore_dock_profile(self, state: Dict[str, Any]) -> None:
        profile_name = state.get("profile")
        original = state.get("original")
        if not isinstance(profile_name, str) or not isinstance(original, dict):
            self._clear_dock_state()
            return
        restore = {
            key: original[key]
            for key in self._DOCK_MANAGED_FIELDS
            if key in original
        }
        if restore:
            result = await asyncio.to_thread(
                self.configuration_service.update_profile_config_fields,
                profile_name,
                restore,
                "dock",
                "restore Automatic Dock snapshot",
            )
            if result.get("success") and "target_fps" in restore:
                await self._run_display_call(
                    self.gamescope_display_service.sync_target_fps,
                    int(restore["target_fps"]),
                )
            elif not result.get("success"):
                decky.logger.warning(
                    "Automatic Dock could not restore profile %s: %s",
                    profile_name,
                    result.get("error", "unknown error"),
                )
                return
        self._clear_dock_state()
        decky.logger.info("Automatic Dock restored handheld profile %s", profile_name)

    async def _apply_dock_profile(
            self, profile_name: str, config: Dict[str, Any], target_fps: int,
            display_info: Dict[str, Any],
    ) -> None:
        state = self._read_dock_state()
        if state and state.get("profile") != profile_name:
            await self._restore_dock_profile(state)
            state = None

        if state is None:
            original = {
                key: config.get(key) for key in self._DOCK_MANAGED_FIELDS
                if key in config
            }
            state = {
                "schema": 1,
                "profile": profile_name,
                "original": original,
                "target_fps": target_fps,
            }
            self._write_dock_state(state)

        # Ask Gamescope for the Dock contract only when the active output or
        # policy actually changed. Re-sending a modeset every monitor tick is
        # pointless and can itself disturb pacing.  A previously fixed policy
        # is revalidated from Gamescope's root refresh feedback so a Steam-side
        # mode change cannot silently turn a 60 FPS lock into a 120 FPS budget.
        display_signature = {
            "connector": display_info.get("connector", ""),
            "make": display_info.get("make", ""),
            "model": display_info.get("model", ""),
            "valid_rates": list(display_info.get("valid_rates", [])),
        }
        same_contract = bool(
            state.get("target_fps") == target_fps
            and state.get("display_signature") == display_signature
        )
        refresh_result: Dict[str, Any]
        exact_refresh_contract = False
        verified_refresh = await self._run_display_call(
            self.gamescope_display_service.read_current_refresh_hz
        )
        if verified_refresh == int(target_fps):
            exact_refresh_contract = True
            refresh_result = {
                "success": True, "applied": False, "verified": True,
                "verified_refresh_hz": verified_refresh,
                "reason": "existing refresh already matches Dock target",
            }
        elif same_contract and state.get("policy") == "fractional-adaptive-fallback":
            # This display was already proven unsuitable for an exact modeset.
            # Keep the 60 FPS Adaptive bridge and avoid hammering Gamescope.
            refresh_result = {
                "success": True, "applied": False, "verified": False,
                "verified_refresh_hz": verified_refresh,
                "reason": "retaining verified Adaptive fallback",
            }
        else:
            refresh_result = await self._run_display_call(
                self.gamescope_display_service.sync_target_fps, int(target_fps)
            )
            exact_refresh_contract = bool(
                refresh_result.get("success") and refresh_result.get("applied")
                and refresh_result.get("verified")
                and int(refresh_result.get("verified_refresh_hz", 0)) == int(target_fps)
            )
        # Adaptive normally prefers native output inside the final 5% of its
        # target.  That is sensible upstream behaviour, but Dock Display Lock
        # promises a 60 FPS output clock.  If an exact 60 Hz modeset cannot be
        # verified, cap the real stream just below that near-target window so
        # Fractional Adaptive fills the remaining slots instead of accepting
        # 57-59 FPS as "close enough".
        fallback_real_cap = max(10, int(target_fps) - 4)

        desired = {
            # Preserve every real frame. Fixed 3x is only a hard capacity ceiling.
            # MAKO's FixedRefreshBudget accumulates fractional output credit
            # against confirmed refresh: ~30 real FPS naturally lands at 2x,
            # ~24-25 real FPS at ~2.4-2.5x, and 3x is reached only near 20 FPS.
            # This deliberately avoids 4x/5x Dock latency and artifact pressure.
            "frame_generation_enabled": True,
            "frame_generation_refresh_threshold": 0,
            "base_fps_cap": 0 if exact_refresh_contract else fallback_real_cap,
            "multiplier": 3,
            "adaptive": not exact_refresh_contract,
            "adaptive_auto_base_fps_cap": False,
            "adaptive_fractional_real_frame_priority": "auto",
            "target_fps": int(target_fps),
            "adaptive_max_multiplier": 3,
            # Fixed Smooth Cadence would deliberately request the full 3x
            # batch under FIFO, defeating the display budget. Keep it off.
            "adaptive_stable_cadence": False,
            "gamescope_vrr_mode": "off",
            # Exact Fixed + refresh budget has no probing. Adaptive fallback
            # uses a small real-FPS guard to keep its output clock locked.
            "dynamic_cadence_recovery": False,
        }
        changes = {
            key: value for key, value in desired.items()
            if config.get(key) != value
        }
        if changes:
            result = await asyncio.to_thread(
                self.configuration_service.update_profile_config_fields,
                profile_name,
                changes,
                "dock",
                "apply Automatic Dock display policy",
            )
            if not result.get("success"):
                decky.logger.warning(
                    "Automatic Dock failed to apply Display Lock to %s: %s",
                    profile_name,
                    result.get("error", "unknown error"),
                )
                return

        policy_name = (
            "fixed-refresh-budget" if exact_refresh_contract
            else "fractional-adaptive-fallback"
        )
        if (state.get("target_fps") != target_fps or
                state.get("policy") != policy_name or
                state.get("display_signature") != display_signature):
            state["target_fps"] = target_fps
            state["policy"] = policy_name
            state["display_signature"] = display_signature
            self._write_dock_state(state)
        decky.logger.debug(
            "Automatic Dock active: target=%s policy=%s refresh_result=%s",
            target_fps, policy_name, refresh_result.get("reason", "applied"),
        )

    async def _prepare_fg_backend_transition(
            self, profile_name: str, backend: str
    ) -> Optional[Dict[str, Any]]:
        """Restore an active GFG Dock snapshot before external FG takes ownership.

        Once the backend write commits, the external/native/off steady-state path
        must not touch Gamescope or Dock state. Therefore the one-time cleanup is
        serialized here while the profile still belongs to GFG Engine. The
        returned original Dock fields let a legacy full-profile payload avoid
        re-applying the transient Dock values it read before this restore.
        """
        if backend == FG_BACKEND_GFG:
            return None
        async with self._dock_policy_lock:
            state = await asyncio.to_thread(self._read_dock_state)
            if not state or state.get("profile") != profile_name:
                return None
            original = state.get("original")
            original_fields = dict(original) if isinstance(original, dict) else {}
            await self._restore_dock_profile(state)
            remaining = await asyncio.to_thread(self._read_dock_state)
            if remaining and remaining.get("profile") == profile_name:
                raise RuntimeError(
                    "Automatic Dock state could not be restored before changing "
                    "Frame Generation backend"
                )
            return original_fields

    async def _automatic_dock_iteration(self) -> None:
        async with self._dock_policy_lock:
            await self._automatic_dock_iteration_unlocked()

    async def _automatic_dock_iteration_unlocked(self) -> None:
        profile_name, response = await asyncio.to_thread(
            self.configuration_service.get_current_profile_snapshot
        )
        if not isinstance(profile_name, str) or not response.get("success"):
            return
        config = response.get("config")
        if not isinstance(config, dict):
            return

        if config.get("fg_backend", FG_BACKEND_GFG) != FG_BACKEND_GFG:
            # Backend transitions restore any active GFG Dock snapshot before
            # committing external ownership. In steady state external/native/off
            # therefore performs no Dock-state read/write and no Gamescope call.
            return

        state = await asyncio.to_thread(self._read_dock_state)
        enabled = bool(config.get("automatic_dock_mode", False))
        if not enabled:
            # The common disabled path stops here: no metadata migration, no
            # Gamescope query, and only one TOML parse per monitor interval.
            if state:
                await self._restore_dock_profile(state)
            return

        if not bool(config.get("frame_generation_provisioned", False)):
            provision = await asyncio.to_thread(
                self.configuration_service.update_profile_config_fields,
                profile_name,
                {"frame_generation_provisioned": True},
                "dock",
                "pre-provision Frame Generation for Automatic Dock",
            )
            if provision.get("success"):
                updated = provision.get("config")
                if isinstance(updated, dict):
                    config = updated
                else:
                    config = dict(config)
                    config["frame_generation_provisioned"] = True
                decky.logger.info(
                    "Automatic Dock pre-provisioned Frame Generation for %s; "
                    "a running game may require one restart",
                    profile_name,
                )
            else:
                decky.logger.warning(
                    "Automatic Dock could not pre-provision Frame Generation for %s: %s",
                    profile_name, provision.get("error", "unknown error"),
                )
                return

        display = await self._run_display_call(
            self.gamescope_display_service.get_active_display_info
        )
        if not display.get("success"):
            # Fail closed. Losing display telemetry must not rewrite a profile.
            return

        if bool(display.get("external")):
            target = self.gamescope_display_service.dock_target_fps(display)
            await self._apply_dock_profile(profile_name, config, target, display)
        elif state:
            await self._restore_dock_profile(state)

    async def _automatic_dock_loop(self) -> None:
        while not self._dock_stop_event.is_set():
            try:
                await self._automatic_dock_iteration()
            except asyncio.CancelledError:
                # Cancellation is reserved for emergency teardown. Normal
                # unload uses the stop event so in-flight to_thread work finishes.
                return
            except Exception as error:
                decky.logger.warning("Automatic Dock monitor failed: %s", error)
            try:
                await asyncio.wait_for(self._dock_stop_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

    async def install_mako(self) -> InstallationResult:
        """Install GFG Engine and refresh existing Flatpak runtime copies.

        Returns:
            InstallationResponse dict with success status and message/error
        """
        result = await asyncio.to_thread(self.installation_service.install)
        if not result.get("success"):
            return result

        refresh = await asyncio.to_thread(self.flatpak_service.refresh_installed_extensions)
        updated_versions = refresh.get("updated_versions", [])
        result["flatpak_extensions_updated"] = updated_versions
        if refresh.get("success"):
            if updated_versions:
                result["message"] = (
                    "GFG Engine installed; refreshed Flatpak runtimes "
                    + ", ".join(updated_versions)
                )
        else:
            refresh_error = refresh.get("error") or "unknown Flatpak error"
            self.installation_service.log.warning(
                "GFG Engine installed, but Flatpak runtimes were not fully refreshed: %s",
                refresh_error,
            )
            result["flatpak_refresh_error"] = refresh_error
            result["message"] = (
                "GFG Engine installed. Flatpak runtime refresh needs attention "
                "in Flatpak Setup."
            )
        return result

    async def check_mako_installed(self) -> InstallationCheckResponse:
        """Check if GFG Engine is already installed

        Returns:
            InstallationCheckResponse dict with installation status and paths
        """
        return await asyncio.to_thread(self.installation_service.check_installation)

    async def uninstall_mako(self) -> InstallationResult:
        """Uninstall GFG Engine by removing the installed files

        Returns:
            UninstallationResponse dict with success status and removed files
        """
        return await asyncio.to_thread(self.installation_service.uninstall)

    async def check_lossless_scaling_dll(self) -> DllDetectionResponse:
        """Check if Lossless Scaling DLL is available at the expected paths

        Returns:
            DllDetectionResponse dict with detection status and path info
        """
        return await asyncio.to_thread(self.dll_detection_service.check_lossless_scaling_dll)

    async def check_scaling_model(
        self, dll: str, method: str, sharpness: float,
    ) -> ModelStatusResponse:
        """Read-only selected-model preflight outside Decky's event loop."""
        return await asyncio.to_thread(
            self.dll_detection_service.check_scaling_model, dll, method, sharpness,
        )

    async def check_frame_generation_model(
        self, dll: str, allow_fp16: bool,
    ) -> ModelStatusResponse:
        """Read-only LSFG resource preflight outside Decky's event loop."""
        return await asyncio.to_thread(
            self.dll_detection_service.check_frame_generation_model, dll, allow_fp16,
        )

    async def get_dll_stats(self) -> DllStatsResponse:
        """Get DLL statistics without hashing on Decky's event loop."""
        return await asyncio.to_thread(self._get_dll_stats_sync)

    def _get_dll_stats_sync(self) -> DllStatsResponse:
        """Get detailed statistics about the detected DLL

        Returns:
            Dict containing DLL path, SHA256 hash, and other stats
        """
        try:
            dll_result = self.dll_detection_service.check_lossless_scaling_dll()

            if not dll_result.get("detected") or not dll_result.get("path"):
                return {
                    "success": False,
                    "error": "DLL not detected",
                    "dll_path": None,
                    "dll_sha256": None
                }

            dll_path = dll_result["path"]
            if dll_path is None:
                return {
                    "success": False,
                    "error": "DLL path is None",
                    "dll_path": None,
                    "dll_sha256": None
                }

            dll_path_obj = Path(dll_path)

            sha256_hash = hashlib.sha256()
            try:
                with open(dll_path_obj, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                dll_sha256 = sha256_hash.hexdigest()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to calculate SHA256: {str(e)}",
                    "dll_path": dll_path,
                    "dll_sha256": None
                }

            return {
                "success": True,
                "dll_path": dll_path,
                "dll_sha256": dll_sha256,
                "dll_source": dll_result.get("source"),
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get DLL stats: {str(e)}",
                "dll_path": None,
                "dll_sha256": None
            }

    async def get_mako_config(self) -> ConfigurationResponse:
        """Read the current GFG Engine configuration.

        Returns:
            ConfigurationResponse dict with current configuration or error
        """
        return await asyncio.to_thread(self.configuration_service.get_config)

    async def get_profile_config(
            self, profile_name: str
    ) -> ConfigurationResponse:
        """Read a saved profile without making it the runtime profile."""
        return await asyncio.to_thread(
            self.configuration_service.get_profile_config, profile_name
        )

    async def get_runtime_status(
            self, profile_name: str = ""
    ) -> RuntimeStatusResponse:
        """Return validated requested-versus-applied Renderer state."""
        return await asyncio.to_thread(self.runtime_state_service.get_status, profile_name)

    async def get_fg_backend_status(self, profile_name: str = "") -> Dict[str, Any]:
        """Return saved/effective FG ownership plus the last OptiScaler launch probe."""
        response = await asyncio.to_thread(
            self.configuration_service.get_profile_config, profile_name
        ) if profile_name else await asyncio.to_thread(
            self.configuration_service.get_config
        )
        if not response.get("success") or not isinstance(response.get("config"), dict):
            return {
                "success": False,
                "error": response.get("error") or "configuration unavailable",
            }
        config = response["config"]
        effective = ConfigurationManager.get_effective_runtime_config(config)
        backend = config.get("fg_backend", FG_BACKEND_GFG)
        status = {
            "success": True,
            "error": None,
            "profile": profile_name or "",
            "fg_backend": backend,
            "saved_fg_enabled": bool(config.get("frame_generation_enabled", False)),
            "effective_fg_enabled": bool(effective.get("frame_generation_enabled", False)),
            "saved_automatic_dock": bool(config.get("automatic_dock_mode", False)),
            "effective_automatic_dock": bool(effective.get("automatic_dock_mode", False)),
            "optiscaler_proxy_requested": config.get("optiscaler_proxy", "auto"),
            "optiscaler_proxy_detected": "",
            "proxy_conflict": False,
            "optiscaler_override": "",
            "optiscaler_dir": "",
            "optiscaler_detection": "",
            "optiscaler_status": "not-evaluated" if backend == "optiscaler" else "not-applicable",
            "renderer_required": bool(
                effective.get("frame_generation_provisioned", False)
                or effective.get("scaling_enabled", False)
                or config.get("external_vulkan_layer") == "vkbasalt"
            ),
            "scaling": bool(config.get("scaling_enabled", False)),
            "shaders": config.get("external_vulkan_layer") == "vkbasalt",
        }
        if backend != "optiscaler":
            return status

        status_path = self.configuration_service.runtime_state_dir / "gfg-extreme-optiscaler.status"
        try:
            if status_path.is_file():
                values: Dict[str, str] = {}
                for line in status_path.read_text(encoding="utf-8").splitlines():
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key in {"backend", "profile", "requested", "detected", "status", "conflict", "override", "dir", "how"}:
                        values[key] = value
                recorded_profile = values.get("profile", "")
                requested_matches = values.get("requested") == config.get("optiscaler_proxy", "auto")
                profile_matches = not profile_name or recorded_profile in {"", profile_name}
                if profile_matches and requested_matches:
                    status["optiscaler_proxy_detected"] = values.get("detected", "")
                    status["proxy_conflict"] = values.get("conflict") == "1"
                    status["optiscaler_override"] = values.get("override", "")
                    status["optiscaler_dir"] = values.get("dir", "")
                    status["optiscaler_detection"] = values.get("how", "")
                    status["optiscaler_status"] = values.get("status", "not-evaluated")
        except (OSError, UnicodeError) as error:
            decky.logger.debug("Could not read OptiScaler status: %s", error)
        return status

    def _build_session_recorder(self) -> SessionRecorder:
        cfg = self.configuration_service
        home = cfg.user_home
        from .constants import (
            MAKO_ROOT, MANGOHUD_LAYER_DIR, MANGOHUD_MANIFEST_FILENAME_64, VULKAN_LAYER_DIR, JSON_FILENAME,
            PRESENT_DIAGNOSTICS_LOG_FILENAME,
        )
        plugin_log = getattr(decky, "DECKY_PLUGIN_LOG", None)
        return SessionRecorder(
            user_home=home, config_dir=cfg.config_dir, runtime_state_dir=cfg.runtime_state_dir,
            wrapper_path=cfg.mako_script_path,
            status_provider=lambda: self.governor_service.get_status(),
            events_path=self.governor_service.events_path,
            diagnostics_paths=[cfg.config_dir / PRESENT_DIAGNOSTICS_LOG_FILENAME,
                               Path("/dev/shm/gfg-present-diagnostics.log")],
            saved_config_path=cfg.config_file_path,
            layer_files={
                "renderer layer manifest": home / VULKAN_LAYER_DIR / JSON_FILENAME,
                "MangoHud layer manifest": home / MANGOHUD_LAYER_DIR / MANGOHUD_MANIFEST_FILENAME_64,
                "MAKO root": home / MAKO_ROOT,
            },
            plugin_log=Path(plugin_log) if plugin_log else None, logger=decky.logger,
        )

    async def start_log_recording(self, profile_name: str = "") -> Dict[str, Any]:
        """Begin recording a diagnostic log (timeline + renderer diagnostics)."""
        return await self.session_recorder.start(profile_name)

    async def stop_log_recording(self) -> Dict[str, Any]:
        """Stop and write the zip to the Steam Deck desktop."""
        return await self.session_recorder.stop()

    async def get_log_recording_status(self) -> Dict[str, Any]:
        return self.session_recorder.status()

    async def get_governor_status(self, profile_name: str = "") -> Dict[str, Any]:
        """Return the live GFG Governor state without mutating the profile."""
        return self.governor_service.get_status(profile_name)

    async def set_governor_enabled(
            self, profile_name: str, enabled: bool
    ) -> Dict[str, Any]:
        """Enable or disable Governor for one profile."""
        return await asyncio.to_thread(
            self.governor_service.set_enabled, profile_name, enabled
        )

    async def set_governor_scale_ready(
            self, profile_name: str, scale_ready: bool
    ) -> Dict[str, Any]:
        """Provision the Scaling Engine at launch so scaled points can be live."""
        return await asyncio.to_thread(
            self.governor_service.set_scale_ready, profile_name, scale_ready
        )

    async def set_governor_hud(
            self, profile_name: str, enabled: Any = None, preset: Any = None, position: Any = None
    ) -> Dict[str, Any]:
        """Configure the in-game HUD (MangoHud layer + Governor status line)."""
        return await asyncio.to_thread(
            self.governor_service.set_hud, profile_name, enabled, preset, position
        )

    async def get_pipeline_inspector(self, profile_name: str = "") -> Dict[str, Any]:
        """Return Saved -> Effective -> Actual pipeline truth."""
        return await asyncio.to_thread(
            self.pipeline_inspector_service.get_status, profile_name
        )

    async def get_config_journal(
            self, profile_name: str = "", limit: int = 20
    ) -> Dict[str, Any]:
        """Return recent configuration mutations."""
        return await asyncio.to_thread(
            self.configuration_service.get_config_journal, profile_name, limit
        )

    async def restore_config_journal_entry(self, entry_id: str) -> ConfigurationResponse:
        """Restore a journal entry while preserving Dock/backend transition safety."""
        entry = await asyncio.to_thread(
            self.configuration_service.config_journal.find, str(entry_id)
        )
        if isinstance(entry, dict):
            profile_name = entry.get("profile")
            changes = entry.get("changes")
            if isinstance(profile_name, str) and isinstance(changes, dict):
                backend_delta = changes.get("fg_backend")
                if isinstance(backend_delta, dict) and "before" in backend_delta:
                    try:
                        backend = ConfigurationManager.validate_config({
                            "fg_backend": backend_delta["before"]
                        })["fg_backend"]
                        await self._prepare_fg_backend_transition(profile_name, backend)
                    except (ValueError, TypeError, KeyError, RuntimeError) as error:
                        return {
                            "success": False, "message": "", "error": str(error), "config": None
                        }
        result = await asyncio.to_thread(
            self.configuration_service.restore_config_journal_entry, entry_id
        )
        if isinstance(entry, dict) and isinstance(entry.get("profile"), str):
            self._schedule_refresh_from_config_response(
                result, profile_name=entry["profile"]
            )
        return result

    async def get_config_schema(self) -> ConfigSchemaResponse:
        """Get configuration schema information for frontend

        Returns:
            Dict with field names, types, defaults, and profile information
        """
        try:
            profiles_response = await asyncio.to_thread(
                self.configuration_service.get_profiles
            )

            schema_data = {
                "field_names": ConfigurationManager.get_field_names(),
                "field_types": {name: field_type.value for name, field_type in ConfigurationManager.get_field_types().items()},
                "defaults": ConfigurationManager.get_defaults(),
                "descriptions": ConfigurationManager.get_field_descriptions(),
            }

            if profiles_response.get("success"):
                schema_data["profiles"] = profiles_response.get("profiles", [])
                schema_data["current_profile"] = profiles_response.get("current_profile")
            else:
                schema_data["profiles"] = [DEFAULT_PROFILE_NAME]
                schema_data["current_profile"] = DEFAULT_PROFILE_NAME

            return schema_data

        except (ValueError, KeyError, AttributeError) as e:
            self.configuration_service.log.warning(f"Failed to get full schema, using fallback: {e}")
            return {
                "field_names": ConfigurationManager.get_field_names(),
                "field_types": {name: field_type.value for name, field_type in ConfigurationManager.get_field_types().items()},
                "defaults": ConfigurationManager.get_defaults(),
                "descriptions": ConfigurationManager.get_field_descriptions(),
                "profiles": [DEFAULT_PROFILE_NAME],
                "current_profile": DEFAULT_PROFILE_NAME
            }

    async def update_mako_config(
            self, config: Dict[str, Any]
    ) -> ConfigurationResponse:
        """Update GFG Engine TOML configuration using the object API.

        Args:
            config: Configuration data dictionary containing all settings

        Returns:
            ConfigurationResponse dict with success status
        """
        candidate = dict(config)
        try:
            # Validate the payload for a stable RPC error contract, but write the
            # raw candidate so ConfigurationService can preserve fields missing
            # from legacy frontends under its RLock.
            preview = ConfigurationManager.validate_config(candidate)
            current_profile, _snapshot = await asyncio.to_thread(
                self.configuration_service.get_current_profile_snapshot
            )
            if isinstance(current_profile, str) and "fg_backend" in candidate:
                original = await self._prepare_fg_backend_transition(
                    current_profile, preview.get("fg_backend", FG_BACKEND_GFG)
                )
                if original:
                    for field_name in self._DOCK_MANAGED_FIELDS:
                        if field_name in original:
                            candidate[field_name] = original[field_name]
        except (ValueError, TypeError, KeyError, RuntimeError) as error:
            return {
                "success": False,
                "message": "",
                "error": str(error),
                "config": None,
            }

        result = await asyncio.to_thread(
            self.configuration_service.update_config_from_dict,
            candidate,
            "backend" if "fg_backend" in candidate else "ui",
            "change Frame Generation backend" if "fg_backend" in candidate else "replace current profile configuration",
        )
        self._schedule_refresh_from_config_response(result)
        return result

    async def get_profiles(self) -> ProfilesResponse:
        """Get list of all profiles and current profile

        Returns:
            ProfilesResponse dict with profile list and current profile
        """
        return await asyncio.to_thread(self.configuration_service.get_profiles)

    async def create_profile(
            self, profile_name: str, source_profile: str = None
    ) -> ProfileResponse:
        """Create a new profile

        Args:
            profile_name: Name for the new profile
            source_profile: Optional source profile to copy from (default: current profile)

        Returns:
            ProfileResponse dict with success status
        """
        return await asyncio.to_thread(
            self.configuration_service.create_profile, profile_name, source_profile
        )

    async def delete_profile(self, profile_name: str) -> ProfileResponse:
        """Delete a profile

        Args:
            profile_name: Name of the profile to delete

        Returns:
            ProfileResponse dict with success status
        """
        return await asyncio.to_thread(
            self.configuration_service.delete_profile, profile_name
        )

    async def rename_profile(
            self, old_name: str, new_name: str
    ) -> ProfileResponse:
        """Rename a profile

        Args:
            old_name: Current profile name
            new_name: New profile name

        Returns:
            ProfileResponse dict with success status
        """
        return await asyncio.to_thread(
            self.configuration_service.rename_profile, old_name, new_name
        )

    async def capture_game_profile(
            self,
            app_id: str,
            display_name: str,
            source_profile: str = None,
    ) -> ProfileResponse:
        """Create or refresh a profile from the currently running game."""
        return await asyncio.to_thread(
            self.configuration_service.capture_game_profile,
            app_id, display_name, source_profile
        )

    async def _restore_orphaned_dock_for_external_profile(self, profile_name: str) -> None:
        """Clear a prior GFG Dock snapshot when selection lands on external FG.

        gfg.3.2 baseline fix: external/native/off steady state intentionally skips
        Dock state, so the one-time recovery must happen at profile selection.
        """
        response = await asyncio.to_thread(
            self.configuration_service.get_profile_config, profile_name
        )
        config = response.get("config") if response.get("success") else None
        if not isinstance(config, dict) or config.get("fg_backend", FG_BACKEND_GFG) == FG_BACKEND_GFG:
            return
        async with self._dock_policy_lock:
            state = await asyncio.to_thread(self._read_dock_state)
            if state:
                await self._restore_dock_profile(state)

    async def set_current_profile(self, profile_name: str) -> ProfileResponse:
        """Set the current active profile

        Args:
            profile_name: Name of the profile to set as current

        Returns:
            ProfileResponse dict with success status
        """
        result = await asyncio.to_thread(
            self.configuration_service.set_current_profile, profile_name
        )
        if result.get("success"):
            await self._restore_orphaned_dock_for_external_profile(profile_name)
            profile = await asyncio.to_thread(
                self.configuration_service.get_profile_config, profile_name
            )
            self._schedule_refresh_from_config_response(profile)
        return result

    async def sync_current_profile(self, app_id: str = "") -> ProfileResponse:
        """Select a live app's saved profile, or restore the default profile."""
        result = await asyncio.to_thread(
            self.configuration_service.sync_current_profile, app_id
        )
        profile_name = result.get("profile_name")
        if result.get("success") and isinstance(profile_name, str):
            await self._restore_orphaned_dock_for_external_profile(profile_name)
            profile = await asyncio.to_thread(
                self.configuration_service.get_profile_config, profile_name
            )
            self._schedule_refresh_from_config_response(profile)
        return result

    async def update_profile_config(
            self, profile_name: str, config: Dict[str, Any]
    ) -> ConfigurationResponse:
        """Update configuration for a specific profile

        Args:
            profile_name: Name of the profile to update
            config: Configuration data dictionary containing settings

        Returns:
            ConfigurationResponse dict with success status
        """
        # The service performs compatibility preservation + validation + write
        # under one RLock. A backend ownership transition may first have to
        # restore transient Dock-managed fields; do that while GFG still owns
        # the profile, then keep the legacy full payload from re-applying them.
        candidate = dict(config)
        try:
            preview = ConfigurationManager.validate_config(candidate)
            if "fg_backend" in candidate:
                original = await self._prepare_fg_backend_transition(
                    profile_name, preview.get("fg_backend", FG_BACKEND_GFG)
                )
                if original:
                    for field_name in self._DOCK_MANAGED_FIELDS:
                        if field_name in original:
                            candidate[field_name] = original[field_name]
        except (ValueError, TypeError, KeyError, RuntimeError) as error:
            return {
                "success": False, "message": "", "error": str(error), "config": None
            }
        result = await asyncio.to_thread(
            self.configuration_service.update_profile_config,
            profile_name,
            candidate,
            "backend" if "fg_backend" in candidate else "ui",
            "change Frame Generation backend" if "fg_backend" in candidate else "replace profile configuration",
        )
        self._schedule_refresh_from_config_response(
            result, profile_name=profile_name
        )
        return result

    async def update_profile_config_fields(
            self, profile_name: str, changes: ConfigurationPatch
    ) -> ConfigurationResponse:
        """Merge independent UI field changes into one canonical profile."""
        effective_changes = dict(changes)
        if "fg_backend" in effective_changes:
            try:
                requested_backend = ConfigurationManager.validate_config({
                    "fg_backend": effective_changes["fg_backend"]
                })["fg_backend"]
                await self._prepare_fg_backend_transition(
                    profile_name, requested_backend
                )
            except (ValueError, TypeError, KeyError, RuntimeError) as error:
                return {
                    "success": False, "message": "", "error": str(error), "config": None
                }
        result = await asyncio.to_thread(
            self.configuration_service.update_profile_config_fields,
            profile_name,
            effective_changes,
            "backend" if "fg_backend" in effective_changes else "ui",
            "change Frame Generation backend" if "fg_backend" in effective_changes else "update profile fields",
        )
        # The Target FPS slider emits a series of writes. Debounce the modeset so
        # only the settled value reaches Gamescope. Other profile writes do not
        # touch the display.
        if "target_fps" in effective_changes:
            self._schedule_refresh_from_config_response(
                result, profile_name=profile_name
            )
        return result

    async def get_launch_option(self) -> LaunchOptionResponse:
        """Get the launch option that users need to set for their games

        Returns:
            Dict containing the launch option string and instructions
        """
        wrapper_path = self.installation_service.get_launch_script_path()
        return {
            "launch_option": f"{shlex.quote(wrapper_path)} %command%",
            "wrapper_path": wrapper_path,
            "instructions": "Add this to your game's launch options in Steam Properties",
            "explanation": "The launcher is created during installation, enables GFG Engine's Vulkan layer for this game, and selects its private configuration"
        }

    async def get_config_file_content(self) -> FileContentResponse:
        """Get the current config file content without blocking the event loop."""
        def read_config() -> FileContentResponse:
            config_path = self.configuration_service.config_file_path
            try:
                if not config_path.exists():
                    return {
                        "success": False,
                        "content": None,
                        "path": str(config_path),
                        "error": "Config file does not exist",
                    }
                return {
                    "success": True,
                    "content": config_path.read_text(encoding="utf-8"),
                    "path": str(config_path),
                    "error": None,
                }
            except Exception as error:
                return {
                    "success": False,
                    "content": None,
                    "path": str(config_path),
                    "error": f"Error reading config file: {error}",
                }

        return await asyncio.to_thread(read_config)

    async def get_launch_script_content(self) -> FileContentResponse:
        """Get the launch script content without blocking the event loop."""
        def read_script() -> FileContentResponse:
            try:
                script_path = self.installation_service.get_launch_script_path()
                path = Path(script_path)
                if not path.exists():
                    return {
                        "success": False,
                        "content": None,
                        "error": f"Launch script not found at {script_path}",
                        "path": str(script_path),
                    }
                return {
                    "success": True,
                    "content": path.read_text(encoding="utf-8"),
                    "path": str(script_path),
                    "error": None,
                }
            except Exception as error:
                decky.logger.error("Error reading launch script: %s", error)
                return {
                    "success": False,
                    "content": None,
                    "path": "unknown",
                    "error": str(error),
                }

        return await asyncio.to_thread(read_script)

    async def check_fgmod_directory(self) -> FgmodCheckResponse:
        """Check the fgmod directory without filesystem I/O on the event loop."""
        def check_directory() -> FgmodCheckResponse:
            try:
                home_path = Path(decky.DECKY_USER_HOME)
                fgmod_path = home_path / "fgmod"
                exists = fgmod_path.exists() and fgmod_path.is_dir()
                return {
                    "success": True,
                    "exists": exists,
                    "path": str(fgmod_path),
                    "error": None,
                }
            except Exception as error:
                decky.logger.error("Error checking fgmod directory: %s", error)
                return {
                    "success": False,
                    "exists": False,
                    "error": str(error),
                }

        return await asyncio.to_thread(check_directory)

    async def check_flatpak_extension_status(self) -> FlatpakExtensionStatus:
        """Check status of GFG Engine Flatpak runtime extensions

        Returns:
            FlatpakExtensionStatus dict with installation status for supported runtime versions
        """
        return await asyncio.to_thread(self.flatpak_service.get_extension_status)

    async def install_flatpak_extension(
            self, version: str
    ) -> FlatpakOverrideResponse:
        """Install GFG Engine Flatpak runtime extension

        Args:
            version: A supported runtime version to install

        Returns:
            BaseResponse dict with success status and message/error
        """
        return await asyncio.to_thread(self.flatpak_service.install_extension, version)

    async def uninstall_flatpak_extension(
            self, version: str
    ) -> FlatpakOverrideResponse:
        """Uninstall GFG Engine Flatpak runtime extension

        Args:
            version: A supported runtime version to uninstall

        Returns:
            BaseResponse dict with success status and message/error
        """
        return await asyncio.to_thread(self.flatpak_service.uninstall_extension, version)

    async def get_flatpak_apps(self) -> FlatpakAppInfo:
        """Get list of installed Flatpak apps and their GFG Engine override status

        Returns:
            FlatpakAppInfo dict with apps list and override status
        """
        return await asyncio.to_thread(self.flatpak_service.get_flatpak_apps)

    async def set_flatpak_app_override(
            self, app_id: str
    ) -> FlatpakOverrideResponse:
        """Set GFG Engine overrides for a Flatpak app

        Args:
            app_id: Flatpak application ID

        Returns:
            FlatpakOverrideResponse dict with operation result
        """
        return await asyncio.to_thread(self.flatpak_service.set_app_override, app_id)

    async def remove_flatpak_app_override(
            self, app_id: str
    ) -> FlatpakOverrideResponse:
        """Remove GFG Engine overrides for a Flatpak app

        Args:
            app_id: Flatpak application ID

        Returns:
            FlatpakOverrideResponse dict with operation result
        """
        return await asyncio.to_thread(self.flatpak_service.remove_app_override, app_id)

    async def _main(self):
        """
        Main entry point for the plugin.

        This method is called by Decky Loader when the plugin is loaded.
        Any initialization code should go here.
        """
        decky.logger.info("GFG Extreme loaded")
        try:
            _host, host_supported, host_error = (
                await asyncio.to_thread(
                    self.installation_service.current_package_host_compatibility
                )
            )
        except OSError as error:
            # Invalid release metadata is itself unsafe: do not regenerate an
            # activation wrapper until installation compatibility is known.
            host_supported = False
            host_error = str(error)

        if not host_supported:
            try:
                if await asyncio.to_thread(
                        self.configuration_service.enforce_unsupported_host_passthrough_if_needed
                ):
                    decky.logger.info(
                        "Replaced incompatible MAKO wrapper with native-host passthrough"
                    )
            except OSError as error:
                decky.logger.warning(
                    "Could not enforce the native-host passthrough wrapper: %s",
                    error,
                )
            try:
                flatpak_cleanup = (
                    await asyncio.to_thread(
                        self.flatpak_service.disable_incompatible_host_overrides
                    )
                )
                if flatpak_cleanup.get("success"):
                    disabled_apps = flatpak_cleanup.get("disabled_apps", [])
                    if disabled_apps:
                        decky.logger.info(
                            "Disabled incompatible GFG Extreme Flatpak overrides for: %s",
                            ", ".join(disabled_apps),
                        )
                else:
                    decky.logger.warning(
                        "Could not verify every persisted Flatpak override: %s",
                        flatpak_cleanup.get("error") or "unknown error",
                    )
            except Exception as error:
                # The host wrapper boundary is independent of Flatpak. Keep the
                # plugin available so users can inspect or remove old state.
                decky.logger.warning(
                    "Could not verify every persisted Flatpak override: %s",
                    error,
                )
            decky.logger.warning("GFG Engine remains disabled: %s", host_error)
            return

        try:
            if await asyncio.to_thread(
                    self.configuration_service.migrate_profile_metadata_if_needed
            ):
                decky.logger.info("Initialized game/process profile metadata")
        except (OSError, ValueError) as error:
            decky.logger.warning("Could not initialize profile metadata: %s", error)
        try:
            if await asyncio.to_thread(
                    self.configuration_service.migrate_launch_script_if_needed
            ):
                decky.logger.info("Upgraded installed GFG launch wrapper to the current format")
        except OSError as error:
            decky.logger.warning("Could not upgrade GFG launch wrapper: %s", error)

        try:
            if await asyncio.to_thread(
                    self.installation_service.prepare_active_standalone_for_decky
            ):
                decky.logger.info(
                    "Adopted the active standalone GFG Engine for Decky launch workflows"
                )
        except OSError as error:
            decky.logger.warning(
                "Could not prepare the active standalone GFG Engine: %s",
                error,
            )

        try:
            if await asyncio.to_thread(
                    self.installation_service.migrate_gamescope_wsi_compatibility_manifest_if_needed
            ):
                decky.logger.info("Staged the guarded Gamescope WSI compatibility manifest")
        except OSError as error:
            decky.logger.warning(
                "Could not stage the Gamescope WSI compatibility manifest: %s",
                error,
            )

        try:
            if await asyncio.to_thread(
                    self.installation_service.refresh_guarded_postprocess_manifests_if_needed
            ):
                decky.logger.info(
                    "Refreshed guarded optional post-process manifests"
                )
        except OSError as error:
            decky.logger.warning(
                "Could not stage optional post-process manifests: %s",
                error,
            )

        try:
            if await asyncio.to_thread(
                    self.installation_service.migrate_diagnostics_helper_if_needed
            ):
                decky.logger.info("Installed the diagnostics helper")
        except OSError as error:
            decky.logger.warning("Could not install the diagnostics helper: %s", error)

        if self._dock_monitor_task is None or self._dock_monitor_task.done():
            self._dock_stop_event.clear()
            self._dock_monitor_task = asyncio.create_task(
                self._automatic_dock_loop()
            )

        await self.governor_service.start()
        decky.logger.info("GFG Governor v0.0.2 started")

    async def _unload(self):
        """Stop background work, then restore the pre-Dock profile safely."""
        # Governor owns a separate runtime TDP overlay. Stop it first so an
        # owned PPT cap is restored before Dock/profile shutdown proceeds.
        await self.governor_service.stop()

        # Stop/debounce display writes first. A cancelled coroutine that is
        # already inside to_thread cannot stop the native thread, so the task
        # itself waits for its bounded display operation before it returns.
        display_task = self._display_sync_task
        if display_task is not None and not display_task.done():
            display_task.cancel()
        if display_task is not None:
            try:
                await display_task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                decky.logger.debug(
                    "Target FPS sync ended during unload with error: %s", error
                )
        self._display_sync_task = None

        # Normal Dock shutdown is cooperative: let an in-flight filesystem or
        # Gamescope operation finish before restoring the saved handheld state.
        self._dock_stop_event.set()
        dock_task = self._dock_monitor_task
        dock_stopped_cleanly = True
        if dock_task is not None:
            try:
                # All normal Gamescope calls are bounded, so 15 seconds is an
                # emergency ceiling rather than the ordinary shutdown path.
                await asyncio.wait_for(asyncio.shield(dock_task), timeout=15.0)
            except asyncio.TimeoutError:
                dock_stopped_cleanly = False
                decky.logger.warning(
                    "Dock monitor did not stop in 15 s; cancelling coroutine "
                    "and preserving Dock restore state"
                )
                dock_task.cancel()
                try:
                    await dock_task
                except asyncio.CancelledError:
                    pass
                except Exception as error:
                    decky.logger.debug(
                        "Automatic Dock monitor ended after cancellation with error: %s",
                        error,
                    )
            except asyncio.CancelledError:
                pass
            except Exception as error:
                decky.logger.debug(
                    "Automatic Dock monitor ended during unload with error: %s", error
                )
        self._dock_monitor_task = None

        state = await asyncio.to_thread(self._read_dock_state)
        if state and dock_stopped_cleanly:
            try:
                await self._restore_dock_profile(state)
            except Exception as error:
                decky.logger.warning(
                    "Could not restore Dock profile on unload: %s", error
                )
        elif state:
            # asyncio cancellation cannot stop a worker already executing inside
            # to_thread.  Restoring here could therefore race a late Dock write.
            # Keep the durable snapshot so the next clean monitor iteration can
            # restore it instead of clearing the only recovery information.
            decky.logger.warning(
                "Skipped Dock restore during forced unload; saved state retained "
                "for recovery on the next plugin load"
            )
        decky.logger.info("GFG Extreme unloaded")

    async def _uninstall(self):
        """
        Called when the plugin is uninstalled.

        This method is called by Decky Loader when the plugin is being uninstalled.
        Performs cleanup of this plugin's private files.
        """
        decky.logger.info("GFG Extreme is being uninstalled")

        # Clean up GFG Engine files when the plugin is uninstalled
        await asyncio.to_thread(self.installation_service.cleanup_on_uninstall)

        # Flatpak runtime extensions are shared by every GFG Engine installation.
        # Never remove them automatically: another plugin may still depend on one.
        decky.logger.info("Leaving shared Flatpak runtime extensions installed")

        decky.logger.info("GFG Extreme uninstall cleanup completed")
