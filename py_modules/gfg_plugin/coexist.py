"""Living next to the standalone GSF Kedavra plugin.

Both plugins drive the same engine: the patched Gamescope installed in /var/lib/kedavra. GFG
Extreme 3.0 carries the same engine and takes it over safely:

  * GFG publishes its HUD at its own path and points kfg_hud there, so the standalone
    plugin's HUD file cannot replace the picture;
  * the Policy Coordinator notices another tool changing the engine's settings (conflict)
    and backs off instead of fighting;
  * "Take over" turns the standalone plugin's HUD off in its own settings (a backup is kept)
    and records GFG Extreme as the engine's owner; Decky keeps the plugin installed, the
    player can remove it from Decky.

Warning shown in the panel: uninstalling the standalone plugin from Decky runs its own
uninstall, which disables the shared engine; GFG then offers "Reinstall engine".
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .user_files import own, write_json_atomic

STANDALONE_NAMES = ("GSF Kedavra", "KEDAVRA")
OWNER_FILE = "owner"


def find_standalone(home: Path) -> List[Dict[str, Any]]:
    out = []
    plugins = Path(home) / "homebrew" / "plugins"
    try:
        dirs = sorted(p for p in plugins.iterdir() if p.is_dir())
    except OSError:
        return out
    for d in dirs:
        try:
            manifest = json.loads((d / "plugin.json").read_text())
        except (OSError, ValueError):
            continue
        if manifest.get("name") in STANDALONE_NAMES:
            version = None
            try:
                version = json.loads((d / "package.json").read_text()).get("version")
            except (OSError, ValueError):
                pass
            out.append({"dir": str(d), "name": manifest.get("name"), "version": version})
    return out


class Coexistence:
    def __init__(self, home: Path, var_root: Path = Path("/var/lib/kedavra"),
                 owner: Optional[Tuple[int, int]] = None, version: str = "") -> None:
        self.home = Path(home)
        self.var = Path(var_root)
        self.owner = owner
        self.version = version
        self.standalone_settings = self.home / ".local/share/kedavra/settings.json"

    def engine_owner(self) -> Optional[str]:
        try:
            return (self.var / OWNER_FILE).read_text().strip() or None
        except OSError:
            return None

    def mark_owner(self) -> None:
        try:
            self.var.mkdir(parents=True, exist_ok=True)
            (self.var / OWNER_FILE).write_text(f"gfg-extreme {self.version}\n")
        except OSError:
            pass

    def status(self) -> Dict[str, Any]:
        found = find_standalone(self.home)
        hud_on = None
        try:
            hud_on = bool(json.loads(self.standalone_settings.read_text()).get("hud", True))
        except (OSError, ValueError):
            pass
        owner = self.engine_owner()
        return {"standalone": found, "standalone_hud": hud_on if found else None,
                "engine_owner": owner, "taken_over": bool(owner and owner.startswith("gfg-extreme"))}

    def take_over(self) -> Dict[str, Any]:
        steps = []
        if self.standalone_settings.exists():
            try:
                data = json.loads(self.standalone_settings.read_text())
            except (OSError, ValueError):
                data = {}
            if data.get("hud", True):
                backup = self.standalone_settings.with_name(f"settings.before-gfg-{int(time.time())}.json")
                try:
                    shutil.copy2(self.standalone_settings, backup)
                    own(backup, self.owner)
                    data["hud"] = False
                    write_json_atomic(self.standalone_settings, data, self.owner)
                    steps.append("GSF Kedavra's own HUD turned off (backup kept)")
                except OSError as error:
                    steps.append(f"Could not change GSF Kedavra's settings: {error}")
        self.mark_owner()
        steps.append("GFG Extreme now owns the KEDAVRA engine")
        return {"ok": True, "steps": steps, **self.status()}
