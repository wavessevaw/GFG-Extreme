"""Set the TDP the way Steam's own slider does: through ``steamos-manager``.

Ported from the earlier GFG Extreme efficiency monitor (v0.0.1_oldtdp), which
changed the TDP on the user's Deck where direct sysfs writes did not stick.
SteamOS exposes the limit as ``TdpLimit`` of ``com.steampowered.SteamOSManager1
.TdpLimit1`` on the user session bus; the manager writes the amdgpu hwmon caps
and Steam's quick menu and performance overlay follow it.  A direct write to the
hwmon caps bypasses the manager, which keeps (and may re-apply) its own value.

Order of preference: ``steamosctl set-tdp-limit N`` (SteamOS 3.7+), then
``busctl --user set-property``.  Whole watts only.  Nothing runs through a
shell, every command has a timeout.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

BUS_NAME = "com.steampowered.SteamOSManager1"
OBJECT_PATH = "/com/steampowered/SteamOSManager1"
INTERFACE = "com.steampowered.SteamOSManager1.TdpLimit1"
COMMAND_TIMEOUT = 4.0


class SteamOSManagerTdp:
    def __init__(self, *, bin_dirs: Optional[Sequence[str]] = None, home: Optional[str] = None,
                 timeout: float = COMMAND_TIMEOUT, runner=None) -> None:
        self._bin_dirs = list(bin_dirs) if bin_dirs is not None else ["/usr/bin", "/bin", "/usr/local/bin"]
        self._home = home
        self._timeout = timeout
        self._runner = runner or self._subprocess
        self.method: Optional[str] = None
        self.range: Optional[Tuple[int, int]] = None
        self.reason = "not-probed"

    # ------------------------------------------------------------- plumbing
    def _which(self, name: str) -> Optional[str]:
        for directory in self._bin_dirs:
            candidate = Path(directory) / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None

    def _environment(self) -> Dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "HOME", "USER", "LC_ALL")}
        env.setdefault("PATH", "/usr/bin:/bin")
        runtimes: List[str] = []
        for value in (os.environ.get("XDG_RUNTIME_DIR"), f"/run/user/{os.getuid()}"):
            if value and value not in runtimes:
                runtimes.append(value)
        if self._home:
            try:
                value = f"/run/user/{Path(self._home).stat().st_uid}"
                if value not in runtimes:
                    runtimes.append(value)
            except OSError:
                pass
        for runtime in runtimes:
            if (Path(runtime) / "bus").exists():
                env["XDG_RUNTIME_DIR"] = runtime
                env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime}/bus"
                break
        else:
            if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
                env["DBUS_SESSION_BUS_ADDRESS"] = os.environ["DBUS_SESSION_BUS_ADDRESS"]
        return env

    def _subprocess(self, args: List[str]) -> Tuple[bool, str]:
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=self._timeout,
                                    env=self._environment(), stdin=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except (OSError, ValueError) as error:
            return False, str(error)
        output = (result.stdout or "").strip()
        if result.returncode != 0:
            return False, ((result.stderr or "").strip() or output or f"exit {result.returncode}")[:300]
        return True, output

    @staticmethod
    def _first_int(text: str) -> Optional[int]:
        match = re.search(r"(-?\d+)", text or "")
        return int(match.group(1)) if match else None

    # --------------------------------------------------------------- public
    def query(self, which: str) -> Optional[int]:
        """'limit', 'min' or 'max' in watts, or None."""
        suffix = {"limit": "", "min": "-min", "max": "-max"}[which]
        prop = {"limit": "TdpLimit", "min": "TdpLimitMin", "max": "TdpLimitMax"}[which]
        ctl = self._which("steamosctl")
        if ctl:
            ok, out = self._runner([ctl, f"get-tdp-limit{suffix}"])
            value = self._first_int(out) if ok else None
            if value is not None:
                return value
        busctl = self._which("busctl")
        if busctl:
            ok, out = self._runner([busctl, "--user", "get-property", BUS_NAME, OBJECT_PATH, INTERFACE, prop])
            if ok and out.startswith("u "):
                return self._first_int(out)
        return None

    def probe(self) -> bool:
        self.method, self.range = None, None
        if self._which("steamosctl"):
            self.method = "steamosctl"
        elif self._which("busctl"):
            self.method = "busctl"
        else:
            self.reason = "no-tool"
            return False
        low, high = self.query("min"), self.query("max")
        if low is None or high is None or not 0 < low <= high <= 60:
            self.method = None
            self.reason = "no-tdp-interface"
            return False
        self.range = (int(low), int(high))
        self.reason = "ok"
        return True

    @property
    def available(self) -> bool:
        return self.method is not None and self.range is not None

    def set(self, watts: int) -> Tuple[bool, str]:
        if not self.available:
            return False, f"steamos-manager unavailable ({self.reason})"
        assert self.range is not None
        wanted = max(self.range[0], min(self.range[1], int(watts)))
        ok, message = False, ""
        if self.method == "steamosctl":
            ok, message = self._runner([self._which("steamosctl") or "steamosctl", "set-tdp-limit", str(wanted)])
        if not ok and self._which("busctl"):
            ok, message = self._runner([self._which("busctl") or "busctl", "--user", "set-property", BUS_NAME,
                                        OBJECT_PATH, INTERFACE, "TdpLimit", "u", str(wanted)])
        return ok, message

    def status(self) -> Dict[str, object]:
        return {"method": self.method, "min_w": self.range[0] if self.range else None,
                "max_w": self.range[1] if self.range else None, "reason": self.reason}
