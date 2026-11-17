import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import helpers
from gfg_plugin.resource_optimizer import Optimizer, eligible, pressures


class ResourceTest(unittest.TestCase):
    def test_mixed_service_and_child_refused(self):
        import os
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            g = root / "group"
            g.mkdir()
            (g/"cgroup.procs").write_text("1")
            pid = root/"1"
            pid.mkdir()
            (pid/"exe").symlink_to("/usr/bin/steam")
            self.assertFalse(eligible(g, os.getuid(),root))
            (pid/"exe").unlink()
            (pid/"exe").symlink_to("/usr/lib/baloo_file")
            self.assertTrue(eligible(g, os.getuid(),root))
            (g/"extra").mkdir()
            self.assertFalse(eligible(g, os.getuid(),root))

    def test_sustained_contention_and_exit(self):
        import os
        o = Optimizer(os.getuid())
        with tempfile.TemporaryDirectory() as path, patch("gfg_plugin.resource_optimizer.eligible",return_value=True), patch("gfg_plugin.resource_optimizer.pressures",return_value={"cpu":12}), patch("gfg_plugin.resource_optimizer.subprocess.run") as run:
            o.group=Path(path)
            for t in range(0,20,5):
                (o.group/"cpu.stat").write_text(f"usage_usec {t*500000}")
                o.tick(42,t,[50]*30,30)
                if t<15: run.assert_not_called()
            self.assertEqual(run.call_count,1)
            (o.group/"cpu.weight").write_text("50")
            o.tick(42,20,[50]*30,30)
            self.assertEqual(o.status["tasks"],1)
            o.tick(0,21,[],0)
            self.assertEqual(run.call_count,2)
            o.tick(0,22,[],0)
            self.assertEqual(run.call_count,2)

    def test_missing_psi(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(pressures(Path(d)), dict(cpu=None,io=None,memory=None))

    def test_recovery_restarted_service_external_change_and_reboot(self):
        from gfg_plugin.resource_optimizer import lease
        import json
        for mode in ("crash","external","restart","reboot","gone"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as path:
                root=Path(path)
                group=root/"group"
                group.mkdir()
                weight=group/"cpu.weight"
                weight.write_text("100")
                receipt=root/"journal"
                with patch("gfg_plugin.resource_optimizer.eligible",return_value=True), patch("gfg_plugin.resource_optimizer.time.sleep",side_effect=RuntimeError):
                    with self.assertRaises(RuntimeError):
                        lease("apply",1000,group,receipt)
                self.assertEqual(weight.read_text(),"50")
                if mode=="external": weight.write_text("75")
                if mode=="restart":
                    group.rename(root/"old")
                    group.mkdir()
                    weight.write_text("50")
                if mode=="gone": group.rename(root/"old")
                if mode=="reboot":
                    data=json.loads(receipt.read_text())
                    data["identity"][0]="previous-boot"
                    receipt.write_text(json.dumps(data))
                lease("restore",1000,group,receipt)
                self.assertFalse(receipt.exists())
                if mode!="gone":
                    self.assertEqual(weight.read_text(),{"crash":"100","external":"75"}.get(mode,"50"))
