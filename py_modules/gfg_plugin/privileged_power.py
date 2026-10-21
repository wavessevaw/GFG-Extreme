"""Which power-control files GFG Extreme may write.

GFG Extreme 3.0 runs as root (Decky's ``root`` flag): it installs and rolls back the KEDAVRA
Gamescope runtime and writes the Steam Deck fastPPT/slowPPT hwmon caps directly. Files it
creates in the user's home are handed to the home owner (``user_files.own``). The 2.x root
helper process (fork, then drop to the user) is gone with the features that needed it.

``writer()`` stays as the actuator's hook for a separate privileged writer; it returns None,
so the actuator writes the caps itself, and only to paths ``allowed_cap_path`` accepts.
"""
from __future__ import annotations

import os
import re
from typing import Optional

_CAP_RE = re.compile(r"^/sys/devices/[A-Za-z0-9_.:/-]+/hwmon/hwmon[0-9]+/power[0-9]+_cap$")


def allowed_cap_path(path: str) -> Optional[str]:
    """Resolved hwmon PPT cap path, or None for anything else."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return None
    return real if _CAP_RE.match(real) else None


class HelperTimeout(OSError):
    """A privileged write did not answer in time (kept for the actuator's error handling)."""


def writer() -> None:
    return None
