#!/usr/bin/env python3
"""Run the real GFG Bridge server with a fake Governor, for shell screenshots and the
Godot<->Python integration test. Writes the discovery file under <home>.

usage: fake_bridge.py <home> [--seconds N] [--log calls.jsonl]
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py_modules"))
from gfg_plugin.shell_bridge import ShellBridge  # noqa: E402


class FakeGovernor:
    def __init__(self, log_path):
        self.mode, self.fusion, self.boost = "autopilot", True, False
        self.log_path = log_path

    def _log(self, *call):
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(call) + "\n")

    async def get_governor_status(self, profile=""):
        return {"profile": "default", "enabled": True, "mode": self.mode, "state": "HOLD",
                "target_output_fps": 90,
                "sensors": {"temp_c": 63.0, "gpu_busy_pct": 91, "cpu_total_pct": 38, "gpu_clock_mhz": 1520},
                "battery": {"percent": 74, "external_power": False, "minutes_left": 128},
                "power_feedback": {"cap_w": 11.5, "draw_w": 11.1},
                "telemetry": {"summary": {"real": {"median": 45.0}, "output": {"median": 89.6}, "frametime": {"median": 22.3}}},
                "frame_fusion": {"setting_enabled": self.fusion, "state": "active" if self.fusion else "off"},
                "frame_os": {"feature_settings": {"continuous_boost": self.boost}}}

    async def get_profiles(self):
        return {"profiles": ["default"], "current_profile": "default"}

    async def set_governor_mode(self, profile, mode):
        self.mode = mode
        self._log("set_mode", profile, mode)
        return {"success": True}

    async def set_governor_frame_fusion(self, enabled):
        self.fusion = enabled
        self._log("set_frame_fusion", enabled)
        return {"success": True}

    async def set_governor_frame_os_feature(self, profile, feature, enabled):
        self.boost = enabled
        self._log("set_feature", profile, feature, enabled)
        return {"success": True}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("home")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    bridge = ShellBridge(FakeGovernor(a.log), Path(a.home), logging.getLogger("fake-bridge"))
    await bridge.start()
    print(bridge.discovery_path, flush=True)
    await asyncio.sleep(a.seconds)
    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
