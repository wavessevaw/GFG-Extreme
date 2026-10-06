"""One-button diagnostic log: Start -> play -> Stop writes a single zip to the Steam Deck desktop.

The bundle answers "why does it not work" without a debugging session: a 1 Hz timeline of the
Governor, the renderer diagnostics appended during the recording, the Governor event journal,
the generated launch wrapper, the in-game overlay files and a self-test of every precondition.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

MAX_TIMELINE_BYTES = 24 * 1024 * 1024
MAX_DIAG_BYTES = 12 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024
SAMPLE_SECONDS = 1.0
DESKTOP_DIRNAME = "Desktop"


def desktop_dir(user_home: Path) -> Path:
    """The Steam Deck Linux desktop (Desktop Mode) of the Decky user."""
    return Path(user_home) / DESKTOP_DIRNAME


def _read_tail(path: Path, limit: int) -> bytes:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - limit))
            return handle.read(limit)
    except OSError:
        return b""


def _read_range(path: Path, start: int, limit: int) -> bytes:
    """Bytes appended after ``start``; if the file was truncated/rotated, from the beginning."""
    try:
        size = path.stat().st_size
        if size < start:
            start = 0
        begin = max(start, size - limit)
        with path.open("rb") as handle:
            handle.seek(begin)
            return handle.read(limit)
    except OSError:
        return b""


def compact_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """Small, flat 1 Hz record that keeps every field needed to explain a decision."""
    tel = status.get("telemetry") or {}
    summary = tel.get("summary") or {}
    snap = tel.get("snapshot") or {}
    point = status.get("active_point") or {}
    request = status.get("request") or {}
    ladder = status.get("ladder") or {}
    power = status.get("power") or {}

    def med(name: str) -> Any:
        return (summary.get(name) or {}).get("median")

    return {
        "state": status.get("state"), "reason": status.get("reason"), "enabled": status.get("enabled"),
        "profile": status.get("profile"), "target": status.get("target_output_fps"),
        "real": med("real"), "output": med("output"), "mult": med("multiplier"),
        "real_p5": (summary.get("real") or {}).get("p5"),
        "samples": summary.get("samples"), "misses": summary.get("misses"),
        "snapshot": {k: snap.get(k) for k in (
            "available", "path", "sample_age_ms", "event_seq", "sample_seq", "last_poll_error", "session_generation")},
        "point": point.get("key"), "point_mode": status.get("active_point_mode"),
        "request": request.get("point") if isinstance(request, dict) else None,
        "request_stage": request.get("stage") if isinstance(request, dict) else None,
        "ladder": {k: ladder.get(k) for k in ("attempts", "rejected", "skipped", "predicted_infeasible", "native_capacity")},
        "capability": status.get("capability"),
        "tdp": power.get("observed_tdp_w"), "tdp_owned": power.get("owned"), "tdp_available": power.get("available"),
        "effort": (status.get("effort") or {}).get("level"),
        "hud": status.get("hud"),
        "battery_min": (status.get("battery") or {}).get("minutes_left"),
    }


class SessionRecorder:
    def __init__(
        self,
        *,
        user_home: Path,
        config_dir: Path,
        runtime_state_dir: Path,
        wrapper_path: Path,
        status_provider: Callable[[], Dict[str, Any]],
        events_path: Path,
        diagnostics_paths: List[Path],
        saved_config_path: Path,
        layer_files: Dict[str, Path],
        plugin_log: Optional[Path] = None,
        logger: Any = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.user_home = Path(user_home)
        self.config_dir = Path(config_dir)
        self.runtime_state_dir = Path(runtime_state_dir)
        self.wrapper_path = Path(wrapper_path)
        self.status_provider = status_provider
        self.events_path = Path(events_path)
        self.diagnostics_paths = [Path(p) for p in diagnostics_paths]
        self.saved_config_path = Path(saved_config_path)
        self.layer_files = {k: Path(v) for k, v in layer_files.items()}
        self.plugin_log = Path(plugin_log) if plugin_log else None
        self.log = logger
        self.clock = clock
        self.recording = False
        self.started_at = 0.0
        self.last_file: Optional[str] = None
        self.last_error: Optional[str] = None
        self._timeline: Optional[Path] = None
        self._offsets: Dict[Path, int] = {}
        self._task: Optional[asyncio.Task] = None
        self._lines = 0
        self._profile = ""

    # ----------------------------------------------------------------- public
    def status(self) -> Dict[str, Any]:
        return {
            "recording": self.recording,
            "elapsed_s": round(self.clock() - self.started_at, 1) if self.recording else 0,
            "samples": self._lines,
            "last_file": self.last_file,
            "last_error": self.last_error,
            "desktop": str(desktop_dir(self.user_home)),
        }

    async def start(self, profile: str = "") -> Dict[str, Any]:
        if self.recording:
            return {"success": True, **self.status()}
        self.last_error = None
        try:
            stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.clock()))
            work = self.config_dir / "recordings"
            work.mkdir(parents=True, exist_ok=True)
            self._timeline = work / f"timeline-{stamp}.jsonl"
            self._timeline.write_text("", encoding="utf-8")
        except OSError as error:
            self.last_error = f"cannot-create-recording: {error}"
            return {"success": False, "error": self.last_error, **self.status()}
        self._offsets = {}
        for path in self.diagnostics_paths:
            try:
                self._offsets[path] = path.stat().st_size
            except OSError:
                self._offsets[path] = 0
        self._profile = profile
        self._lines = 0
        self.started_at = self.clock()
        self.recording = True
        self._append({"t": self.clock(), "marker": "start", "profile": profile})
        self._task = asyncio.create_task(self._sampler())
        return {"success": True, **self.status()}

    async def stop(self) -> Dict[str, Any]:
        if not self.recording:
            return {"success": False, "error": "not-recording", **self.status()}
        self.recording = False
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._append({"t": self.clock(), "marker": "stop"})
        try:
            path = await asyncio.to_thread(self._write_bundle)
        except Exception as error:  # a failed export must not lose the recording
            self.last_error = f"export-failed: {error}"
            return {"success": False, "error": self.last_error, **self.status()}
        self.last_file = str(path)
        return {"success": True, "file": self.last_file, **self.status()}

    # --------------------------------------------------------------- internals
    async def _sampler(self) -> None:
        while self.recording:
            try:
                record = compact_status(self.status_provider())
                record["t"] = self.clock()
                self._append(record)
            except Exception as error:
                self._append({"t": self.clock(), "marker": "sample-error", "error": str(error)})
            await asyncio.sleep(SAMPLE_SECONDS)

    def _append(self, record: Dict[str, Any]) -> None:
        if self._timeline is None:
            return
        try:
            if self._timeline.stat().st_size > MAX_TIMELINE_BYTES:
                return
            with self._timeline.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            self._lines += 1
        except OSError:
            pass

    def self_test(self) -> List[Dict[str, Any]]:
        """Every precondition of the Governor and the overlay, each with ok/detail."""
        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": name, "ok": bool(ok), "detail": detail})

        wrapper_text = ""
        try:
            wrapper_text = self.wrapper_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        add("launch wrapper installed", bool(wrapper_text), str(self.wrapper_path))
        add("wrapper contains in-game overlay support", "hud/active.conf" in wrapper_text)
        add("wrapper contains Governor overlay support", "mako_governor_overlay" in wrapper_text)
        for name, path in self.layer_files.items():
            add(f"file present: {name}", path.exists(), str(path))
        hud = self.config_dir / "hud"
        add("overlay config published (active.conf)", (hud / "active.conf").is_file(), str(hud / "active.conf"))
        add("overlay status line file present", (hud / "status.txt").is_file(), str(hud / "status.txt"))
        for path in self.diagnostics_paths:
            add(f"renderer diagnostics log: {path.name}", path.is_file(),
                f"{path.stat().st_size} bytes" if path.is_file() else "missing")
        add("saved profile readable", self.saved_config_path.is_file(), str(self.saved_config_path))
        add("desktop folder writable", os.access(desktop_dir(self.user_home).parent, os.W_OK),
            str(desktop_dir(self.user_home)))
        for label, sys_path in (
            ("TDP control: fastPPT/slowPPT cap writable",
             "/sys/class/hwmon"),
        ):
            writable = False
            try:
                for hw in Path(sys_path).iterdir():
                    for cap in ("power1_cap", "power2_cap"):
                        p = hw / cap
                        if p.exists() and os.access(p, os.W_OK):
                            writable = True
            except OSError:
                pass
            add(label, writable)
        return checks

    def _system_info(self) -> Dict[str, Any]:
        def read(path: str) -> str:
            try:
                return Path(path).read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                return ""

        def run(cmd: List[str]) -> str:
            try:
                return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                return ""

        return {
            "kernel": platform.release(),
            "dmi_product_name": read("/sys/devices/virtual/dmi/id/product_name"),
            "dmi_board_name": read("/sys/devices/virtual/dmi/id/board_name"),
            "os_release": read("/etc/os-release"),
            "gamescope_processes": run(["pgrep", "-a", "gamescope"])[:2000],
            "game_overlay_env_hint": "see timeline.jsonl 'capability' and 'snapshot' fields",
            "plugin_version": "GFG Extreme Decky 4.0.0-gfg.4 / Governor 0.0.3",
        }

    def _write_bundle(self) -> Path:
        out_dir = desktop_dir(self.user_home)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.clock()))
        target = out_dir / f"GFG-Extreme-log-{stamp}.zip"
        tmp = target.with_suffix(".zip.part")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("README.txt", (
                "GFG Extreme diagnostic log.\n"
                f"profile: {self._profile}\nduration_s: {round(self.clock() - self.started_at, 1)}\n"
                "timeline.jsonl   1 Hz Governor state (state, reason, real/output FPS, point, ladder, TDP, overlay)\n"
                "self_test.json   every precondition with ok/detail\n"
                "system.json      device, kernel, gamescope\n"
                "diagnostics-*.log renderer diagnostics appended during the recording\n"
                "governor-events.jsonl  Governor decisions during the recording\n"
                "launch-wrapper.sh the generated launcher\n"
                "overlay/         in-game overlay config and status line\n"
                "profile.json     saved profile\n"
                "plugin.log       tail of the Decky plugin log\n"))
            if self._timeline is not None and self._timeline.is_file():
                bundle.write(self._timeline, "timeline.jsonl")
            bundle.writestr("self_test.json", json.dumps(self.self_test(), indent=2))
            bundle.writestr("system.json", json.dumps(self._system_info(), indent=2))
            for path, start in self._offsets.items():
                data = _read_range(path, start, MAX_DIAG_BYTES)
                if data:
                    bundle.writestr(f"diagnostics-{path.name}", data)
            events = []
            try:
                for line in self.events_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        if float(json.loads(line).get("ts", 0)) >= self.started_at - 1:
                            events.append(line)
                    except (ValueError, TypeError):
                        continue
            except OSError:
                pass
            bundle.writestr("governor-events.jsonl", "\n".join(events) + ("\n" if events else ""))
            for src, name in (
                (self.wrapper_path, "launch-wrapper.sh"),
                (self.config_dir / "hud" / "active.conf", "overlay/active.conf"),
                (self.config_dir / "hud" / "status.txt", "overlay/status.txt"),
                (self.saved_config_path, "profile.json"),
            ):
                data = _read_tail(Path(src), MAX_FILE_BYTES)
                if data:
                    bundle.writestr(name, data)
            if self.plugin_log is not None:
                data = _read_tail(self.plugin_log, 2 * MAX_FILE_BYTES)
                if data:
                    bundle.writestr("plugin.log", data)
            try:
                for manifest in sorted(self.runtime_state_dir.glob("*launch*.json"))[:10]:
                    data = _read_tail(manifest, 64 * 1024)
                    if data:
                        bundle.writestr(f"launch-manifests/{manifest.name}", data)
            except OSError:
                pass
        os.replace(tmp, target)
        try:
            os.chmod(target, 0o644)
        except OSError:
            pass
        return target
