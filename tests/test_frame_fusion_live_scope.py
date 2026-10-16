"""Regression for Fusion scope lost behind an unchanged Saved fingerprint.

Field log GFG 2.1.4: the renderer's environment allowed Fusion, but its
native requested scope stayed false throughout 961 active-Autopilot samples.
An in-flight Governor point prevents standby-overlay writes; the regular live
sync must watch the settings-owned Fusion flag as well as Saved TOML changes.
"""
import asyncio
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "py_modules")]

from test_governor_runtime import RuntimeBase


class LiveFusionScopeTests(RuntimeBase):
    def setUp(self):
        super().setUp()
        self.svc.set_mode("game", "autopilot")
        self.svc._active_profile = "game"
        self.svc._point = {"key": "30x3"}
        self.svc._point_deltas = {"frame_generation_enabled": True,
                                  "adaptive": False, "multiplier": 3,
                                  "base_fps_cap": 30, "target_fps": 90}
        self.saved = self.svc._saved_profile_config("game")
        self.assertIsNotNone(self.saved)
        self.svc._ensure_overlay_sync(
            "game", {**self.svc._base_for("game", self.saved),
                     **self.svc._point_deltas}, "30x3")
        self.svc._saved_fp = self.cfg.saved_config_fingerprint()
        self.svc._fusion_scope_synced = True

    def scope(self):
        text = self.svc.overlay.path_for("game").read_text(encoding="utf-8")
        profiles = tomllib.loads(text)["profile"]
        profile = next(p for p in profiles if p["name"] == "game")
        return profile["gfg_frame_fusion"], profile["base_fps_cap"]

    def sync(self):
        asyncio.run(self.svc._sync_overlay("game", self.saved))

    def test_disabling_live_fusion_updates_busy_point_without_reverting_fps(self):
        self.assertEqual(self.scope(), (True, 30))
        rev = self.svc.overlay.read_header("game")["rev"]
        self.assertTrue(self.svc.set_frame_fusion(False)["success"])
        self.assertEqual(self.scope(), (True, 30),
                         "standby refresh must not overwrite an active point")
        self.sync()
        self.assertEqual(self.scope(), (False, 30))
        self.assertGreater(self.svc.overlay.read_header("game")["rev"], rev)
        self.assertEqual(self.svc._fusion_scope_synced, False)
        self.assertIn("# gfg-governor-point: 30x3", self.svc.overlay.path_for("game").read_text())

    def test_reenabling_fusion_updates_live_scope_with_unchanged_saved(self):
        self.svc.set_frame_fusion(False)
        self.sync()
        rev = self.svc.overlay.read_header("game")["rev"]
        self.assertTrue(self.svc.set_frame_fusion(True)["success"])
        self.sync()
        self.assertEqual(self.scope(), (True, 30))
        self.assertGreater(self.svc.overlay.read_header("game")["rev"], rev)
        self.assertEqual(self.svc._fusion_scope_synced, True)
        self.assertEqual(self.cfg.saved_config_fingerprint(), self.svc._saved_fp)

    def test_initial_live_sync_checks_scope_even_when_header_is_leased(self):
        self.svc._fusion_scope_synced = None
        self.svc._saved_fp = None
        self.svc.set_frame_fusion(False)
        self.sync()
        self.assertEqual(self.scope(), (False, 30))
        self.assertIs(self.svc._fusion_scope_synced, False)

    def test_no_extra_rewrites_when_runtime_scope_is_unchanged(self):
        self.sync()
        rev = self.svc.overlay.read_header("game")["rev"]
        self.sync()
        self.assertEqual(self.svc.overlay.read_header("game")["rev"], rev)

    def test_failed_overlay_write_does_not_acknowledge_new_scope(self):
        self.svc.set_frame_fusion(False)
        with patch.object(self.svc.overlay, "ensure", side_effect=OSError("readonly")):
            self.sync()
        self.assertEqual(self.scope(), (True, 30))
        self.assertTrue(self.svc._fusion_scope_synced)
        self.sync()
        self.assertEqual(self.scope(), (False, 30))

    def test_inflight_renderer_request_still_owns_its_overlay(self):
        self.svc.set_frame_fusion(False)
        self.svc._request = object()
        self.sync()
        self.assertEqual(self.scope(), (True, 30))
        self.svc._request = None
        self.sync()
        self.assertEqual(self.scope(), (False, 30))


if __name__ == "__main__":
    unittest.main()
