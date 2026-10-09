"""Live orchestration service for GFG Governor (GFG Extreme 1.6.9).

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
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared_config import FG_BACKEND_GFG
from .constants import PRESENT_DIAGNOSTICS_FALLBACK_LOG, PRESENT_DIAGNOSTICS_LOG_FILENAME
from .governor_core import (
    multiplier_tolerance,
    BudgetController, EffortEstimator, OperatingPoint, OperatingPointPlanner, PowerSearch, TrialLadder,
    effort_assessment, window_verdict,
)
from .governor_battery import BatteryEstimator, read_battery
from .steamos_tdp import SteamOSManagerTdp
from .game_model import GameModelStore, context_key, floor_key, game_prefix
from .session_stats import SessionStats
from .frame_os.control_channel import DEFAULT_PATH as DEFAULT_SHM, ControlChannel
from . import hud_rings
from .frame_os import layer_install as frame_os_layer
from .frame_os.runner import FrameOsRunner
from .frame_os.memory import GameMemory, seed_pairs
from .frame_os.proof import METRICS as FRAME_OS_METRICS
from .package_paths import PLUGIN_ROOT
from .host_sensors import HostSensors, diagnose
from . import extreme as extreme_policy
from .cpu_freq import CpuFreqActuator
from .power_split import PowerSplit, Sample as SplitSample, SplitMemory, levels_khz
from .governor_hud import HudWriter, normalize as hud_normalize, output_fps as hud_output_fps
from .governor_overlay import (
    OVERLAY_DIRNAME,
    OverlayRecord,
    OverlayStore,
    PointNotApplicable,
    base_deltas,
    injection_deltas,
    point_deltas,
)
from .governor_device import detect_model, target_for
from .governor_power import SteamDeckPowerActuator
from .governor_telemetry import TelemetryObserver
from .governor_confirmation import (  # noqa: F401  (Request and the operation sets are re-exported)
    APPLIED_OPERATIONS, EARLY_DELIVERED_SPAN_SECONDS, FAILED_OPERATIONS, Request, evaluate_confirmation, confirmation_evidence, matches,
)

VERSION = "1.6.9"


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
    PREDICTIVE_SKIP = True  # skip points the observed native cadence already rules out
    # A point failing at the user's TDP may have met a cutscene or loading screen:
    # drop it for a while, not for the rest of the session.
    CEILING_REJECT_TTL_S = 600.0
    # Budget mode (default): lowest TDP first, then fewer generated frames.
    DEFAULT_MODE = "budget"
    MODES = ("budget", "balanced", "quality", "extreme")
    BUDGET_MODES = ("budget", "balanced", "extreme")   # run by the BudgetController
    FLAVORS = {"budget": "battery", "balanced": "balanced", "extreme": "extreme"}
    BUDGET_WINDOW_SECONDS = 8.0
    BUDGET_MIN_SPAN_SECONDS = 6.0
    BUDGET_MIN_SAMPLES = 5
    FAST_CHECK_SECONDS = 3.0     # starvation is checked every iteration on this much FPS
    FAST_MIN_SAMPLES = 3
    EXTERNAL_RECLAIM_SECONDS = 30.0
    MAX_EXTERNAL_RECLAIMS = 3
    # Measured APU draw above the cap by this much, two windows in a row, means
    # the cap is not binding (limit raised elsewhere, e.g. ryzenadj).
    CAP_IGNORED_MARGIN_W = 1.5

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
        self.diagnostics_log_path = disk
        self.observer = TelemetryObserver(disk, Path(PRESENT_DIAGNOSTICS_FALLBACK_LOG))
        self.planner = OperatingPointPlanner()
        self.activity: Any = None  # ActivityLog, set by the plugin
        self._journal_state: tuple = ()
        self._journal_game: Optional[tuple] = None
        self.session_stats = SessionStats()
        self._session_app_id = ""
        self._session_profile = ""
        self.sensors = HostSensors()
        self.game_models = GameModelStore(self.configuration.config_dir / "gfg-game-models.json")
        self.power = SteamDeckPowerActuator(manager=SteamOSManagerTdp(home=os.environ.get("HOME")))
        self.power.journal = self._journal_power
        # Smart power split (1.5): the CPU clock cap that gives a GPU-bound game's watts to the GPU
        self.cpu = CpuFreqActuator(marker=self.configuration.runtime_state_dir / "cpu-cap.json")
        self.cpu.journal = self._journal_power
        self._split: Optional[PowerSplit] = None
        self._split_memory: Optional[SplitMemory] = None
        self._split_key: Optional[tuple] = None
        self._split_ready: Optional[tuple] = None
        # Extreme (1.6): the power ceiling in force and the render scale the renderer confirmed
        self._extreme_ceiling: Optional[Dict[str, Any]] = None
        self._extreme_ack: Optional[Dict[str, Any]] = None      # {"pct", "sharpness", "evidence"}
        self._extreme_scale_failures = 0
        self._extreme_scale_blocked: Optional[str] = None   # Extreme only: the profile scales itself
        self._scale_blocked: Optional[str] = None           # every mode: the renderer refused the scale
        self._extreme_rs: Optional[Dict[str, Any]] = None   # the renderer's last runtime-state report
        self._extreme_rs_at = -1e9
        self.search = PowerSearch()
        self.settings_path = self.configuration.config_dir / "gfg-governor.json"
        self.events_path = self.configuration.runtime_state_dir / "governor-events.jsonl"
        self.diagnostics_marker_path = self.configuration.runtime_state_dir / "governor-diagnostics.enabled"
        # GFG Frame OS (development, off by default): per-profile mode, launch marker, 10 Hz runner.
        self.frame_os_marker_path = self.configuration.runtime_state_dir / "frame-os.enabled"
        self.frame_os = FrameOsRunner(ControlChannel(Path(os.environ.get("GFG_FRAME_OS_SHM") or DEFAULT_SHM)))
        # Frame OS memory: this game's A/B record, loaded once per game session
        self._fo_memory: Optional[GameMemory] = None
        self._fo_memory_key: Optional[tuple] = None
        self._fo_saved: Dict[str, int] = {}
        self.frame_os_layer_source = frame_os_layer.bundled_dir(PLUGIN_ROOT)
        share = getattr(self.configuration, "local_share_dir", None)
        self.frame_os_layer_dir: Optional[Path] = frame_os_layer.target_dir(share) if share else None
        self.frame_os_layer_error: Optional[str] = None
        # Ring HUD (GFG HUD layer): bitmap + the size the layer reports, both in /dev/shm.
        self.ring_hud_path = Path(os.environ.get("GFG_HUD_FILE") or hud_rings.DEFAULT_PATH)
        self.ring_hud_extent = Path(os.environ.get("GFG_HUD_EXTENT_FILE") or hud_rings.DEFAULT_EXTENT)
        self.ring_hud_marker_path = self.configuration.runtime_state_dir / "hud-rings.enabled"
        self._ring_hud_key = None
        self._ring_hud_lock = threading.Lock()
        self._ring_hud_due = 0.0
        self._ring_hud_seq = 0
        # steadiness (field report 1.3: the HUD flickered): last good values, held briefly
        self._hud_values: Optional[tuple] = None      # (time, fps, real)
        self._hud_fos: Optional[tuple] = None         # (time, frame_os dict)
        self._hud_tag: Optional[tuple] = None         # (time shown, level, delivered)
        self._rings_live_at: Optional[float] = None   # last time the layer was known to draw
        self.ring_hud_layer_error: Optional[str] = None
        self.frame_os_registry_dir: Optional[Path] = getattr(self.configuration, "user_vulkan_layer_dir", None)
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
        self._standby_fp: Any = None
        self._in_saved_notify = False
        listeners = getattr(self.configuration, "saved_listeners", None)
        if isinstance(listeners, list):
            listeners.append(self.notify_saved_changed)
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
        # Frame OS Act: the adaptive overlay written on top of the live point (None: not injecting)
        self._injection: Optional[Dict[str, Any]] = None
        self._injection_started_at = None
        self._injection_seq = 0
        self._injection_hold_until = 0.0
        self._injection_starvation_yields = 0  # per session; Act circuit breaker
        self._menu_since: Optional[float] = None
        # A zero-slot swapchain is observe-only until the renderer reports
        # stable recovered resources. Never claim/release PPT at 1 Hz.
        self._capacity_paused = False
        self._capacity_restore_at: Optional[float] = None
        self._request: Optional[Request] = None
        self._request_counter = getattr(self, "_request_counter", 0)
        self._ladder: Optional[TrialLadder] = None
        self._budget: Optional[BudgetController] = None
        # The live controller's game-model keys, fixed when it was built: failures drained after a
        # mode switch or game exit still go to the mode/game they were found in.
        self._budget_keys: Optional[tuple] = None
        self._applied_tdp: Optional[float] = None
        self._external_at: Optional[float] = None
        self._reclaims = 0
        self._over_cap_windows = 0
        self._draw_samples: List[float] = []
        self._tdp_set_seq = 0
        self._fast_point_key: Optional[str] = None
        self._fast_last_sample_seq = 0  # never count a cached FPS window as another check
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

    _settings_lock = threading.Lock()

    def _save_settings(self) -> None:
        """Atomic, and safe from both the event loop (Frame OS memory) and RPC worker threads
        (review 1.3.0: a shared temp name could interleave two writes into invalid JSON, which
        reloads as defaults)."""
        with self._settings_lock:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(3):
                try:
                    text = json.dumps(self._settings, indent=2, sort_keys=True) + "\n"
                    break
                except RuntimeError:      # a dict changed size under another thread: take it again
                    if attempt == 2:
                        raise
            temp = self.settings_path.with_name(f".{self.settings_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            try:
                temp.write_text(text, encoding="utf-8")
                os.chmod(temp, 0o600)
                temp.replace(self.settings_path)
            except OSError:
                try:
                    temp.unlink()
                except OSError:
                    pass
                raise

    def _profile_settings(self, profile: str) -> Dict[str, Any]:
        value = self._settings.get("profiles", {}).get(profile, {})
        return value if isinstance(value, dict) else {}

    def _profile_enabled(self, profile: str) -> bool:
        return bool(self._profile_settings(profile).get("enabled", False))

    def _mode(self, profile: str) -> str:
        mode = self._profile_settings(profile).get("mode")
        return mode if mode in self.MODES else self.DEFAULT_MODE

    def set_mode(self, profile: str, mode: str) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        mode = str(mode or "").strip().lower()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        if mode not in self.MODES:
            return {"success": False, "error": f"Unknown mode: {mode}"}
        was = self._mode(profile)
        self._settings.setdefault("profiles", {}).setdefault(profile, {})["mode"] = mode
        self._save_settings()
        overlay_error = None
        if "extreme" in (mode, was) and mode != was:
            # Extreme renders below full resolution when that buys real frames: the Scaling Engine
            # is provisioned from the next launch on (process-static), like a scale-ready launch.
            overlay_error = self._ensure_base_overlay_sync(profile)
            self._extreme_act_switch(profile, entering=mode == "extreme")
            self._save_settings()
        if profile == self._active_profile:
            self._forced_mode_change = True
        self._poke()
        return {"success": True, "error": None, "profile": profile, "mode": mode,
                **({"overlay_error": overlay_error} if overlay_error else {})}

    def game_model_target(self, profile: str) -> Optional[Dict[str, Any]]:
        """Which game "Reset what GFG learned" would reset for ``profile``, or None.

        The game running under this profile, else the profile's last session, by Steam AppID.
        Without an AppID only what was stored under the profile itself (games launched without
        one), and only when there is something: never a silent reset of nothing.
        """
        profile = str(profile or "").strip()
        if not profile:
            return None
        app_id = ""
        if profile == self._active_profile:
            app_id = self._game_app_id()
        last = self._settings.get("last_session") or {}
        if not app_id and isinstance(last, dict) and last.get("profile") == profile:
            app_id = str(last.get("app_id") or "")
        prefix = game_prefix(profile, app_id)
        if not prefix.startswith("app:"):
            if not (self.game_models.count_game(prefix) or prefix in self._scale_ignored_games()):
                return None
            app_id = ""
        return {"profile": profile, "app_id": app_id, "game": prefix}

    def forget_game_model(self, profile: str) -> Dict[str, Any]:
        """Forget what was learned for the profile's game (every target and mode): warm starts,
        failed points and failed lower levels (review 1.1.x: a stale memory had no reset).

        The game is ``game_model_target``'s, keyed exactly as it was stored.  Runs on the event
        loop (plugin RPC), like every other game-model write, so it never races the Governor loop.
        """
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        target = self.game_model_target(profile)
        if target is None:
            return {"success": False, "error": "no-game-identified", "profile": profile, "game": None}
        prefix = target["game"]
        forgotten = self.game_models.forget_game(prefix)
        if self._frame_os_games().pop(prefix, None) is not None:
            forgotten += 1
            self._save_settings_quietly()
            if self._fo_memory_key and self._fo_memory_key[0] == prefix:
                self._fo_memory = GameMemory()
                self._fo_memory.start_session()
                self.frame_os.apply_memory(self._fo_memory.disabled(), {})
        if self._scale_ignored_games().pop(prefix, None) is not None:
            forgotten += 1
            self._save_settings_quietly()
            self._scale_blocked = None
        if self._split_games().pop(prefix, None) is not None:
            forgotten += 1
            self._save_settings_quietly()
            if self._split_key and self._split_key[0] == prefix and self._split is not None:
                self._split_memory = SplitMemory()
                self._split_memory.start_session()
                self._split.start_level, self._split.prior_pairs, self._split.pairs = 0, [], []
                self._split.enabled = self._power_split_enabled()
        budget = self._budget
        if budget is not None and profile == self._active_profile:
            # The live controller forgets too, or the next drain would write it all back.
            budget.known_failures.clear()
            budget.new_failures.clear()
            budget.floor_failures.clear()
            budget.new_floor_failures.clear()
        self._journal("game-model-forgotten", profile=profile, game=prefix, entries=forgotten)
        return {"success": True, "error": None, "profile": profile, "game": prefix,
                "app_id": target["app_id"], "forgotten": forgotten}

    def _update_sensors(self) -> None:
        """Host sensors + a one-line diagnosis. Never allowed to break the control loop."""
        try:
            sensors = self.sensors.sample()
            tel = (self._status.get("telemetry") or {})
            summary = tel.get("summary") or {}
            # Only the live controller's numbers: a previous mode's feedback must not survive it.
            fb = (self._status.get("power_feedback") or {}) if self._budget is not None else {}
            cap = fb.get("cap_w") or (self._budget.tdp if self._budget is not None else None)
            self._status["sensors"] = sensors
            self._status["diagnosis"] = diagnose(
                sensors, cap_w=cap, draw_w=fb.get("draw_w"),
                frametime=summary.get("frametime"),
            )
            if self._budget is not None:  # heat holds back probes towards more real frames
                self._budget.set_thermal(str(self._status["diagnosis"].get("thermal") or "unknown"), self._clock())
        except Exception as error:
            self.log.debug("Governor sensors unavailable: %s", error)

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
        thermal = (status.get("diagnosis") or {}).get("thermal")
        reason: Optional[str] = None
        if not status.get("enabled") or status.get("state") not in ("LOCKED", "OPTIMIZE_POWER", "GUARD", "OBSERVE_ONLY"):
            if self._exhausted and status.get("enabled"):
                # A game that already holds the target is not a nightmare just because
                # no Governor point was accepted.
                raw = stable or "nightmare"
                reason = "holds the target on its own" if stable else "no setting held the target"
            else:
                raw = None
        elif self._budget is not None:
            real = (telemetry.get("real") or {}).get("median")
            budget = self._budget
            raw, reason = effort_assessment(self._point, real, budget.exhausted,
                                            tdp_w=budget.effective_w if budget.tdp_control else None,
                                            thermal=thermal)
        else:
            real = (telemetry.get("real") or {}).get("median")
            raw, reason = effort_assessment(self._point, real, self._exhausted and not stable, thermal=thermal)
        self._effort.update(self._clock(), raw, reason)

    def hud_settings(self, profile: str) -> Dict[str, Any]:
        raw = self._profile_settings(profile).get("hud") or {}
        preset, position = hud_normalize(raw.get("preset"), raw.get("position", "bottom-left"))
        style = raw.get("style") if raw.get("style") in self.HUD_STYLES else "rings"
        # A missing setting is a new install (or an older profile). Preserve an explicitly
        # disabled HUD on upgrades, but show Rings bottom-left by default.
        return {"enabled": bool(raw.get("enabled", True)), "preset": preset, "position": position, "style": style}

    HUD_STYLES = ("rings", "text")
    RING_HUD_PERIOD_S = 1.0
    HUD_HOLD_S = 5.0          # a missing sample/telemetry for this long keeps the last picture
    HUD_TAG_MIN_S = 2.0       # a status badge stays at least this long (no flipping every second)
    _hud_values: Optional[tuple] = None
    _hud_fos: Optional[tuple] = None
    _hud_tag: Optional[tuple] = None
    _rings_live_at: Optional[float] = None

    def set_hud(self, profile: str, enabled: Any = None, preset: Any = None, position: Any = None,
                style: Any = None) -> Dict[str, Any]:
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
        if style in self.HUD_STYLES:
            current["style"] = style
        self._settings.setdefault("profiles", {}).setdefault(profile, {})["hud"] = current
        self._save_settings()
        self._ring_hud_due = 0.0           # redraw at once with the new look
        try:
            self._sync_frame_os_marker()   # stages the HUD layer and its launch marker
        except OSError:
            pass
        self._sync_hud(profile)
        self._poke()
        # MangoHud is loaded at launch with a hidden config and re-reads it: live.
        return {"success": True, "error": None, "hud": current, "relaunch_required": False}

    def _sync_hud(self, profile: str) -> None:
        """Publish/remove the active HUD config and keep the status line fresh."""
        try:
            settings = self.hud_settings(profile)
            # Decide the desired state first, then apply exactly that once (rate-limited inside
            # HudWriter); an older pending config is replaced, never flushed first.
            if settings["enabled"]:
                status = self.get_status(profile)
                rings = settings["style"] == "rings" and self._ring_hud_live_steady()
                if rings and self._publish_ring_hud(status, settings):
                    # Hide the fallback only after publishing a usable ring HUD.
                    self.hud.deactivate()
                else:
                    self._clear_ring_hud()
                    # MangoHud re-reads a changed config, so the FPS source follows the telemetry.
                    self.hud.activate(settings["preset"], settings["position"],
                                      generated_fps=hud_output_fps(status) is not None)
                    # get_status, not _status: power/effort/active point are only merged in there.
                    self.hud.write_status(status, settings["preset"])
            elif self._hud_preload_wanted():
                self._clear_ring_hud()
                self.hud.deactivate()
            else:
                self._clear_ring_hud()
                self.hud.remove()
        except OSError as error:
            self.log.debug("Governor HUD sync failed: %s", error)

    def _ring_hud_live_steady(self) -> bool:
        """The layer draws; a probe that briefly says "not running" (or a failed probe) does not
        swap the rings for the text line and back (field report 1.3: flicker)."""
        now = self._clock()
        if self._ring_hud_live():
            self._rings_live_at = now
            return True
        return self._rings_live_at is not None and now - self._rings_live_at <= self.HUD_HOLD_S

    def _ring_hud_live(self) -> bool:
        """The GFG HUD layer draws in this game: since the launch it wrote the swapchain size with
        the HUD flag set ("W H 1").  Otherwise (old launch, layer missing, Flatpak, an HDR or
        unsupported swapchain it passes through: "W H 0") the text line stays as the fallback."""
        try:
            written = self.ring_hud_extent.stat().st_mtime
            parts = self.ring_hud_extent.read_text().split()
        except OSError:
            return False
        if len(parts) >= 3 and parts[2] == "0":
            return False
        launch = self._launch if isinstance(self._launch, dict) else {}
        key = launch.get("launch_key") if launch.get("running") else None
        started = key[2] if isinstance(key, (list, tuple)) and len(key) > 2 else None   # wall-clock launch time
        return isinstance(started, (int, float)) and written >= float(started) - 5.0

    def _publish_ring_hud(self, status: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        with self._ring_hud_lock:
            return self._publish_ring_hud_locked(status, settings)

    def _publish_ring_hud_locked(self, status: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        """Refresh at 1 Hz, skip identical pictures, and never display stale FPS."""
        now = self._clock()
        if now < self._ring_hud_due:
            return self._ring_hud_key is not None
        tel = status.get("telemetry") or {}
        summary = tel.get("summary") or tel
        snapshot = tel.get("snapshot")
        latest = (snapshot or {}).get("latest") or {}
        age = (snapshot or {}).get("sample_age_ms")
        fresh = snapshot is None or (isinstance(age, (int, float)) and 0 <= age <= 2500)

        def number(value):
            return round(float(value)) if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 else None

        # Renderer samples already summarize an interval. Avoid another 12/20-second average.
        fps = latest.get("output_fps") if snapshot is not None else (summary.get("output") or {}).get("median")
        real = latest.get("real_fps") if snapshot is not None else (summary.get("real") or {}).get("median")
        power = status.get("power") or {}
        battery = status.get("battery") or {}
        fo = status.get("frame_os") or {}
        benefit = fo.get("benefit") or {}
        # Renderer samples arrive about once a second: one late sample must not blank the numbers
        # (they flipped between a value and "—").  Hold the last good ones for HUD_HOLD_S.
        if fresh and number(fps) is not None:
            self._hud_values = (now, number(fps), number(real))
        held = self._hud_values if (self._hud_values and now - self._hud_values[0] <= self.HUD_HOLD_S) else None
        data: Dict[str, Any] = {
            # HUD is independent from Governor: turning off power optimization
            # must not blank out live FPS from the same renderer.
            "fps": held[1] if held else None,
            "real": held[2] if held else None,
            "tdp": number(power.get("observed_tdp_w") if power.get("observed_tdp_w") is not None
                          else power.get("current_tdp_w")),
            "target": number(status.get("target_output_fps") or (status.get("device") or {}).get("target")),
            "limit": number(power.get("initial_tdp_w") or power.get("maximum_tdp_w")) or 15,
            "battery_min": number(battery.get("minutes_left")), "battery_pct": number(battery.get("percent")),
        }
        # ENERGY uses Steam's slider maximum, not Extreme's actuator ceiling.
        # Keep the actual cap separate from APU draw and preserve fractions.
        maximum = power.get("gamescope_max_tdp_w")
        if maximum is None:
            maximum = power.get("maximum_tdp_w")
        if (not isinstance(maximum, (int, float)) or isinstance(maximum, bool)
                or not math.isfinite(maximum) or maximum <= 0):
            maximum = extreme_policy.EXTREME_CEILING_W
        data["maximum_tdp"] = float(maximum)
        current = power.get("observed_tdp_w")
        if current is None:
            current = power.get("current_tdp_w")
        caps = [value for value in (current, power.get("observed_fast_w"))
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value >= 0]
        data["energy_tdp"] = max(caps) if caps else None
        # Display *delivered* MotionBoost, not a requested policy. A pacer ACK
        # alone is insufficient: the adaptive Render v4 overlay must also be in
        # place, and fresh renderer samples must show the real cadence increased
        # without losing the expected output rate.
        if fo.get("enabled") and (fo.get("telemetry") or {}).get("live"):
            def percent(key):
                value = benefit.get(key) if benefit.get("ready") else None
                return round(value) if isinstance(value, (int, float)) and math.isfinite(value) else None
            decision = fo.get("decision") or {}
            level = decision.get("level")
            active = bool(fo.get("mode") == "act" and self.frame_os.executor_active
                          and fo.get("acknowledged"))
            calm = self.frame_os.policy.calm_real_hz if self.frame_os.policy else None
            measured_real = data["real"]
            measured_out = data["fps"]
            target = data.get("target")
            delivered = bool(active and level == "boost" and measured_real is not None
                             and isinstance(calm, (int, float)) and calm > 0
                             and measured_real >= 1.2 * calm
                             and measured_out is not None and target
                             and measured_out >= 0.85 * target)
            ratio = (round(measured_out / measured_real, 1)
                     if measured_real and measured_out else None)
            # A neutral badge (CALM / VERIFYING / REST) stays at least HUD_TAG_MIN_S: boosts start
            # and stop within a second.  A verified BOOST is never held or delayed: it shows and
            # goes with its evidence.
            shown = self._hud_tag
            if (shown and not delivered and not shown[2] and shown[1] != level
                    and now - shown[0] < self.HUD_TAG_MIN_S):
                level = shown[1]
            elif not shown or (shown[1], shown[2]) != (level, delivered):
                self._hud_tag = (now, level, delivered)
            data["frame_os"] = {
                "level": level, "estimate": benefit.get("estimate"), "verified_boost": delivered,
                "active": active, "actual_real": measured_real, "actual_ratio": ratio,
                "ab": bool(fo.get("ab_control")), "measured": benefit.get("measured") or {},
                "response": percent("response_pct"), "frames": percent("frames_pct"),
                "energy": percent("energy_pct")}
            self._hud_fos = (now, data["frame_os"])
        elif self._hud_fos and now - self._hud_fos[0] <= self.HUD_HOLD_S and fo.get("enabled"):
            # the pacer's telemetry missed a beat: keep the Frame OS rings instead of resizing
            data["frame_os"] = self._hud_fos[1]
        ext = status.get("extreme") or {}
        if ext.get("enabled"):
            # Extreme: the TDP ring is drawn against the ceiling, and only a render scale the
            # renderer confirmed is named (EXTREME_FOUNDATION: no requested values on screen).
            ceiling = (ext.get("ceiling") or {}).get("ceiling_w")
            if isinstance(ceiling, (int, float)) and ceiling > 0:
                data["limit"] = number(ceiling)
            applied = ext.get("applied") or {}
            pct = applied.get("render_pct")
            data["extreme"] = {"render_pct": int(pct) if isinstance(pct, (int, float)) and pct < 100 else None}
        scale = hud_rings.overlay_scale(self.ring_hud_extent)
        key = (hud_rings.visual_key(data, settings["preset"], settings["position"], scale),
               tuple((self._launch or {}).get("launch_key") or ()))
        if key == self._ring_hud_key and self.ring_hud_path.is_file():
            self._ring_hud_due = now + self.RING_HUD_PERIOD_S
            return True
        seq = self._ring_hud_seq + 1
        if not hud_rings.write_overlay(data, preset=settings["preset"], position=settings["position"],
                                       seq=seq, path=self.ring_hud_path, extent_path=self.ring_hud_extent, scale=scale):
            self._ring_hud_key = None
            self._ring_hud_due = 0.0   # retry next tick, not after a long stale display
            return False
        self._ring_hud_seq, self._ring_hud_key = seq, key
        self._ring_hud_due = now + self.RING_HUD_PERIOD_S
        return True

    def _clear_ring_hud(self) -> None:
        with self._ring_hud_lock:
            self._ring_hud_key = None
            if self._ring_hud_seq and self._ring_hud_due != -1.0:
                seq = self._ring_hud_seq + 1
                if hud_rings.write_overlay(None, preset="standard", position="top-left", seq=seq,
                                            path=self.ring_hud_path, extent_path=self.ring_hud_extent):
                    self._ring_hud_seq = seq
                    self._ring_hud_due = -1.0   # next publish draws at once; failures retry

    def _current_hud_profile(self) -> str:
        """Only the selected Saved profile controls the global Vulkan HUD launch marker."""
        try:
            name, _snapshot = self.configuration.get_current_profile_snapshot()
            return str(name or "")
        except Exception:
            return str(self._active_profile or "")

    def _hud_preload_wanted(self) -> bool:
        """Load the HUD only for the selected profile, honoring an explicit opt-out."""
        profile = self._current_hud_profile()
        return bool(profile and (self._profile_enabled(profile) or self.hud_settings(profile)["enabled"]))

    def _sync_hud_presence(self) -> None:
        """Start/toggle path: hidden HUD config for Governor/HUD users, none otherwise.

        Never hides a HUD that is shown: ``_sync_hud`` owns the visible state.
        """
        try:
            if not self._hud_preload_wanted():
                self.hud.remove()
            elif not self.hud.config_exists():
                self.hud.deactivate()
        except OSError as error:
            self.log.debug("Governor HUD presence sync failed: %s", error)

    def _scale_ready(self, profile: str) -> bool:
        """Scale-ready launch: the player's switch, or Extreme (which upscales for real frames)."""
        settings = self._profile_settings(profile)
        return bool(settings.get("scale_ready", False)) or settings.get("mode") == "extreme"

    def _poke(self) -> None:
        """Wake an idle loop right away (callable from worker threads)."""
        loop, wake = self._wake_loop, self._wake
        if loop is not None and wake is not None:
            try:
                loop.call_soon_threadsafe(wake.set)
            except RuntimeError:
                pass

    def _is_idle(self) -> bool:
        profile = self._current_hud_profile()
        hud_on = bool(profile and self.hud_settings(profile)["enabled"])
        return not (self._any_profile_enabled() or hud_on or self._restore_pending or self._forced_release
                    or self._point or self._request)

    def _any_profile_enabled(self) -> bool:
        profiles = self._settings.get("profiles", {})
        return isinstance(profiles, dict) and any(
            isinstance(value, dict) and bool(value.get("enabled", False)) for value in profiles.values()
        )

    def _sync_diagnostics_marker(self) -> None:
        """Keep renderer diagnostics on for every managed launch.

        Diagnostics are read from the environment once, when the game starts.
        With the marker present for every launch, the Governor can be turned on
        in an already running game and still get FPS telemetry.
        """
        self.diagnostics_marker_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.diagnostics_marker_path.read_text(encoding="utf-8") == "enabled\n":
                return
        except OSError:
            pass
        temp = self.diagnostics_marker_path.with_suffix(".tmp")
        temp.write_text("enabled\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(self.diagnostics_marker_path)

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

    def _ensure_overlay_sync(
        self, profile: str, deltas: Dict[str, Any], point_key: str
    ) -> Optional[OverlayRecord]:
        if self.overlay is None:
            raise OSError("overlay-unsupported")
        with self._io_lock:
            return self.overlay.ensure(profile, deltas, point_key=point_key)

    def _restore_overlay_sync(self, profile: str, released: bool = False) -> Optional[str]:
        """Restore ``profile``'s overlay to the Saved projection (standby).

        The lease is kept while the plugin runs, so the next launch still reads
        the overlay and the Governor can be turned on mid-game.  ``released``
        (plugin unload) writes owner=0 instead: new launches then use Saved.
        Returns an error string, or None when restored and verified.  Nothing
        is removed: a running game keeps a valid (Saved) file to watch.
        """
        if self.overlay is None or not self.overlay.exists(profile):
            return None
        try:
            saved = self._saved_profile_config(profile)
            if saved is None and not released:
                return "saved-profile-unavailable"
            if released:
                self._write_overlay_sync(profile, self._base_for(profile, saved), "released", released=True)
            else:
                with self._io_lock:
                    self.overlay.ensure(profile, self._base_for(profile, saved), point_key="base")
        except (OSError, ValueError) as error:
            return str(error)
        return None

    def _saved_profile_names(self) -> list[str]:
        direct = getattr(self.configuration, "saved_profile_names", None)
        if callable(direct):
            try:
                return [str(name) for name in direct() if str(name or "").strip()]
            except Exception as error:  # pragma: no cover - defensive
                self.log.debug("Governor could not list profiles: %s", error)
                return []
        getter = getattr(self.configuration, "get_profiles", None)
        names: list[str] = []
        if callable(getter):
            try:
                response = getter()
            except Exception as error:  # pragma: no cover - defensive
                self.log.debug("Governor could not list profiles: %s", error)
                response = None
            listed = response.get("profiles") if isinstance(response, dict) else None
            if isinstance(listed, list):
                names = [str(name) for name in listed if str(name or "").strip()]
        return names

    def _standby_overlays_sync(self, force: bool = False) -> None:
        # One pass at a time: the Saved-write listener and the loop both call this.
        with self._io_lock:
            self._standby_overlays_sync_locked(force)

    def _standby_overlays_sync_locked(self, force: bool) -> None:
        """Keep a leased Saved-projection overlay for every profile.

        Every managed launch then reads the overlay, so enabling the Governor in
        a running game needs no relaunch.  Runs when Saved changed (cheap stat)
        and never touches the profile whose Governor point is in flight: that
        overlay belongs to ``_sync_overlay``.
        """
        if self.overlay is None:
            return
        fingerprint = getattr(self.configuration, "saved_config_fingerprint", lambda: None)()
        if not force and fingerprint is not None and fingerprint == self._standby_fp:
            return
        names = self._saved_profile_names()
        if not names:
            return
        busy = (
            self._active_profile
            if (self._point_deltas or self._request is not None or self._rollback_deltas is not None)
            else None
        )
        for profile in names:
            if profile == busy or profile in self._restore_pending:
                continue
            try:
                saved = self._saved_profile_config(profile)
                if saved is None:
                    continue  # retried when Saved changes again, not every second
                with self._io_lock:
                    self.overlay.ensure(profile, self._base_for(profile, saved), point_key="base")
            except (OSError, ValueError) as error:
                self.log.debug("Governor standby overlay for %s failed: %s", profile, error)
        try:
            with self._io_lock:
                self.overlay.release_unknown(names)
        except OSError as error:
            self.log.debug("Governor could not release stale overlays: %s", error)
        self._standby_fp = fingerprint

    def notify_saved_changed(self) -> None:
        """Saved config was written by the plugin: refresh standby overlays now.

        Synchronous, before the Saved write returns, so a game launched right
        after an edit already reads the new launch-time fields.  The profile
        under an in-flight Governor point is left to the loop (``_sync_overlay``).
        """
        if self._in_saved_notify:
            return
        self._in_saved_notify = True
        try:
            self._standby_overlays_sync(force=True)
        except Exception as error:  # never fail the Saved write
            self.log.debug("Governor standby refresh after Saved write failed: %s", error)
        finally:
            self._in_saved_notify = False
        self._poke()

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
        self._sync_hud_presence()
        overlay_error: Optional[str] = None
        if enabled:
            overlay_error = self._ensure_base_overlay_sync(profile)
            if overlay_error is None:
                self._status.pop("capability", None)
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

    FRAME_OS_MODES = ("off", "observe", "shadow", "act")
    FRAME_OS_ACT_ENV = "GFG_FRAME_OS_EXPERIMENTAL_ACT"

    def _frame_os_act_unlocked(self) -> bool:
        """Act changes Vulkan frame timing and power: require an explicit opt-in (setting or env)."""
        return os.environ.get(self.FRAME_OS_ACT_ENV) == "1" or bool(self._settings.get("frame_os_act_unlocked"))

    INJECTION_HOLD_S = 60.0
    # Field log 1.5.0: Act took the point right after its trial and the Governor never searched
    # lower watts again (11 min at the 10 W start, a whole session at a trial's 13 W fast raise).
    # Act now starts only once the budget has settled (locked for ACT_SETTLE_S: a successful lower
    # probe re-locks and restarts the wait), and steps aside every ACT_RESEARCH_EVERY_S for
    # ACT_RESEARCH_S so the Governor can try a lower level with the plain point.
    ACT_SETTLE_S = 60.0
    ACT_RESEARCH_EVERY_S = 600.0
    ACT_RESEARCH_S = 120.0
    # Do not interpret the transitional cadence right after an Act change as
    # persistent frame starvation. Requires fresh, consecutive renderer samples.
    INJECTION_GRACE_S = 4.0
    INJECTION_MIN_SAMPLES = 3
    STARVATION_RUN = 3
    _injection_started_at: Optional[float] = None

    def _frame_os_ab(self) -> bool:
        """A/B proof windows in Act (on unless the player turned them off)."""
        return self._settings.get("frame_os_ab") is not False

    def set_frame_os_ab(self, enabled: bool) -> Dict[str, Any]:
        self._settings["frame_os_ab"] = bool(enabled)
        self._save_settings()
        self.frame_os.proof.enabled = bool(enabled)
        self._poke()
        return {"success": True, "error": None, "ab": self._frame_os_ab()}

    def _power_split_enabled(self) -> bool:
        """Smart power split (CPU clock cap in GPU-bound games): on unless the player turned it off."""
        return self._settings.get("power_split") is not False

    def set_power_split(self, enabled: bool) -> Dict[str, Any]:
        self._settings["power_split"] = bool(enabled)
        self._save_settings()
        if self._split is not None:
            self._split.enabled = bool(enabled) and not (self._split_memory and self._split_memory.disabled())
        self._poke()
        return {"success": True, "error": None, "power_split": self._power_split_enabled()}

    def set_frame_os_act_unlock(self, enabled: bool) -> Dict[str, Any]:
        self._settings["frame_os_act_unlocked"] = bool(enabled)
        if not enabled:
            # locking means "back to measuring": a later unlock must not silently re-arm Act
            for value in (self._settings.get("profiles") or {}).values():
                if isinstance(value, dict) and value.get("frame_os") == "act":
                    value["frame_os"] = "observe"
        self._save_settings()
        try:
            self._sync_frame_os_marker()   # a locked Act profile stops loading the layer
        except OSError as error:
            return {"success": False, "error": f"marker: {error}"}
        self._poke()
        return {"success": True, "error": None, "act_unlocked": self._frame_os_act_unlocked()}

    def frame_os_features(self, profile: str) -> Dict[str, bool]:
        raw = self._profile_settings(profile).get("frame_os_features")
        raw = raw if isinstance(raw, dict) else {}
        return {"latency": raw.get("latency") is not False,
                "shield": raw.get("shield") is True}

    def set_frame_os_feature(self, profile: str, feature: str, enabled: bool) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        if not profile or feature not in ("latency", "shield") or type(enabled) is not bool:
            return {"success": False, "error": "Profile, latency/shield and a boolean are required"}
        settings = self._settings.setdefault("profiles", {}).setdefault(profile, {})
        previous = settings.get("frame_os_features")
        features = {**self.frame_os_features(profile), feature: enabled}
        settings["frame_os_features"] = features
        try:
            self._save_settings()
        except OSError as error:
            if previous is None:
                settings.pop("frame_os_features", None)
            else:
                settings["frame_os_features"] = previous
            return {"success": False, "error": str(error)}
        self._poke()
        return {"success": True, "error": None, "profile": profile, "features": features}

    def _frame_os_mode(self, profile: str) -> str:
        mode = str(self._profile_settings(profile).get("frame_os", "off"))
        if mode == "act" and not self._frame_os_act_unlocked():
            # Also protects profiles saved by an older build; a new UI alone is not a safety gate.
            return "off"
        return mode if mode in self.FRAME_OS_MODES else "off"

    def set_frame_os(self, profile: str, mode: str) -> Dict[str, Any]:
        """Development switch for GFG Frame OS.  observe/shadow never change frames; act does."""
        profile = str(profile or "").strip()
        if not profile or mode not in self.FRAME_OS_MODES:
            return {"success": False, "error": "profile and a mode of off/observe/shadow/act are required"}
        if mode == "act" and not self._frame_os_act_unlocked():
            return {"success": False, "error": "Frame OS Act is locked until Deck validation; developer opt-in required"}
        self._settings.setdefault("profiles", {}).setdefault(profile, {})["frame_os"] = mode
        # Explicit re-arm is required after a session was protected from repeated
        # output starvation; switching back to Act represents that explicit choice.
        if profile == self._active_profile and mode == "act":
            self._injection_starvation_yields = 0
            self._injection_hold_until = 0.0
        self._save_settings()
        try:
            self._sync_frame_os_marker()
        except OSError as error:
            return {"success": False, "error": f"marker: {error}"}
        self._poke()
        return {"success": True, "error": None, "profile": profile, "mode": mode, "relaunch_required": True}

    def _sync_frame_os_marker(self) -> None:
        """The launcher loads the gfg-pacer layer only while some profile uses Frame OS."""
        profiles = list(dict.fromkeys([*self._saved_profile_names(),
                                          *self._settings.get("profiles", {})]))
        wanted = any(self._frame_os_mode(profile) != "off" for profile in profiles)
        if wanted:
            # The launcher loads the layer only when it is staged; a build without it stays inert.
            if self.frame_os_layer_dir is not None:
                staged = frame_os_layer.stage(self.frame_os_layer_source, self.frame_os_layer_dir, self.log,
                                              registry_dir=self.frame_os_registry_dir)
                self.frame_os_layer_error = staged["error"]
            self.frame_os_marker_path.parent.mkdir(parents=True, exist_ok=True)
            self.frame_os_marker_path.write_text("enabled\n", encoding="utf-8")
        else:
            try:
                self.frame_os_marker_path.unlink()
            except FileNotFoundError:
                pass
        # Ring HUD: the launcher adds the GFG HUD layer while some profile shows the rings.
        selected = self._current_hud_profile()
        rings = bool(selected and self.hud_settings(selected)["enabled"]
                     and self.hud_settings(selected)["style"] == "rings")
        if rings and self.frame_os_layer_dir is not None:
            staged = frame_os_layer.stage(self.frame_os_layer_source, self.frame_os_layer_dir, self.log,
                                          registry_dir=self.frame_os_registry_dir, layer_key="hud")
            self.ring_hud_layer_error = staged["error"]
            self.ring_hud_marker_path.parent.mkdir(parents=True, exist_ok=True)
            self.ring_hud_marker_path.write_text("enabled\n", encoding="utf-8")
        else:
            try:
                self.ring_hud_marker_path.unlink()
            except FileNotFoundError:
                pass

    def _trusted_game_focus(self) -> Optional[bool]:
        """Treat a missing Steam focus-restored event as unknown, never permanent REST."""
        focus = getattr(self.observer, "game_focused", None)
        focus_at = getattr(self.observer, "game_focused_at", None)
        if focus is False and (focus_at is None or self.observer.time_fn() - focus_at > 5.0):
            return None
        return focus

    MENU_MAX_S = 120.0

    def _menu_covering(self) -> bool:
        """Steam's menu covers the game.  The renderer reports focus only when it changes, so a
        menu left open stays "covering" past the 5 s freshness of the event, until the output is
        visibly back at target (the game shows again: the focus-restored event was missed) or for
        at most MENU_MAX_S.  Review 1.3.0: expiring after 5 s let menu samples (generation
        suspended) be judged as a starved point and lock Act out for the session."""
        focus = getattr(self.observer, "game_focused", None)
        if focus is not False:
            return False
        at = getattr(self.observer, "game_focused_at", None)
        age = None if at is None else self.observer.time_fn() - at
        if age is not None and age <= 5.0:
            return True
        if age is None:
            return False
        budget = self._budget
        target = float(budget.point.target_output_fps) if budget is not None else float(
            self._status.get("target_output_fps") or 0)
        summary = self.observer.summary(self.FAST_CHECK_SECONDS)
        output = (summary.get("output") or {}).get("median")
        real = (summary.get("real") or {}).get("median")
        back = isinstance(output, (int, float)) and target > 0 and output >= 0.85 * target
        # Under the menu the renderer suspends generation (output ~ real frames); generated frames
        # on screen mean the game shows, even when the point is starved (field case 1.2.3).
        generating = (isinstance(output, (int, float)) and isinstance(real, (int, float)) and real > 0
                      and output >= 1.4 * real)
        if back or generating:
            return False
        if age <= self.MENU_MAX_S:
            return True
        # Long-lived Steam menus still suspend generation. Expired focus
        # timestamps alone do not prove anything in native (x1) mode.
        point = self._point or {}
        multiplier = point.get("multiplier") if isinstance(point, dict) else None
        return (isinstance(multiplier, (int, float)) and multiplier > 1.2
                and isinstance(output, (int, float)) and isinstance(real, (int, float))
                and real > 0 and output < 1.2 * real)

    def _configure_frame_os(self, profile: str) -> None:
        budget = self._budget
        mode = self._frame_os_mode(profile) if profile else "off"
        live = bool(budget is not None and self._point is not None and self._status.get("enabled"))
        if mode == "off" or not live:
            self.frame_os.configure(enabled=False, mode="observe", output_hz=0, calm_real_hz=0,
                                    max_multiplier=1, calm_w=None)
            return
        point = budget.point
        # rest for as long as Steam's menu really covers the game (the event is sent only once)
        self.frame_os.focused = False if self._menu_covering() else self._trusted_game_focus()
        self.frame_os.proof.enabled = self._frame_os_ab()
        try:
            self.frame_os.draw_w = self.power.status().get("draw_w")
        except Exception:
            self.frame_os.draw_w = (self._status.get("power_feedback") or {}).get("draw_w")
        self.frame_os.configure(
            enabled=True, mode=mode, output_hz=float(point.target_output_fps),
            calm_real_hz=float(point.base_target_fps),
            max_multiplier=float(self.observer.current_max_multiplier or 3.0),
            calm_w=budget.tdp if budget.tdp_control else None,
            latency_enabled=self.frame_os_features(profile)["latency"],
            stall_shield_enabled=self.frame_os_features(profile)["shield"],
        )
        self._sync_frame_os_memory(profile)

    def _frame_os_games(self) -> Dict[str, Any]:
        games = self._settings.get("frame_os_games")
        if not isinstance(games, dict):
            games = self._settings["frame_os_games"] = {}
        return games

    def _sync_frame_os_memory(self, profile: str) -> None:
        """Load this game's Frame OS memory once per game session, then store new A/B pairs as they
        arrive (rare: one control window per 20-90 s) and switch off effects they rule out."""
        launch = self._launch if isinstance(self._launch, dict) else {}
        launch_key = tuple(launch.get("launch_key") or ()) if launch.get("running") else ()
        prefix = self._fo_memory_key[0] if self._fo_memory_key else game_prefix(profile, self._game_app_id())
        # Review 1.3.0: only a real new launch starts a memory session; a probe that briefly says
        # "not running" (every game exit, a failed probe) must not re-load or count a session.
        if launch_key and launch_key != (self._fo_memory_key or (None, None))[1]:
            prefix = game_prefix(profile, self._game_app_id())
            key = (prefix, launch_key)
            memory = GameMemory(self._frame_os_games().get(prefix))
            disabled = memory.start_session()
            self._fo_memory, self._fo_memory_key = memory, key
            # this session's pairs are new: what the meter holds belongs to the game before
            self.frame_os.proof.pairs = {m: [] for m in FRAME_OS_METRICS}
            self._fo_saved = {m: 0 for m in FRAME_OS_METRICS}
            self.frame_os.apply_memory(disabled, seed_pairs(memory))
            self._frame_os_games()[prefix] = memory.to_record()
            self._save_settings_quietly()
            for effect, why in memory.ruled_out.items():
                self._journal("frame-os-effect-off", profile=profile, game=prefix, effect=effect, verdict=why)
            return
        memory = self._fo_memory
        if memory is None:
            return
        fresh: Dict[str, List[float]] = {}
        for metric in FRAME_OS_METRICS:
            pairs = self.frame_os.proof.pairs[metric]
            saved = self._fo_saved.get(metric, 0)
            if len(pairs) < saved:
                saved = 0          # the runner started over (Frame OS switched off and on)
            if len(pairs) > saved:
                fresh[metric] = list(pairs[saved:])
            self._fo_saved[metric] = len(pairs)
        if not fresh:
            return
        memory.add_pairs(fresh)
        self._frame_os_games()[prefix] = memory.to_record()
        self._save_settings_quietly()

    def _split_games(self) -> Dict[str, Any]:
        games = self._settings.get("power_split_games")
        if not isinstance(games, dict):
            games = self._settings["power_split_games"] = {}
        return games

    def _sync_split_memory(self, profile: str) -> None:
        """A new game launch starts a power split session (this game's memory, a fresh ladder);
        a probe that briefly says "not running" does not (same rule as the Frame OS memory)."""
        launch = self._launch if isinstance(self._launch, dict) else {}
        launch_key = tuple(launch.get("launch_key") or ()) if launch.get("running") else ()
        if launch_key and launch_key != (self._split_key or (None, None))[1]:
            if not self.cpu.discover():
                return
            prefix = game_prefix(profile, self._game_app_id())
            memory = SplitMemory(self._split_games().get(prefix))
            off = memory.start_session()
            split = PowerSplit(levels_khz(self.cpu.max_khz, self.cpu.min_khz))
            split.enabled = self._power_split_enabled() and not off
            split.start_level = memory.level
            split.prior_pairs = list(memory.pairs)
            self._split, self._split_memory, self._split_key = split, memory, (prefix, launch_key)
            self.cpu.release_external()
            self._split_games()[prefix] = memory.to_record()
            self._save_settings_quietly()
            if memory.ruled_out:
                self._event("power-split-off", "no-measured-benefit", profile=profile, game=prefix,
                            pairs=len(memory.pairs))
            return
        if self._split is not None and self._split_memory is not None and self._split_key is not None:
            if self._split_memory.record(self._split):
                self._split_games()[self._split_key[0]] = self._split_memory.to_record()
                self._save_settings_quietly()

    async def _sync_power_split(self, profile: str) -> None:
        """Step the CPU clock cap once per iteration.  Anything but a live budget point at its
        watts (a pending point, Act, a menu, a loading screen, no game) runs uncapped."""
        ready, self._split_ready = self._split_ready, None
        if getattr(self.cpu, "restore_pending", False):
            await asyncio.to_thread(self.cpu.restore)
        self._sync_split_memory(profile)
        split, budget = self._split, self._budget
        if split is None:
            if self.cpu.owned:
                await asyncio.to_thread(self.cpu.restore)
            self._status["power_split"] = {"enabled": self._power_split_enabled(), "phase": "off",
                                           "available": bool(self.cpu.discover())}
            return
        # a point that changed later in this iteration has other real frames: wait for it to be live
        eligible = bool(ready and budget is not None and budget.point.key == ready[0]
                        and budget.tdp_control and self.power.state.owned
                        and not self._menu_covering() and self._trusted_game_focus() is not False
                        and not self.cpu.external_change
                        and not getattr(self.cpu, "restore_pending", False))
        if eligible and split.enabled and not self.cpu.owned:
            eligible = await asyncio.to_thread(self.cpu.claim)
        sensors = self._status.get("sensors") or {}
        recent = self.observer.summary(self.FAST_CHECK_SECONDS)
        draw = statistics.median(self._draw_samples[-3:]) if self._draw_samples else None
        target_real = ready[1] if ready else 0.0
        now = self._clock()
        pairs_before = len(split.pairs)
        cap = split.step(now, eligible, SplitSample(
            real_fps=(recent.get("real") or {}).get("median"), target_real=target_real,
            top_core_pct=sensors.get("cpu_top_core_pct"), gpu_busy_pct=sensors.get("gpu_busy_pct"),
            gpu_mhz=sensors.get("gpu_clock_mhz"), draw_w=draw, tdp_w=self._applied_tdp,
            steady=budget is not None and budget.phase == "locked"))
        if self.cpu.owned:
            if cap is None and split.level == 0 and split.ab_phase is None:
                await asyncio.to_thread(self.cpu.restore)
            elif not await asyncio.to_thread(self.cpu.set_cap_khz, cap):
                split.step(now, False, SplitSample(None, target_real, None, None, None, None, None))
        change = split.last_change
        if change is not None:
            self._event("power-split", change["reason"], profile=profile, cpu_khz=change["to_khz"],
                        before_khz=change["from_khz"], level=change["level"], tdp_w=self._applied_tdp,
                        real=(recent.get("real") or {}).get("median"),
                        top_core=sensors.get("cpu_top_core_pct"), gpu_busy=sensors.get("gpu_busy_pct"))
        if len(split.pairs) > pairs_before:
            pair = split.pairs[-1]
            self._event("power-split-ab", "measured", profile=profile, **pair)
        self._status["power_split"] = {**split.summary(), "available": True,
                                       "control": self.cpu.status(),
                                       "game_off": bool(self._split_memory and self._split_memory.disabled())}

    # ------------------------------------------------------------------ Extreme (1.6)
    # Battery/Balanced suggest Extreme when the ceiling leaves at least this much power unused.
    EXTREME_OFFER_HEADROOM_W = 1.5

    def _extreme_offset(self, profile: str) -> float:
        return extreme_policy.clamp_offset(self._profile_settings(profile).get("extreme_sharpness_offset", 0.0))

    def set_extreme_sharpness(self, profile: str, offset: Any) -> Dict[str, Any]:
        """The player's sharpening correction on top of Extreme's table (GFG settings, never Saved)."""
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        value = extreme_policy.clamp_offset(offset)
        self._settings.setdefault("profiles", {}).setdefault(profile, {})["extreme_sharpness_offset"] = value
        self._save_settings()
        self._poke()
        return {"success": True, "error": None, "profile": profile, "offset": value}

    def _extreme_act_consent(self) -> Optional[bool]:
        value = self._settings.get("extreme_act_consent")
        return value if isinstance(value, bool) else None

    def set_extreme_act_consent(self, allow: bool) -> Dict[str, Any]:
        """The first Extreme switch asks once whether Frame OS Act may join (the existing opt-in)."""
        self._settings["extreme_act_consent"] = bool(allow)
        if allow:
            self._settings["frame_os_act_unlocked"] = True
        self._save_settings()
        return {"success": True, "error": None, "consent": bool(allow),
                "act_unlocked": self._frame_os_act_unlocked()}

    def _extreme_act_switch(self, profile: str, entering: bool) -> None:
        """Act follows Extreme for players who allowed it; leaving gives the old Frame OS mode back."""
        settings = self._settings.setdefault("profiles", {}).setdefault(profile, {})
        if entering:
            if self._extreme_act_consent() and self._frame_os_act_unlocked() and settings.get("frame_os") != "act":
                settings["extreme_prev_frame_os"] = str(settings.get("frame_os", "off"))
                settings["frame_os"] = "act"
        elif "extreme_prev_frame_os" in settings:
            previous = settings.pop("extreme_prev_frame_os")
            if settings.get("frame_os") == "act":   # the player did not change it meanwhile
                settings["frame_os"] = previous if previous in self.FRAME_OS_MODES else "off"
        try:
            self._sync_frame_os_marker()
        except OSError as error:
            self.log.debug("Frame OS marker not updated: %s", error)

    SCALE_IGNORED_TTL_S = 14 * 86400.0   # a game that ignores render scale is re-checked after this

    def _scale_ignored_games(self) -> Dict[str, Any]:
        games = self._settings.get("scale_ignored_games")
        if not isinstance(games, dict):
            games = self._settings["scale_ignored_games"] = {}
        return games

    def _game_ignores_scale(self, profile: str) -> Optional[str]:
        entry = self._scale_ignored_games().get(game_prefix(profile, self._game_app_id()))
        if isinstance(entry, dict) and time.time() - float(entry.get("at", 0)) < self.SCALE_IGNORED_TTL_S:
            return str(entry.get("reason") or "game-ignores-render-scale")
        return None

    def _block_scale(self, profile: str, reason: str) -> None:
        """No more render-scale trials this game session (any mode); a game that overrides the
        swapchain size is remembered, so the next sessions skip the scaled points at once."""
        self._scale_blocked = reason
        if reason == extreme_policy.GAME_IGNORES_SCALE:
            self._scale_ignored_games()[game_prefix(profile, self._game_app_id())] = {
                "reason": "game-ignores-render-scale", "at": round(time.time())}
            self._save_settings_quietly()
        self._event("render-scale-blocked", reason, profile=profile)

    def _scale_gate(self, profile: str, req: Request) -> str:
        """ok / wait / failed: a new render scale counts only once the renderer shows it.

        Every budget mode (since 1.6.1): a field log showed Battery "confirming" 30x3@80 on its
        frame ratio alone while the renderer reported the scaler inactive (the game kept its
        full-size swapchain), then buying watts up to 19 W for a resolution change that never
        happened.
        """
        budget = self._budget
        if budget is None:
            return "ok"
        rung = int(req.point.render_scale_pct)
        sharpness = req.deltas.get("scaling_sharpness")
        last = self._extreme_ack
        if rung >= 100 or rung == (last or {}).get("pct", 100):
            # Back to full resolution, or the same scale as before: nothing new to show.
            self._extreme_ack = {**(last or {"evidence": None, "mark": req.event_mark}), "pct": rung,
                                 "sharpness": sharpness,
                                 **({"mark": req.event_mark} if sharpness != (last or {}).get("sharpness") else {})}
            if rung >= 100 and (last or {}).get("pct", 100) < 100:
                self._extreme_ack["evidence"] = None
            return "ok"
        factor = req.deltas.get("scaling_factor")
        expected = (100.0 / float(factor) if isinstance(factor, (int, float)) and float(factor) > 0
                    else float(rung))   # relative to native: the profile's own scaling counts too
        evidence = self.observer.scaling_after(req.event_mark)
        record = extreme_policy.scale_acknowledged(evidence, expected)
        refused = extreme_policy.scale_refused(evidence) if record is None else None
        if record is None and refused is None:
            # Second source: the renderer's runtime-state file of the game's processes.
            states = self._extreme_runtime_states(req.created_wall)
            record = extreme_policy.scale_acknowledged(states, expected)
            refused = extreme_policy.scale_refused(states) if record is None else None
        if record is None:
            if refused is not None:
                # The renderer says the scaler is off: no reason to wait for the timeout.
                self._event("render-scale-refused", refused, profile=profile, point=req.point.key)
                self._block_scale(profile, refused)
                return "failed"
            if self._clock() - req.created <= extreme_policy.SCALE_ACK_TIMEOUT_S:
                return "wait"
            self._extreme_scale_failures += 1
            if self._extreme_scale_failures >= extreme_policy.MAX_SCALE_ACK_FAILURES:
                self._block_scale(profile, "renderer-did-not-confirm-render-scale")
            self._event("render-scale-not-acknowledged", "timeout", profile=profile, point=req.point.key,
                        failures=self._extreme_scale_failures)
            return "failed"
        self._extreme_scale_failures = 0
        self._extreme_ack = {"pct": rung, "sharpness": sharpness, "mark": req.event_mark,
                             "evidence": {k: record.get(k) for k in ("kind", "source", "output")}}
        self._event("render-scale-acknowledged", record.get("kind") or "", profile=profile, point=req.point.key,
                     render_pct=rung, native_pct=round(expected, 1), source=record.get("source"),
                     output=record.get("output"))
        return "ok"

    def _extreme_runtime_states(self, since_unix_s: float = 0.0) -> list:
        """The renderer's runtime-state records (next to the overlay and the Saved config)."""
        base = Path(self.configuration.config_dir)
        pids = [p for p in ((self._launch or {}).get("pids") or []) if isinstance(p, int)]
        try:
            return extreme_policy.read_runtime_states((base / OVERLAY_DIRNAME, base), pids, since_unix_s)
        except Exception as error:  # diagnostics only: never disturb the Governor
            self.log.debug("Renderer runtime state unreadable: %s", error)
            return []

    async def _refresh_extreme_sharpness(self, profile: str, saved: Optional[Dict[str, Any]]) -> None:
        """A changed sharpening correction goes live on the scaled point (no new trial: same scale)."""
        if (saved is None or self._request is not None or self._point is None
                or "scaling_sharpness" not in self._point_deltas):
            return
        pct = int(self._point.get("render_scale_pct", 100))
        want, _ = extreme_policy.sharpness_for(pct, saved, self._extreme_offset(profile))
        if want is None or want == self._point_deltas.get("scaling_sharpness"):
            return
        self._point_deltas = {**self._point_deltas, "scaling_sharpness": want}
        if self._injection is not None:
            self._injection = {**self._injection, "scaling_sharpness": want}
        desired = {**self._base_for(profile, saved), **(self._injection or self._point_deltas)}
        mark = self.observer.event_seq
        try:
            record = await asyncio.to_thread(self._ensure_overlay_sync, profile, desired, self._point["key"])
        except (OSError, ValueError) as error:
            self._event("extreme-sharpness-failed", "overlay-write-failed", profile=profile, error=str(error))
            return
        if record is not None:
            self._record = record
        if self._extreme_ack is not None:
            self._extreme_ack = {**self._extreme_ack, "sharpness": want, "mark": mark}
        self._event("extreme-sharpness-set", "player-correction", profile=profile, sharpness=want)

    def _sync_extreme(self, profile: str, saved: Optional[Dict[str, Any]]) -> None:
        """Extreme's status snapshot (cached for the UI; nothing here touches the system)."""
        mode = self._mode(profile) if profile else ""
        budget = self._budget
        launch_key = self._launch_key
        if launch_key != getattr(self, "_extreme_launch", None):
            self._extreme_launch = launch_key  # a new game session: a fresh chance for the scaler
            self._extreme_scale_failures, self._extreme_scale_blocked, self._scale_blocked = 0, None, None
        launch = self._launch or {}
        running = bool(launch.get("running"))
        capability = self._capability(profile, launch) if running else {}
        if mode != "extreme":
            self._status["extreme"] = {"enabled": False, "state": "OFF"}
            self._status["extreme_offer"] = self._extreme_offer(profile, mode, budget, running)
            return
        self._status.pop("extreme_offer", None)
        saved = saved or {}
        if extreme_policy.user_scaling(saved):
            self._extreme_scale_blocked = "profile-scaling"
        elif self._extreme_scale_blocked == "profile-scaling":
            self._extreme_scale_blocked = None
        wsi_blocked = (self._status.get("overlay") or {}).get("scale_ready_ignored")
        ack = self._extreme_ack or {}
        point = budget.point if budget is not None and budget.flavor == "extreme" else None
        applied_pct = ack.get("pct") if point is not None else None
        sharpness_ack = extreme_policy.sharpness_acknowledged(
            self.observer.scaling_after(int(ack.get("mark") or 0)), ack.get("sharpness")) if ack else None
        _, sharpness_reason = extreme_policy.sharpness_for(int(applied_pct or 100), saved, 0.0)
        requested_pct = point.render_scale_pct if point is not None else None
        verifying = bool(self._request is not None and budget is not None and budget.flavor == "extreme"
                         and int(self._request.point.render_scale_pct) != int(ack.get("pct", 100))
                         and self._status.get("reason") == "awaiting-render-scale-acknowledgement")
        split = {**(self._status.get("power_split") or {}), "setting": self._power_split_enabled()}
        cpu = self.cpu.status()
        split["available"] = bool(cpu.get("available") and cpu.get("writable"))
        split["restore_pending"] = bool(cpu.get("restore_pending"))
        split["cap_khz"] = cpu.get("cap_khz") if cpu.get("owned") and not split["restore_pending"] else None
        fo = self.frame_os.last or {}
        act_enabled = self._frame_os_mode(profile) == "act"
        facts = {
            "running": running,
            "scale_pct": int(applied_pct) if applied_pct is not None else None,
            "scale_ack": bool(ack.get("evidence")) or applied_pct == 100,
            "sharpness": ack.get("sharpness"),
            "sharpness_ack": sharpness_ack,
            "sharpness_reason": sharpness_reason,
            "scale_provisioned": bool(capability.get("scale_capable")),
            "scale_blocked": (self._extreme_scale_blocked or self._game_ignores_scale(profile)
                              or (self._scale_blocked if self._scale_blocked != extreme_policy.GAME_IGNORES_SCALE
                                  else "game-ignores-render-scale")
                              or (f"scale-ready-blocked:{wsi_blocked}" if wsi_blocked else None)),
            "cpu_bound": (self._status.get("diagnosis") or {}).get("bottleneck") == "cpu",
            "split": split,
            "act": {"consent": self._extreme_act_consent(), "enabled": act_enabled,
                    "pacer_live": bool((fo.get("telemetry") or {}).get("live")),
                    "injecting": self._injection is not None,
                    "acknowledged": bool(fo.get("acknowledged") and self.frame_os.executor_active)},
            "pacing": extreme_policy.pacing_facts(self.frame_os_features(profile), fo,
                        mode=self._frame_os_mode(profile), paused=self._status.get("state") == "PAUSED"),
            "warm_started": bool(budget is not None and budget.warm_started),
        }
        state = extreme_policy.session_state(
            enabled=True, running=running, overlay_active=bool(capability.get("overlay_active", running)),
            paused=self._status.get("state") == "PAUSED", request=self._request is not None,
            verifying_scale=verifying, phase=budget.phase if budget is not None else None,
            restart_required=False)
        ceiling = self._extreme_ceiling or self._extreme_power_ceiling()
        if running and self._clock() - self._extreme_rs_at >= 5.0:
            # What the renderer itself reports about scaling (diagnostics for logs, 1 per 5 s).
            self._extreme_rs_at = self._clock()
            states = self._extreme_runtime_states()
            self._extreme_rs = states[-1] if states else None
        seen = self.observer.latest_scaling
        renderer = {"event": {k: seen.get(k) for k in ("kind", "source", "output", "effective_factor", "sharpness")}
                    if seen else None,
                    "runtime_state": {k: (self._extreme_rs or {}).get(k) for k in (
                        "active", "source", "output", "effective_factor", "method", "reason")}
                    if self._extreme_rs else None}
        self._status["extreme"] = {
            "enabled": True,
            "state": state,
            "reason": self._status.get("reason"),
            "ceiling": ceiling,
            "tdp_w": budget.tdp if budget is not None else None,
            "requested": {"render_pct": requested_pct,
                          "sharpness": (self._request.deltas.get("scaling_sharpness") if self._request
                                        else self._point_deltas.get("scaling_sharpness"))} if point is not None else None,
            "applied": ({"render_pct": int(applied_pct),
                         "sharpness": ack.get("sharpness") if sharpness_ack else None,
                         "sharpness_confirmed": sharpness_ack,
                         "source": (ack.get("evidence") or {}).get("source"),
                         "output": (ack.get("evidence") or {}).get("output")}
                        if applied_pct is not None and self._point is not None else None),
            "sharpness_offset": self._extreme_offset(profile),
            "act_consent": self._extreme_act_consent(),
            "feature_settings": self.frame_os_features(profile),
            "renderer_scaling": renderer,
            "boosters": extreme_policy.booster_states(facts),
            "gain": extreme_policy.gain_unavailable(),
        }

    def _extreme_offer(self, profile: str, mode: str, budget: Optional[BudgetController],
                       running: bool) -> Optional[Dict[str, Any]]:
        """Battery/Balanced: power the ceiling would still give to frames, without a promised number."""
        if mode not in ("budget", "balanced") or not running or budget is None or not budget.tdp_control:
            return None
        if budget.phase != "locked" or budget.tdp is None or budget.heat_limited:
            return None
        if (self._status.get("diagnosis") or {}).get("bottleneck") == "cpu":
            return None
        ceiling = self._extreme_power_ceiling()
        headroom = round(ceiling["ceiling_w"] - float(budget.tdp), 1)
        if headroom < self.EXTREME_OFFER_HEADROOM_W:
            return None
        return {"headroom_w": headroom, "ceiling_w": ceiling["ceiling_w"], "tdp_w": budget.tdp,
                "real_target": budget.point.base_target_fps}

    def _save_settings_quietly(self) -> None:
        try:
            self._save_settings()
        except OSError as error:
            self.log.debug("Frame OS memory not stored: %s", error)

    def set_scale_ready(self, profile: str, scale_ready: bool) -> Dict[str, Any]:
        profile = str(profile or "").strip()
        if not profile:
            return {"success": False, "error": "Profile is required"}
        value = self._settings.setdefault("profiles", {}).setdefault(profile, {})
        value["scale_ready"] = bool(scale_ready)
        self._save_settings()
        error = self._ensure_base_overlay_sync(profile)
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
            with self._io_lock:
                self.overlay.ensure(profile, self._base_for(profile, saved), point_key="base")
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
        try:
            await asyncio.to_thread(self._sync_hud_presence)
        except OSError as error:
            self.log.debug("Governor could not prepare the hidden HUD config: %s", error)
        reopen = getattr(self.power, "reopen", None)
        if callable(reopen):
            reopen()
        await asyncio.to_thread(self.power.discover)
        self.cpu.reopen()
        try:  # also puts back a CPU clock limit a crashed session left behind
            await asyncio.to_thread(self.cpu.discover)
        except Exception as error:
            self.log.debug("CPU clock control unavailable: %s", error)
        try:
            await asyncio.to_thread(self._sync_frame_os_marker)
        except OSError as error:
            self.log.debug("Frame OS marker not written: %s", error)
        self.frame_os.start()
        self._wake = asyncio.Event()
        self._wake_loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._loop())

    def _reconcile_overlays(self) -> None:
        """After a plugin restart: refresh leases of enabled profiles, restore the rest."""
        if self.overlay is None:
            return
        names = list(dict.fromkeys([*self._saved_profile_names(), *self._settings.get("profiles", {})]))
        for profile in names:
            error = self._ensure_base_overlay_sync(profile)
            if error:
                self._restore_pending[profile] = "startup-reconcile"
        self._standby_overlays_sync(force=True)

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
        await self.frame_os.stop()
        # Restore overlays to Saved (verified, lease dropped) before power ownership is released.
        names = list(dict.fromkeys([*self._saved_profile_names(), *self._settings.get("profiles", {})]))
        for profile in names:
            error = await asyncio.to_thread(self._restore_overlay_sync, profile, True)
            if error:
                self.log.error("Governor could not restore overlay for %s on unload: %s", profile, error)
                self._event("overlay-restore-failed", "plugin-stop", profile=profile, error=error)
        self._reset_run_state()
        try:
            # shutdown(): waits for a write still running in a worker thread, then restores and
            # refuses later writes, so a slow write cannot land after the restore.
            shutdown = getattr(self.power, "shutdown", None)
            result = await asyncio.to_thread(shutdown if callable(shutdown) else self.power.restore_if_owned)
            if result.get("restored"):
                self._event("power-restored", "plugin-stop")
        except Exception as error:
            self.log.warning("Governor could not restore owned TDP: %s", error)
        try:
            await asyncio.to_thread(self.cpu.shutdown)
        except Exception as error:
            self.log.warning("Governor could not restore the CPU clock limit: %s", error)

    def get_status(self, profile: str = "") -> Dict[str, Any]:
        value = dict(self._status)
        if profile and profile != value.get("profile"):
            value["requested_profile"] = profile
            value["enabled"] = self._profile_enabled(profile)
        value["scale_ready"] = self._scale_ready(profile or value.get("profile", ""))
        value["hud"] = self.hud_settings(profile or value.get("profile", ""))
        value["effort"] = self._effort.status()
        value["session"] = self.session_stats.summary()
        value["last_session"] = self._settings.get("last_session")
        value["session_history"] = (self._settings.get("session_history") or [])[: self.SESSION_HISTORY]
        value["frame_os"] = {"mode": self._frame_os_mode(profile or value.get("profile", "")),
                             "act_unlocked": self._frame_os_act_unlocked(),
                             "ab": self._frame_os_ab(),
                             "feature_settings": self.frame_os_features(profile or value.get("profile", "")),
                             "game": self._fo_memory.summary() if self._fo_memory is not None else None,
                             "starvation_yields": self._injection_starvation_yields,
                             "output_starvation_lockout": self._injection_starvation_yields >= 2,
                             "layer_installed": bool(self.frame_os_layer_dir and frame_os_layer.is_staged(self.frame_os_layer_dir)),
                             "layer_error": self.frame_os_layer_error,
                             **{k: v for k, v in self.frame_os.last.items() if k != "input"}}
        value["power_split"] = {**(self._status.get("power_split") or {}), "setting": self._power_split_enabled(),
                                "control": self.cpu.status()}
        value["extreme"] = self._status.get("extreme") or {"enabled": False, "state": "OFF"}
        value["scale_blocked"] = (("game-ignores-render-scale" if self._scale_blocked == extreme_policy.GAME_IGNORES_SCALE
                                   else self._scale_blocked)
                                  or (self._game_ignores_scale(profile) if profile else None))
        value["power"] = self.power.status()
        value["power_search"] = self.search.status.to_dict()
        value["request"] = self._request.to_dict() if self._request else None
        value["active_point"] = self._point
        value["active_point_mode"] = self._point_mode
        value["ladder"] = self._ladder.status() if self._ladder else None
        value["mode"] = self._mode(profile or value.get("profile", ""))
        value["budget"] = self._budget.status() if self._budget else None
        if self._restore_pending:
            value["restore_pending"] = dict(self._restore_pending)
        return value

    def _display_probe(self) -> Dict[str, Any]:
        """Active display + the internal panel's actual refresh rate when Gamescope reports it."""
        result = self.display.get_active_display_info()
        reader = getattr(self.display, "read_current_refresh_hz", None)
        if isinstance(result, dict) and result.get("success") and not result.get("external") and callable(reader):
            try:
                result = {**result, "current_refresh_hz": reader()}
            except Exception as error:
                self.log.debug("Governor refresh-rate probe unavailable: %s", error)
        return result

    async def _display_info(self) -> Dict[str, Any]:
        now = time.monotonic()
        if now - self._last_display_poll < self.DISPLAY_REFRESH_SECONDS and self._last_display:
            return self._last_display
        self._last_display_poll = now
        try:
            result = await asyncio.to_thread(self._display_probe)
            if isinstance(result, dict) and result.get("success"):
                self._last_display = result
        except Exception as error:
            self.log.debug("Governor display probe unavailable: %s", error)
        return self._last_display

    # -------------------------------------------------------------- helpers
    async def _restore_power(self, reason: str) -> None:
        profile = self._active_profile
        continuing_extreme = (
            profile and self._profile_enabled(profile) and self._mode(profile) == "extreme"
            and reason in ("governor-mode-changed", "display-mode-changed", "ladder-exhausted",
                           "not-healthy-at-ceiling", "renderer-capacity-unavailable",
                           "renderer-capacity-request-cancelled")
        )
        if continuing_extreme:
            # Replanning is not leaving Extreme: restoring a 20 W baseline here
            # created the transition overshoots in the field recordings.
            await self._budget_power(profile)
        else:
            setter = getattr(self.power, "set_ceiling_w", None)
            if callable(setter):
                setter(None)
            restored = await asyncio.to_thread(self.power.restore_if_owned)
            if restored.get("restored"):
                self._event("power-restored", reason)
        if self.cpu.owned:                # the CPU clock goes back with the watts
            await asyncio.to_thread(self.cpu.restore)
        if self._split is not None and self._split.level:
            self._split.step(self._clock(), False, SplitSample(None, 0.0, None, None, None, None, None))
        self.search = PowerSearch()

    def _clear_point_state(self) -> None:
        self._extreme_ack = None  # the overlay goes back to the launch scale
        self._point = None
        self._point_mode = ""
        self._point_external = None
        self._point_deltas = {}
        self._injection = None
        self._injection_started_at = None
        self.frame_os.executor_active = False
        self._request = None
        self._ladder = None
        # Failures the controller found since its last drain would be lost with it.
        self._store_failures(self._budget)
        self._budget = None
        self._budget_keys = None
        self._applied_tdp = None
        self._over_cap_windows = 0
        self._draw_samples = []
        self._fast_point_key = None
        self._fast_last_sample_seq = self.observer.sample_seq
        self._rollback_deltas = None
        self._synced_deltas = None
        self._evaluation_after_seq = self.observer.sample_seq
        # Per-point state that must not outlive the point (audit 1.0.7).  A ladder kept on purpose
        # sets ``_exhausted`` again right after (``_release_point_keep_ladder``).
        self._exhausted = False
        # Reclaim attempts against an outside TDP tool are kept (they reset with the profile or
        # enable state): a new game or display change must not restart that fight.
        self._status.pop("power_feedback", None)
        self._status.pop("last_verdict", None)

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
            if reason == "startup-reconcile":
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
        sharpness = None
        if self._mode(profile) == "extreme":
            sharpness, _ = extreme_policy.sharpness_for(point.render_scale_pct, saved, self._extreme_offset(profile))
        deltas = point_deltas(
            point.to_dict(), saved,
            scale_capable=bool(capability.get("scale_capable")),
            scale_ready=self._scale_ready(profile),
            sharpness=sharpness,
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
        self._injection = None  # this write replaced any Act overlay
        self.frame_os.executor_active = False
        self._ladder.mark_attempt() if self._ladder else None
        self._request = Request(
            request_id=self._request_counter, point=point, deltas=full, previous_deltas=previous,
            revision=record.revision, created=self._clock(), event_mark=mark,
            generation=generation, external=external, created_wall=time.time(),
        )
        self._point_deltas_pending = full
        self._event("operating-point-requested", "ladder-trial", profile=profile, point=point.key,
                    revision=record.revision, request_id=self._request_counter)
        self._status.update({"state": "APPLY", "reason": "awaiting-renderer-confirmation"})
        return True

    EARLY_DELIVERED_SPAN_SECONDS = EARLY_DELIVERED_SPAN_SECONDS
    SESSION_HISTORY = 8

    def _evaluate_confirmation(self, req: Request) -> tuple[str, str]:
        """Return (wait|confirmed|failed, reason).  Never trusts the file write."""
        return evaluate_confirmation(
            req, self.observer, self._clock(), budget=True,  # Quality too since 1.0.6: reject in 8 s, not 25
            min_samples=self.MIN_SAMPLES, min_span_s=self.MIN_SAMPLE_SPAN_SECONDS,
            timeout_s=self.CONFIRM_TIMEOUT_SECONDS, early_span_s=self.EARLY_DELIVERED_SPAN_SECONDS,
            fast_mismatch=self._budget is None,  # only Quality; Battery uses its own point guard
        )

    async def _fail_request(self, profile: str, reason: str) -> None:
        req = self._request
        self._request = None
        if req is None:
            return
        if self._ladder is not None:
            self._ladder.reject(req.point.key, reason)
            if self._budget is None and reason not in self.TRANSIENT_FAILURES:
                self._remember_ladder_failure(profile, req.point)
        if self._budget is not None:
            observed = None
            if reason in ("confirmation-timeout", "delivered-deeper-ratio"):
                recent = self.observer.summary(self.WINDOW_SECONDS, after_event_seq=req.event_mark)
                observed = {"real": (recent.get("real") or {}).get("median"),
                            "output": (recent.get("output") or {}).get("median")}
            self._budget.request_failed(self._clock(), reason, observed)
        self._event("operating-point-rejected", reason, profile=profile, point=req.point.key,
                    revision=req.revision, request_id=req.request_id,
                    cadence=confirmation_evidence(req, self.observer),
                    bottleneck=(self._status.get("diagnosis") or {}).get("bottleneck"))
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
        desired = {**base, **(self._injection or self._point_deltas)}
        key = self._point["key"] if self._point else "base"
        try:
            record = await asyncio.to_thread(self._ensure_overlay_sync, profile, desired, key)
            if record is not None:
                self._record = record
            self._saved_fp = fingerprint
        except (OSError, ValueError) as error:
            self._status.setdefault("overlay", {})["sync_error"] = str(error)

    def _journal(self, kind: str, **fields: Any) -> None:
        if self.activity is not None:
            self.activity.record("governor", kind, **fields)

    def _journal_power(self, kind: str, **fields: Any) -> None:
        self._journal(kind, profile=self._status.get("profile"), **fields)

    def _sample_session(self) -> None:
        """One time-weighted sample for the player's session summary (fresh telemetry only)."""
        if self.session_stats.started is None or not self._status.get("enabled"):
            return
        if self._menu_covering():
            self.session_stats.last = self._clock()  # Steam's menu: not part of the averages
            return
        tel = self._status.get("telemetry") or {}
        snap, summary = tel.get("snapshot") or {}, tel.get("summary") or {}
        if not snap.get("available") or (1e9 if snap.get("sample_age_ms") is None else snap["sample_age_ms"]) > self.MAX_SAMPLE_AGE_MS:
            self.session_stats.last = self._clock()  # loading screen / menu: not part of the averages
            return
        try:
            power = self.power.status()
        except Exception:
            power = {}
        diagnosis = self._status.get("diagnosis") or {}
        self.session_stats.add(
            self._clock(),
            output=(summary.get("output") or {}).get("median"),
            real=(summary.get("real") or {}).get("median"),
            tdp=power.get("observed_tdp_w"), draw=power.get("draw_w"),
            reference_w=power.get("initial_tdp_w") if power.get("owned") else None,
            temp_c=(self._status.get("sensors") or {}).get("temp_c"),
            stuttering=diagnosis.get("smoothness") == "stuttering",
            hot=diagnosis.get("thermal") in ("hot", "heating"),
            mode=self._mode(self._session_profile or str(self._status.get("profile") or "")),
            battery_w=self._battery_discharge_w(),
            frame_os=self._frame_os_level(),
            benefit=(self.frame_os.last or {}).get("benefit") if self._frame_os_level() else None,
        )

    def _frame_os_level(self) -> Optional[str]:
        last = self.frame_os.last or {}
        if not last.get("enabled") or not (last.get("telemetry") or {}).get("live"):
            return None
        level = (last.get("decision") or {}).get("level")
        return f"{level}" if last.get("acting") else (f"{level}?" if level else None)

    def _battery_discharge_w(self) -> Optional[float]:
        battery = self._status.get("battery") or {}
        power = battery.get("power_uw")
        if not battery.get("discharging") or not isinstance(power, (int, float)) or power <= 500_000:
            return None  # on the charger (or noise): no battery time to gain
        return float(power) / 1_000_000.0

    def _finish_session(self) -> None:
        """Store the summary under the profile the game was played with (audit 1.0.7: a profile
        switch before the exit was seen filed it under the new one)."""
        profile = self._session_profile
        result = self.session_stats.finish()
        if result is None:
            return
        # The mode comes from the per-mode seconds ("mixed" after a switch); the current mode only
        # when none was sampled.
        result.setdefault("mode", self._mode(profile) if profile else "")
        result.update({"ended": time.time(), "profile": profile or "", "app_id": self._session_app_id})
        power = self.power.status()
        result["energy_reference_w"] = power.get("gamescope_max_tdp_w") or power.get("maximum_tdp_w")
        self._settings["last_session"] = result
        history = [h for h in self._settings.get("session_history") or [] if isinstance(h, dict)]
        self._settings["session_history"] = ([result] + history)[: self.SESSION_HISTORY]
        try:
            self._save_settings()
        except OSError as error:
            self.log.debug("Session summary not stored: %s", error)

    def _journal_transitions(self) -> None:
        status = self._status
        key = (status.get("enabled"), status.get("state"), status.get("reason"))
        if key != self._journal_state:
            self._journal_state = key
            self._journal("state", enabled=key[0], state=key[1], reason=key[2], profile=status.get("profile"),
                          point=(self._point or {}).get("key"), capability=status.get("capability"))
        launch = self._launch if status.get("enabled") else None
        if launch is None:
            if not status.get("enabled") and self._journal_game is not None:
                self._finish_session()  # turned off mid-game: the session ends now, not at re-enable
                self._journal_game = None
            return
        game = tuple(launch.get("launch_key") or ()) if launch.get("running") else None
        if game != self._journal_game:
            if self._journal_game is not None:
                self._finish_session()
            if game is not None:
                self.session_stats.start(game, self._clock())
                self._session_profile = str(status.get("profile") or "")
                self._session_app_id = str(launch.get("app_id") or "")  # the launch is gone by the exit
                self._journal("game-detected", profile=status.get("profile"), launch_key=list(game),
                              governor_launch=bool(launch.get("governor_launch")),
                              renderer_loaded=launch.get("renderer_loaded"))
            elif self._journal_game is not None:
                self._journal("game-exited", profile=status.get("profile"), launch_key=list(self._journal_game),
                              reason=launch.get("reason"))
            self._journal_game = game

    # Diagnostics are on in every managed game: keep one session's log bounded.
    DIAGNOSTICS_LOG_MAX_BYTES = 64 * 1024 * 1024

    def _cap_diagnostics_log(self) -> None:
        """Truncate an oversized diagnostics log in place.

        The wrapper opens it with ``>>`` (O_APPEND), so the game keeps writing
        at the new end, and the telemetry tailer already survives truncation.
        """
        try:
            if self.diagnostics_log_path.stat().st_size > self.DIAGNOSTICS_LOG_MAX_BYTES:
                os.truncate(self.diagnostics_log_path, 0)
                if self.observer.path == self.diagnostics_log_path:
                    self.observer.rewind_after_truncation()
                self._event("diagnostics-log-truncated", "size-cap", limit=self.DIAGNOSTICS_LOG_MAX_BYTES)
        except OSError:
            pass

    async def _iteration(self) -> None:
        await asyncio.to_thread(self._cap_diagnostics_log)
        await self._iteration_core()
        self._journal_transitions()
        self._update_effort()
        self._update_battery()
        await asyncio.to_thread(self._update_sensors)
        self._sample_session()
        profile = self._status.get("profile") or ""
        try:
            await self._sync_power_split(profile)
        except Exception as error:  # never disturb the Governor; the cap goes back
            self.log.warning("Power split step failed: %s", error)
            await asyncio.to_thread(self.cpu.restore)
        try:
            saved = (await asyncio.to_thread(self._saved_profile_config, profile)
                     if profile and self._mode(profile) == "extreme" else None)
            await self._refresh_extreme_sharpness(profile, saved)
            self._sync_extreme(profile, saved)
        except Exception as error:  # status only: never disturb the Governor
            self.log.warning("Extreme step failed: %s", error)
        try:
            self._configure_frame_os(profile)
        except Exception as error:  # development feature: never disturb the Governor
            self.log.debug("Frame OS configure failed: %s", error)
        if profile:
            await asyncio.to_thread(self._sync_hud, profile)

    async def _sample_passive_hud(self, profile: str) -> None:
        """Keep the 1 Hz overlay accurate without claiming TDP or changing renderer settings."""
        if not self.hud_settings(profile)["enabled"]:
            return
        await asyncio.to_thread(self.observer.poll)
        snapshot = self.observer.snapshot()
        self._status["telemetry"] = {
            "snapshot": snapshot,
            "summary": self.observer.summary(self.WINDOW_SECONDS),
        }
        # The ring layer reports size for an actual game session. This probe is
        # normally done by Governor, but a HUD-only user needs it too.
        await self._launch_info(profile)
        display = await self._display_info()
        external = bool(display.get("external", False))
        if self._device is None:
            self._device = await asyncio.to_thread(detect_model)
        policy = target_for(
            self._device["model"], external=external,
            valid_rates=display.get("valid_rates"),
            current_hz=display.get("current_refresh_hz"),
        )
        self._status.update({
            "target_output_fps": int(policy["target"]),
            "device": {**self._device, "mode": policy["mode"], "target_reason": policy["reason"]},
            "display": {
                "external": external,
                "internal": bool(display.get("internal", not external)),
                "valid_rates": display.get("valid_rates", []),
                "current_refresh_hz": display.get("current_refresh_hz"),
            },
        })

    async def _iteration_core(self) -> None:
        await asyncio.to_thread(self._standby_overlays_sync)
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
            # 1.2.2 ships with Rings on by default. The HUD is independent of
            # Governor power control: continue reading passive renderer FPS even
            # when optimization has been explicitly disabled.
            await self._sample_passive_hud(profile)
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
        policy = target_for(self._device["model"], external=external, valid_rates=display.get("valid_rates"),
                            current_hz=display.get("current_refresh_hz"))
        target = int(policy["target"])
        self._status.update({
            "target_output_fps": target,
            "device": {**self._device, "mode": policy["mode"], "target_reason": policy["reason"]},
            "display": {
                "external": external,
                "internal": bool(display.get("internal", not external)),
                "valid_rates": display.get("valid_rates", []),
                "current_refresh_hz": display.get("current_refresh_hz"),
            },
            "telemetry": {"snapshot": snapshot, "summary": summary},
        })

        # A new telemetry session / launch / display mode invalidates any applied point.
        launch = await self._launch_info(profile)
        launch_key = launch.get("launch_key") if launch.get("running") else None
        generation = snapshot.get("session_generation")
        # The panel's refresh rate changed the target: a controller built for the old one is stale.
        controller = self._budget or self._ladder
        target_changed = controller is not None and int(getattr(controller, "target_output_fps", target)) != target
        new_game_session = (
            (self._generation_seen is not None and generation != self._generation_seen)
            or (self._launch_key is not None and launch_key is not None and launch_key != self._launch_key)
        )
        if new_game_session:
            # A failed Act executor belongs to the old game/telemetry session.
            # Never carry the lockout to a different game.
            self._injection_starvation_yields = 0
            self._injection_hold_until = 0.0
        changed = (
            target_changed or new_game_session
            or (self._point_external is not None and external != self._point_external)
        )
        self._generation_seen = generation
        if launch_key is not None:
            self._launch_key = launch_key
        if getattr(self, "_forced_mode_change", False):
            self._forced_mode_change = False
            if self._point or self._request or self._ladder or self._budget:
                await self._release_point(profile, "governor-mode-changed")
                self._status.update({"state": "PLAN", "reason": "governor-mode-changed"})
                return
        if changed and (self._point or self._request or self._ladder or self._budget):
            reason = "display-mode-changed" if target_changed or (
                self._point_external is not None and external != self._point_external
            ) else "new-game-session"
            await self._release_point(profile, reason)
            self._status.update({"state": "PLAN", "reason": reason})
            return

        # Steam's menu / quick access covers the game: the renderer suspends frame generation, so
        # the output drops for reasons that have nothing to do with the point.  Measure nothing,
        # change nothing, and drop what was sampled meanwhile once the game is back.
        if self._menu_covering():
            if self._menu_since is None:
                self._menu_since = self._clock()
            self._status.update({"state": "PAUSED", "reason": "steam-menu-open"})
            return
        if self._menu_since is not None:
            away = self._clock() - self._menu_since
            self._menu_since = None
            seq = self.observer.sample_seq
            self._evaluation_after_seq = max(self._evaluation_after_seq, seq)
            self._tdp_set_seq = max(self._tdp_set_seq, seq)
            self._injection_seq = max(self._injection_seq, seq)
            if self._request is not None:
                self._request.created += away        # the confirmation timeout does not run in the menu

        # Resource availability is not a renderer/FPS trial. When Vulkan
        # temporarily has no generated-frame slots (x1 only), release the
        # Governor overlay and power exactly once; remain observe-only until
        # resources have returned for a short, stable interval. In particular,
        # do this *before* checking an outstanding request's timeout, so the
        # switch cannot blacklist a good point for ten minutes.
        if self._mode(profile) in self.BUDGET_MODES:
            current_capacity = self.observer.current_max_multiplier
            if current_capacity is not None and current_capacity <= 1.0 + 1e-6:
                # A second zero-slot report during an incomplete recovery
                # cancels the recovery timer. A brief positive report must
                # never be treated as two seconds of stable availability.
                self._capacity_restore_at = None
                if not self._capacity_paused:
                    self._capacity_paused = True
                    if self._point or self._request or self._budget or self.power.state.owned:
                        await self._release_point(profile, "renderer-capacity-unavailable")
                    self._event("renderer-capacity-paused", "no-generated-frame-slots",
                                profile=profile, max_multiplier=current_capacity)
                if profile in self._restore_pending:
                    # A failed overlay restore leaves the old renderer settings
                    # live. Never announce observe-only or silently resume a
                    # recovered swapchain until Saved has actually been restored.
                    self._status.update({"state": "PAUSED", "reason": "overlay-restore-failed"})
                    return
                self._status.update({"state": "OBSERVE_ONLY", "reason": "renderer-capacity-unavailable"})
                return
            if self._capacity_paused:
                if profile in self._restore_pending:
                    # _retry_restores() runs above on every iteration. Wait
                    # for it to succeed before starting the capacity recovery
                    # timer, so a failed write cannot become a stale FG lease.
                    self._capacity_restore_at = None
                    self._status.update({"state": "PAUSED", "reason": "overlay-restore-failed"})
                    return
                if current_capacity is None:
                    self._status.update({"state": "OBSERVE_ONLY", "reason": "renderer-capacity-awaiting-report"})
                    return
                if self._capacity_restore_at is None:
                    self._capacity_restore_at = self._clock()
                if self._clock() - self._capacity_restore_at < BudgetController.CAPACITY_RECOVERY_CONFIRM_S:
                    self._status.update({"state": "OBSERVE_ONLY", "reason": "renderer-capacity-recovering"})
                    return
                self._capacity_paused = False
                self._capacity_restore_at = None
                # Samples from the zero-resource window do not prove that a
                # newly selected multiplier works. Confirmation remains fresh.
                self._evaluation_after_seq = self.observer.sample_seq
                self._event("renderer-capacity-restored", "generated-frame-slots-returned",
                            profile=profile, max_multiplier=current_capacity)
            req = self._request
            if (req is not None and current_capacity is not None
                    and float(req.point.multiplier) > current_capacity + 1e-6):
                # Cancel and restore the base overlay, not the previous
                # capacity-incompatible point. Do not call _fail_request:
                # this was no trial failure and must not affect TTL/backoff.
                await self._release_point(profile, "renderer-capacity-request-cancelled")
                self._status.update({"state": "PLAN", "reason": "renderer-capacity-request-cancelled"})
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
            if self._budget is not None:
                gate = self._scale_gate(profile, req)
                if gate == "wait":
                    self._status.update({"state": "APPLY", "reason": "awaiting-render-scale-acknowledgement"})
                    return
                if gate == "failed":
                    await self._fail_request(profile, "render-scale-not-acknowledged")
                    return
                # Budget mode judges the point on its own windows after confirmation.
                await self._accept_request(profile, req, "renderer-confirmed")
                return
            fresh = self.observer.summary(
                self.WINDOW_SECONDS * 2, after_event_seq=req.window_floor_event_seq,
            )
            if self._ladder is None:  # defensive; requests are only created by the ladder
                self._ladder = TrialLadder(external_display=external, target_output_fps=target)
                self._load_ladder_failures(profile, target)
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

        sample_age_ms = snapshot.get("sample_age_ms")
        if not snapshot.get("available") or sample_age_ms is None or sample_age_ms > self.MAX_SAMPLE_AGE_MS:
            if self.power.state.owned:
                await asyncio.to_thread(self.power.restore_if_owned)
            telemetry_reason = "waiting-for-fps-events"
            path = str(snapshot.get("path") or "")
            # A game launched before Governor was enabled has neither renderer
            # diagnostics nor the overlay binding: no FPS will ever arrive, so
            # say "relaunch" instead of waiting forever.
            capability = self._capability(profile, launch) if self.overlay is not None else None
            if capability is not None:
                self._status["capability"] = capability
            if (
                capability is not None and not capability["overlay_active"]
                and snapshot.get("sample_seq", 0) == 0
            ):
                telemetry_reason = capability["reason"]
            elif snapshot.get("last_poll_error"):
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
            if self._injection is not None:
                # the game is gone or frozen: never leave the Act overlay for the next launch
                await self._drop_injection(profile, "telemetry-stale")
            return
        if summary.get("samples", 0) < self.MIN_SAMPLES or summary.get("sample_span_s", 0.0) < self.MIN_SAMPLE_SPAN_SECONDS:
            self._status.update({"state": "PROBE", "reason": "collecting-fresh-evidence"})
            return

        if self._mode(profile) in self.BUDGET_MODES:
            await self._budget_step(profile, external, target)
            return

        if self._point is None:
            decision = self.planner.recommend(
                external_display=external,
                target_output_fps=target,
                observed_p5_fps=(summary.get("real") or {}).get("p5"),
                observed_multiplier=(summary.get("multiplier") or {}).get("median"),
            )
            candidate = decision.point.to_dict() if decision.point else None
            adopt = bool(candidate and decision.proven and matches(candidate, summary))
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
            self._load_ladder_failures(profile, target)

        saved = await asyncio.to_thread(self._saved_profile_config, profile) or config

        cpu_bound = (self._status.get("diagnosis") or {}).get("bottleneck") == "cpu"

        max_multiplier = self.observer.current_max_multiplier

        def applicable(point: OperatingPoint) -> Optional[str]:
            if max_multiplier is not None and float(point.multiplier) > max_multiplier + 1e-6:
                return "renderer-generated-capacity"
            if cpu_bound and point.render_scale_pct < 100:
                # Render scale frees GPU time; a CPU-bound game gets a worse picture and no more real frames.
                return "cpu-bound-render-scale-does-not-help"
            try:
                point_deltas(point.to_dict(), saved, scale_capable=bool(capability["scale_capable"]),
                             scale_ready=self._scale_ready(profile))
            except PointNotApplicable as error:
                return error.reason
            return None

        # Model-based start: native cadence (if ever observed) bounds the real FPS of any point.
        summary = self.observer.summary(self.WINDOW_SECONDS)
        if self.PREDICTIVE_SKIP:
            self._ladder.observe_native_capacity(
                (summary.get("real") or {}).get("median"), (summary.get("multiplier") or {}).get("median"),
            )
        point = self._ladder.next_point(applicable, now=self._clock())
        if point is None:
            released = await self._release_point_keep_ladder(profile)
            if released:
                self._status.update({"state": "PLAN", "reason": "target-not-proven-viable"})
            return
        if not await self._begin_request(profile, saved, point, external, capability):
            return

    # ------------------------------------------------------------ budget mode
    async def _accept_request(self, profile: str, req: Request, reason: str) -> None:
        self._point = req.point.to_dict()
        self._point_mode = "applied"
        self._point_external = req.external
        self._point_deltas = {k: v for k, v in req.deltas.items()}
        self._request = None
        self._evaluation_after_seq = self.observer.sample_seq
        self._event("operating-point-applied", reason, profile=profile, point=self._point,
                    revision=req.revision, confirmation=req.confirmation_mode)
        self._status.update({"state": self._budget_state(), "reason": "operating-point-confirmed",
                             "recommended_point": self._point, "recommendation_proven": True,
                             "active_point_matches": True})
        await self._apply_budget_tdp(profile)  # the point is live: now its watts

    def _budget_state(self) -> str:
        budget = self._budget
        if budget is None:
            return "PLAN"
        if budget.phase == "locked":
            return "LOCKED"
        if budget.phase == "guard":
            return "GUARD"
        return "OPTIMIZE_POWER"

    async def _budget_power(self, profile: str) -> Optional[Dict[str, Any]]:
        """Own the PPT caps for budget mode.  Returns limits, or None when observe-only on TDP."""
        power = self.power
        if not power.state.available and not await self._rediscover_power():
            return None
        if not power.state.owned:
            if self._external_at is not None:
                if self._reclaims >= self.MAX_EXTERNAL_RECLAIMS:
                    return None
                if self._clock() - self._external_at < self.EXTERNAL_RECLAIM_SECONDS:
                    return None
                self._reclaims += 1
                self._external_at = None
                self._applied_tdp = None
                self._event("tdp-reclaim", "external-change-settled", profile=profile, attempt=self._reclaims)
            bounded_claim = getattr(power, "claim_at_ceiling_w", None)
            if self._mode(profile) == "extreme" and callable(bounded_claim):
                claimed = await asyncio.to_thread(bounded_claim, extreme_policy.EXTREME_CEILING_W)
            else:
                claimed = await asyncio.to_thread(power.claim)
            if not claimed.get("owned") or claimed.get("success") is False:
                self._status.update({"state": "PAUSED", "reason": "extreme-ceiling-not-applied"})
                return None
            self._applied_tdp = None  # caps were restored meanwhile: write the target again
            self._event("power-claimed", "budget-mode", profile=profile)
        else:
            status = await asyncio.to_thread(power.verify_ownership)
            if status.get("external_change"):
                self._external_at = self._clock()
                self._event("tdp-external-change", "budget-mode", profile=profile)
                return None
        values = power.status()
        top = values.get("maximum_tdp_w")
        # The actuator clamps every write (Governor, Act boost, recovery) to this ceiling.
        if self._mode(profile) == "extreme":
            ceiling = self._extreme_power_ceiling()
            if ceiling != self._extreme_ceiling:
                self._event("extreme-power-ceiling", ceiling["source"], profile=profile, **ceiling)
            self._extreme_ceiling = ceiling
            top = min(float(top), ceiling["ceiling_w"]) if isinstance(top, (int, float)) else ceiling["ceiling_w"]
        else:
            self._extreme_ceiling = None
        setter = getattr(power, "set_ceiling_w", None)
        strict_setter = getattr(power, "set_strict_ceiling_w", None)
        if self._extreme_ceiling and callable(strict_setter):
            strict_setter(self._extreme_ceiling["ceiling_w"])
        elif callable(setter):
            setter(self._extreme_ceiling["ceiling_w"] if self._extreme_ceiling
                   else BudgetController.EMERGENCY_CEILING_W)
        if self._extreme_ceiling:
            ceiling_w = self._extreme_ceiling["ceiling_w"]
            current = values.get("observed_tdp_w", values.get("current_tdp_w"))
            fast = values.get("observed_fast_w", current)
            if (not isinstance(current, (int, float)) or not isinstance(fast, (int, float))
                    or max(current, fast) > ceiling_w + 0.000001):
                result = await asyncio.to_thread(power.set_tdp_w, ceiling_w)
                verified = power.status()
                slow = verified.get("observed_tdp_w", verified.get("current_tdp_w"))
                fast = verified.get("observed_fast_w", slow)
                if (not result.get("success") or not isinstance(slow, (int, float))
                        or not isinstance(fast, (int, float)) or max(slow, fast) > ceiling_w + 0.000001):
                    self._status.update({"state": "PAUSED", "reason": "extreme-ceiling-not-applied"})
                    return None
                self._applied_tdp = None
                self._event("extreme-ceiling-applied", "before-renderer-trial", profile=profile,
                            watts=ceiling_w)
        return {"min": values.get("minimum_tdp_w"), "max": top}

    def _extreme_power_ceiling(self) -> Dict[str, Any]:
        """min(15 W, the player's own limit when GFG took the caps, the hardware maximum)."""
        state = self.power.state
        inherited = [getattr(state, key, None) for key in ("initial_slow_uw", "initial_fast_uw")]
        inherited = [v for v in inherited if isinstance(v, (int, float)) and v > 0]
        user = min(inherited) if inherited else None
        maxima = [getattr(state, key, None) for key in ("slow_max_uw", "fast_max_uw")]
        maxima = [v for v in maxima if isinstance(v, (int, float)) and v > 0]
        hardware = min(maxima) if maxima else None
        return extreme_policy.power_ceiling(user / 1e6 if user else None, hardware / 1e6 if hardware else None)

    def _budget_can_scale(self, capability: Dict[str, Any]) -> bool:
        cpu_bound = (self._status.get("diagnosis") or {}).get("bottleneck") == "cpu"
        if self._budget is not None and self._budget.flavor == "extreme" and self._extreme_scale_blocked:
            return False  # the profile scales on its own
        if self._scale_blocked or (self._active_profile and self._game_ignores_scale(self._active_profile)):
            return False  # the renderer refused or never confirmed a scale for this game
        return bool(capability.get("scale_capable")) and not cpu_bound

    async def _budget_step(self, profile: str, external: bool, target: int) -> None:
        launch = await self._launch_info(profile)
        capability = self._capability(profile, launch)
        self._status["capability"] = capability
        if not capability["overlay_active"]:
            if self.power.state.owned and self._budget is None:
                await asyncio.to_thread(self.power.restore_if_owned)
            self._status.update({"state": "PLAN", "reason": capability["reason"]})
            return
        now = self._clock()
        limits = await self._budget_power(profile)
        if (limits is None and self._mode(profile) == "extreme"
                and self._status.get("reason") == "extreme-ceiling-not-applied"):
            return  # never convert a failed ceiling write into an observe-only renderer trial
        budget = self._budget
        if budget is None:
            budget = BudgetController(
                target_output_fps=target, now=now,
                min_tdp_w=(limits or {}).get("min"), max_tdp_w=(limits or {}).get("max"),
                tdp_control=limits is not None,
                flavor=self.FLAVORS.get(self._mode(profile), "battery"),
            )
            self._budget = budget
            budget.scale_capable = self._budget_can_scale(capability)
            budget.current_max_multiplier = self.observer.current_max_multiplier
            key, floor = self._game_key(profile, target), self._floor_key(profile, target)
            self._budget_keys = (key, floor)
            budget.load_failures(self.game_models.failures(key), now)
            # review 1.1.x: a rebuilt controller keeps the remaining back-off of failed lower levels.
            budget.load_floor_failures(self.game_models.floor_failures(floor), now)
            remembered = self.game_models.get(key)
            if remembered and budget.warm_start(remembered["point"], remembered.get("tdp_w"), now):
                self._event("budget-warm-start", "remembered-from-last-session", profile=profile,
                            point=budget.point.key, tdp_w=budget.tdp, confirmations=remembered.get("confirmations"))
            else:
                self._event("budget-start", "battery-first", profile=profile, point=budget.point.key,
                            tdp_w=budget.tdp, tdp_control=budget.tdp_control)
        elif limits is None and budget.tdp_control and self._external_at is not None:
            if self._reclaims < self.MAX_EXTERNAL_RECLAIMS:
                self._status.update({"state": "PAUSED", "reason": "external-tdp-change"})
                return
            # Something keeps rewriting the caps: stop fighting it, keep choosing points.
            budget.tdp_control = False
            self._event("tdp-control-yielded", "external-tdp-change", profile=profile)

        if budget.flavor == "extreme" and self._extreme_ceiling is not None:
            budget.limit_power(self._extreme_ceiling["ceiling_w"])  # e.g. the player lowered it in QAM
        # Render-scale rungs need the Scaling Engine provisioned at launch and a GPU-bound game.
        budget.scale_capable = self._budget_can_scale(capability)
        # Current resources, re-read every step: a swapchain recreation can raise it again.
        budget.current_max_multiplier = self.observer.current_max_multiplier
        old_point_key = budget.point.key
        capacity_action = budget.adapt_to_capacity(now)
        if capacity_action == "move":
            self._event("budget-capacity-transition", budget.last_reason, profile=profile,
                        before=old_point_key, after=budget.point.key,
                        max_multiplier=budget.current_max_multiplier)
            # A capacity transition cannot be judged with the previous point's
            # cached real/output FPS window.
            self._evaluation_after_seq = self.observer.sample_seq
            self._tdp_set_seq = self.observer.sample_seq
            self._fast_last_sample_seq = self.observer.sample_seq
            self._draw_samples = []
        # 1. The operating point first.  Lowering TDP before the renderer has
        # taken the point would starve the game in its *old* mode for a few
        # seconds, which the player sees as a stutter at startup.
        point = budget.point
        if self._point is None or self._point.get("key") != point.key:
            if budget.exhausted and budget.request_failures >= budget.MAX_REQUEST_FAILURES:
                self._status.update({"state": "PLAN", "reason": "renderer-did-not-confirm-points"})
                return
            saved = await asyncio.to_thread(self._saved_profile_config, profile)
            if saved is None:
                self._status.update({"state": "PAUSED", "reason": "saved-profile-unavailable"})
                return
            try:
                await self._begin_request(profile, saved, point, external, capability)
            except PointNotApplicable as error:
                budget.request_failed(now, error.reason)
                self._status.update({"state": "PLAN", "reason": error.reason})
            return

        # 2. The point is live: apply this level's watts.
        if not await self._apply_budget_tdp(profile):
            return
        # Frame OS Act owns the real cadence while it injects: the Governor holds this point and its
        # watts (the energy broker moves them) and does not judge windows the pacer shapes on purpose.
        if await self._sync_injection(profile):
            self._status.update({"state": "LOCKED", "reason": "frame-os-act-holds-point"})
            return
        # the point is live at its watts: the power split may act (on this point only)
        self._split_ready = (point.key, float(point.base_target_fps))
        self._remember_if_held(profile, target, budget, point, now)
        self._store_failures(budget)

        # The draw sensor is an instantaneous / ~1 s value: sample it every
        # iteration and judge the window by its median, not its last reading.
        draw = self.power.status().get("draw_w")
        if isinstance(draw, (int, float)) and math.isfinite(float(draw)):
            self._draw_samples.append(float(draw))

        # Every iteration: a game short of its cap with the draw at the cap gets
        # watts within seconds.  Lowering stays with the windows below.
        if self._fast_point_key != point.key:  # samples from another point say nothing
            self._fast_point_key, self._tdp_set_seq = point.key, self.observer.sample_seq
            self._fast_last_sample_seq = self.observer.sample_seq
            budget.starved_checks = 0
        recent = self.observer.summary(self.FAST_CHECK_SECONDS, after_seq=self._tdp_set_seq)
        sample_seq = recent.get("last_sample_seq")
        new_evidence = (recent.get("samples", 0) >= self.FAST_MIN_SAMPLES
                        and isinstance(sample_seq, int)
                        and sample_seq > self._fast_last_sample_seq)
        if new_evidence:
            self._fast_last_sample_seq = sample_seq
            draw_now = statistics.median(self._draw_samples[-3:]) if self._draw_samples else None
            before = budget.tdp
            if budget.fast_check(now, (recent.get("real") or {}).get("median"), draw_now) == "move":
                self._event("budget-step", budget.last_reason, profile=profile,
                            real=(recent.get("real") or {}).get("median"), draw_w=draw_now,
                            before={"tdp_w": before}, after={"point": budget.point.key, "tdp_w": budget.tdp,
                                                            "phase": budget.phase})
                self._draw_samples = []
                self._store_failures(budget)  # a mode switch may drop this controller next
                self._status.update({"state": self._budget_state(), "reason": budget.last_reason})
                await self._apply_budget_tdp(profile)
                return
        else:
            # A controller called at 1 Hz can otherwise count the same FPS
            # samples twice and boost watts without two independent checks.
            budget.fast_check(now, None, None)

        # 3. Judge one fresh, non-overlapping window.
        fresh = self.observer.summary(self.BUDGET_WINDOW_SECONDS, after_seq=self._evaluation_after_seq)
        if fresh.get("samples", 0) < self.BUDGET_MIN_SAMPLES or fresh.get("sample_span_s", 0.0) < self.BUDGET_MIN_SPAN_SECONDS:
            self._status.update({"state": self._budget_state(), "reason": budget.last_reason})
            return
        verdict = window_verdict(fresh, point)
        self._evaluation_after_seq = self.observer.sample_seq
        feedback = self._power_feedback(profile, budget)
        before = (budget.point.key, budget.tdp, budget.phase)
        reason_before, holds_before = budget.last_reason, getattr(budget, "not_power_bound_holds", 0)
        action = budget.observe(now, verdict, (fresh.get("real") or {}).get("median"),
                                (fresh.get("output") or {}).get("median"))
        self._store_failures(budget)  # now, not after the next TDP write: a release may come first
        after = (budget.point.key, budget.tdp, budget.phase)
        if str(budget.last_reason).startswith("guard-not-power-bound") and (
                budget.last_reason != reason_before or getattr(budget, "not_power_bound_holds", 0) != holds_before):
            # review 1.1.x: the guard spent nothing because the APU drew well under the cap; without
            # this event a log showed only a missed window and no reaction.
            self._event("budget-guard-not-power-bound", budget.last_reason, profile=profile,
                        draw_w=feedback.get("draw_w"), cap_w=budget.tdp, verdict=verdict.reason,
                        count=getattr(budget, "not_power_bound_holds", 0))
        if action == "move" or before != after:
            self._event("budget-step", budget.last_reason, profile=profile, verdict=verdict.to_dict(),
                        before={"point": before[0], "tdp_w": before[1], "phase": before[2]},
                        after={"point": after[0], "tdp_w": after[1], "phase": after[2]})
        if budget.phase == "locked" and before[2] != "locked":
            self._event("operating-point-locked", budget.last_reason, profile=profile, point=self._point,
                        tdp_w=budget.tdp)
        self._status.update({"state": self._budget_state(), "reason": budget.last_reason,
                             "last_verdict": verdict.to_dict(), "power_feedback": feedback})
        await self._apply_budget_tdp(profile)

    def _act_power_settled(self) -> bool:
        """The budget found its watts for this point: locked, no probe, for ACT_SETTLE_S."""
        budget = self._budget
        if budget is None or not budget.tdp_control:
            return True
        settled_since = getattr(budget, "settled_since", getattr(budget, "locked_since", None))
        return (budget.phase == "locked" and budget.probe is None and settled_since is not None
                and self._clock() - float(settled_since) >= self.ACT_SETTLE_S)

    async def _sync_injection(self, profile: str) -> bool:
        """Write (or take back) the Act adaptive overlay; True while Act injects on this point."""
        live = bool(((self.frame_os.last or {}).get("telemetry") or {}).get("live"))
        # only while the pacer is really in the game: without it the renderer would take 45 real
        acting = (self._frame_os_mode(profile) == "act" and self._request is None and bool(self._point_deltas)
                  and self._clock() >= self._injection_hold_until
                  and self._injection_starvation_yields < 2
                  and (self._injection is not None or self._act_power_settled()))
        if (acting and self._injection is not None and self._budget is not None and self._budget.tdp_control
                and self._injection_started_at is not None
                and self._clock() - self._injection_started_at >= self.ACT_RESEARCH_EVERY_S):
            # step aside for a while: the Governor re-checks whether a lower level holds
            acting = False
            self._injection_hold_until = self._clock() + self.ACT_RESEARCH_S
            self._event("frame-os-injection-yielded", "power-research", profile=profile,
                        tdp_w=self._budget.tdp)
        if acting and self._budget is not None:
            # Safety: heat or a starved output hands the point back to the Governor's own judgement.
            hot = (self._status.get("diagnosis") or {}).get("thermal") == "hot"
            fast = self.observer.summary(self.FAST_CHECK_SECONDS, after_seq=self._injection_seq)
            output = (fast.get("output") or {}).get("median")
            settled = (self._injection is None or self._injection_started_at is None
                       or (self._clock() - self._injection_started_at >= self.INJECTION_GRACE_S
                           and (fast.get("samples") or 0) >= self.INJECTION_MIN_SAMPLES))
            floor = 0.8 * float(self._budget.point.target_output_fps)
            recent = [sample.output_fps for sample in self.observer.samples_since(
                self.observer.time_fn() - self.FAST_CHECK_SECONDS,
                after_seq=self._injection_seq)][-self.STARVATION_RUN:]
            lasting = (len(recent) >= self.STARVATION_RUN
                       and all(isinstance(v, (int, float)) and v < floor for v in recent))
            starved = (settled and lasting and isinstance(output, (int, float))
                       and output < floor)
            # A starved output under a Steam menu (generation suspended) still takes the overlay
            # back, but it is no evidence against Act: it never counts toward the session lockout.
            menu = self._menu_covering() or getattr(self.observer, "game_focused", None) is False
            if hot or starved:
                acting = False
                if self._injection is not None:
                    self._event("frame-os-injection-yielded", "hot" if hot else "output-starved",
                                profile=profile, output=output)
                    if starved and not hot and not menu:
                        self._injection_starvation_yields += 1
                        if self._injection_starvation_yields >= 2:
                            self._event("frame-os-injection-locked-out", "repeated-output-starvation",
                                        profile=profile, output=output)
                    self._injection_hold_until = self._clock() + self.INJECTION_HOLD_S  # no flapping
        cadences = self.frame_os.injection if acting and live else None
        wanted = None
        if cadences is not None and self._budget is not None:
            boost, rest = cadences
            wanted = injection_deltas(self._point_deltas, float(self._budget.point.target_output_fps), boost, rest)
        if wanted == self._injection:
            self.frame_os.executor_active = wanted is not None
            return wanted is not None
        saved = await asyncio.to_thread(self._saved_profile_config, profile)
        if saved is None:
            return False
        desired = {**self._base_for(profile, saved), **(wanted or self._point_deltas)}
        key = self._point["key"] if self._point else "base"
        try:
            record = await asyncio.to_thread(self._ensure_overlay_sync, profile, desired, key)
        except (OSError, ValueError) as error:
            self._event("frame-os-injection-failed", "overlay-write-failed", profile=profile, error=str(error))
            return False
        if record is not None:
            self._record = record
        self._event("frame-os-injection", "start" if wanted else "stop", profile=profile, point=key,
                    base_fps_cap=(wanted or {}).get("base_fps_cap"),
                    adaptive_max_multiplier=(wanted or {}).get("adaptive_max_multiplier"))
        self._injection = wanted
        self.frame_os.executor_active = wanted is not None
        self._injection_seq = self.observer.sample_seq
        self._injection_started_at = self._clock() if wanted is not None else None
        # windows measured under injection say nothing about the plain point
        self._evaluation_after_seq = self.observer.sample_seq
        return wanted is not None

    async def _drop_injection(self, profile: str, reason: str) -> None:
        saved = await asyncio.to_thread(self._saved_profile_config, profile)
        if saved is not None:
            key = self._point["key"] if self._point else "base"
            try:
                await asyncio.to_thread(self._ensure_overlay_sync, profile,
                                        {**self._base_for(profile, saved), **self._point_deltas}, key)
            except (OSError, ValueError):
                pass
        self._event("frame-os-injection", "stop", profile=profile, cause=reason)
        self._injection = None
        self._injection_started_at = None
        self.frame_os.executor_active = False

    def _power_feedback(self, profile: str, budget: BudgetController) -> Dict[str, Any]:
        """Compare the measured APU draw with the cap we wrote."""
        samples, self._draw_samples = self._draw_samples, []
        draw = round(statistics.median(samples), 2) if samples else None
        budget.draw_w = draw
        cap = self._applied_tdp
        result: Dict[str, Any] = {"draw_w": draw, "cap_w": cap, "cap_ignored": budget.cap_ignored}
        if not isinstance(draw, (int, float)) or cap is None or not budget.tdp_control:
            return result
        if float(draw) > float(cap) + self.CAP_IGNORED_MARGIN_W:
            self._over_cap_windows += 1
        else:
            self._over_cap_windows = 0
            if budget.cap_ignored:
                budget.cap_ignored = False
                self._event("tdp-cap-binding-again", "draw-within-cap", profile=profile, draw_w=draw, cap_w=cap)
        if self._over_cap_windows >= 2 and not budget.cap_ignored:
            budget.cap_ignored = True
            self._event("tdp-cap-ignored", "draw-above-cap", profile=profile, draw_w=draw, cap_w=cap)
        result["cap_ignored"] = budget.cap_ignored
        return result

    HOLD_BEFORE_REMEMBER_S = 90.0

    def _game_app_id(self) -> str:
        launch = self._launch if isinstance(self._launch, dict) else {}
        return launch.get("app_id", "") if launch.get("running") else ""

    def _game_key(self, profile: str, target: int) -> str:
        mode = self._mode(profile)
        if mode == "extreme" and self._extreme_ceiling:
            # a point learnt at 15 W says nothing about the same game at the player's 12 W
            mode = f"extreme-{self._extreme_ceiling['ceiling_w']:g}w"
        return context_key(profile, target, mode, self._game_app_id())

    def _floor_key(self, profile: str, target: int) -> str:
        return floor_key(profile, target, self._game_app_id())

    # Not evidence about the point itself: a new game session, or a log line that lost its numbers.
    TRANSIENT_FAILURES = frozenset({"telemetry-session-changed", "trial-evidence-incomplete"})

    def _remember_ladder_failure(self, profile: str, point: OperatingPoint) -> None:
        """Quality mode: a point that did not hold is skipped by the next ladder for 10 minutes
        (mode switch, reload), like Battery's failure memory.  Stored at the TDP it failed at."""
        try:
            tdp = (self.power.status() or {}).get("observed_tdp_w")
            self.game_models.record_failure(self._game_key(profile, int(point.target_output_fps)), point.key,
                                            float(tdp) if isinstance(tdp, (int, float)) and tdp > 0 else 15.0)
        except Exception as error:  # best-effort
            self.log.debug("Game model failure not stored: %s", error)

    def _load_ladder_failures(self, profile: str, target: int) -> None:
        if self._ladder is None:
            return
        now = self._clock()
        try:
            failures = self.game_models.failures(self._game_key(profile, target))
        except Exception:
            return
        for key, (_tdp, age) in failures.items():
            self._ladder.reject(key, "remembered-failure", until=now + self.game_models.FAILURE_TTL_S - age)

    def _store_failures(self, budget: Any) -> None:
        if budget is None or self._budget_keys is None:
            return
        key, floor = self._budget_keys
        while budget.new_failures:
            point_key, tdp = budget.new_failures.pop(0)
            try:
                self.game_models.record_failure(key, point_key, tdp)
            except Exception as error:  # best-effort, like remembering held points
                self.log.debug("Game model failure not stored: %s", error)
        floors = getattr(budget, "new_floor_failures", None) or []
        while floors:
            point_key, tdp, count = floors.pop(0)
            try:
                self.game_models.record_floor_failure(floor, point_key, tdp, count)
            except Exception as error:
                self.log.debug("Game model floor failure not stored: %s", error)

    def _remember_if_held(self, profile: str, target: int, budget: Any, point: Any, now: float) -> None:
        """Store the point/TDP once it has held, so the next session can start there."""
        if (
            budget.phase != "locked" or budget.recover is not None or budget.cap_ignored or budget.exhausted
            or getattr(budget, "verifying", None)
            or point.degraded or getattr(budget, "settled_since", budget.locked_since) is None
            or now - getattr(budget, "settled_since", budget.locked_since) < self.HOLD_BEFORE_REMEMBER_S
            or (budget.tdp_control and budget.tdp != self._applied_tdp)
        ):
            return
        # review 1.1.x: a state that held while heat held quality back is not what the game needs
        # when cool; remembering it would warm-start the next session from a throttled state.
        thermal = (self._status.get("diagnosis") or {}).get("thermal")
        if getattr(budget, "heat_limited", False) or thermal in ("hot", "heating"):
            return
        try:
            self.game_models.record(self._game_key(profile, target), point.key,
                                    budget.tdp if budget.tdp_control else None)
        except Exception as error:  # remembering is best-effort and must never disturb the loop
            self.log.debug("Game model not stored: %s", error)

    async def _apply_budget_tdp(self, profile: str) -> bool:
        budget = self._budget
        if budget is None or not budget.tdp_control or budget.tdp is None or not self.power.state.owned:
            return True
        # Frame OS (act mode) adds the watts of a funded boost / removes them in rest.
        offset = self.frame_os.tdp_offset_w
        # Without an offset the controller's own value goes out as is (emergency watts included).
        target = budget.tdp if not offset else round(
            min(max(budget.normal_max_w, budget.tdp), max(budget.min_w, budget.tdp + offset)), 1)
        if target == self._applied_tdp:
            return True
        result = await asyncio.to_thread(self.power.set_tdp_w, target)
        if not result.get("success"):
            self._status.update({"state": "PAUSED", "reason": "tdp-write-failed"})
            return False
        self._applied_tdp = target
        self._evaluation_after_seq = self.observer.sample_seq
        self._tdp_set_seq = self.observer.sample_seq
        self._event("tdp-set", budget.last_reason, watts=target, profile=profile,
                    **({"frame_os_offset_w": target - budget.tdp} if target != budget.tdp else {}))
        return True

    async def _release_point_keep_ladder(self, profile: str) -> bool:
        ladder = self._ladder
        ok = await self._release_point(profile, "ladder-exhausted")
        self._ladder = ladder  # remember rejections: no re-trial until the session changes
        self._exhausted = True
        return ok

    POWER_REDISCOVER_SECONDS = 30.0

    async def _rediscover_power(self) -> bool:
        """TDP control was probed only at plugin start; steamos-manager or the session bus may come
        up later (audit 1.0.8).  Probe again, at most every 30 s."""
        now = self._clock()
        if now - getattr(self, "_power_probed_at", -1e9) < self.POWER_REDISCOVER_SECONDS:
            return False
        self._power_probed_at = now
        try:
            await asyncio.to_thread(self.power.discover)
        except Exception as error:
            self.log.debug("Governor power rediscovery failed: %s", error)
            return False
        return bool(self.power.state.available)

    async def _power_step(self, profile: str, summary: Dict[str, Any]) -> None:
        point = self._point
        assert point is not None
        health_ratio = self.CAP_BOUND_HEALTH_RATIO if self._point_mode == "applied" else self.UNCAPPED_HEALTH_RATIO
        if not self.power.state.available and not await self._rediscover_power():
            reason = "tdp-control-not-writable" if self.power.state.fast_cap_path else "tdp-control-unavailable"
            self._status.update({"state": "OBSERVE_ONLY", "reason": reason})
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
            output_fps=(fresh.get("output") or {}).get("median"),
            output_target_fps=float(point["target_output_fps"]),
        )
        action = outcome.get("action")
        # Every window is judged once: the next one starts on fresh samples only.
        self._evaluation_after_seq = self.observer.sample_seq
        if self.search.status.reason == "point-not-healthy-at-ceiling" and self._point_mode == "applied" \
                and self._ladder is not None:
            # Governor chose this point and it cannot hold even at the user's
            # TDP: reject it and let the ladder try the next (cheaper) point
            # instead of parking at the ceiling for the rest of the session.
            key = str(point.get("key"))
            self._ladder.reject(key, "not-healthy-at-ceiling", until=self._clock() + self.CEILING_REJECT_TTL_S)
            self._event("operating-point-rejected", "not-healthy-at-ceiling", profile=profile, point=key)
            ladder = self._ladder
            await self._release_point(profile, "not-healthy-at-ceiling")
            self._ladder = ladder
            self._status.update({"state": "PLAN", "reason": "rejected:not-healthy-at-ceiling"})
            return
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
            # Clear before the iteration: a poke that lands while it runs
            # (a Saved write, a toggle) wakes the next one right away.
            if self._wake is not None:
                self._wake.clear()
            try:
                await self._iteration()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.log.warning("Governor iteration failed: %s", error)
                self._status.update({"state": "PAUSED", "reason": "iteration-error", "error": str(error)})
            timeout = self.IDLE_LOOP_SECONDS if self._is_idle() else self.LOOP_SECONDS
            wake = self._wake
            waiters = [asyncio.ensure_future(self._stop.wait())]
            if wake is not None:
                waiters.append(asyncio.ensure_future(wake.wait()))
            try:
                await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for waiter in waiters:
                    waiter.cancel()
