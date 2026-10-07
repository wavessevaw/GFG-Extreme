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

from .privileged_power import writer as privileged_writer

MAX_TIMELINE_BYTES = 24 * 1024 * 1024
MAX_DIAG_BYTES = 12 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024
SAMPLE_SECONDS = 1.0
DESKTOP_DIRNAME = "Desktop"
PROBE_EVERY_SAMPLES = 5
HOST_MANGOHUD_MANIFEST = Path("/usr/share/vulkan/implicit_layer.d/MangoHud.x86_64.json")
# Environment the launch wrapper sets for the game; enough to tell why a layer did or did not load.
PROBE_ENV_KEYS = (
    "MAKO_PROFILE", "MAKO_CONFIG", "MAKO_EXTERNAL_VULKAN_LAYER", "MANGOHUD", "DISABLE_MANGOHUD",
    "MANGOHUD_CONFIGFILE", "VK_INSTANCE_LAYERS", "VK_IMPLICIT_LAYER_PATH", "VK_ADD_IMPLICIT_LAYER_PATH",
    "VK_LAYER_PATH", "VK_LOADER_LAYERS_ENABLE", "VK_LOADER_LAYERS_DISABLE", "GAMESCOPE_WAYLAND_DISPLAY",
    "PRESSURE_VESSEL_RUNTIME", "STEAM_COMPAT_APP_ID", "SteamAppId",
)


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
        "tdp_fast": power.get("observed_fast_w"), "apu_w": power.get("draw_w"),
        "tdp_method": power.get("method"),
        "effort": (status.get("effort") or {}).get("level"),
        "hud": status.get("hud"),
        "battery_min": (status.get("battery") or {}).get("minutes_left"),
        "frametime": summary.get("frametime"),
        "sensors": status.get("sensors"),
        "diagnosis": status.get("diagnosis"),
    }


def probe_power_sensors(hwmon_root: Path = Path("/sys/class/hwmon")) -> List[Dict[str, Any]]:
    """Every hwmon with power* attributes: which caps exist, who else may set them, measured draw."""
    found: List[Dict[str, Any]] = []
    try:
        hwmons = sorted(Path(hwmon_root).iterdir())
    except OSError:
        return found
    for hwmon in hwmons:
        try:
            files = sorted(hwmon.glob("power*"))
        except OSError:
            continue
        if not files:
            continue
        entry: Dict[str, Any] = {"hwmon": hwmon.name}
        try:
            entry["path"] = str(hwmon.resolve())
            entry["name"] = (hwmon / "name").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            entry.setdefault("name", None)
        for path in files:
            try:
                entry[path.name] = path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError) as error:
                entry[path.name] = f"<{type(error).__name__}>"
        found.append(entry)
    return found


