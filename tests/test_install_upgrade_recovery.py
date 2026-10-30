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
        (rig.inst.state / "healthy").write_text("prior state")
        tracked = [rig.inst.boot, rig.inst.tune, rig.inst.untune, rig.inst.unit,
                   rig.inst.limits, rig.inst.state / "healthy"]
        before = {p: p.read_bytes() for p in tracked}
        calls_before = len(rig.sys.calls)
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
        self.assertEqual({p: p.read_bytes() for p in tracked}, before)
        self.assertFalse((rig.inst.var / "runtime.new").exists())
        self.assertFalse(any(c[0] in ("sh", "systemctl") for c in rig.sys.calls[calls_before:]))

    def test_setcap_failure_on_first_install_leaves_no_runtime(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        original_run = rig.sys
        def fail_setcap(argv, **kwargs):
            if Path(argv[0]).name == "setcap":
                return 1, "injected setcap failure"
            return original_run(argv, **kwargs)
        rig.inst.run = fail_setcap
        with self.assertRaisesRegex(RuntimeError, "setcap"):
            rig.inst.install()
        self.assertFalse(rig.inst.runtime.exists())
        self.assertFalse((rig.inst.var / "runtime.new").exists())
        self.assertFalse(rig.inst.unit.exists())
        self.assertFalse(rig.sys.enabled)

    def test_success_applies_capability_to_staged_binary(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        calls = [argv for argv in rig.sys.calls if Path(argv[0]).name == "setcap"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(Path(calls[0][-1]), rig.inst.var / "runtime.new/bin/gamescope")
        self.assertTrue((rig.inst.runtime / "bin/gamescope").exists())

    def test_successful_upgrade_still_installs_candidate(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        installed = rig.inst.runtime / "bin/gamescope"
        installed.write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        result = rig.inst.install()
        self.assertEqual(installed.read_text(), "candidate-runtime")
        self.assertTrue(result["needs_reboot"])
        self.assertTrue(rig.sys.enabled)


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

    def test_enable_failure_preserves_boot_state_and_does_not_apply_profile(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        for name in ("trial", "healthy"):
            (rig.inst.state / name).write_text("previous " + name)
        tracked = [rig.inst.boot, rig.inst.tune, rig.inst.untune, rig.inst.unit, rig.inst.limits,
                   rig.inst.state / "trial", rig.inst.state / "healthy"]
        before = {p: p.read_bytes() for p in tracked}
        call_count = len(rig.sys.calls)
        original_run = rig.sys
        def fail_enable(argv, **kwargs):
            if len(argv) > 1 and argv[0] == "systemctl" and argv[1] == "enable":
                return 1, "injected enable failure"
            return original_run(argv, **kwargs)
        rig.inst.run = fail_enable
        with self.assertRaisesRegex(RuntimeError, "systemctl enable"):
            rig.inst.install()
        with self.subTest("boot state and scripts"):
            self.assertEqual({p: p.read_bytes() if p.exists() else None for p in tracked}, before)
        with self.subTest("profile application"):
            self.assertFalse(any(c[0] == "sh" for c in rig.sys.calls[call_count:]),
                             "a rejected upgrade must not apply system settings")

    def test_enable_failure_on_first_install_leaves_no_installed_engine_or_unit(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        original_run = rig.sys
        def fail_enable(argv, **kwargs):
            if len(argv) > 1 and argv[0] == "systemctl" and argv[1] == "enable":
                return 1, "injected enable failure"
            return original_run(argv, **kwargs)
        rig.inst.run = fail_enable
        with self.assertRaisesRegex(RuntimeError, "systemctl enable"):
            rig.inst.install()
        self.assertFalse(rig.inst.runtime.exists())
        self.assertFalse(rig.inst.unit.exists())
        self.assertFalse(rig.inst.boot.exists())
        self.assertFalse(rig.inst.limits.exists())
        self.assertFalse(rig.sys.enabled)
        self.assertFalse(any(c[0] == "sh" for c in rig.sys.calls))

    def test_successful_upgrade_does_not_leave_rollback_runtime(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        rig.inst.install()
        self.assertFalse((rig.inst.var / "runtime.rollback").exists())

    def test_daemon_reload_failure_restores_previous_runtime(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        installed = rig.inst.runtime / "bin/gamescope"
        installed.write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        original_run = rig.sys
        failed = False
        def fail_once(argv, **kwargs):
            nonlocal failed
            if argv[:2] == ["systemctl", "daemon-reload"] and not failed:
                failed = True
                return 1, "injected daemon-reload failure"
            return original_run(argv, **kwargs)
        rig.inst.run = fail_once
        with self.assertRaisesRegex(RuntimeError, "daemon-reload"):
            rig.inst.install()
        self.assertEqual(installed.read_text(), "previous-runtime")
        self.assertFalse((rig.inst.var / "runtime.rollback").exists())
        self.assertTrue(rig.sys.enabled)

    def test_partially_enabled_service_is_disabled_again_on_first_install(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        original_run = rig.sys
        def fail_after_enable(argv, **kwargs):
            if argv[:2] == ["systemctl", "enable"]:
                rig.sys.enabled = True  # simulate partial side effect before error
                return 1, "injected partial enable"
            return original_run(argv, **kwargs)
        rig.inst.run = fail_after_enable
        with self.assertRaisesRegex(RuntimeError, "systemctl enable"):
            rig.inst.install()
        self.assertFalse(rig.sys.enabled)
        self.assertFalse(rig.inst.runtime.exists())
        self.assertFalse(rig.inst.unit.exists())

    def test_failed_runtime_restore_retains_backup_and_reports_incomplete_rollback(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        original_run = rig.sys
        backup = rig.inst.var / "runtime.rollback"
        path_type = type(backup)
        original_rename = path_type.rename
        def fail_enable(argv, **kwargs):
            if argv[:2] == ["systemctl", "enable"]:
                return 1, "injected enable failure"
            return original_run(argv, **kwargs)
        def fail_restore(path, destination):
            if path == backup:
                raise PermissionError("injected runtime restore failure")
            return original_rename(path, destination)
        rig.inst.run = fail_enable
        with patch.object(path_type, "rename", fail_restore):
            with self.assertRaisesRegex(RuntimeError, "rollback incomplete"):
                rig.inst.install()
        self.assertEqual((backup / "bin/gamescope").read_text(), "previous-runtime")

    def test_existing_rollback_copy_is_not_overwritten(self):
        rig = fixture.InstallerTest()
        rig.setUp()
        self.addCleanup(rig.tearDown)
        backup = rig.inst.var / "runtime.rollback/bin"
        backup.mkdir(parents=True)
        (backup / "gamescope").write_text("recoverable-runtime")
        with self.assertRaisesRegex(RuntimeError, "rollback still exists"):
            rig.inst.install()
        self.assertEqual((backup / "gamescope").read_text(), "recoverable-runtime")

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
