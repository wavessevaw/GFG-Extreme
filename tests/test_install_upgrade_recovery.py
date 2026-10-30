"""Regression for a failed upgrade; exercises a temporary root and fake system only."""
import unittest
from pathlib import Path

import test_kedavra_install as fixture


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

if __name__ == "__main__":
    unittest.main()