def probe_game_processes(proc_root: Path = Path("/proc"), limit: int = 8) -> List[Dict[str, Any]]:
    """Vulkan processes started through the GFG wrapper: their layer env and which layers are mapped.

    A game counts when its environment carries ``MAKO_CONFIG`` (exported by the wrapper) and it has
    ``libvulkan`` mapped.  ``mangohud_loaded`` answers "did the in-game overlay layer load at all".
    """
    found: List[Dict[str, Any]] = []
    try:
        entries = sorted((p for p in Path(proc_root).iterdir() if p.name.isdigit()), key=lambda p: int(p.name))
    except OSError:
        return found
    for proc in entries:
        try:
            env: Dict[str, str] = {}
            for item in (proc / "environ").read_bytes().split(b"\0"):
                key, sep, value = item.partition(b"=")
                if sep:
                    env[key.decode("utf-8", "ignore")] = value.decode("utf-8", "ignore")
            if "MAKO_CONFIG" not in env:
                continue
            maps = (proc / "maps").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "libvulkan" not in maps:
            continue
        libs = sorted({line.rsplit(" ", 1)[-1] for line in maps.splitlines() if ".so" in line})
        try:
            comm = (proc / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            comm = ""
        found.append({
            "pid": int(proc.name), "comm": comm,
            "env": {k: env[k] for k in PROBE_ENV_KEYS if k in env},
            "mangohud_loaded": any("libMangoHud" in lib for lib in libs),
            "layer_libraries": [lib for lib in libs if "vulkan" in lib.lower() or "MangoHud" in lib
                                or "mako" in lib.lower() or "gamescope" in lib.lower()][:40],
        })
        if len(found) >= limit:
            break
    return found


ACTIVITY_LOOKBACK_S = 1800.0


# What to do about a failed setup check (matched by substring of the check name).
SETUP_ADVICE = (
    ("launch wrapper installed", "Open Settings → System and install the engine."),
    ("file present", "An engine file is missing. Reinstall the engine in Settings → System."),
    ("wrapper contains", "The launcher is out of date. Reinstall the engine in Settings → System."),
    ("host MangoHud Vulkan layer", "MangoHud's Vulkan layer is not installed on this system, so the in-game overlay cannot appear."),
    ("in-game overlay switched on", "Turn the overlay on in Settings → In-game overlay."),
    ("overlay config published", "Turn the overlay on in Settings → In-game overlay."),
    ("overlay status line", "Turn the overlay on and press RUN; the status line is written while the Governor runs."),
    ("renderer diagnostics log", "Start the game with the GFG launch command (Settings → Launch command), then press RUN."),
    ("diagnostics marker", "Press RUN once, then restart the game."),
    ("rotation writable", "The diagnostics log belongs to another user or is a symlink; remove it from ~/.config/mako-render."),
    ("TDP control", "GFG cannot write TDP. Accept the root access request when the plugin loads, or reinstall the plugin."),
    ("saved profile readable", "The profile file is missing; open Settings → Profile and create or select one."),
    ("desktop folder writable", "Logs cannot be saved to the Desktop folder."),
)


def advice_for(check: str) -> str:
    return next((text for key, text in SETUP_ADVICE if key in check), "")


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
        hud_enabled: Optional[Callable[[str], bool]] = None,
        process_probe: Callable[[], List[Dict[str, Any]]] = probe_game_processes,
        host_mangohud_manifest: Path = HOST_MANGOHUD_MANIFEST,
        activity: Any = None,
        power_probe: Callable[[], List[Dict[str, Any]]] = probe_power_sensors,
    ) -> None:
        self.activity = activity
        self.power_probe = power_probe
        self._power_start: List[Dict[str, Any]] = []
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
        self.hud_enabled = hud_enabled
        self.process_probe = process_probe
        self.host_mangohud_manifest = Path(host_mangohud_manifest)
        self._game_processes: List[Dict[str, Any]] = []
        self.recording = False
        self.started_at = 0.0
        self.last_file: Optional[str] = None
        self.last_error: Optional[str] = None
        self.last_findings: List[str] = []
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
            "findings": self.last_findings,
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
        self._game_processes = []
        try:
            self._power_start = self.power_probe()
        except Exception:
            self._power_start = []
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
                if self._lines % PROBE_EVERY_SAMPLES == 1:
                    await self._probe()
            except Exception as error:
                self._append({"t": self.clock(), "marker": "sample-error", "error": str(error)})
            await asyncio.sleep(SAMPLE_SECONDS)

    async def _probe(self) -> None:
        """Keep the latest non-empty snapshot: the game may already be closed when Stop is pressed."""
        found = await asyncio.to_thread(self.process_probe)
        if found:
            self._game_processes = found

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

    def check_setup(self, profile: str = "") -> Dict[str, Any]:
        """The same preconditions the log records, with advice for each failure, for the Diagnostics screen."""
        if profile and not self.recording:
            self._profile = profile
        checks = self.self_test()
        for check in checks:
            if not check["ok"]:
                check["advice"] = advice_for(check["check"])
        failed = [c for c in checks if not c["ok"]]
        return {"success": True, "checks": checks, "failed": len(failed), "total": len(checks)}

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
        if self.hud_enabled is not None:
            add("in-game overlay switched on for this profile", self.hud_enabled(self._profile), self._profile)
        add("host MangoHud Vulkan layer present", self.host_mangohud_manifest.is_file(),
            str(self.host_mangohud_manifest))
        add("overlay config published (active.conf)", (hud / "active.conf").is_file(), str(hud / "active.conf"))
        add("overlay status line file present", (hud / "status.txt").is_file(), str(hud / "status.txt"))
        for index, path in enumerate(self.diagnostics_paths):
            present = path.is_file()
            if index == 0:
                add(f"renderer diagnostics log: {path.name}", present,
                    f"{path.stat().st_size} bytes" if present else "missing")
            else:
                # Legacy RAM fallback: the renderer writes it only on old setups.  Missing is normal.
                add(f"optional diagnostics fallback: {path.name}", True,
                    f"{path.stat().st_size} bytes" if present else "not used (normal)")
        marker = self.runtime_state_dir / "governor-diagnostics.enabled"
        add("Governor diagnostics marker present", marker.is_file(), str(marker))
        # The wrapper silently skips diagnostics when the log or a rotation is
        # a symlink or owned by someone else (see wrapper_generation).
        if self.diagnostics_paths:
            log = self.diagnostics_paths[0]
            foreign = []
            for entry in [log] + [log.with_name(f"{log.name}.{i}") for i in range(1, 5)]:
                try:
                    st = entry.lstat()
                except OSError:
                    continue
                if entry.is_symlink() or not entry.is_file() or st.st_uid != os.getuid():
                    foreign.append(f"{entry.name} uid={st.st_uid}")
            add("diagnostics log rotation writable by wrapper", not foreign,
                ", ".join(foreign) or f"uid={os.getuid()}")
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
            helper = privileged_writer()
            add(label, writable or helper is not None,
                f"root helper pid {helper.pid}" if helper is not None else
                ("direct" if writable else "plugin runs without root"))
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
            # Other TDP controllers (ryzenadj-based Decky plugins, PowerTools, ...) set the SMU
            # limits directly and win over the hwmon caps without changing what those files read.
            "tdp_tools_processes": run(["pgrep", "-a", "-f", "ryzenadj|powertools|PowerControl|SimpleDeckyTDP"])[:2000],
            "decky_plugins": sorted(p.name for p in (self.user_home / "homebrew" / "plugins").glob("*"))
            if (self.user_home / "homebrew" / "plugins").is_dir() else [],
            "game_overlay_env_hint": "see timeline.jsonl 'capability' and 'snapshot' fields",
            "plugin_version": "GFG Extreme 1.0.2 (engine 4.0.0-gfg.4)",
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
                "summary.txt      plain-language verdict of this log (read this first)\n"
                "timeline.jsonl   1 Hz Governor state (state, reason, real/output FPS, point, ladder, TDP, overlay)\n"
                "self_test.json   every precondition with ok/detail\n"
                "system.json      device, kernel, gamescope\n"
                "diagnostics-*.log renderer diagnostics appended during the recording\n"
                "governor-events.jsonl  Governor decisions during the recording\n"
                "activity.jsonl   your actions (UI clicks, game launches/exits), Governor states, TDP writes;\n"
                "                 starts 30 min before the recording\n"
                "launch-wrapper.sh the generated launcher\n"
                "overlay/         in-game overlay config and status line\n"
                "game-processes.json  layer env of the running game and whether MangoHud was loaded\n"
                "power-sensors.json   every hwmon power cap/draw at start and end of the recording\n"
                "profile.json     saved profile\n"
                "plugin.log       tail of the Decky plugin log\n"))
            if self._timeline is not None and self._timeline.is_file():
                bundle.write(self._timeline, "timeline.jsonl")
            bundle.writestr("self_test.json", json.dumps(self.self_test(), indent=2))
            bundle.writestr("system.json", json.dumps(self._system_info(), indent=2))
            processes = self._game_processes or self.process_probe()
            try:
                power_end = self.power_probe()
            except Exception as error:
                power_end = [{"error": str(error)}]
            bundle.writestr("power-sensors.json", json.dumps(
                {"start": self._power_start, "end": power_end}, indent=2))
            bundle.writestr("game-processes.json", json.dumps(processes, indent=2))
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
            if self.activity is not None:
                # Include what happened before Record was pressed (game launch, Run).
                actions = self.activity.since(self.started_at - ACTIVITY_LOOKBACK_S)
                bundle.writestr("activity.jsonl", "\n".join(actions) + ("\n" if actions else ""))
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
                manifests = sorted(self.runtime_state_dir.glob("launches/*.json"),
                                   key=lambda p: p.stat().st_mtime, reverse=True)
                for manifest in manifests[:10]:
                    data = _read_tail(manifest, 64 * 1024)
                    if data:
                        bundle.writestr(f"launch-manifests/{manifest.name}", data)
            except OSError:
                pass
        try:  # the verdict goes first in the bundle; a failed analysis must never lose the log
            from .log_report import analyze, render
            with zipfile.ZipFile(tmp) as finished:
                report = analyze(finished)
            summary = render(report)
            self.last_findings = list(report["findings"])[:4]
            with zipfile.ZipFile(tmp, "a", zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("summary.txt", summary)
        except Exception as error:
            if self.log:
                self.log.warning("Log summary failed: %s", error)
        os.replace(tmp, target)
        try:
            os.chmod(target, 0o644)
        except OSError:
            pass
        return target
