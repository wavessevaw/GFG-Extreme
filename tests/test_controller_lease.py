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

    def test_legacy_standalone_is_visible_as_incompatible(self):
        import json
        from gfg_plugin.coexist import Coexistence
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); plugin=home/'homebrew/plugins/KEDAVRA'
            plugin.mkdir(parents=True)
            (plugin/'plugin.json').write_text(json.dumps({'name':'GSF Kedavra'}))
            coexist=Coexistence(home,var_root=home/'var')
            self.assertIn('1.6.1',coexist.control_error())
            (plugin/'py_modules').mkdir()
            (plugin/'py_modules/kedavra_controller.py').write_text('# compatible module')
            self.assertEqual(coexist.control_error(),'')

    def test_legacy_guard_blocks_actual_command_path(self):
        from gfg_plugin.kedavra.ctl import Control
        ctl=Control.__new__(Control)
        ctl.control_guard=lambda:'Update companion'
        ctl._ctl_owned=lambda *args:self.fail('Command escaped compatibility guard')
        with self.assertRaisesRegex(RuntimeError,'Update companion'):
            ctl._ctl('kfg_post','detail=1')
