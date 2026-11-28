import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from helpers import Clock
from gfg_plugin.settings import Settings
from gfg_plugin.resolution import ResolutionController


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.settings = Settings(Path(root.name) / "config.json")
        self.clock, self.ctl = Clock(), Mock()
        self.st = dict(fresh=True, sr_capable=True, sr_output_width=1280, sr_output_height=800,
                       refresh_ns=16666667, app_id=769)
        self.ctl.status.return_value = self.st
        self.r = ResolutionController(self.settings, self.ctl, self.clock)

    def arm(self):
        self.settings.set_section("engine", {"super_resolution": True})
        self.assertTrue(self.r.launch(33))

    def test_capability_identity_opt_in(self):
        self.assertFalse(self.r.launch(33))
        self.settings.set_section("engine", {"super_resolution": True})
        for app in (769, -1, 2**32, "33", True):
            self.assertFalse(self.r.launch(app))
        self.st["fresh"] = False
        self.assertFalse(self.r.launch(33))
        self.ctl.set_var.assert_not_called()

    def test_launch_overlay_exit_late_attach_disable(self):
        self.arm()
        token = self.r.token
        self.assertFalse(self.r.launch(33))
        self.clock.t += 8
        self.r.tick(0, self.st)
        self.ctl.set_var.assert_called_with("kfg_sr", f"33:500:{token}")
        self.st["app_id"] = 33
        self.r.tick(33, self.st)
        self.st["app_id"] = 769
        self.r.tick(33, self.st)
        self.assertEqual(self.r.app,33)
        self.r.tick(0,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","0")
        self.r.tick(44,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","44:500:0")
        self.settings.set_section("engine", {"super_resolution": False})
        self.r.tick(44,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","0")

    def test_aborted_launch(self):
        self.arm()
        self.clock.t += 31
        self.r.tick(0,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","0")

    def session(self):
        self.arm()
        self.st.update(app_id=33, sr_managed_app=33, sr_virtual_width=800, sr_virtual_height=500,
                       sr_selected=True, sr_width=800, sr_height=500)

    def samples(self, count, fps=24, gpu=98, cpu=65, target=30):
        for _ in range(count):
            self.st["time_ns"]=self.st.get("time_ns",0)+1
            self.r.observe(self.st,{"real":fps},{"gpu_busy_pct":gpu,"cpu_top_core_pct":cpu},target,10,False)

    def test_gpu_and_repeat_profile(self):
        self.session()
        self.samples(60)
        self.assertEqual(self.settings.data["sr_profiles"][self.r.key]["next"],480)
        self.r.stop()
        self.r.launch(33)
        self.assertEqual(self.r.height,480)

    def test_cpu_limit(self):
        self.session()
        self.samples(60,24,54,98)
        self.assertEqual(self.settings.data["sr_profiles"][self.r.key]["next"],540)

    def test_supply_or_target_transition_invalidates_window(self):
        self.session()
        self.samples(46,target=30)
        self.samples(32,target=45)
        self.assertFalse(self.r.done)

    def test_failing_surface_releases_without_rearming(self):
        self.session()
        self.st.update(sr_selected=False,sr_width=1280,sr_height=800)
        self.samples(12)
        self.r.tick(33,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","0")
        self.assertEqual(self.r.app,0)
        self.assertEqual(self.r.blocked,33)
        self.r.tick(0,self.st)
        self.assertTrue(self.r.launch(33))
        self.assertEqual(self.r.height,540)

    def test_duplicate_status_is_not_new_evidence(self):
        self.session()
        self.st["time_ns"]=1
        for _ in range(64):
            self.r.observe(self.st,{"real":24},{"gpu_busy_pct":98},30)
        self.assertEqual(len(self.r.samples),1)

    def test_first_refresh_after_scheduler_start(self):
        self.st["refresh_ns"] = 0
        self.session()
        self.st["refresh_ns"] = 16666667
        self.samples(60)
        self.assertTrue(self.r.key.endswith(":60"))
        self.r.stop()
        self.st["refresh_ns"] = 0
        self.assertTrue(self.r.launch(33))
        self.assertEqual(self.r.height,480)

    def test_hdr_after_learning(self):
        self.session()
        self.samples(60)
        self.st.update(transfer="pq",sr_selected=False)
        self.samples(12)
        self.assertEqual(self.r.blocked,33)
        self.ctl.set_var.assert_called_with("kfg_sr","0")
