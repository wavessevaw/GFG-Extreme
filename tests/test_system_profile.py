import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (puts py_modules on the path)
from gfg_plugin.kedavra import system_profile as sp


def fake_tree(root: Path, zram: bool):
    files = {
        "proc/sys/vm/swappiness": "100", "proc/sys/vm/min_free_kbytes": "67584",
        "proc/sys/kernel/sched_autogroup_enabled": "1",
        "sys/kernel/mm/transparent_hugepage/enabled": "always [madvise] never",
        "sys/block/nvme0n1/queue/scheduler": "[mq-deadline] kyber bfq none",
        "sys/block/nvme0n1/queue/read_ahead_kb": "128",
        "proc/swaps": "Filename Type\n/dev/zram0 partition 8G 0 100\n" if zram else "Filename Type\n",
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n")
    return files


def scripts(root: Path):
    state, orig, done = root / "state", root / "run/orig", root / "run/done"
    state.mkdir(exist_ok=True)
    fix = lambda s: s.replace("'/proc/", f"'{root}/proc/").replace("'/sys/", f"'{root}/sys/").replace(" /proc/swaps", f" {root}/proc/swaps")
    tune = root / "tune.sh"
    tune.write_text(fix(sp.tune_script(state, orig, done)))
    untune = root / "untune.sh"
    untune.write_text(sp.restore_script(orig, done))
    return tune, untune, done


class SystemProfileTest(unittest.TestCase):
    def test_apply_then_restore_brings_every_value_back(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            before = {k: (root / k).read_text() for k in fake_tree(root, zram=True)}
            tune, untune, done = scripts(root)
            subprocess.run(["sh", str(tune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "150")
            self.assertEqual((root / "sys/kernel/mm/transparent_hugepage/enabled").read_text().strip(), "always")
            self.assertEqual((root / "sys/block/nvme0n1/queue/scheduler").read_text().strip(), "kyber")
            self.assertIn("failed=0", done.read_text())
            subprocess.run(["sh", str(tune)], check=True)     # a second run keeps the first originals
            subprocess.run(["sh", str(untune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "100")
            self.assertEqual((root / "proc/sys/vm/min_free_kbytes").read_text().strip(), "67584")
            self.assertEqual((root / "sys/kernel/mm/transparent_hugepage/enabled").read_text().strip(), "madvise")
            self.assertEqual((root / "sys/block/nvme0n1/queue/scheduler").read_text().strip(), "mq-deadline")
            self.assertFalse(done.exists())

    def test_restore_failure_retains_remaining_entries_in_dependency_order(self):
        with tempfile.TemporaryDirectory(prefix="profile space ") as d:
            root = Path(d)
            scheduler, dependent, last = [root / n for n in ("scheduler", "missing", "last")]
            scheduler.write_text("new")
            last.write_text("new")
            orig, done = root / "orig", root / "done"
            orig.write_text(f"{scheduler}\told-scheduler\n{dependent}\told-dependent\n{last}\told-last\n")
            done.touch()
            script = root / "restore.sh"
            script.write_text(sp.restore_script(orig, done))
            result = subprocess.run(["sh", str(script)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("journal retained", result.stderr)
            self.assertTrue(done.exists())
            self.assertEqual(last.read_text().strip(), "old-last")
            self.assertEqual(scheduler.read_text(), "new")
            self.assertEqual(orig.read_text(), f"{scheduler}\told-scheduler\n{dependent}\told-dependent\n")
            dependent.touch()
            subprocess.run(["sh", str(script)], check=True)
            self.assertEqual(dependent.read_text().strip(), "old-dependent")
            self.assertEqual(scheduler.read_text().strip(), "old-scheduler")
            self.assertFalse(orig.exists()); self.assertFalse(done.exists())
            subprocess.run(["sh", str(script)], check=True)

    def test_write_failure_does_not_erase_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root / "target"
            target.write_text("active"); target.chmod(0o444)
            orig, done = root / "orig", root / "done"
            saved = f"{target}\toriginal\n"
            orig.write_text(saved); done.touch()
            script = root / "restore.sh"; script.write_text(sp.restore_script(orig, done))
            try:
                import os
                if os.geteuid() == 0:
                    self.skipTest("permission test needs unprivileged execution")
                result = subprocess.run(["sh", str(script)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(orig.read_text(), saved)
                self.assertEqual(target.read_text(), "active")
                self.assertTrue(done.exists())
            finally:
                target.chmod(0o644)

    def test_readback_choice_and_mismatch(self):
        import os
        for actual, success in (("always [madvise] never", True), ("always madvise [never]", False)):
            with self.subTest(actual=actual), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                target, orig, done = root / "setting", root / "orig", root / "done"
                target.write_text("always"); orig.write_text(f"{target}\tmadvise\n"); done.touch()
                bindir = root / "bin"; bindir.mkdir()
                cat = bindir / "cat"
                cat.write_text(f"#!/bin/sh\nprintf '%s\\n' '{actual}'\n")
                cat.chmod(0o755)
                script = root / "restore.sh"; script.write_text(sp.restore_script(orig, done))
                result = subprocess.run(["sh", str(script)], capture_output=True,
                                        env={**os.environ, "PATH": str(bindir) + ":" + os.environ["PATH"]})
                self.assertEqual(result.returncode == 0, success)
                self.assertEqual(orig.exists(), not success)
                self.assertEqual(done.exists(), not success)

    def test_swap_settings_need_zram(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fake_tree(root, zram=False)
            tune, _, _ = scripts(root)
            subprocess.run(["sh", str(tune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "100")
            self.assertEqual((root / "proc/sys/vm/min_free_kbytes").read_text().strip(), "131072")

    def test_switched_off_profile_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fake_tree(root, zram=True)
            tune, _, done = scripts(root)
            (root / "state/profile_off").touch()
            subprocess.run(["sh", str(tune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "100")
            self.assertFalse(done.exists())

    def test_disabled_engine_does_not_apply_system_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fake_tree(root, zram=True)
            tune, _, done = scripts(root)
            (root / "state/disabled").touch()
            subprocess.run(["sh", str(tune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "100")
            self.assertEqual((root / "proc/sys/vm/min_free_kbytes").read_text().strip(), "67584")
            self.assertFalse(done.exists())
            self.assertFalse((root / "run/orig").exists())

    def test_no_security_or_package_changes(self):
        text = sp.tune_script(Path("/s"), Path("/o"), Path("/d"))
        for banned in ("mitigations", "pacman", "grub", "modprobe", "readonly", "perf_event", "energy_performance"):
            self.assertNotIn(banned, text)

    def test_pending_install_does_not_apply_system_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fake_tree(root, zram=True)
            tune, _, done = scripts(root)
            (root / "install-transaction.json").write_text("pending")
            subprocess.run(["sh", str(tune)], check=True)
            self.assertEqual((root / "proc/sys/vm/swappiness").read_text().strip(), "100")
            self.assertFalse(done.exists())
            self.assertFalse((root / "run/orig").exists())


if __name__ == "__main__":
    unittest.main()
