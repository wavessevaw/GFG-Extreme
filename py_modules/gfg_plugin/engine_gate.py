"""First-run gate (user, 3.1.0): the panel opens only once the KEDAVRA engine is installed and
running in this boot. Before that it shows one screen: install the engine, then reboot.

States, in the order a new player meets them:
  install   no engine installed, or the plugin carries a newer engine than the installed one
  reboot    installed in this boot (Gamescope still runs the old binary until the Deck reboots)
  failed    the last install failed, or the Deck rebooted and the engine is still not mounted
  ready     installed and mounted for this boot: the full panel
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


def boot_id(path: Path = BOOT_ID) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def read_record(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text())
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def gate(installed: Optional[str], bundled: Optional[str], mounted: bool, boot: str,
         record: Dict[str, Any]) -> Dict[str, Any]:
    """The panel's state from what is on disk and what this boot runs."""
    if record.get("error") and record.get("version") == bundled:
        return {"state": "failed", "error": str(record["error"])[:600]}
    if not installed:
        return {"state": "install", "update": False}
    if bundled and bundled != "unknown" and installed != bundled:
        return {"state": "install", "update": True, "installed": installed, "bundled": bundled}
    if record.get("boot_id") and record.get("boot_id") == boot:
        return {"state": "reboot"}
    if not mounted:
        if record.get("boot_id"):
            return {"state": "failed", "error": "The Deck rebooted, but Gamescope KEDAVRA was not started at boot. "
                                                "Install again, or save a report and send it."}
        return {"state": "reboot"}
    return {"state": "ready"}
