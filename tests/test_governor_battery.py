import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.governor_battery import BatteryEstimator, format_minutes, read_battery  # noqa: E402


def make(root, **kw):
    bat = Path(root) / "BAT1"
    bat.mkdir()
    for k, v in kw.items():
        (bat / k).write_text(str(v))


class BatteryTests(unittest.TestCase):
    def test_reads_energy_battery(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, energy_now=30_000_000, power_now=10_000_000, capacity=60, status="Discharging")
            b = read_battery(Path(d))
            self.assertTrue(b["available"] and b["discharging"])
            est = BatteryEstimator().update(b)
            self.assertEqual(est["minutes_left"], 180)

    def test_charge_based_battery(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, charge_now=4_000_000, voltage_now=7_500_000, current_now=1_500_000, capacity=50, status="Discharging")
            est = BatteryEstimator().update(read_battery(Path(d)))
            self.assertEqual(est["minutes_left"], 160)  # 30 Wh / 11.25 W

    def test_charging_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(read_battery(Path(d))["available"])
            make(d, energy_now=1, power_now=1, status="Charging")
            self.assertIsNone(BatteryEstimator().update(read_battery(Path(d)))["minutes_left"])

    def test_smoothing_and_noise_floor(self):
        e = BatteryEstimator()
        base = {"available": True, "discharging": True, "energy_uwh": 30_000_000}
        first = e.update({**base, "power_uw": 10_000_000})["minutes_left"]
        spike = e.update({**base, "power_uw": 20_000_000})["minutes_left"]
        self.assertLess(first - spike, 20)  # a 2x spike moves it only slightly
        self.assertIsNone(BatteryEstimator().update({**base, "power_uw": 100_000})["minutes_left"])

    def test_format(self):
        self.assertEqual(format_minutes(125), "2h05")
        self.assertEqual(format_minutes(45), "45m")
        self.assertIsNone(format_minutes(None))


if __name__ == "__main__":
    unittest.main()
