import tempfile
import unittest
from pathlib import Path
import helpers
from gfg_plugin import filters, settings
from gfg_plugin.filter_budget import shed


class FocusIntegrationTest(unittest.TestCase):
    def test_saved_profile_focus_overrides_and_restores_dls(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'settings.json'
            s = settings.Settings(path)
            cfg = filters.normalize({'effects': ['vibrance'], 'sharpen': 'dls',
                                     'sharpness': 0.35, 'denoise': 0.17, 'focus': True})
            s.update_profile('default', {'filters': cfg, 'fg': 'off'})
            restored = settings.Settings(path).data['profiles']['default']['filters']
            self.assertEqual(filters.to_post(restored), 'vibrance,detail=1')
            self.assertEqual(filters.to_post({**restored, 'focus': False}), 'vibrance,dls=0.35:0.17')

    def test_focus_only_is_active_and_fixed_strength(self):
        cfg = filters.normalize({'focus': True, 'sharpness': 0.05})
        self.assertTrue(filters.is_active(cfg))
        self.assertEqual(filters.to_post(cfg), 'detail=1')
        self.assertEqual(filters.to_post({**cfg, 'focus': False}), '')
        self.assertEqual(filters.preset_of(cfg), 'custom')

    def test_existing_filter_budget_can_bypass_without_rewriting_preference(self):
        cfg = filters.normalize({'focus': True})
        self.assertEqual(filters.to_post(shed(cfg, 1)), 'detail=1')
        self.assertEqual(filters.to_post(shed(cfg, 2)), '')
        self.assertTrue(cfg['focus'])
