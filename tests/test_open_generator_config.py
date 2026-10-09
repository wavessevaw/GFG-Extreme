"""Open generator is persisted in the wrapper sidecar and selected once at launch."""
import unittest
from unittest.mock import patch
from py_modules.gfg_plugin import wrapper_generation as wrapper
from py_modules.gfg_plugin.config_schema import ConfigurationManager, SCRIPT_ONLY_FIELDS
from py_modules.gfg_plugin.profile_storage import normalize_wrapper_settings

class OpenGeneratorConfigTests(unittest.TestCase):
    def test_opt_in_default_and_profile_persistence(self):
        self.assertFalse(ConfigurationManager.get_defaults()["open_frame_generation"])
        self.assertIn("open_frame_generation", SCRIPT_ONLY_FIELDS)
        self.assertTrue(normalize_wrapper_settings({"open_frame_generation": True})["open_frame_generation"])
        self.assertFalse(normalize_wrapper_settings({})["open_frame_generation"])

    def test_only_gfg_can_select_open(self):
        for owner, expected in (("gfg", 1), ("off", 0), ("native", 0), ("optiscaler", 0)):
            cfg = ConfigurationManager.get_defaults()
            cfg.update(open_frame_generation=True, fg_backend=owner)
            lines = wrapper.script_configuration_lines(cfg)
            self.assertIn("export GFG_OPEN_FG=" + str(expected), lines)
