"""Read-only Saved -> Effective -> Actual pipeline inspection."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from shared_config import FG_BACKEND_GFG, FG_BACKEND_OPTISCALER, OPTISCALER_PROXY_VALUES
from .config_schema import ConfigurationManager
from .constants import STEAM_APP_ID_ENV_KEYS


_MAX_MANIFEST_BYTES = 64 * 1024
_PROXY_NAMES = tuple(value for value in OPTISCALER_PROXY_VALUES if value != "auto")
_PROXY_RE = re.compile(r"(?:^|[/\\])(" + "|".join(map(re.escape, _PROXY_NAMES)) + r")\.dll(?:\s|$)", re.I)


def profile_manifest_key(profile_name: str) -> str:
    return hashlib.sha256(profile_name.encode("utf-8")).hexdigest()[:16]


def _proc_starttime(process_dir: Path) -> Optional[int]:
    try:
        value = (process_dir / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    end = value.rfind(")")
    if end < 0:
        return None
    fields = value[end + 2:].split()
    # fields[0] is stat field 3 (state), so field 22 is index 19.
    if len(fields) <= 19:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def _proc_ppid(process_dir: Path) -> Optional[int]:
    try:
        value = (process_dir / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    end = value.rfind(")")
    if end < 0:
        return None
    fields = value[end + 2:].split()
    if len(fields) < 2:
        return None
    try:
        return int(fields[1])  # field 4, after field 3 state
    except ValueError:
        return None


def _read_environment(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for item in path.read_bytes().split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        values[key.decode("utf-8", errors="ignore")] = value.decode("utf-8", errors="ignore")
    return values


class PipelineInspectorService:
    """Compare persisted intent, runtime projection, and live process mappings."""

    def __init__(self, configuration_service: Any, proc_root: Path = Path("/proc")):
        self.configuration = configuration_service
        self.proc_root = proc_root
        self.log = configuration_service.log

    def _manifest_path(self, profile_name: str) -> Path:
        return self.configuration.runtime_state_dir / "launches" / f"{profile_manifest_key(profile_name)}.json"

    def _read_manifest(self, profile_name: str) -> Optional[Dict[str, Any]]:
        path = self._manifest_path(profile_name)
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if len(raw) > _MAX_MANIFEST_BYTES:
            return None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            return None
        if not isinstance(value, dict) or value.get("schema") != 1:
            return None
        if value.get("profile") != profile_name:
            return None
        return value

    def _process_dirs(self) -> list[Path]:
        try:
            return [path for path in self.proc_root.iterdir() if path.name.isdigit() and path.is_dir()]
        except OSError:
            return []

    def _candidate_pids(self, manifest: Dict[str, Any]) -> tuple[list[int], bool]:
        launch_pid = manifest.get("pid")
        launch_start = manifest.get("starttime")
        app_id = str(manifest.get("app_id") or "").strip()
        dirs = self._process_dirs()
        by_pid = {int(path.name): path for path in dirs}
        launch_valid = False
        candidates: set[int] = set()
        if isinstance(launch_pid, int) and launch_pid in by_pid:
            current_start = _proc_starttime(by_pid[launch_pid])
            if isinstance(launch_start, int) and current_start == launch_start:
                launch_valid = True
                candidates.add(launch_pid)

        if launch_valid:
            children: Dict[int, list[int]] = {}
            for pid, path in by_pid.items():
                parent = _proc_ppid(path)
                if parent is not None:
                    children.setdefault(parent, []).append(pid)
            queue = [launch_pid]
            seen = {launch_pid}
            while queue and len(seen) < 256:
                parent = queue.pop(0)
                for child in children.get(parent, []):
                    if child in seen:
                        continue
                    seen.add(child)
                    candidates.add(child)
                    queue.append(child)

        if app_id.isdigit() and app_id != "0":
            for pid, path in by_pid.items():
                try:
                    env = _read_environment(path / "environ")
                except (OSError, ValueError):
                    continue
                if app_id in {env.get(key, "").strip() for key in STEAM_APP_ID_ENV_KEYS}:
                    candidates.add(pid)
        return sorted(candidates), launch_valid

    @staticmethod
    def _process_name(process_dir: Path) -> str:
        try:
            return (process_dir / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""

    def _inspect_maps(self, pids: Iterable[int]) -> Dict[str, Any]:
        renderer_pids: list[int] = []
        proxy_hits: list[Dict[str, Any]] = []
        vkbasalt_pids: list[int] = []
        readable = 0
        denied = 0
        processes: list[Dict[str, Any]] = []
        for pid in pids:
            process_dir = self.proc_root / str(pid)
            try:
                text = (process_dir / "maps").read_text(encoding="utf-8", errors="replace")
            except PermissionError:
                denied += 1
                continue
            except OSError:
                continue
            readable += 1
            lowered = text.casefold()
            renderer = "libmako-render.so" in lowered
            vkbasalt = "vkbasalt" in lowered
            proxy_names = sorted({match.group(1).casefold() for match in _PROXY_RE.finditer(text)}, key=str.casefold)
            if renderer:
                renderer_pids.append(pid)
            if vkbasalt:
                vkbasalt_pids.append(pid)
            for proxy in proxy_names:
                proxy_hits.append({"pid": pid, "proxy": proxy})
            if renderer or vkbasalt or proxy_names:
                processes.append({
                    "pid": pid,
                    "name": self._process_name(process_dir),
                    "renderer": renderer,
                    "vkbasalt": vkbasalt,
                    "proxies": proxy_names,
                })
        return {
            "readable_processes": readable,
            "permission_denied": denied,
            "renderer_loaded": bool(renderer_pids),
            "renderer_pids": renderer_pids,
            "optiscaler_proxy_loaded": bool(proxy_hits),
            "optiscaler_proxy_hits": proxy_hits,
            "vkbasalt_loaded": bool(vkbasalt_pids),
            "vkbasalt_pids": vkbasalt_pids,
            "processes": processes,
        }

    def live_launch(self, profile_name: str) -> Dict[str, Any]:
        """Identify the running launch of ``profile_name`` for Governor.

        Uses the same PID-reuse protection as the Inspector (launch PID plus
        /proc starttime) and reports whether the wrapper bound the process to a
        Governor overlay, and what the Scaling Engine provisioning was at launch.
        """
        from .governor_overlay import parse_launch_line

        manifest = self._read_manifest(profile_name)
        if manifest is None:
            return {"running": False, "reason": "no-launch-manifest"}
        pids, launch_valid = self._candidate_pids(manifest)
        if not pids or not launch_valid:
            return {"running": False, "reason": "launch-process-not-running"}
        maps = self._inspect_maps(pids)
        effective = manifest.get("effective") if isinstance(manifest.get("effective"), dict) else {}
        return {
            "running": True,
            "reason": "running",
            "pids": pids,
            "launch_key": [manifest.get("pid"), manifest.get("starttime"), manifest.get("timestamp")],
            "renderer_loaded": bool(maps.get("renderer_loaded")),
            "governor_launch": parse_launch_line(manifest.get("governor_launch", "")),
            "saved_scaling_at_launch": bool(effective.get("scaling_enabled", False)),
            "app_id": str(manifest.get("app_id") or "").strip(),
        }

    def get_status(self, profile_name: str = "") -> Dict[str, Any]:
        response = (
            self.configuration.get_profile_config(profile_name)
            if profile_name
            else self.configuration.get_config()
        )
        if not response.get("success") or not isinstance(response.get("config"), dict):
            return {"success": False, "error": response.get("error") or "configuration unavailable"}
        config = response["config"]
        if not profile_name:
            current, _ = self.configuration.get_current_profile_snapshot()
            profile_name = current
        effective = ConfigurationManager.get_effective_runtime_config(config)
        backend = config.get("fg_backend", FG_BACKEND_GFG)
        renderer_required = bool(
            effective.get("frame_generation_provisioned", False)
            or effective.get("scaling_enabled", False)
            or config.get("external_vulkan_layer") == "vkbasalt"
        )
        saved = {
            "fg_backend": backend,
            "frame_generation_enabled": bool(config.get("frame_generation_enabled", False)),
            "frame_generation_provisioned": bool(config.get("frame_generation_provisioned", False)),
            "automatic_dock_mode": bool(config.get("automatic_dock_mode", False)),
            "target_fps": config.get("target_fps"),
            "scaling_enabled": bool(config.get("scaling_enabled", False)),
            "shaders_enabled": config.get("external_vulkan_layer") == "vkbasalt",
            "optiscaler_proxy": config.get("optiscaler_proxy", "auto"),
        }
        effective_view = {
            "fg_backend": backend,
            "frame_generation_enabled": bool(effective.get("frame_generation_enabled", False)),
            "frame_generation_provisioned": bool(effective.get("frame_generation_provisioned", False)),
            "automatic_dock_mode": bool(effective.get("automatic_dock_mode", False)),
            "target_fps": effective.get("target_fps"),
            "scaling_enabled": bool(effective.get("scaling_enabled", False)),
            "shaders_enabled": config.get("external_vulkan_layer") == "vkbasalt",
            "renderer_required": renderer_required,
        }
        manifest = self._read_manifest(profile_name)
        actual: Dict[str, Any] = {
            "state": "not-launched",
            "renderer_loaded": False,
            "optiscaler_proxy_loaded": False,
            "vkbasalt_loaded": False,
            "permission_denied": 0,
            "processes": [],
        }
        reasons: list[str] = []
        if saved["frame_generation_enabled"] and not effective_view["frame_generation_enabled"]:
            reasons.append(
                f"Saved GFG Frame Generation is suppressed because backend={backend}."
            )
        if saved["automatic_dock_mode"] and not effective_view["automatic_dock_mode"]:
            reasons.append(
                f"Saved Automatic Dock is inactive because backend={backend}."
            )
        double_fg = False
        if manifest is None:
            reasons.append("No launch manifest for this profile yet.")
        else:
            pids, launch_valid = self._candidate_pids(manifest)
            maps = self._inspect_maps(pids)
            actual.update(maps)
            actual["candidate_pids"] = pids
            actual["launch_pid_valid"] = launch_valid
            actual["state"] = "running" if pids else "ended"
            if not launch_valid and not pids:
                reasons.append("The recorded launch process has ended or its PID was reused.")
            if maps["permission_denied"] and not maps["readable_processes"]:
                reasons.append("Runtime inspection is unavailable because /proc maps cannot be read.")
            elif pids:
                if renderer_required and not maps["renderer_loaded"]:
                    reasons.append("GFG renderer was expected but is not mapped in the inspected game processes.")
                if backend == FG_BACKEND_OPTISCALER and not maps["optiscaler_proxy_loaded"]:
                    reasons.append("OptiScaler was requested but no supported proxy DLL is mapped.")
                if backend != FG_BACKEND_GFG and maps["renderer_loaded"] and not (
                    effective.get("scaling_enabled") or config.get("external_vulkan_layer") == "vkbasalt"
                ):
                    reasons.append("GFG renderer is mapped even though the external backend does not require GFG features.")
                double_fg = bool(
                    backend == FG_BACKEND_GFG
                    and effective.get("frame_generation_enabled")
                    and maps["optiscaler_proxy_loaded"]
                )
                if double_fg:
                    reasons.append("Potential double frame generation: GFG is active and an OptiScaler proxy is mapped.")
        return {
            "success": True,
            "error": None,
            "profile": profile_name,
            "saved": saved,
            "effective": effective_view,
            "manifest": manifest,
            "actual": actual,
            "mismatch_reasons": reasons,
            "double_fg_warning": double_fg,
        }
