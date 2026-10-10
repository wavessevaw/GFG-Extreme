"""Fault injection around real Governor lifecycle; no hardware claims."""
import asyncio
import json
import unittest
from unittest.mock import patch
import test_governor_runtime as legacy
from gfg_plugin.governor_restore import power_restore_error, cpu_restore_error


class RestoreResultTests(unittest.TestCase):
    def test_power_requires_explicit_success_and_released_ownership(self):
        for result in (None, {}, {"success": False, "error": "write"},
                       {"success": True, "state": {"owned": True}},
                       {"success": True, "state": {"restore_pending": True}}):
            self.assertIsNotNone(power_restore_error(result))
        for reason in ("restored", "not-owned", "external-change"):
            self.assertIsNone(power_restore_error({"success": True, "reason": reason,
                                                   "state": {"owned": False}}))

    def test_cpu_noop_and_external_takeover_are_complete(self):
        self.assertIsNone(cpu_restore_error({"owned": False, "restore_pending": False}))
        self.assertIsNotNone(cpu_restore_error({"owned": False, "restore_pending": True}))
        self.assertIsNotNone(cpu_restore_error({"owned": True, "restore_pending": False}))


class RestoreBarrierTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.RuntimeBase()
        self.fixture.setUp()
        self.svc = self.fixture.svc
        self.svc._active_profile = "game"
        self.svc._status.update(profile="game", enabled=True, state="LOCKED")
        self.svc.power.claim()
        self.svc._settings["profiles"]["game"]["enabled"] = False

    def tearDown(self):
        self.fixture.tearDown()

    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_failed_power_stop_is_pending_and_retries_before_new_work(self):
        actual = self.svc.power.restore_if_owned
        calls = []
        def fail():
            calls.append(1)
            return {"success": False, "restored": False, "error": "readback failed"}
        self.svc.power.restore_if_owned = fail
        self.run_async(self.svc._release("game", "governor-disabled"))
        state = self.svc.get_status("game")
        self.assertEqual(state["state"], "RESTORE_PENDING")
        self.assertIn("power", state["actuator_restore_pending"])
        self.assertFalse(self.svc._is_idle())
        with patch.object(self.svc, "_standby_overlays_sync", side_effect=AssertionError("new overlay")), \
             patch.object(self.svc, "_sync_flow", side_effect=AssertionError("flow")):
            self.run_async(self.svc._iteration())
        self.assertEqual(len(calls), 1, "retry must respect cooldown")
        self.assertFalse(self.svc.power.writes)
        self.svc.power.restore_if_owned = actual
        self.fixture.t["now"] += self.svc.ROLLBACK_RETRY_SECONDS
        self.run_async(self.svc._iteration())
        self.assertFalse(self.svc._actuator_restore_blocked())
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.svc.get_status()["state"], "DISABLED")

    def test_power_exception_still_attempts_cpu_undo(self):
        self.svc.cpu.discover()
        self.assertTrue(self.svc.cpu.claim())
        self.assertTrue(self.svc.cpu.set_cap_khz(2400000))
        with patch.object(self.svc.power, "restore_if_owned", side_effect=OSError("power unavailable")):
            self.run_async(self.svc._release("game", "governor-disabled"))
        self.assertFalse(self.svc.cpu.owned)
        self.assertEqual(self.svc.get_status()["state"], "RESTORE_PENDING")
        self.assertIn("power unavailable", self.svc.get_status()["actuator_restore_pending"]["power"])

    def test_cpu_false_result_with_pending_is_not_success(self):
        self.svc.cpu.discover()
        self.assertTrue(self.svc.cpu.claim())
        self.assertTrue(self.svc.cpu.set_cap_khz(2400000))
        def fail():
            self.svc.cpu.restore_pending = True
            self.svc.cpu.error = "CPU readback failed"
            return False
        with patch.object(self.svc.cpu, "restore", side_effect=fail):
            self.run_async(self.svc._release("game", "governor-disabled"))
        self.assertFalse(self.svc.power.state.owned)
        self.assertEqual(self.svc.get_status()["state"], "RESTORE_PENDING")
        self.assertIn("cpu", self.svc.get_status()["actuator_restore_pending"])
        self.fixture.t["now"] += self.svc.ROLLBACK_RETRY_SECONDS
        self.run_async(self.svc._retry_actuator_restores())
        self.assertFalse(self.svc.cpu.owned)
        self.assertFalse(self.svc.cpu.restore_pending)
        self.assertFalse(self.svc._actuator_restore_blocked())

    def test_external_power_takeover_is_released_without_retry_or_overwrite(self):
        def external():
            self.svc.power.state.owned = False
            self.svc.power.values.update(owned=False, observed_tdp_w=7)
            return {"success": True, "restored": False, "reason": "external-change",
                    "state": dict(self.svc.power.values)}
        self.svc.power.restore_if_owned = external
        self.run_async(self.svc._release("game", "governor-disabled"))
        self.assertEqual(self.svc.get_status()["state"], "DISABLED")
        self.assertFalse(self.svc._actuator_restore_blocked())
        self.assertEqual(self.svc.power.values["observed_tdp_w"], 7)
        self.assertFalse(self.svc.power.writes)

    def test_pending_restore_blocks_new_target_entrypoints(self):
        self.svc._actuator_restore_errors["power"] = "unverified"
        self.assertIsNone(self.run_async(self.svc._budget_power("game")))
        self.assertFalse(self.run_async(self.svc._apply_budget_tdp("game")))
        self.run_async(self.svc._power_step("game", {}))
        self.assertFalse(self.svc.power.writes)

    def test_profile_switch_waits_for_old_actuator_restore(self):
        self.assertTrue(self.fixture.cfg.create_profile("other", "mako")["success"])
        self.assertTrue(self.fixture.cfg.set_current_profile("other")["success"])
        self.fixture.saved_hash = legacy.sha(self.fixture.cfg.config_file_path)
        with patch.object(self.svc.power, "restore_if_owned",
                          return_value={"success": False, "error": "still owned"}):
            self.run_async(self.svc._iteration())
        self.assertEqual(self.svc._active_profile, "game")
        self.assertEqual(self.svc.get_status()["state"], "RESTORE_PENDING")

    def test_shutdown_reports_restore_failure(self):
        with patch.object(self.svc.power, "restore_if_owned",
                          return_value={"success": False, "error": "shutdown restore failed"}):
            self.run_async(self.svc.stop())
        self.assertEqual(self.svc.get_status()["state"], "RESTORE_PENDING")
        self.assertIn("power", self.svc.get_status()["actuator_restore_pending"])

    def test_owned_cpu_with_no_changed_cap_releases_without_false_failure(self):
        self.svc.cpu.discover()
        self.assertTrue(self.svc.cpu.claim())
        self.run_async(self.svc._release("game", "governor-disabled"))
        self.assertFalse(self.svc.cpu.owned)
        self.assertFalse(self.svc._actuator_restore_blocked())
        self.assertEqual(self.svc.get_status()["state"], "DISABLED")


if __name__ == "__main__":
    unittest.main()
