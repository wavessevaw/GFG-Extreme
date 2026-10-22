"""Where GFG Extreme 3.0 keeps its files, and the release identity."""
from __future__ import annotations

from pathlib import Path

VERSION = "3.1.2"
CODENAME = ""

# 3.0 data (settings, learned power points, sessions, logs). Owned by the desktop user.
DATA_DIRNAME = ".config/gfg-extreme"
# 2.x data: read once by the migration, never written, so a reinstall of 2.1.6 still finds it.
LEGACY_DATA_DIRNAME = ".config/mako-render"
# 2.x renderer payload and launch wrappers (removed or replaced by legacy_cleanup).
LEGACY_PAYLOAD_DIRNAME = ".local/share/mako-render"
LEGACY_WRAPPERS = (".local/bin/gfg", ".local/bin/mako-run")

# The HUD bitmap GFG Extreme publishes for the KEDAVRA Gamescope (kfg_hud). A path of its own,
# so a standalone GSF Kedavra plugin still running beside it cannot overwrite the picture.
HUD_PATH = Path("/dev/shm/gfg-extreme-hud.raw")


def data_dir(home: Path) -> Path:
    return Path(home) / DATA_DIRNAME


def runtime_dir(home: Path) -> Path:
    """Logs, telemetry and session history (rotated)."""
    return data_dir(home) / "runtime"
