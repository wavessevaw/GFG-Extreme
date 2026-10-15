"""GFG Bridge: the local link between GFG Shell (Godot) and the GFG Extreme plugin.

Transport: line-delimited JSON over TCP on 127.0.0.1 with a random port and a random
token. Godot has no Unix-socket client, so loopback + token is the portable choice.
The port and token live in a discovery file readable only by the Deck user
(``~/.local/state/gfg-extreme/shell-bridge.json``, mode 0600, chowned to the user).

Scope is deliberately small. The Bridge only *reads* Governor state and forwards a
fixed allow-list of settings calls to the existing Governor methods; it never writes
TDP, GPU clocks or renderer settings itself, so the Governor stays the single owner
of power control.

Request:  {"id": 1, "method": "status", "params": {...}, "token": "..."}
Response: {"id": 1, "ok": true, "result": {...}}  /  {"id": 1, "ok": false, "error": "..."}
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

API_VERSION = 1
DISCOVERY_RELATIVE = Path(".local/state/gfg-extreme/shell-bridge.json")
MAX_LINE = 16 * 1024
SHELL_MODES = ("budget", "balanced", "quality", "autopilot")
SHELL_FEATURES = ("continuous_boost",)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _median(stats: Any) -> Optional[float]:
    if isinstance(stats, dict):
        for key in ("median", "p50", "mean"):
            if _num(stats.get(key)) is not None:
                return round(float(stats[key]), 1)
    return _num(stats)


def compact_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """The few fields the shell renders; tolerant of every key being absent."""
    status = status if isinstance(status, dict) else {}
    sensors = status.get("sensors") if isinstance(status.get("sensors"), dict) else {}
    battery = status.get("battery") if isinstance(status.get("battery"), dict) else {}
    telemetry = status.get("telemetry") if isinstance(status.get("telemetry"), dict) else {}
    summary = telemetry.get("summary") if isinstance(telemetry.get("summary"), dict) else {}
    feedback = status.get("power_feedback") if isinstance(status.get("power_feedback"), dict) else {}
    fusion = status.get("frame_fusion") if isinstance(status.get("frame_fusion"), dict) else {}
    frame_os = status.get("frame_os") if isinstance(status.get("frame_os"), dict) else {}
    features = frame_os.get("feature_settings") if isinstance(frame_os.get("feature_settings"), dict) else {}
    cpu = sensors.get("cpu") if isinstance(sensors.get("cpu"), dict) else {}
    return {
        "profile": str(status.get("profile") or ""),
        "enabled": status.get("enabled") is True,
        "mode": str(status.get("mode") or ""),
        "state": str(status.get("state") or ""),
        "reason": str(status.get("reason") or ""),
        "target_fps": _num(status.get("target_output_fps")),
        "fps": {"real": _median(summary.get("real")), "output": _median(summary.get("output")),
                "frametime_ms": _median(summary.get("frametime"))},
        "sensors": {
            "temp_c": _num(sensors.get("temp_c")),
            "gpu_busy_pct": _num(sensors.get("gpu_busy_pct")),
            "gpu_clock_mhz": _num(sensors.get("gpu_clock_mhz")),
            "cpu_pct": _num(sensors.get("cpu_total_pct")) if "cpu_total_pct" in sensors else _num(cpu.get("total_pct")),
            "fan_rpm": _num(sensors.get("fan_rpm")),
        },
        "power": {"tdp_w": _num(feedback.get("cap_w")), "draw_w": _num(feedback.get("draw_w"))},
        "battery": {
            "percent": _num(battery.get("percent")),
            "charging": battery.get("external_power") is True,
            "minutes_left": battery.get("minutes_left") if isinstance(battery.get("minutes_left"), int) else None,
        },
        "frame_fusion": {"setting": fusion.get("setting_enabled") is True, "state": str(fusion.get("state") or "")},
        "continuous_boost": features.get("continuous_boost") is True,
    }


class ShellBridge:
    """Owns the listening socket. ``plugin`` is the Decky Plugin instance (its async RPCs)."""

    def __init__(self, plugin: Any, user_home: Path, logger: Any,
                 uid: Optional[int] = None, gid: Optional[int] = None) -> None:
        self.plugin = plugin
        self.user_home = Path(user_home)
        self.log = logger
        self.uid, self.gid = uid, gid
        self.token = ""
        self.port = 0
        self._server: Optional[asyncio.AbstractServer] = None
        self._methods: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
            "hello": self._hello,
            "status": self._status,
            "profiles": self._profiles,
            "set_mode": self._set_mode,
            "set_frame_fusion": self._set_frame_fusion,
            "set_feature": self._set_feature,
        }

    @property
    def discovery_path(self) -> Path:
        return self.user_home / DISCOVERY_RELATIVE

    async def start(self) -> None:
        if self._server is not None:
            return
        self.token = secrets.token_hex(24)
        self._server = await asyncio.start_server(self._client, host="127.0.0.1", port=0, limit=MAX_LINE)
        self.port = int(self._server.sockets[0].getsockname()[1])
        self._write_discovery()
        self.log.info("GFG Bridge listening on 127.0.0.1:%d", self.port)

    async def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.close()
            try:
                await server.wait_closed()
            except Exception:
                pass
        try:
            self.discovery_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            self.log.warning("GFG Bridge discovery file not removed: %s", error)

    def _write_discovery(self) -> None:
        path = self.discovery_path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump({"api": API_VERSION, "port": self.port, "token": self.token, "pid": os.getpid()}, handle)
        if self.uid is not None:
            for p in (tmp, path.parent):
                try:
                    os.chown(p, self.uid, self.gid if self.gid is not None else -1)
                except OSError:
                    pass
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        authed = False
        try:
            while True:
                try:
                    line = await reader.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    break
                if not line:
                    break
                response = await self.handle_line(line, authed)
                if response.get("ok") and response.get("_authed"):
                    authed = True
                response.pop("_authed", None)
                writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode())
                await writer.drain()
                if response.get("error") == "unauthorized":
                    break
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    async def handle_line(self, line: bytes, authed: bool = False) -> Dict[str, Any]:
        try:
            request = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"id": None, "ok": False, "error": "bad-json"}
        if not isinstance(request, dict):
            return {"id": None, "ok": False, "error": "bad-request"}
        rid = request.get("id")
        if not authed:
            token = request.get("token")
            if not isinstance(token, str) or not self.token or not secrets.compare_digest(token, self.token):
                return {"id": rid, "ok": False, "error": "unauthorized"}
        method = self._methods.get(str(request.get("method") or ""))
        if method is None:
            return {"id": rid, "ok": False, "error": "unknown-method", "_authed": True}
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        try:
            result = await method(params)
        except Exception as error:  # a Governor failure must not kill the connection
            self.log.warning("GFG Bridge %s failed: %s", request.get("method"), error)
            return {"id": rid, "ok": False, "error": "internal", "_authed": True}
        if isinstance(result, dict) and result.get("success") is False:
            return {"id": rid, "ok": False, "error": str(result.get("error") or "rejected"), "_authed": True}
        return {"id": rid, "ok": True, "result": result, "_authed": True}

    # ----------------------------------------------------------------- methods
    async def _hello(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {"api": API_VERSION, "methods": sorted(self._methods), "modes": list(SHELL_MODES)}

    async def _status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        status = await self.plugin.get_governor_status(str(params.get("profile") or ""))
        return compact_status(status)

    async def _profiles(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.plugin.get_profiles()
        response = response if isinstance(response, dict) else {}
        return {"profiles": list(response.get("profiles") or []),
                "current": str(response.get("current_profile") or response.get("current") or "")}

    async def _current_profile(self, params: Dict[str, Any]) -> str:
        profile = str(params.get("profile") or "").strip()
        if profile:
            return profile
        return (await self._profiles({}))["current"]

    async def _set_mode(self, params: Dict[str, Any]) -> Dict[str, Any]:
        mode = str(params.get("mode") or "").lower()
        if mode not in SHELL_MODES:
            return {"success": False, "error": "mode-not-allowed"}
        profile = await self._current_profile(params)
        if not profile:
            return {"success": False, "error": "no-profile"}
        return await self.plugin.set_governor_mode(profile, mode)

    async def _set_frame_fusion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        enabled = params.get("enabled")
        if type(enabled) is not bool:
            return {"success": False, "error": "enabled-must-be-bool"}
        return await self.plugin.set_governor_frame_fusion(enabled)

    async def _set_feature(self, params: Dict[str, Any]) -> Dict[str, Any]:
        feature, enabled = str(params.get("feature") or ""), params.get("enabled")
        if feature not in SHELL_FEATURES or type(enabled) is not bool:
            return {"success": False, "error": "feature-not-allowed"}
        profile = await self._current_profile(params)
        if not profile:
            return {"success": False, "error": "no-profile"}
        return await self.plugin.set_governor_frame_os_feature(profile, feature, enabled)
