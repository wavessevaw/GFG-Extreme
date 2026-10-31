"""Interrupted installer recovery on a temporary root; never touches host systemd."""
import unittest
import shutil
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import test_kedavra_install as fixture


class InterruptedInstallTest(unittest.TestCase):
    def setUp(self):
        self.rig = fixture.InstallerTest()
        self.rig.setUp()
        self.addCleanup(self.rig.tearDown)

    def test_retry_after_interruption_between_runtime_renames(self):
        rig = self.rig
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        staged = rig.inst.var / "runtime.new"
        rename = type(staged).rename

        def interrupt(path, dest):
            if path == staged:
                raise SystemExit("simulated abrupt process termination")
            return rename(path, dest)

        with patch.object(type(staged), "rename", interrupt):
            with self.assertRaises(SystemExit):
                rig.inst.install()
        self.assertEqual((rig.inst.var / "runtime.rollback/bin/gamescope").read_text(), "previous-runtime")
        # A new installer instance must recover without manual file operations.
        fresh = fixture.kedavra_install.Installer(rig.inst.plugin_dir, rig.inst.home, root=rig.root, run=rig.sys)
        fresh.install()
        self.assertEqual((fresh.runtime / "bin/gamescope").read_text(), "candidate-runtime")
        self.assertFalse((fresh.var / "runtime.rollback").exists())

    def test_interrupted_enable_restores_previous_files_before_retry(self):
        rig = self.rig
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        (rig.inst.state / "healthy").write_text("previous healthy")
        paths = rig.inst._install_paths()
        before = {p: p.read_bytes() if p.exists() else None for p in paths}

        def interrupt(argv, **kw):
            result = rig.sys(argv, **kw)
            if argv[:2] == ["systemctl", "enable"]:
                raise SystemExit("terminated after service enablement")
            return result

        rig.inst.run = interrupt
        with self.assertRaises(SystemExit):
            rig.inst.install()
        def reject_retry(argv, **kw):
            if argv[0] == "setcap":
                return 1, "reject next candidate"
            return rig.sys(argv, **kw)
        fresh = fixture.kedavra_install.Installer(rig.inst.plugin_dir, rig.inst.home, root=rig.root, run=reject_retry)
        with self.assertRaisesRegex(RuntimeError, "setcap"):
            fresh.install()
        self.assertEqual((fresh.runtime / "bin/gamescope").read_text(), "previous-runtime")
        self.assertEqual({p: p.read_bytes() if p.exists() else None for p in paths}, before)
        self.assertTrue(rig.sys.enabled)
        self.assertFalse((fresh.var / "install-transaction.json").exists())

    def test_interrupted_first_install_restores_absence_and_service_state(self):
        rig = self.rig
        def interrupt(argv, **kw):
            result = rig.sys(argv, **kw)
            if argv[:2] == ["systemctl", "enable"]:
                raise SystemExit("terminated after first enablement")
            return result
        rig.inst.run = interrupt
        with self.assertRaises(SystemExit):
            rig.inst.install()
        rig.inst.run = rig.sys
        rig.inst._recover_install_transaction()
        rig.inst._recover_install_transaction()  # recovery is idempotent
        self.assertFalse(rig.inst.runtime.exists())
        self.assertFalse(rig.inst.unit.exists())
        self.assertFalse(rig.sys.enabled)
        self.assertFalse(any(c[0] == "sh" for c in rig.sys.calls))

    def test_committed_cleanup_does_not_restore_old_runtime(self):
        rig = self.rig
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        backup = rig.inst.var / "runtime.rollback"
        original = shutil.rmtree
        def interrupt(path, *args, **kwargs):
            if Path(path) == backup:
                raise SystemExit("terminated during committed cleanup")
            return original(path, *args, **kwargs)
        with patch.object(shutil, "rmtree", interrupt):
            with self.assertRaises(SystemExit):
                rig.inst.install()
        rig.inst._recover_install_transaction()
        self.assertEqual((rig.inst.runtime / "bin/gamescope").read_text(), "candidate-runtime")
        self.assertFalse(backup.exists())

    def test_corrupt_journal_preserves_runtime_and_backup(self):
        rig = self.rig
        rig.inst.install()
        backup = rig.inst.var / "runtime.rollback"
        shutil.copytree(rig.inst.runtime, backup)
        journal = rig.inst.var / "install-transaction.json"
        journal.write_text('{"version": 1}')
        with self.assertRaisesRegex(RuntimeError, "invalid installer transaction"):
            rig.inst.install()
        self.assertTrue(journal.exists())
        self.assertTrue((backup / "bin/gamescope").exists())
        self.assertTrue((rig.inst.runtime / "bin/gamescope").exists())

    def test_recovery_can_resume_after_another_interruption(self):
        rig = self.rig
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        def interrupt(argv, **kw):
            if argv[:2] == ["systemctl", "enable"]:
                raise SystemExit("interrupted installation")
            return rig.sys(argv, **kw)
        rig.inst.run = interrupt
        with self.assertRaises(SystemExit):
            rig.inst.install()
        with patch.object(rig.inst, "_restore_file", side_effect=SystemExit("interrupted recovery")):
            with self.assertRaises(SystemExit):
                rig.inst._recover_install_transaction()
        self.assertEqual((rig.inst.runtime / "bin/gamescope").read_text(), "previous-runtime")
        rig.inst.run = rig.sys
        rig.inst._recover_install_transaction()
        self.assertEqual((rig.inst.runtime / "bin/gamescope").read_text(), "previous-runtime")
        self.assertFalse((rig.inst.var / "install-transaction.json").exists())

    def test_abrupt_child_exit_releases_lock_and_allows_recovery(self):
        rig = self.rig
        rig.inst.install()
        (rig.inst.runtime / "bin/gamescope").write_text("previous-runtime")
        (rig.inst.bundle / "bin/gamescope").write_text("candidate-runtime")
        code = '''
import os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import test_kedavra_install as fixture
system = fixture.FakeSystem()
system.enabled = True
inst = fixture.kedavra_install.Installer(sys.argv[2], sys.argv[3], root=Path(sys.argv[4]), run=system)
staged = inst.var / "runtime.new"
rename = type(staged).rename
def stop(path, destination):
    if path == staged:
        os._exit(77)
    return rename(path, destination)
with patch.object(type(staged), "rename", stop):
    inst.install()
'''
        result = subprocess.run([sys.executable, "-B", "-c", code, str(Path(__file__).parent),
                                 str(rig.inst.plugin_dir), str(rig.inst.home), str(rig.root)], timeout=30)
        self.assertEqual(result.returncode, 77)
        self.assertFalse(rig.inst.runtime.exists())
        rig.inst.install()
        self.assertEqual((rig.inst.runtime / "bin/gamescope").read_text(), "candidate-runtime")

    def test_concurrent_operation_cannot_recover_active_transaction(self):
        if os.name != "posix":
            self.skipTest("flock is a POSIX/SteamOS check; Windows uses a fake system only")
        rig = self.rig
        with rig.inst._install_lock():
            with self.assertRaisesRegex(RuntimeError, "another installer operation"):
                rig.inst.install()
            with self.assertRaisesRegex(RuntimeError, "another installer operation"):
                rig.inst.uninstall()


if __name__ == "__main__":
    unittest.main()
