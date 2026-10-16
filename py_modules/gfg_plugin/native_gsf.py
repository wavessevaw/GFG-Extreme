"""Independent native GSF launch preference and live status, no power controls."""
from __future__ import annotations
import json
import os
import pwd
import subprocess
from pathlib import Path
import time
from .managed_files import write_managed_text_atomically

MODES = ("off", "2", "3")
MARKER = "native-gsf.mode"

def installation(user_home: Path | None) -> dict:
    """A Steam launch option is usable only when its executable exists too."""
    if user_home is None:
        return {"installed": False, "launcher_ready": False, "launch_command": None,
                "component_version": None}
    root = user_home / ".local/share/gfg-native"
    launcher = user_home / ".local/bin/gfg-native"
    ready = launcher.is_file() and os.access(launcher, os.X_OK)
    installed = ready and all((root / f).is_file() and os.access(root / f, os.R_OK)
                             for f in ("libVkLayer_gfg_native.so", "VkLayer_gfg_native.json"))
    version = None
    try:
        version = json.loads((root / "MANIFEST.json").read_text()).get("version")
    except (OSError, ValueError, AttributeError):
        pass
    return {"installed": installed, "launcher_ready": ready,
            "launch_command": str(launcher) + " %command%" if installed else None,
            "component_version": version}

def stage_packaged(user_home: Path, package_root: Path | None = None) -> dict:
    """Install only a checksum-verified bundled native component as the game user.

    Staging on plugin startup does not activate the layer. The mode click is
    still the opt-in. No network, power change or system installation occurs.
    The idempotent installer preserves the last distinct component for rollback.
    """
    package = package_root or Path(__file__).resolve().parents[2] / "bin/gfg-native"
    if not (package / "install.sh").is_file():
        ready = installation(user_home)
        return {"success": ready["installed"], "packaged": False, **ready,
                **({} if ready["installed"] else {"error": "native-component-not-packaged-or-installed"})}
    env = dict(os.environ, HOME=str(user_home),
               XDG_DATA_HOME=str(user_home / ".local/share"),
               XDG_STATE_HOME=str(user_home / ".local/state"))
    try:
        command = ["bash", str(package / "install.sh")]
        owner = user_home.stat().st_uid
        if os.geteuid() == 0 and owner != 0:
            command = ["runuser", "-u", pwd.getpwuid(owner).pw_name, "--", *command]
        result = subprocess.run(command, env=env,
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            return {"success": False, "error": "native-package-check-or-install-failed"}
        ready = installation(user_home)
        return {"success": ready["installed"], "packaged": True, **ready,
                **({} if ready["installed"] else {"error": "native-launcher-not-ready-after-install"})}
    except (OSError, KeyError, subprocess.TimeoutExpired) as error:
        return {"success": False, "error": str(error)}


def requested(runtime: Path) -> str:
    try:
        mode = (runtime / MARKER).read_text().strip()
        return mode if mode in MODES else "off"
    except (OSError, UnicodeError):
        return "off"

def set_mode(runtime: Path, mode: str, logger, user_home: Path | None = None) -> dict:
    if mode not in MODES:
        return {"success": False, "error": "invalid-native-gsf-mode"}
    try:
        marker = runtime / MARKER
        write_managed_text_atomically(marker, mode + "\n", 0o600, logger)
        # Decky may run as root. The game user must be able to read its mode.
        if user_home is not None and os.geteuid() == 0:
            owner = user_home.stat()
            os.chown(marker, owner.st_uid, owner.st_gid, follow_symlinks=False)
    except OSError as error:
        return {"success": False, "error": str(error)}
    return {"success": True, "mode": mode, "relaunch_required": True}

def status(runtime: Path, user_home: Path | None) -> dict:
    mode = requested(runtime)
    ready = installation(user_home)
    installed = ready["installed"]
    contexts = []
    folder = user_home / ".local/state/gfg-native/status" if user_home is not None else None
    try:
        paths = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:32] if folder is not None else []
        for path in paths:
            try:
                if path.stat().st_size > 16384:
                    continue
                raw = json.loads(path.read_text())
                if raw.get("schema") != 1 or raw.get("engine") != "gfg-native-gsf":
                    continue
                pid = raw["pid"]
                if type(pid) is not int or pid <= 0 or time.time()*1000 - raw["updated_unix_ms"] > 10000:
                    continue
                process = Path(f"/proc/{pid}/stat").read_text()
                start = int(process[process.rfind(")")+2:].split()[19])
                if start != raw["process_start_ticks"]:
                    continue
                contexts.append(raw)
            except (OSError, ValueError, KeyError, TypeError):
                continue
    except OSError:
        pass
    return {"requested_mode": mode, **ready, "contexts": contexts,
            "state": "active-wsi" if contexts else "off" if mode == "off" else "waiting" if installed else "unavailable",
            "reason": None if contexts else "restart-game-to-apply" if installed else "native-component-not-installed",
            "physical_displayed_fps": None, "unique_displayed_fps": None,
            "hardware_acceptance": "NOT TESTED"}
