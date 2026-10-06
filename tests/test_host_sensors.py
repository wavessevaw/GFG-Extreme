import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.host_sensors import HostSensors, diagnose  # noqa: E402
from gfg_plugin.governor_telemetry import frametime_stats  # noqa: E402


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class SensorTests(unittest.TestCase):
    def test_reads_sysfs_and_computes_cpu_delta_and_slope(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            write(root / "hw/hwmon3/name", "amdgpu\n"); write(root / "hw/hwmon3/temp1_input", "72000\n"); write(root / "hw/hwmon3/fan1_input", "3100\n")
            write(root / "drm/card0/device/gpu_busy_percent", "93\n")
            write(root / "drm/card0/device/pp_dpm_sclk", "0: 200Mhz\n1: 1600Mhz *\n")
            write(root / "ps/BAT1/capacity", "64\n"); write(root / "ps/BAT1/status", "Discharging\n"); write(root / "ps/BAT1/power_now", "8500000\n")
            write(root / "stat", "cpu 100 0 100 800 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0\ncpu1 50 0 50 400 0 0 0 0\n")
            now = {"t": 0.0}
            s = HostSensors(hwmon_root=root / "hw", drm_root=root / "drm", power_supply_root=root / "ps",
                            proc_stat=root / "stat", clock=lambda: now["t"])
            first = s.sample(force=True)
            self.assertEqual((first["temp_c"], first["fan_rpm"], first["gpu_busy_pct"], first["gpu_clock_mhz"]), (72.0, 3100.0, 93.0, 1600.0))
            self.assertEqual((first["battery_pct"], first["battery_discharge_w"]), (64.0, 8.5))
            self.assertIsNone(first["cpu_total_pct"])
            write(root / "hw/hwmon3/temp1_input", "76000\n")
            write(root / "stat", "cpu 400 0 100 900 0 0 0 0\ncpu0 350 0 50 450 0 0 0 0\ncpu1 50 0 50 450 0 0 0 0\n")
            now["t"] = 60.0
            second = s.sample()
            self.assertEqual(second["cpu_total_pct"], 75.0)
            self.assertEqual(second["cpu_top_core_pct"], 85.7)
            self.assertEqual(second["temp_slope_c_per_min"], 4.0)

    def test_missing_sensors_are_none(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            v = HostSensors(hwmon_root=r, drm_root=r, power_supply_root=r, proc_stat=r / "none").sample(force=True)
            self.assertTrue(all(v[k] is None for k in ("temp_c", "gpu_busy_pct", "cpu_total_pct", "battery_pct", "fan_rpm")))

    def test_diagnosis(self):
        self.assertEqual(diagnose({"gpu_busy_pct": 97})["bottleneck"], "gpu")
        self.assertEqual(diagnose({"gpu_busy_pct": 50, "cpu_top_core_pct": 98})["bottleneck"], "cpu")
        self.assertEqual(diagnose({"gpu_busy_pct": 50}, cap_w=10, draw_w=9.9)["bottleneck"], "power")
        self.assertEqual(diagnose({"thermal_headroom_c": 5})["thermal"], "hot")
        self.assertEqual(diagnose({"temp_c": 75, "temp_slope_c_per_min": 2.0, "thermal_headroom_c": 15})["thermal"], "heating")
        self.assertEqual(diagnose({}, frametime={"stutter_ratio": 0.1})["smoothness"], "stuttering")

    def test_frametime_stats_expose_spikes_hidden_by_average_fps(self):
        smooth = frametime_stats([60] * 100)
        spiky = frametime_stats([60] * 90 + [14] * 10)
        self.assertEqual(smooth["stutter_ratio"], 0.0)
        self.assertGreater(spiky["p99_ms"], 60)
        self.assertEqual(spiky["stutter_ratio"], 0.1)


if __name__ == "__main__":
    unittest.main()
