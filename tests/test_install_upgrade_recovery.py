"""Regression for a failed upgrade; exercises a temporary root and fake system only."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import test_kedavra_install as fixture
from gfg_plugin.kedavra import system_profile


class UpgradeRecoveryTest(unittest.TestCase):
    def test_setcap_failure_keeps_previous_runtime(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        installed = rig.inst.runtime / "bin/gamescope"
        installed.write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        original_run = rig.sys

        def fail_setcap(argv, **kwargs):
            if Path(argv[0]).name == "setcap":
                return 1, "injected setcap failure"
            return original_run(argv, **kwargs)

        rig.inst.run = fail_setcap
        with self.assertRaisesRegex(RuntimeError, "setcap"):
            rig.inst.install()
        self.assertEqual(installed.read_text(), "previous-runtime",
                         "a rejected upgrade must retain the previously installed runtime")


    def test_enable_failure_keeps_previous_runtime(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        installed = rig.inst.runtime / "bin/gamescope"
        installed.write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        original_run = rig.sys

        def fail_enable(argv, **kwargs):
            if len(argv) > 1 and argv[0] == "systemctl" and argv[1] == "enable":
                return 1, "injected enable failure"
            return original_run(argv, **kwargs)

        rig.inst.run = fail_enable
        with self.assertRaisesRegex(RuntimeError, "systemctl enable"):
            rig.inst.install()
        self.assertEqual(installed.read_text(), "previous-runtime",
                         "a rejected upgrade must retain the previously installed runtime")

    def test_watchdog_rollback_does_not_apply_system_profile(self):
        # Run the actual boot and profile scripts against one temporary fake setting.
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        (rig.inst.state / "trial").touch()
        fake_setting = rig.tmp / "fake-setting"
        fake_setting.write_text("original\n")
        with patch.object(system_profile, "SETTINGS", ((str(fake_setting), "changed", None),)):
            rig.inst.tune.write_text(system_profile.tune_script(
                rig.inst.state, rig.inst.profile_orig, rig.inst.profile_done))
        subprocess.run(["sh", str(rig.inst.boot)], check=True)
        self.assertTrue((rig.inst.state / "auto_rollback").exists())
        self.assertTrue((rig.inst.state / "disabled").exists())
        subprocess.run(["sh", str(rig.inst.tune)], check=True)
        self.assertEqual(fake_setting.read_text(), "original\n",
                         "a watchdog rollback must not apply the system profile")
        self.assertFalse(rig.inst.profile_orig.exists())

if __name__ == "__main__":
    unittest.main()
