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
            group=Path(path)
            o.groups={"baloo":group}
            (group/"cpu.weight").write_text("100")
            for t in range(0,20,5):
                (group/"cpu.stat").write_text(f"usage_usec {t*500000}")
                o.tick(42,t,[50]*30,30)
                if t<15: run.assert_not_called()
            self.assertEqual(run.call_count,1)
            (group/"cpu.weight").write_text("50")
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

    def test_syncthing_requires_matching_executable_and_uid(self):
        import os
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            group = root / "syncthing.service"
            group.mkdir()
            (group / "cgroup.procs").write_text("1")
            pid = root / "1"
            pid.mkdir()
            exe = pid / "exe"
            exe.symlink_to("/usr/bin/syncthing")
            self.assertTrue(eligible(group, os.getuid(), root, "syncthing"))
            self.assertFalse(eligible(group, os.getuid()+1, root, "syncthing"))
            self.assertFalse(eligible(group, os.getuid(), root, "baloo"))
            exe.unlink()
            exe.symlink_to("/usr/bin/steam")
            self.assertFalse(eligible(group, os.getuid(), root, "syncthing"))

    def test_busiest_eligible_service_and_single_trial(self):
        import os
        opt = Optimizer(os.getuid())
        with tempfile.TemporaryDirectory() as directory, patch("gfg_plugin.resource_optimizer.eligible", return_value=True), patch("gfg_plugin.resource_optimizer.pressures", return_value={"cpu":12}), patch("gfg_plugin.resource_optimizer.subprocess.run") as run:
            opt.groups = {}
            for role in ("baloo", "syncthing"):
                group = Path(directory) / role
                group.mkdir()
                (group / "cpu.weight").write_text("100")
                opt.groups[role] = group
            for t in range(0, 20, 5):
                for role, rate in (("baloo", 300000), ("syncthing", 800000)):
                    (opt.groups[role] / "cpu.stat").write_text(f"usage_usec {rate*t}")
                opt.tick(42, t, [50]*30, 30)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[-2:], ["apply", "syncthing"])
            self.assertTrue(any(x.endswith(" restore syncthing") for x in cmd))
            self.assertEqual(run.call_count, 1)
            (opt.groups["syncthing"] / "cpu.weight").write_text("50")
            opt.tick(42, 20, [50]*30, 30)
            self.assertEqual(opt.status["tasks"], 1)
            opt.tick(42, 25, [80]*30, 30)
            self.assertEqual(run.call_count, 2)
            self.assertIsNone(opt.active)

    def test_game_open_in_engine_menu_without_eligible_tasks(self):
        import os
        opt = Optimizer(os.getuid())
        opt.groups = {}
        with patch("gfg_plugin.resource_optimizer.pressures", return_value={"cpu": 0}) as psi:
            opt.tick(42, 0, [], 30, sample=False)
            self.assertEqual(opt.status["state"], "Auto")
            self.assertIn("gameplay telemetry", opt.status["result"])
            psi.assert_not_called()
            opt.tick(42, 1, [], 30)
            self.assertIn("Monitoring", opt.status["result"])
            self.assertEqual(opt.status["tasks"], 0)
            opt.tick(42, 2, [], 30, sample=False)
            self.assertEqual(opt.app, 42)
            self.assertEqual(psi.call_count, 1)
            opt.tick(0, 3, [], 0)
            self.assertEqual(opt.status["result"], "Waiting for game")
            self.assertNotIn("pressure", opt.status)
            opt.tick(0, 4, [], 0, inactive_reason="Disabled")
            self.assertEqual(opt.status["result"], "Disabled")

    def test_user_services_attribute_cpu_without_regulating_unknowns(self):
        from gfg_plugin.resource_usage import sample_groups, busiest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            group = root / "app.slice/custom.service"
            group.mkdir(parents=True)
            stat = group / "cpu.stat"
            stat.write_text("usage_usec 0")
            first, _ = sample_groups([root / "app.slice"], {}, 1)
            stat.write_text("usage_usec 2500000")
            _, rows = sample_groups([root / "app.slice"], first, 6)
            self.assertEqual([(r["unit"], r["cpu"]) for r in busiest(rows)], [("custom.service", 50)])

    def test_heavy_indexing_before_frames_are_late(self):
        import os
        opt = Optimizer(os.getuid())
        with tempfile.TemporaryDirectory() as path, patch("gfg_plugin.resource_optimizer.eligible", return_value=True), patch("gfg_plugin.resource_optimizer.pressures", return_value={"cpu": 15}), patch("gfg_plugin.resource_optimizer.subprocess.run") as run:
            group = Path(path)
            opt.groups = {"baloo": group}
            (group / "cpu.weight").write_text("100")
            (group / "cpu.max").write_text("max 100000")
            for t in range(0, 20, 5):
                (group / "cpu.stat").write_text(f"usage_usec {t*700000}")
                opt.tick(42, t, [32]*30, 30)
                if t < 15:
                    run.assert_not_called()
            self.assertEqual(run.call_args.args[0][-2:], ["limit", "baloo"])

    def test_quota_cleanup_and_external_override(self):
        from gfg_plugin.resource_optimizer import lease
        for external in (False, True):
            with self.subTest(external=external), tempfile.TemporaryDirectory() as directory:
                group = Path(directory)
                receipt = group / "journal"
                (group / "cpu.weight").write_text("100")
                quota = group / "cpu.max"
                quota.write_text("max 100000")
                with patch("gfg_plugin.resource_optimizer.eligible", return_value=True), patch("gfg_plugin.resource_optimizer.time.sleep", side_effect=RuntimeError):
                    with self.assertRaises(RuntimeError):
                        lease("limit", 1000, group, receipt)
                self.assertEqual(quota.read_text(), "25000 100000")
                if external:
                    quota.write_text("40000 100000")
                lease("restore", 1000, group, receipt)
                self.assertEqual(quota.read_text(), "40000 100000" if external else "max 100000")
                self.assertFalse(receipt.exists())

    def test_sustained_indexing_with_cpu_headroom_on_battery(self):
        import os
        for battery in (False, True):
            opt = Optimizer(os.getuid())
            with self.subTest(battery=battery), tempfile.TemporaryDirectory() as path, patch("gfg_plugin.resource_optimizer.eligible", return_value=True), patch("gfg_plugin.resource_optimizer.pressures", return_value={"cpu": 0}), patch("gfg_plugin.resource_optimizer.subprocess.run") as run:
                group = Path(path)
                opt.groups = {"baloo": group}
                (group/"cpu.weight").write_text("100")
                (group/"cpu.max").write_text("max 100000")
                for t in range(0, 20, 5):
                    (group/"cpu.stat").write_text(f"usage_usec {t*700000}")
                    opt.tick(42, t, [32]*30, 30, on_battery=battery)
                self.assertEqual(run.called, battery)
                if battery:
                    self.assertEqual(run.call_args.args[0][-2:], ["limit", "baloo"])
                    opt.tick(42, 17, [], 0, on_battery=False)
                    self.assertIsNone(opt.active)

    def test_io_bound_nested_scope_no_double_count(self):
        from gfg_plugin.resource_usage import sample_groups, busiest
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            scope = root / "apps.slice" / "demo.scope"
            child = scope / "private.service"
            child.mkdir(parents=True)
            for group in (scope, child):
                (group / "cpu.stat").write_text("usage_usec 100")
                (group / "io.stat").write_text("179:0 rbytes=0 wbytes=0")
            first, _ = sample_groups([root], {}, 0)
            for group in (scope, child):
                (group / "io.stat").write_text("179:0 rbytes=10485760 wbytes=20971520")
            _, rows = sample_groups([root], first, 10)
            self.assertEqual(busiest(rows), [dict(unit="demo.scope", group=str(scope), role="Unclassified", cpu=0, device="179:0", read_mib=1, write_mib=2)])

    def test_role_labels_use_session_and_verified_paths(self):
        from gfg_plugin.resource_usage import display_role
        p = Path("app.slice/app-steam-42-123.scope")
        self.assertEqual(display_role(p, 42, ()), "Active Steam app scope")
        self.assertEqual(display_role(p, 420, ()), "Unclassified")
        self.assertEqual(display_role(Path("system.slice/demo.service"), 42, ()), "System unit")
        self.assertEqual(display_role(Path("app.slice/syncthing.service"), 42, ()), "Unclassified")
        self.assertEqual(display_role(p, 42, {p}), "Verified background service")

    def test_deck_game_and_launcher_roles(self):
        from gfg_plugin.resource_usage import display_role
        scope = Path("app.slice/app-steam-app3629430-21139.scope")
        self.assertEqual(display_role(scope, 3629430, ()), "Active Steam app scope")
        self.assertEqual(display_role(scope, 362943, ()), "Unclassified")
        self.assertEqual(display_role(scope, 0, ()), "Unclassified")
        self.assertEqual(display_role(Path("app.slice/steam-launcher.service"), 3629430, ()), "Session infrastructure")
