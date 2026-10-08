"""Display refresh leases: same exact Gamescope path as the Target FPS slider."""
import asyncio
import unittest

from test_governor_runtime import RuntimeBase


class RefreshLeaseTests(RuntimeBase):
    def setUp(self):
        super().setUp()
        self.svc.DEFAULT_MODE = "budget"
        self.svc._device = {"model": "oled", "product": "Galileo"}
        self.display.hz = 90
        self.display.supported = [45, 60, 90]
        self.display.calls = []
        self.display.read_current_refresh_hz = lambda: self.display.hz

        def sync(value):
            self.display.calls.append(value)
            if value not in self.display.supported:
                return {"success": True, "applied": False, "reason": "unsupported"}
            self.display.hz = value
            return {"success": True, "applied": True, "verified": True,
                    "verified_refresh_hz": value}
        self.display.sync_target_fps = sync
        self.display.get_active_display_info = lambda: {
            "success": True, "external": self.display.external,
            "internal": not self.display.external,
            "valid_rates": list(self.display.supported)}
        self.svc._active_profile = "game"

    def sync(self, *, force_off=False):
        return asyncio.run(self.svc._sync_savings_refresh(
            "game", self.display.get_active_display_info(), force_off=force_off))

    def test_hard_oled_exact_60_and_light_medium_keep_90(self):
        for level in ("light", "medium", "off"):
            self.assertTrue(self.svc.set_savings_effort("game", level)["success"])
            self.sync()
            self.assertEqual(self.display.hz, 90)
            self.assertEqual(self.display.calls, [])
        self.svc.set_savings_effort("game", "hard")
        self.assertEqual(self.sync()["current_refresh_hz"], 60)
        self.assertEqual(self.display.hz, 60)
        self.assertEqual(self.svc._savings_refresh_lease["original_hz"], 90)
        self.svc.set_savings_effort("game", "medium")
        self.sync()
        self.assertEqual(self.display.hz, 90)
        self.assertIsNone(self.svc._savings_refresh_lease)
        self.assertEqual(self.display.calls, [60, 90])

    def test_lcd_hard_45_restores_60(self):
        self.svc._device = {"model": "lcd", "product": "Jupiter"}
        self.display.hz = 60
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        self.assertEqual(self.display.hz, 45)
        self.svc.set_savings_effort("game", "off")
        self.sync()
        self.assertEqual(self.display.hz, 60)

    def test_manual_slider_override_is_not_overwritten(self):
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        self.display.hz = 75  # external user action in Steam
        self.sync()
        self.assertIsNone(self.svc._savings_refresh_lease)
        self.assertEqual(self.svc._savings_refresh_override, "game")
        self.sync()
        self.assertEqual(self.display.hz, 75)
        self.assertEqual(self.display.calls, [60])
        self.svc.set_savings_effort("game", "off")
        self.sync()
        self.assertEqual(self.display.hz, 75)

    def test_docked_display_untouched_and_no_false_45_target(self):
        self.svc._device = {"model": "lcd", "product": "Jupiter"}
        self.display.external = True
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        self.assertEqual(self.display.hz, 90)
        self.assertEqual(self.display.calls, [])
        self.assertIsNone(self.svc._savings_refresh_lease)

    def test_unsupported_rate_is_reported_without_modeset(self):
        self.svc._device = {"model": "lcd", "product": "Jupiter"}
        self.display.supported = [60, 90]
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        self.assertIn("unavailable", self.svc._savings_refresh_error)
        self.assertEqual(self.display.calls, [])
        self.assertEqual(self.display.hz, 90)

    def test_leaving_battery_restores_hard_owned_refresh(self):
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        self.svc.set_mode("game", "balanced")
        self.sync()
        self.assertEqual(self.display.hz, 90)
        self.assertIsNone(self.svc._savings_refresh_lease)

    def test_reload_can_restore_persisted_lease(self):
        self.svc.set_savings_effort("game", "hard")
        self.sync()
        saved = self.svc._settings["savings_refresh_lease"]
        self.assertEqual(saved["original_hz"], 90)
        # A disabled profile on restart no longer qualifies for Hard.
        self.svc.set_savings_effort("game", "off")
        self.svc._savings_refresh_lease = dict(saved)
        self.sync(force_off=True)
        self.assertEqual(self.display.hz, 90)
        self.assertNotIn("savings_refresh_lease", self.svc._settings)


if __name__ == "__main__":
    unittest.main()
