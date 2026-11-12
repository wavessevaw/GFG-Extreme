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
        self.assertEqual(filters.to_post(shed(cfg, 2)), 'detail=1')
        self.assertTrue(cfg['focus'])

    def test_focus_with_every_preset_and_other_effects(self):
        # The presence of Vivid (which selects CAS), DLS, colour grading, AA and
        # finish effects must never take ownership of the Focus switch.
        for preset_id, _, _ in filters.PRESETS:
            with self.subTest(preset=preset_id):
                cfg = filters.preset(preset_id)
                cfg['focus'] = True
                post = filters.to_post(cfg)
                self.assertEqual(post.split(',').count('detail=1'), 1)
                self.assertNotIn('cas=', post)
                self.assertNotIn('dls=', post)
                for level in (0, 1, 2):
                    self.assertIn('detail=1', filters.to_post(shed(cfg, level)),
                                  (preset_id, level))
        for effect, _, _ in filters.EFFECTS:
            with self.subTest(effect=effect):
                cfg = filters.normalize({'effects': [effect], 'sharpen': 'dls',
                                         'aa': 'smaa', 'focus': True})
                post = filters.to_post(cfg)
                self.assertIn(effect, post.split(','))
                self.assertEqual(post.count('detail=1'), 1)
                self.assertIn('smaa', post.split(','))

    def test_focus_persists_when_other_filters_are_stripped(self):
        cfg = filters.normalize({'effects': ['vibrance', 'clarity'],
                                 'sharpen': 'cas', 'aa': 'smaa', 'focus': True})
        self.assertEqual(filters.to_post(shed(cfg, 2)), 'detail=1')
        self.assertIn('detail=1', filters.to_post(shed(cfg, 0)).split(','))
        self.assertIn('vibrance', filters.to_post(shed(cfg, 0)).split(','))
        self.assertTrue(cfg['focus'])

    def test_compositor_processing_evidence_reaches_ui(self):
        from gfg_plugin.service import Service
        for status in ('processing', 'hdr_bypass', 'steam_ui'):
            source = {'fresh': True, 'focus_status': status, 'focus_frames': 123}
            self.assertEqual(Service._engine_view(source), source)
