import unittest

from sandbox.run import make_rig, play
from sandbox.vdeck import VGame


class Response60Test(unittest.TestCase):
    def test_auto_follows_active_output_without_editing_settings(self):
        for dock in (True, False):
            with self.subTest(dock=dock):
                rig = make_rig(VGame("g", 40.0), refresh=59.94, dock=dock, boost=True)
                play(rig, 15)
                self.assertEqual(rig.service.last_policy.multiplier, 2)
                self.assertFalse(rig.service.boost.enabled)
                self.assertEqual(rig.settings.data["profiles"]["default"]["fg"], "auto")
                rig.engine.refresh = 90
                play(rig, 15)
                self.assertNotEqual(rig.service.pilot.phase, "fixed")
                rig.engine.refresh = 60
                play(rig, 15)
                self.assertEqual(rig.service.last_policy.multiplier, 2)

    def test_off_at_60(self):
        rig = make_rig(VGame("g", 40.0), fg="off", refresh=60)
        play(rig, 10)
        self.assertEqual(rig.service.last_policy.multiplier, 0)
