"""Upgrades from experimental builds must return to the ordinary renderer."""
import unittest
from py_modules.gfg_plugin import wrapper_generation as wrapper
from py_modules.gfg_plugin.config_schema import ConfigurationManager, SCRIPT_ONLY_FIELDS
from py_modules.gfg_plugin.profile_storage import normalize_wrapper_settings

class GeneratorRetirementTests(unittest.TestCase):
    def test_saved_open_opt_in_is_discarded_and_other_settings_survive(self):
        raw = {"open_frame_generation": True, "fg_backend": "gfg", "automatic_dock_mode": True}
        normalized = normalize_wrapper_settings(raw)
        self.assertNotIn("open_frame_generation", normalized)
        self.assertNotIn("open_frame_generation", SCRIPT_ONLY_FIELDS)
        self.assertTrue(normalized["automatic_dock_mode"])
        self.assertEqual(normalized["fg_backend"], "gfg")
        self.assertNotIn("open_frame_generation", ConfigurationManager.validate_config(raw))

    def test_stale_opt_in_cannot_select_a_private_generator(self):
        for owner in ("gfg", "off", "native", "optiscaler"):
            cfg = ConfigurationManager.get_defaults()
            cfg.update(open_frame_generation=True, fg_backend=owner)
            lines = wrapper.script_configuration_lines(cfg)
            self.assertIn("unset GFG_OPEN_FG GFG_OPEN_DIAGNOSTICS_DIR", lines)
            self.assertNotIn("export GFG_OPEN_FG=1", "\n".join(lines))
            self.assertNotIn("gfg-open", "\n".join(lines))

    def test_previous_wrapper_requires_regeneration(self):
        old = "\n".join(("# mako-wrapper-format: 85", wrapper.HOST_COMPATIBILITY_MARKER,
                          wrapper.DIAGNOSTICS_DEFAULT_MARKER, *wrapper.REQUIRED_WRAPPER_EXPORTS))
        self.assertFalse(wrapper.is_current_wrapper(old))
        self.assertTrue(wrapper.is_current_wrapper(old.replace("# mako-wrapper-format: 85", wrapper.WRAPPER_FORMAT_MARKER)))
