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

    def test_real_control_lets_hdr_enabled_through(self):
        # 3.0.10 on a Deck: "unknown convar hdr_enabled" every second, the switch never worked.
        import subprocess
        from gfg_plugin.kedavra.ctl import Control
        calls = []
        run = lambda args, **kw: (calls.append(args[1:]), subprocess.CompletedProcess(args, 0, "", ""))[1]  # noqa: E731
        Control("/tmp", "/tmp", runner=run).set_var("hdr_enabled", 0)
        self.assertEqual(calls, [["hdr_enabled", "0"]])

    def test_a_failing_switch_is_retried_every_10_s_and_journalled_once(self):
        rig = make_rig(VGame("g", 55.0))
        tries = []

        def broken(n, v):
            if n == "hdr_enabled":
                tries.append(v)
                raise RuntimeError("gamescopectl failed")
        rig.engine.set_var = broken
        rig.settings.data["engine"]["hdr_output"] = False
        play(rig, 60)
        self.assertLessEqual(len(tries), 7)
        fails = [e for e in rig.log if e.get("kind") == "hdr-output-failed"]
        self.assertEqual(len(fails), 1)


if __name__ == "__main__":
    unittest.main()
