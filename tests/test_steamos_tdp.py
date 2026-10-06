import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_power import SteamDeckPowerActuator  # noqa: E402
from gfg_plugin.steamos_tdp import SteamOSManagerTdp  # noqa: E402


def write(path: Path, value):
    path.write_text(f"{value}\n", encoding="utf-8")


class FakeManager:
    """steamos-manager that writes both caps like the real daemon does."""

    def __init__(self, hwmon: Path, low=3, high=20, accept=True, apply=True):
        self.hwmon, self.range, self.accept, self.apply = hwmon, (low, high), accept, apply
        self.calls = []

    def probe(self):
        return True

    def set(self, watts):
        self.calls.append(watts)
        if not self.accept:
            return False, "org.freedesktop.DBus.Error.AccessDenied"
        if self.apply:
            write(self.hwmon / "power1_cap", watts * 1_000_000)
            write(self.hwmon / "power2_cap", watts * 1_000_000)
        return True, ""


class ManagerActuatorTests(unittest.TestCase):
    def make(self, root: Path):
        h = root / "hwmon" / "hwmon0"
        h.mkdir(parents=True)
        write(h / "power1_label", "fastPPT")
        write(h / "power2_label", "slowPPT")
        write(h / "power1_cap", 20_000_000)
        write(h / "power2_cap", 20_000_000)
        return h

    def actuator(self, root, manager, writable=False):
        return SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon",
                                      access=lambda p, m: writable, helper=lambda: None,
                                      manager=manager, verify_seconds=0.0, sleep=lambda s: None)

    def test_tdp_goes_through_steamos_manager_like_the_steam_slider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            manager = FakeManager(h)
            act = self.actuator(root, manager)
            status = act.discover()
            self.assertTrue(status["available"])
            self.assertEqual(status["method"], "steamos-manager")
            act.claim()
            result = act.set_tdp_w(17.4)
            self.assertTrue(result["success"], result)
            self.assertEqual(manager.calls, [17])
            self.assertEqual(result["state"]["observed_tdp_w"], 17.0)
            self.assertFalse(act.verify_ownership()["external_change"])
            self.assertTrue(act.restore_if_owned()["restored"])
            self.assertEqual(manager.calls, [17, 20])

    def test_manager_accepting_but_caps_unchanged_is_an_error_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            act = self.actuator(root, FakeManager(h, apply=False))
            act.discover(); act.claim()
            result = act.set_tdp_w(15)
            self.assertFalse(result["success"])
            self.assertIn("cap reads", result["error"])

    def test_manager_refusal_without_direct_access_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            act = self.actuator(root, FakeManager(h, accept=False))
            act.discover(); act.claim()
            result = act.set_tdp_w(15)
            self.assertFalse(result["success"])
            self.assertIn("steamos-manager", result["error"])
            self.assertEqual(int((h / "power2_cap").read_text()), 20_000_000)

    def test_manager_refusal_falls_back_to_direct_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            act = self.actuator(root, FakeManager(h, accept=False), writable=True)
            act.discover(); act.claim()
            self.assertTrue(act.set_tdp_w(15)["success"])
            self.assertEqual(int((h / "power2_cap").read_text()), 15_000_000)


class ManagerRangeTests(unittest.TestCase):
    make = ManagerActuatorTests.make
    actuator = ManagerActuatorTests.actuator

    def manager_15(self, h):
        manager = FakeManager(h, high=15)
        manager.range = (3, 15)

        def set_clamped(watts, _orig=manager.set):
            return _orig(max(3, min(15, watts)))
        manager.set = set_clamped
        return manager

    def test_above_steam_range_without_root_is_capped_not_a_failure_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            write(h / "power2_cap_max", 20_000_000)
            act = self.actuator(root, self.manager_15(h))
            status = act.discover()
            self.assertEqual(status["maximum_tdp_w"], 15.0)  # Steam's range is the real limit here
            act.claim()
            act.set_ceiling_w(20)
            result = act.set_tdp_w(18)
            self.assertTrue(result["success"], result)
            self.assertTrue(act.state.owned)
            self.assertEqual(result["state"]["observed_tdp_w"], 15.0)

    def test_above_steam_range_with_direct_access_writes_hwmon(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            write(h / "power1_cap", 12_000_000); write(h / "power2_cap", 12_000_000)
            manager = self.manager_15(h)
            act = self.actuator(root, manager, writable=True)
            act.discover(); act.claim(); act.set_ceiling_w(20)
            self.assertTrue(act.set_tdp_w(18)["success"])
            self.assertEqual(int((h / "power2_cap").read_text()), 18_000_000)
            self.assertEqual(manager.calls, [])

    def test_reclaim_after_own_failed_write_keeps_users_original_for_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            manager = FakeManager(h)
            act = self.actuator(root, manager)
            act.discover(); act.claim()
            self.assertTrue(act.set_tdp_w(12)["success"])
            manager.apply = False  # daemon stops applying: our write does not land
            write(h / "power1_cap", 13_000_000); write(h / "power2_cap", 13_000_000)
            act.state.expected_slow_uw = act.state.expected_fast_uw = 13_000_000
            self.assertFalse(act.set_tdp_w(11)["success"])
            self.assertFalse(act.state.owned)
            act.claim()
            self.assertEqual(act.state.initial_slow_uw, 20_000_000)

    def test_restore_prefers_exact_direct_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h = self.make(root)
            write(h / "power1_cap", 20_000_000); write(h / "power2_cap", 15_000_000)
            manager = FakeManager(h)
            act = self.actuator(root, manager, writable=True)
            act.discover(); act.claim()
            self.assertTrue(act.set_tdp_w(10)["success"])
            self.assertTrue(act.restore_if_owned()["restored"])
            self.assertEqual((int((h / "power1_cap").read_text()), int((h / "power2_cap").read_text())),
                             (20_000_000, 15_000_000))
            self.assertEqual(manager.calls, [10])


class SteamosctlCommandTests(unittest.TestCase):
    def fake_tools(self, directory: Path):
        log = directory / "calls.log"
        script = directory / "steamosctl"
        script.write_text(
            "#!/bin/sh\n"
            f"echo \"$@\" >> {log}\n"
            "case \"$1\" in\n"
            "  get-tdp-limit-min) echo 3 ;;\n"
            "  get-tdp-limit-max) echo 20 ;;\n"
            "  get-tdp-limit) echo 20 ;;\n"
            "  set-tdp-limit) exit 0 ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return log

    def test_probe_reads_range_and_set_clamps_to_it(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            log = self.fake_tools(d)
            manager = SteamOSManagerTdp(bin_dirs=[str(d)])
            self.assertTrue(manager.probe())
            self.assertEqual(manager.range, (3, 20))
            self.assertEqual(manager.set(30), (True, ""))
            self.assertIn("set-tdp-limit 20", log.read_text())

    def test_without_tools_it_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = SteamOSManagerTdp(bin_dirs=[temp])
            self.assertFalse(manager.probe())
            self.assertEqual(manager.reason, "no-tool")
            self.assertFalse(manager.set(10)[0])


if __name__ == "__main__":
    unittest.main()
