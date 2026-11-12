import unittest
import helpers
from gfg_plugin.kedavra.hud import render_benchmark

class BenchmarkHudTest(unittest.TestCase):
    def test_all_display_scales_fit_compositor_limit(self):
        for scale in (.88,1.32,1.76):
            for phase in ('measure','aborted','result'):
                with self.subTest(scale=scale,phase=phase):
                    w,h,pixels=render_benchmark(dict(phase=phase,tested=4),scale)
                    self.assertEqual(len(pixels),w*h*4)
                    self.assertLessEqual(len(pixels),1024*1024)
                    self.assertGreaterEqual(h*.3,60)
