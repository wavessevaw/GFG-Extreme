"""Documented SteamOS Manager FanControl1: OEM BIOS (0) or OS (1).

This selects the existing firmware curve. It does not write BIOS settings or
claim a custom predictive fan curve / temperature or FPS improvement.
"""
from typing import Optional, Tuple
from .steamos_tdp import SteamOSManagerTdp, BUS_NAME, OBJECT_PATH

INTERFACE = "com.steampowered.SteamOSManager1.FanControl1"


class SteamOSManagerFan(SteamOSManagerTdp):
    def __init__(self, *, uid=None, **kwargs):
        super().__init__(**kwargs)
        self.uid = uid

    def _environment(self):
        env = super()._environment()
        if self.uid is not None:
            runtime = f"/run/user/{self.uid}"
            env["XDG_RUNTIME_DIR"] = runtime
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime}/bus"
            if self._home:
                env["HOME"] = self._home
        return env

    def query(self) -> Optional[int]:
        tool = self._which("busctl")
        if tool is None:
            return None
        ok, text = self._runner([tool, "--user", "get-property", BUS_NAME, OBJECT_PATH,
                                INTERFACE, "FanControlState"])
        if not ok or text not in ("u 0", "u 1"):
            return None
        return int(text[-1])

    def set(self, state: int) -> Tuple[bool, str]:
        if state not in (0, 1):
            return False, "invalid-oem-controller"
        tool = self._which("busctl")
        if tool is None:
            return False, "no-busctl"
        return self._runner([tool, "--user", "set-property", BUS_NAME, OBJECT_PATH,
                             INTERFACE, "FanControlState", "u", str(state)])
