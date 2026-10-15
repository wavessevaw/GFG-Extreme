"""GFG Bridge: token-gated, allow-listed, read-mostly link for GFG Shell."""
import asyncio
import json
import logging
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
from gfg_plugin.shell_bridge import ShellBridge, compact_status


class FakePlugin:
    def __init__(self):
        self.calls = []

    async def get_governor_status(self, profile=""):
        self.calls.append(("status", profile))
        return {"profile": "p1", "enabled": True, "mode": "autopilot", "state": "HOLD",
                "target_output_fps": 90,
                "sensors": {"temp_c": 61.5, "gpu_busy_pct": 88, "cpu_total_pct": 40, "gpu_clock_mhz": 1600},
                "battery": {"percent": 77, "external_power": False, "minutes_left": 140},
                "power_feedback": {"cap_w": 12, "draw_w": 11.2},
                "telemetry": {"summary": {"real": {"median": 45.04}, "output": {"median": 89.9}, "frametime": {"median": 22.2}}},
                "frame_fusion": {"setting_enabled": True, "state": "active"},
                "frame_os": {"feature_settings": {"continuous_boost": True}}}

    async def get_profiles(self):
        return {"profiles": ["default", "p1"], "current_profile": "p1"}

    async def set_governor_mode(self, profile, mode):
        self.calls.append(("mode", profile, mode))
        return {"success": True}

    async def set_governor_frame_fusion(self, enabled):
        self.calls.append(("fusion", enabled))
        return {"success": True}

    async def set_governor_frame_os_feature(self, profile, feature, enabled):
        self.calls.append(("feature", profile, feature, enabled))
        return {"success": True}

    async def set_governor_enabled(self, profile, enabled):
        self.calls.append(("enabled", profile, enabled))
        return {"success": True}

    async def set_governor_autopilot_preference(self, profile, preference):
        self.calls.append(("preference", profile, preference))
        return {"success": True}

    async def set_governor_hud(self, profile, enabled=None, preset=None, position=None, style=None):
        self.calls.append(("hud", profile, enabled))
        return {"success": True}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin = FakePlugin()
        self.bridge = ShellBridge(self.plugin, Path(self.tmp.name), logging.getLogger("t"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_async(self, coro):
        return asyncio.run(coro)

    def call(self, req, authed=False):
        return self.run_async(self.bridge.handle_line(json.dumps(req).encode(), authed))

    def test_compact_status_maps_governor_fields(self):
        c = compact_status(self.run_async(self.plugin.get_governor_status()))
        self.assertEqual(c["mode"], "autopilot")
        self.assertEqual(c["fps"], {"real": 45.0, "output": 89.9, "frametime_ms": 22.2})
        self.assertEqual(c["power"], {"tdp_w": 12.0, "draw_w": 11.2})
        self.assertEqual(c["battery"]["percent"], 77.0)
        self.assertTrue(c["frame_fusion"]["setting"])
        self.assertTrue(c["continuous_boost"])
        self.assertTrue(c["boost"])
        self.assertFalse(compact_status({"frame_os": {"feature_settings": {"boost": False}}})["boost"])

    def test_compact_status_tolerates_empty_and_garbage(self):
        c = compact_status({"sensors": "x", "battery": None, "telemetry": {"summary": 3}})
        self.assertIsNone(c["fps"]["real"])
        self.assertIsNone(c["sensors"]["temp_c"])
        self.assertEqual(compact_status(None)["mode"], "")

    def test_requires_token(self):
        self.bridge.token = "secret"
        self.assertEqual(self.call({"id": 1, "method": "hello"})["error"], "unauthorized")
        self.assertEqual(self.call({"id": 1, "method": "hello", "token": "nope"})["error"], "unauthorized")
        r = self.call({"id": 2, "method": "hello", "token": "secret"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["api"], 1)

    def test_bad_json_and_unknown_method(self):
        self.assertEqual(self.run_async(self.bridge.handle_line(b"{nope", True))["error"], "bad-json")
        self.assertEqual(self.call({"id": 3, "method": "set_tdp", "params": {"w": 30}}, True)["error"], "unknown-method")

    def test_mode_allow_list_excludes_extreme_and_uses_current_profile(self):
        self.assertEqual(self.call({"id": 1, "method": "set_mode", "params": {"mode": "extreme"}}, True)["error"], "mode-not-allowed")
        self.assertTrue(self.call({"id": 2, "method": "set_mode", "params": {"mode": "quality"}}, True)["ok"])
        self.assertIn(("mode", "p1", "quality"), self.plugin.calls)

    def test_feature_and_fusion_validation(self):
        self.assertFalse(self.call({"id": 1, "method": "set_feature", "params": {"feature": "shield", "enabled": True}}, True)["ok"])
        self.assertFalse(self.call({"id": 1, "method": "set_frame_fusion", "params": {"enabled": "yes"}}, True)["ok"])
        self.assertTrue(self.call({"id": 1, "method": "set_feature", "params": {"feature": "continuous_boost", "enabled": False}}, True)["ok"])
        self.assertTrue(self.call({"id": 1, "method": "set_frame_fusion", "params": {"enabled": True}}, True)["ok"])
        self.assertIn(("feature", "p1", "continuous_boost", False), self.plugin.calls)
        self.assertTrue(self.call({"id": 1, "method": "set_feature", "params": {"feature": "boost", "enabled": False}}, True)["ok"])
        self.assertIn(("feature", "p1", "boost", False), self.plugin.calls)
        self.assertIn(("fusion", True), self.plugin.calls)

    def test_enabled_preference_and_hud(self):
        c = compact_status({"autopilot_preference": "battery", "hud": {"enabled": True},
                            "frame_os": {"feature_settings": {"touch_boost": False}}})
        self.assertEqual(c["preference"], "battery")
        self.assertTrue(c["hud"])
        self.assertFalse(c["touch_boost"])
        self.assertTrue(c["latency"])
        self.assertEqual(compact_status({})["preference"], "auto")
        self.assertFalse(compact_status({})["hud"])
        ok = lambda m, p: self.call({"id": 1, "method": m, "params": p}, True)["ok"]
        self.assertTrue(ok("set_enabled", {"enabled": False}))
        self.assertFalse(ok("set_enabled", {"enabled": "no"}))
        self.assertTrue(ok("set_preference", {"preference": "smoothness"}))
        self.assertFalse(ok("set_preference", {"preference": "extreme"}))
        self.assertTrue(ok("set_hud", {"enabled": True}))
        self.assertTrue(ok("set_feature", {"feature": "touch_boost", "enabled": False}))
        self.assertTrue(ok("set_feature", {"feature": "latency", "enabled": True}))
        for call in [("enabled", "p1", False), ("preference", "p1", "smoothness"), ("hud", "p1", True),
                     ("feature", "p1", "touch_boost", False), ("feature", "p1", "latency", True)]:
            self.assertIn(call, self.plugin.calls)

    def test_end_to_end_socket_and_discovery_file(self):
        async def scenario():
            await self.bridge.start()
            path = self.bridge.discovery_path
            info = json.loads(path.read_text())
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            reader, writer = await asyncio.open_connection("127.0.0.1", info["port"])
            writer.write((json.dumps({"id": 1, "method": "status", "token": info["token"]}) + "\n").encode())
            first = json.loads(await reader.readline())
            # Later requests on an authenticated connection need no token.
            writer.write(b'{"id": 2, "method": "profiles"}\n')
            second = json.loads(await reader.readline())
            writer.close()
            await self.bridge.stop()
            return first, second, path.exists()
        first, second, still_there = self.run_async(scenario())
        self.assertTrue(first["ok"])
        self.assertEqual(first["result"]["fps"]["output"], 89.9)
        self.assertEqual(second["result"]["current"], "p1")
        self.assertFalse(still_there)

    def test_unauthorized_connection_is_closed(self):
        async def scenario():
            await self.bridge.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", self.bridge.port)
            writer.write(b'{"id": 1, "method": "status"}\n')
            reply = json.loads(await reader.readline())
            eof = await reader.read()
            writer.close()
            await self.bridge.stop()
            return reply, eof
        reply, eof = self.run_async(scenario())
        self.assertEqual(reply["error"], "unauthorized")
        self.assertEqual(eof, b"")
        self.assertEqual(self.plugin.calls, [])


if __name__ == "__main__":
    unittest.main()
