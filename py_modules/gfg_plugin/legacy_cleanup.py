"""Remove what GFG Extreme 2.x (MAKO) left on the Deck, and put back what it changed.

Runs once per home after the migration (and again from the panel on request). Every step is
reversible from the backup zip the migration made, or harmless to skip:

1. System state 2.x may have left behind if it was stopped mid-session (crash, forced
   reinstall): the CPU clock cap, the manual GPU clock, Half Rate Shading and the fan
   controller. Each is put back only when it still reads exactly what 2.x wrote, so a value
   the player chose afterwards stays.
2. The MAKO renderer payload (~/.local/share/mako-render), its Vulkan layer registrations,
   the MAKO Flatpak runtime extensions and the MAKO entries in Flatpak app overrides.
3. Launch wrappers: ~/.local/bin/gfg and ~/.local/bin/mako-run become a two-line passthrough,
   so a game whose launch options still say "~/.local/bin/gfg %command%" keeps starting.

Never touched: the player's Lossless Scaling purchase in steamapps and an lsfg-vk layer the
player installed (GFG 3.0 uses neither; the panel mentions the layer),
~/.config/vkBasalt, and ~/.config/mako-render (2.x settings, kept for a rollback to 2.1.6).
"""
from __future__ import annotations

import configparser
import io
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import LEGACY_DATA_DIRNAME, LEGACY_PAYLOAD_DIRNAME, LEGACY_WRAPPERS
from .steamos_tdp import BUS_NAME, OBJECT_PATH, SteamOSManagerTdp
from .user_files import own, write_text_atomic

LAYER_MANIFESTS = (
    "VkLayer_MAKO_render.json", "VkLayer_MAKO_render.x86.json",
    "VkLayer_MAKO_spatial_scaling.json", "VkLayer_MAKO_spatial_scaling.x86.json",
    "VkLayer_MAKO_EXTREME_predictive.json", "VkLayer_GFG_Extreme_frame_os.json",
    "VkLayer_GFG_Extreme_hud.json",
)
# Installed by the player for 2.x's LSFG-VK backend, not by GFG: reported, never removed.
USER_LSFG_MANIFEST = ".local/share/vulkan/implicit_layer.d/VkLayer_LSFGVK_frame_generation.json"
FLATPAK_EXTENSION = "org.freedesktop.Platform.VulkanLayer.makorender"
MAKO_MARKERS = ("mako-render", "makorender", ".local/bin/gfg", ".local/bin/mako-run")
EXTRA_FILES = (".local/bin/gfg-diagnostics",)

SHIM = """#!/bin/sh
# GFG Extreme 3.0: frame generation now runs inside Gamescope (KEDAVRA), not in the game.
# This file only keeps old launch options ("~/.local/bin/gfg %command%") working.
# You can remove it from the game's launch options.
exec "$@"
"""

CPU_PATH = re.compile(r"^/sys/devices/system/cpu/cpufreq/policy\d+/scaling_max_freq$")
VRS_PATH = re.compile(r"^/tmp/[A-Za-z0-9._-]{1,64}$")


def _read_int(path: Path) -> Optional[int]:
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


class SessionTools(SteamOSManagerTdp):
    """busctl / steamosctl / flatpak in the desktop user's session (the plugin runs as root)."""

    def run(self, tool: str, *args: str) -> Tuple[bool, str]:
        exe = self._which(tool)
        if exe is None:
            return False, f"no {tool}"
        return self._runner([exe, *args])


