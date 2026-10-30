import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401

from gfg_plugin.host_sensors import HostSensors


class HostSensorsTest(unittest.TestCase):
    def test_reads_and_reuses_discovered_hwmons(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i, (name, files) in enumerate([("acpitz", {"temp1_input": "40000"}),
                                               ("steamdeck_hwmon", {"fan1_input": "3100"}),
                                               ("amdgpu", {"temp1_input": "61500"})]):
                h = root / "hwmon" / f"hwmon{i}"
                h.mkdir(parents=True)
                (h / "name").write_text(name + "\n")
                for f, v in files.items():
                    (h / f).write_text(v + "\n")
            t = [0.0]
            s = HostSensors(hwmon_root=root / "hwmon", drm_root=root / "drm", power_supply_root=root / "ps",
                            proc_stat=root / "stat", clock=lambda: t[0])
            v = s.sample()
            self.assertEqual((v["temp_c"], v["fan_rpm"]), (61.5, 3100.0))
            (root / "hwmon/hwmon2/temp1_input").write_text("70000\n")
            (root / "hwmon/hwmon2/name").write_text("renamed\n")  # names are not read again until rediscovery
            t[0] = 3.0
            self.assertEqual(s.sample()["temp_c"], 70.0)
            t[0] = 3.0 + HostSensors.DISCOVER_S
            self.assertIsNone(s.sample()["temp_c"])  # rediscovered: no amdgpu or k10temp hwmon left
