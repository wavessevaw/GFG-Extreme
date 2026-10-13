import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
from gfg_plugin.steam_shell import SteamShell, allowed_target, allowed_socket


def target(title='Steam Big Picture Mode', **kw):
    return {'id': '1', 'type': 'page', 'title': title,
            'url': 'https://steamloopback.host/Valve%20Steam%20Gamepad/default',
            'webSocketDebuggerUrl': 'ws://127.0.0.1:8080/devtools/page/1', **kw}


class FakeSteam:
    def __init__(self):
        self.targets = [target()]
        self.calls = []
        self.offline = False
        self.bad = False

    async def tabs(self):
        if self.offline: raise OSError('offline')
        return self.targets

    async def evaluate(self, tab, script):
        self.calls.append((tab['id'], script))
        if self.bad: raise OSError('closed')
        enabled = '"enabled": true' in script
        return {'applied': enabled, 'surfaces': ['home'] if enabled else []}


class BoundaryTests(unittest.TestCase):
    def test_only_steam_gamepad_targets(self):
        self.assertTrue(allowed_target(target()))
        for title in ('QuickAccess_1', 'MainMenu_2', 'SteamKeyboard'):
            self.assertTrue(allowed_target(target(title)))
        for url in ('https://store.steampowered.com/', 'https://steamloopback.host.evil/routes/',
                    'https://example.com/Valve Steam Gamepad/default', 'file:///tmp/steam.html'):
            self.assertFalse(allowed_target(target(url=url)))
        self.assertFalse(allowed_target(target(type='service_worker')))
        self.assertFalse(allowed_target(target('Steam', url='https://steamloopback.host/library')))
        self.assertFalse(allowed_target(target('Steam', url='https://steamloopback.host/index.html')))
        self.assertFalse(allowed_target(target('Steam', url='https://steamloopback.host/routes/library')))
        self.assertTrue(allowed_target(target('SP', url='https://steamloopback.host/index.html')))

    def test_debugging_socket_cannot_redirect_to_remote_or_other_local_services(self):
        self.assertTrue(allowed_socket('ws://localhost:8080/devtools/page/1'))
        for url in ('ws://example.com:8080/devtools/page/1', 'ws://127.0.0.1:22/devtools/page/1',
                    'ws://localhost:8080/admin', 'ws://user@localhost:8080/devtools/page/1',
                    'ws://localhost:bad/devtools/page/1'):
            self.assertFalse(allowed_socket(url))


class ShellTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / 'shell.json'
        self.steam = FakeSteam()
        self.shell = SteamShell(self.file, transport=self.steam)

    async def test_enable_persist_reload_and_restore(self):
        self.assertFalse(self.shell.enabled)
        result = await self.shell.set_enabled(True)
        self.assertTrue(result['active'])
        self.assertEqual(result['coverage'], ['home'])
        self.assertTrue(SteamShell(self.file, transport=self.steam).enabled)
        result = await self.shell.set_enabled(False)
        self.assertFalse(result['active'])
        self.assertFalse(json.loads(self.file.read_text())['enabled'])
        self.assertIn('"enabled": false', self.steam.calls[-1][1])

    async def test_failed_save_leaves_preference_and_ui_unchanged(self):
        with patch.object(self.shell, '_save', side_effect=OSError('read only')):
            result = await self.shell.set_enabled(True)
        self.assertFalse(result['success'])
        self.assertFalse(self.shell.enabled)
        self.assertEqual(self.steam.calls, [])

    async def test_missing_assets_cannot_enable(self):
        self.shell.assets = Path(self.tmp.name)
        self.assertFalse((await self.shell.set_enabled(True))['success'])
        self.assertFalse(self.file.exists())

    async def test_offline_waits_and_recovers_without_a_false_active_status(self):
        self.steam.offline = True
        result = await self.shell.set_enabled(True)
        self.assertTrue(result['enabled'])
        self.assertFalse(result['active'])
        self.assertEqual(result['state'], 'waiting')
        self.steam.offline = False
        await self.shell.sync()
        self.assertTrue(self.shell.status()['active'])

    async def test_new_window_and_failed_window_are_reported_separately(self):
        await self.shell.set_enabled(True)
        self.steam.targets.append(target('QuickAccess', id='2'))
        await self.shell.sync()
        self.assertEqual(len(self.shell.status()['targets']), 2)
        self.steam.bad = True
        await self.shell.sync()
        self.assertFalse(self.shell.status()['active'])
        self.assertIsNotNone(self.shell.status()['error'])

    async def test_stop_cleans_live_targets_but_preserves_restart_preference(self):
        await self.shell.set_enabled(True)
        await self.shell.start()
        await asyncio.sleep(0)
        await self.shell.stop()
        self.assertIn('"enabled": false', self.steam.calls[-1][1])
        self.assertTrue(json.loads(self.file.read_text())['enabled'])
        self.assertIsNone(self.shell._task)

    async def test_stale_or_malicious_targets_are_not_styled(self):
        self.steam.targets.append(target('Web', id='3', url='https://example.com/'))
        await self.shell.set_enabled(True)
        self.assertEqual([id for id, _ in self.steam.calls], ['1'])

    async def test_rpc_rejects_non_boolean_input(self):
        for value in ('true', 1, None, {}):
            self.assertFalse((await self.shell.set_enabled(value))['success'])
        self.assertFalse(self.file.exists())

    async def test_malformed_saved_preference_keeps_standard_appearance(self):
        self.file.write_text('{bad')
        shell = SteamShell(self.file, transport=self.steam)
        self.assertFalse(shell.enabled)
        self.assertIsNotNone(shell.status()['error'])


if __name__ == '__main__': unittest.main()
