"""Extreme transition ceiling and optional native feature acknowledgement."""
import asyncio
import logging
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_power import SteamDeckPowerActuator
from gfg_plugin.governor_service import GovernorService


class Configuration:
    def __init__(self, root):
        self.config_dir = root
        self.runtime_state_dir = root / "runtime-state"


class TransitionTests(unittest.TestCase):
    def make_power(self, root, fast=24, slow=20):
        h = root / "hwmon" / "hwmon0"
        h.mkdir(parents=True)
        for name, value in (("power1_label", "fastPPT"), ("power2_label", "slowPPT"),
                            ("power1_cap", int(fast * 1e6)), ("power2_cap", int(slow * 1e6)),
                            ("power1_cap_min", 3000000), ("power2_cap_min", 3000000),
                            ("power1_cap_max", 30000000), ("power2_cap_max", 30000000)):
            (h / name).write_text(str(value) + "\n")
        power = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
        power.discover()
        return power

    def test_claim_applies_ceiling_before_returning_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            power = self.make_power(Path(temp))
            result = power.claim_at_ceiling_w(15)
            self.assertTrue(result["success"])
            self.assertEqual((result["observed_fast_w"], result["observed_tdp_w"]), (15, 15))
            self.assertEqual((power.state.initial_fast_uw, power.state.initial_slow_uw),
                             (24000000, 20000000))
            self.assertTrue(power.restore_if_owned()["restored"])
            self.assertEqual((power.status()["observed_fast_w"], power.status()["observed_tdp_w"]), (24, 20))

    def test_lower_fast_cap_is_an_inherited_user_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            power = self.make_power(Path(temp), fast=10, slow=12)
            result = power.claim_at_ceiling_w(15)
            self.assertTrue(result["success"])
            self.assertLessEqual(max(result["observed_fast_w"], result["observed_tdp_w"]), 10)

    def service(self, root, power):
        service = GovernorService(Configuration(root), None, logging.getLogger("extreme-test"))
        service.power = power
        service._settings = {"profiles": {"Game": {"enabled": True, "mode": "extreme"}}}
        service._active_profile = "Game"
        return service

    def test_no_point_trial_starts_above_inherited_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            power = self.make_power(root)
            service = self.service(root, power)
            self.assertIsNotNone(asyncio.run(service._budget_power("Game")))
            self.assertIsNone(service._point)
            self.assertEqual((power.status()["observed_fast_w"], power.status()["observed_tdp_w"]), (15, 15))

    def test_replanning_in_extreme_keeps_ceiling_but_disable_restores(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            power = self.make_power(root)
            service = self.service(root, power)
            asyncio.run(service._budget_power("Game"))
            asyncio.run(service._restore_power("display-mode-changed"))
            self.assertTrue(power.state.owned)
            self.assertEqual((power.status()["observed_fast_w"], power.status()["observed_tdp_w"]), (15, 15))
            service._settings["profiles"]["Game"]["enabled"] = False
            asyncio.run(service._restore_power("user-disabled"))
            self.assertFalse(power.state.owned)
            self.assertEqual((power.status()["observed_fast_w"], power.status()["observed_tdp_w"]), (24, 20))

    def test_device_100_w_cap_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            power = self.make_power(root, fast=100, slow=100)
            h = root / "hwmon" / "hwmon0"
            (h / "power1_cap_max").write_text("120000000\n")
            (h / "power2_cap_max").write_text("120000000\n")
            power.discover()
            service = self.service(root, power)
            self.assertEqual(asyncio.run(service._budget_power("Game"))["max"], 100.0)
            self.assertEqual(service._extreme_ceiling["ceiling_w"], 100.0)
            self.assertEqual((power.status()["observed_fast_w"], power.status()["observed_tdp_w"]), (100, 100))
            self.assertTrue(power.restore_if_owned()["restored"])

    def test_failed_ceiling_stops_trials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            power = self.make_power(root)
            def fail(*args, **kwargs):
                raise OSError("refused")
            power._write_value = fail
            service = self.service(root, power)
            self.assertIsNone(asyncio.run(service._budget_power("Game")))
            self.assertEqual(service._status["reason"], "extreme-ceiling-not-applied")

    def test_failed_ceiling_never_creates_observe_only_budget(self):
        from unittest.mock import AsyncMock
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            power = self.make_power(root)
            service = self.service(root, power)
            service._launch_info = AsyncMock(return_value={"running": True})
            service._capability = lambda *args: {"overlay_active": True}
            async def rejected(profile):
                service._status.update(state="PAUSED", reason="extreme-ceiling-not-applied")
                return None
            service._budget_power = rejected
            asyncio.run(service._budget_step("Game", False, 90))
            self.assertIsNone(service._budget)
            self.assertIsNone(service._request)

    def test_successful_ceiling_retry_is_not_blocked_by_old_status_reason(self):
        from unittest.mock import AsyncMock, patch
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            service = self.service(root, self.make_power(root))
            service._status.update(state="PAUSED", reason="extreme-ceiling-not-applied")
            service._launch_info = AsyncMock(return_value={"running": True})
            service._capability = lambda *args: {"overlay_active": True}
            service._budget_power = AsyncMock(return_value={"min": 3, "max": 15})
            with patch("gfg_plugin.governor_service.BudgetController") as controller:
                controller.side_effect = RuntimeError("budget-start-reached")
                with self.assertRaisesRegex(RuntimeError, "budget-start-reached"):
                    asyncio.run(service._budget_step("Game", False, 90))
                controller.assert_called_once()
