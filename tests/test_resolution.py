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
        self.ctl.set_var.assert_called_with("kfg_sr", f"33:640:{token}")
        self.st["app_id"] = 33
        self.r.tick(33, self.st)
        self.st["app_id"] = 769
        self.r.tick(33, self.st)
        self.assertEqual(self.r.app,33)
        self.r.tick(0,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","0")
        self.r.tick(44,self.st)
        self.ctl.set_var.assert_called_with("kfg_sr","44:640:0")
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
        self.st.update(app_id=33, sr_managed_app=33, sr_virtual_width=1024, sr_virtual_height=640,
                       sr_selected=True, sr_width=1024, sr_height=640)

    def samples(self, count, fps=24, gpu=98, cpu=65, target=30):
        for _ in range(count):
            self.st["time_ns"]=self.st.get("time_ns",0)+1
            self.r.observe(self.st,{"real":fps},{"gpu_busy_pct":gpu,"cpu_top_core_pct":cpu},target,10,False)

    def test_fixed_steam_owned_resolution(self):
        self.session()
        self.assertEqual(self.r.token, 0)
        self.samples(60)
        self.assertEqual(self.r.height, 640)
        self.assertEqual(self.r.message, "640p confirmed; Native SR active")
        self.r.stop()
        self.assertTrue(self.r.launch(33))
        self.ctl.set_var.assert_called_with("kfg_sr", "33:640:0")

    def test_no_virtual_display_resize_or_learning(self):
        self.session()
        self.st.update(sr_selected=False, sr_width=1280, sr_height=800)
        self.samples(60)
        self.assertEqual(self.r.height, 640)
        self.assertEqual(self.r.message, "Steam 640p not confirmed or surface unsupported")
        self.assertFalse(self.settings.data.get("sr_profiles"))
