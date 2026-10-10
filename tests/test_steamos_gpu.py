"""Verify the QAM-compatible SteamOSManager GPU clock path using a fake session bus."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.steamos_gpu import SteamOSGpuBackend, BUS_NAME, OBJECT_PATH, INTERFACE
from gfg_plugin.autopilot.gpu_clock import GpuClock


class FakeBus:
    def __init__(self, *, level="auto", manual=1100, error=False):
        self.level = level
        self.manual = manual
        self.error = error
        self.calls = []

    def __call__(self, argv):
        self.calls.append(tuple(argv))
        if self.error:
            return False, "ServiceUnknown"
        if "get-property" in argv:
            name = argv[-1]
            value = {"GpuPerformanceLevel": 's "' + self.level + '"',
                     "ManualGpuClock": f"u {self.manual}",
                     "ManualGpuClockMin": "u 200",
                     "ManualGpuClockMax": "u 1600"}.get(name)
            return (True, value) if value is not None else (False, "unknown-property")
        if "set-property" in argv:
            name, value = argv[-3], argv[-1]
            if name == "GpuPerformanceLevel":
                self.level = value
            elif name == "ManualGpuClock":
                self.manual = int(value)
            else:
                return False, "invalid-property"
            return True, ""
        return False, "unknown command"


class SteamOSGpuTests(unittest.TestCase):
    def backend(self, fake):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        file = Path(temporary.name) / "busctl"
        file.write_text("#!/bin/sh\nexit 0\n")
        file.chmod(0o755)
        return SteamOSGpuBackend(bin_dirs=[temporary.name], runner=fake)

    def test_qam_clock_uses_session_bus_and_restores_auto_plus_manual_value(self):
        fake = FakeBus()
        clock = GpuClock(backend=self.backend(fake), writes_enabled=True)
        info = clock.status()
        self.assertEqual(info["level"], "auto")
        self.assertEqual(info["manual_clock_mhz"], 1100)
        self.assertEqual(info["current_limit_mhz"], 1600)
        result = clock.lower_ceiling()
        self.assertTrue(result["applied"], result)
        self.assertEqual((fake.level, fake.manual), ("manual", 1500))
        self.assertEqual(clock.status()["current_limit_mhz"], 1500)
        restored = clock.restore()
        self.assertTrue(restored["restored"], restored)
        self.assertEqual((fake.level, fake.manual), ("auto", 1100))
        self.assertFalse(clock.owned)
        writes = [c for c in fake.calls if "set-property" in c]
        self.assertEqual(writes[0][-3:], ("GpuPerformanceLevel", "s", "manual"))
        self.assertEqual(writes[1][-3:], ("ManualGpuClock", "u", "1500"))
        self.assertEqual(writes[-1][-3:], ("GpuPerformanceLevel", "s", "auto"))
        self.assertTrue(all(BUS_NAME in c and OBJECT_PATH in c and INTERFACE in c for c in writes))

    def test_user_manual_clock_is_never_modified(self):
        fake = FakeBus(level="manual", manual=800)
        clock = GpuClock(backend=self.backend(fake), writes_enabled=True)
        self.assertEqual(clock.lower_ceiling()["reason"], "user-manual-clock")
        self.assertFalse(any("set-property" in c for c in fake.calls))
        self.assertEqual((fake.level, fake.manual), ("manual", 800))

    def test_qam_manual_override_wins_over_our_trial(self):
        fake = FakeBus()
        clock = GpuClock(backend=self.backend(fake), writes_enabled=True)
        self.assertTrue(clock.lower_ceiling()["applied"])
        fake.manual = 900
        result = clock.restore()
        self.assertTrue(result.get("yielded"))
        self.assertFalse(clock.owned)
        self.assertEqual((fake.level, fake.manual), ("manual", 900))

    def test_service_missing_fails_closed(self):
        fake = FakeBus(error=True)
        clock = GpuClock(backend=self.backend(fake), writes_enabled=True)
        self.assertFalse(clock.status()["available"])
        self.assertFalse(clock.lower_ceiling()["applied"])
        self.assertFalse(any("set-property" in c for c in fake.calls))


if __name__ == "__main__":
    unittest.main()
