import tempfile
import unittest
from pathlib import Path
import helpers
from gfg_plugin.kedavra.controller import ControllerLease, ControllerUnavailable

class LeaseTest(unittest.TestCase):
    def test_priority_release_and_no_command_race(self):
        with tempfile.TemporaryDirectory() as d:
            a=ControllerLease('gsf',Path(d)); b=ControllerLease('gfg',Path(d)); other=ControllerLease('gfg',Path(d))
            self.assertTrue(a.active())
            self.assertTrue(b.active())
            self.assertFalse(a.active())
            self.assertFalse(other.active())
            with self.assertRaises(ControllerUnavailable):
                with a.command(): self.fail('Unowned command')
            with b.command(): pass
            b.release()
            self.assertFalse(b.active())
            self.assertTrue(a.active())
            a.release();a.release()
            self.assertTrue(other.active())