class LegacyCleanup:
    def __init__(self, home: Path, tools: Optional[SessionTools] = None, sys_root: Path = Path("/"),
                 owner: Optional[Tuple[int, int]] = None) -> None:
        self.home = Path(home)
        self.legacy = self.home / LEGACY_DATA_DIRNAME
        self.tools = tools or SessionTools(home=str(home), timeout=20.0)
        self.root = Path(sys_root)
        self.owner = owner
        self.log: List[Dict[str, Any]] = []

    def _note(self, step: str, ok: bool, text: str) -> None:
        self.log.append({"step": step, "ok": ok, "text": text})

    # ------------------------------------------------------------ 1. system state
    def recover_system_state(self) -> None:
        self._recover_cpu()
        self._recover_gpu()
        self._recover_vrs()
        self._recover_fan()

    def _recover_cpu(self) -> None:
        marker = self.legacy / "runtime-state" / "cpu-cap.json"
        try:
            data = json.loads(marker.read_text())
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for name, entry in data.items():
            if not CPU_PATH.match(str(name)) or not isinstance(entry, dict):
                continue
            initial, written = entry.get("initial"), entry.get("written")
            previous = entry.get("previous", written)
            if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (initial, written, previous)):
                continue
            path = self.root / str(name).lstrip("/")
            found = _read_int(path)
            if found is None or found == initial:
                continue
            if found not in (written, previous):
                self._note("cpu", True, f"{path.parent.name}: changed since 2.x, left as is")
                continue
            try:
                path.write_text(f"{initial}\n")
                ok = _read_int(path) == initial
            except OSError as error:
                ok = False
                self._note("cpu", False, f"{path.parent.name}: {error}")
                continue
            self._note("cpu", ok, f"{path.parent.name}: CPU clock limit back to {initial // 1000} MHz"
                       if ok else f"{path.parent.name}: restore did not verify")

    def _gpu_get(self, prop: str) -> Optional[str]:
        ok, out = self.tools.run("busctl", "--user", "get-property", BUS_NAME, OBJECT_PATH,
                                 "com.steampowered.SteamOSManager1.GpuPerformanceLevel1", prop)
        if not ok:
            return None
        return out.split(" ", 1)[-1].strip().strip('"')

    def _recover_gpu(self) -> None:
        receipt = self.legacy / "autopilot-gpu-receipt.json"
        try:
            data = json.loads(receipt.read_text())
        except (OSError, ValueError):
            return
        if not isinstance(data, dict) or data.get("phase") not in ("partial", "owned", "restore-pending"):
            return
        level = self._gpu_get("GpuPerformanceLevel")
        if level != "manual":
            self._note("gpu", True, "GPU clock: not in manual mode, nothing to put back")
            return
        manual = self._gpu_get("ManualGpuClock")
        if data.get("applied_max") is not None and manual not in (str(data.get("applied_max")), str(data.get("saved_manual"))):
            self._note("gpu", True, "GPU clock: changed since 2.x, left as is")
            return
        steps = []
        if isinstance(data.get("saved_manual"), int):
            steps.append(("set-manual-gpu-clock", str(data["saved_manual"])))
        saved = data.get("saved_level") if data.get("saved_level") in ("auto", "manual", "low", "high", "profile_peak") else "auto"
        steps.append(("set-gpu-performance-level", saved))
        for cmd, value in steps:
            ok, out = self.tools.run("steamosctl", cmd, value)
            if not ok:
                self._note("gpu", False, f"GPU clock: steamosctl {cmd} failed: {out}")
                return
        self._note("gpu", True, f"GPU clock: back to {saved}")

    def _recover_vrs(self) -> None:
        receipt = self.legacy / "autopilot-vrs-receipt.json"
        try:
            data = json.loads(receipt.read_text())
        except (OSError, ValueError):
            return
        path = str((data or {}).get("session_path") or "")
        if data.get("original") != "1x1" or not VRS_PATH.match(path):
            return
        p = self.root / path.lstrip("/")
        try:
            if p.is_symlink() or p.read_text().strip() != "2x2":
                return
            # In place: Mesa watches this inode.
            with open(p, "r+") as f:
                f.truncate(0)
                f.write("1x1")
            self._note("vrs", True, "Half Rate Shading: off again, as before 2.x")
        except OSError as error:
            self._note("vrs", False, f"Half Rate Shading: {error}")

    def _recover_fan(self) -> None:
        marker = self.legacy / "runtime-state" / "extreme-fan-undo.json"
        try:
            data = json.loads(marker.read_text())
        except (OSError, ValueError):
            return
        original = data.get("original") if isinstance(data, dict) else None
        if original not in (0, 1) or original == 0:
            return
        iface = "com.steampowered.SteamOSManager1.FanControl1"
        ok, out = self.tools.run("busctl", "--user", "get-property", BUS_NAME, OBJECT_PATH, iface, "FanControlState")
        if not ok or out.strip() != "u 0":
            return
        ok, out = self.tools.run("busctl", "--user", "set-property", BUS_NAME, OBJECT_PATH, iface,
                                 "FanControlState", "u", str(original))
        self._note("fan", ok, "Fan: back to the OS fan curve" if ok else f"Fan: {out}")

    # ------------------------------------------------------------ 2. MAKO payload
    def files_to_remove(self) -> List[Path]:
        out = []
        payload = self.home / LEGACY_PAYLOAD_DIRNAME
        if payload.exists():
            out.append(payload)
        layers = self.home / ".local/share/vulkan/implicit_layer.d"
        for name in LAYER_MANIFESTS:
            if (layers / name).exists() or (layers / name).is_symlink():
                out.append(layers / name)
        for rel in EXTRA_FILES:
            if (self.home / rel).exists():
                out.append(self.home / rel)
        return out

    def remove_payload(self) -> None:
        for path in self.files_to_remove():
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self._note("files", True, f"Removed {path.relative_to(self.home)}")
            except OSError as error:
                self._note("files", False, f"Could not remove {path}: {error}")

    def flatpak_extensions(self) -> List[str]:
        ok, out = self.tools.run("flatpak", "list", "--user", "--runtime", "--columns=ref")
        if not ok:
            return []
        return [line.strip() for line in out.splitlines() if line.strip().startswith(FLATPAK_EXTENSION)]

    def remove_flatpak(self) -> None:
        for ref in self.flatpak_extensions():
            ok, out = self.tools.run("flatpak", "uninstall", "--user", "--noninteractive", "-y", ref)
            self._note("flatpak", ok, f"Removed Flatpak extension {ref}" if ok else f"Flatpak {ref}: {out}")

    @staticmethod
    def clean_override(text: str) -> Optional[str]:
        """Flatpak override file without MAKO entries; None when nothing changes."""
        cp = configparser.RawConfigParser(delimiters=("=",), interpolation=None, strict=False)
        cp.optionxform = str  # type: ignore[assignment]
        try:
            cp.read_string(text)
        except configparser.Error:
            return None
        changed = False
        if cp.has_section("Context"):
            for key in ("filesystems", "unset-environment"):
                if not cp.has_option("Context", key):
                    continue
                items = [i for i in cp.get("Context", key).split(";") if i]
                keep = [i for i in items if not any(m in i for m in MAKO_MARKERS)
                        and not (key == "unset-environment" and i.lstrip("!").startswith("MAKO_"))]
                if keep != items:
                    changed = True
                    if keep:
                        cp.set("Context", key, ";".join(keep) + ";")
                    else:
                        cp.remove_option("Context", key)
        if cp.has_section("Environment"):
            for key, value in list(cp.items("Environment")):
                if key.startswith("MAKO_") or key.startswith("GFG_") or any(m in value for m in MAKO_MARKERS):
                    cp.remove_option("Environment", key)
                    changed = True
        if not changed:
            return None
        for section in list(cp.sections()):
            if not cp.items(section):
                cp.remove_section(section)
        buf = io.StringIO()
        cp.write(buf, space_around_delimiters=False)
        return buf.getvalue()

    def override_files(self) -> List[Path]:
        d = self.home / ".local/share/flatpak/overrides"
        try:
            return sorted(p for p in d.iterdir() if p.is_file())
        except OSError:
            return []

    def clean_overrides(self) -> None:
        for path in self.override_files():
            try:
                new = self.clean_override(path.read_text())
            except OSError:
                continue
            if new is None:
                continue
            try:
                if new.strip():
                    write_text_atomic(path, new, self.owner)
                else:
                    path.unlink()
                self._note("flatpak", True, f"Removed MAKO entries from the Flatpak overrides of {path.name}")
            except OSError as error:
                self._note("flatpak", False, f"{path.name}: {error}")

    # ------------------------------------------------------------ 3. wrappers
    def shim_wrappers(self) -> None:
        for rel in LEGACY_WRAPPERS:
            path = self.home / rel
            if not path.exists() and not path.is_symlink():
                continue
            try:
                if path.is_symlink() or path.is_dir():
                    continue
                if path.read_text(errors="replace") == SHIM:
                    continue
                write_text_atomic(path, SHIM, self.owner, mode=0o755)
                self._note("wrapper", True, f"~/{rel} now only starts the game (old launch options keep working)")
            except OSError as error:
                self._note("wrapper", False, f"~/{rel}: {error}")

    # ------------------------------------------------------------ all
    def run(self, *, system_state: bool = True) -> Dict[str, Any]:
        self.log = []
        if system_state:
            self.recover_system_state()
        self.remove_payload()
        self.remove_flatpak()
        self.clean_overrides()
        self.shim_wrappers()
        return {"ok": all(e["ok"] for e in self.log), "steps": self.log}

    def pending(self) -> Dict[str, Any]:
        """What a cleanup would still do (shown in the panel)."""
        wrappers = [rel for rel in LEGACY_WRAPPERS if (self.home / rel).is_file()
                    and (self.home / rel).read_text(errors="replace") != SHIM]
        overrides = []
        for p in self.override_files():
            try:
                if self.clean_override(p.read_text()) is not None:
                    overrides.append(p.name)
            except OSError:
                pass
        files = [str(p.relative_to(self.home)) for p in self.files_to_remove()]
        return {"files": files, "wrappers": wrappers, "overrides": overrides,
                "clean": not (files or wrappers or overrides),
                "user_lsfg_layer": (self.home / USER_LSFG_MANIFEST).exists()}
