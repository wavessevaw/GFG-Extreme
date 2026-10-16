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
        # Production _accept_request caches the *full* overlay, including
        # Fusion consent, rather than just the cadence deltas.
        self.svc._point_deltas = {"gfg_frame_fusion": True,
                                  "frame_generation_enabled": True,
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

    def test_native_opt_in_is_emitted_into_the_renderer_toml(self):
        # This would fail in 2.1.5 even if Governor calculated a true delta:
        # generate_toml_content_multi_profile silently dropped the field.
        for requested in (False, True):
            with self.subTest(requested=requested):
                projected = self.cfg.build_governor_overlay_text(
                    "game", {"gfg_frame_fusion": requested})
                profile = next(p for p in tomllib.loads(projected)["profile"]
                               if p["name"] == "game")
                self.assertIn("gfg_frame_fusion", profile)
                self.assertIs(profile["gfg_frame_fusion"], requested)
                self.assertIs(tomllib.loads(projected)["profile"][0]["gfg_frame_fusion"],
                              False, "other Saved profiles must never inherit Fusion")

    def test_actual_autopilot_runtime_overlay_contains_fusion_true(self):
        self.assertEqual(self.scope(), (True, 30))
        # The serialized policy is distinct from the process launch env gate.
        self.assertIn("gfg_frame_fusion = true",
                      self.svc.overlay.path_for("game").read_text(encoding="utf-8"))

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

    def test_cached_old_full_point_cannot_override_latest_consent(self):
        self.assertIs(self.svc._point_deltas["gfg_frame_fusion"], True)
        self.svc.set_frame_fusion(False)
        self.sync()
        self.assertEqual(self.scope(), (False, 30))
        self.assertIs(self.svc._point_deltas["gfg_frame_fusion"], True,
                      "the original trial cache may stay intact")

    def test_active_frame_os_injection_cannot_restore_stale_fusion(self):
        self.svc._injection = {**self.svc._point_deltas,
                               "base_fps_cap": 45}
        self.svc.set_frame_fusion(False)
        self.sync()
        self.assertEqual(self.scope(), (False, 45))
        self.assertTrue(self.svc._injection["gfg_frame_fusion"],
                        "stale injected overlay is deliberately present")

    def test_switching_away_from_autopilot_closes_fusion_with_live_point(self):
        self.svc.set_mode("game", "balanced")
        self.sync()
        self.assertEqual(self.scope(), (False, 30))
        self.assertIs(self.svc._point_deltas["gfg_frame_fusion"], True)

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
