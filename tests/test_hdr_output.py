import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sandbox.run import make_rig, play  # noqa: E402
from sandbox.vdeck import VGame  # noqa: E402


class HdrOutputTest(unittest.TestCase):
    def test_off_is_sent_and_kept_then_given_back(self):
        rig = make_rig(VGame("g", 55.0))
        sent = []
        orig = rig.engine.set_var
        rig.engine.set_var = lambda n, v: (sent.append((n, str(v))) if n == "hdr_enabled" else None, orig(n, v))[1]
        play(rig, 30)
        self.assertEqual(sent, [])  # on: Steam's own setting, nothing sent
        rig.settings.data["engine"]["hdr_output"] = False
        play(rig, 31)
        self.assertEqual(sent, [("hdr_enabled", "0")] * 4)  # at once, then every 10 s
        rig.settings.data["engine"]["hdr_output"] = True
        play(rig, 30)
        self.assertEqual(sent[-1], ("hdr_enabled", "1"))
        self.assertEqual(len(sent), 5)

    def test_unload_gives_hdr_back(self):
        rig = make_rig(VGame("g", 55.0))
        rig.settings.data["engine"]["hdr_output"] = False
        play(rig, 5)
        rig.service.stop()
        self.assertEqual(rig.engine.vars.get("hdr_enabled"), "1")


if __name__ == "__main__":
    unittest.main()
