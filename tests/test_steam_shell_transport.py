"""Exercise real HTTP/WebSocket CDP traffic, not a mocked SteamTransport."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py_modules'))
from gfg_plugin.steam_shell import SteamTransport
try:
    from aiohttp import web
except ImportError:
    web = None


@unittest.skipIf(web is None, 'aiohttp required; installed explicitly in CI')
class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.commands = []
        self.legacy = False
        self.bad_browser = False
        self.target = {'targetId': 'native-page', 'type': 'page', 'title': 'SharedJSContext',
                       'url': 'https://steamloopback.host/index.html'}
        app = web.Application()
        app.router.add_get('/json/version', self.version)
        app.router.add_get('/json', self.pages)
        app.router.add_get('/devtools/browser/test', self.socket)
        app.router.add_get('/devtools/page/native-page', self.socket)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.TCPSite(self.runner, '127.0.0.1', 8080).start()
        self.addAsyncCleanup(self.runner.cleanup)
        self.transport = SteamTransport()

    async def version(self, request):
        if self.legacy:
            return web.Response(status=404)
        address = 'ws://example.com:8080/devtools/browser/test' if self.bad_browser else 'ws://127.0.0.1:8080/devtools/browser/test'
        return web.json_response({'webSocketDebuggerUrl': address})

    async def pages(self, request):
        return web.json_response([dict(self.target, id='native-page',
            webSocketDebuggerUrl='ws://127.0.0.1:8080/devtools/page/native-page')])

    async def socket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for message in ws:
            command = message.json()
            self.commands.append(command)
            method = command['method']
            if method == 'Target.getTargets':
                result = {'targetInfos': [self.target, dict(self.target, targetId='external', url='https://example.com/')]}
            elif method == 'Target.attachToTarget':
                self.assertEqual(command['params'], {'targetId': 'native-page', 'flatten': True})
                result = {'sessionId': 'attached-window'}
            else:
                if '/browser/' in request.path:
                    self.assertEqual(command['sessionId'], 'attached-window')
                result = {'result': {'value': {'applied': True, 'surfaces': ['home']}}}
            # Unrelated events must not be mistaken for command results.
            await ws.send_json({'method': 'Target.targetInfoChanged', 'params': {}})
            await ws.send_json({'id': command['id'], 'result': result})
        return ws

    async def test_browser_discovery_attach_and_evaluate(self):
        tabs = await self.transport.tabs()
        self.assertEqual(len(tabs), 1)
        self.assertEqual(self.transport.target_count, 2)
        self.assertTrue((await self.transport.evaluate(tabs[0], '1'))['applied'])
        self.assertEqual([c['method'] for c in self.commands],
                         ['Target.getTargets', 'Target.attachToTarget', 'Runtime.evaluate'])

    async def test_real_big_picture_about_blank_is_discovered(self):
        self.target = dict(self.target, title='Steam Big Picture Mode',
                           url='about:blank?createflags=42')
        tabs = await self.transport.tabs()
        self.assertEqual(len(tabs), 1)
        self.assertTrue((await self.transport.evaluate(tabs[0], '1'))['applied'])

    async def test_legacy_fallback(self):
        self.legacy = True
        tabs = await self.transport.tabs()
        self.assertTrue((await self.transport.evaluate(tabs[0], '1'))['applied'])
        self.assertEqual([c['method'] for c in self.commands], ['Runtime.evaluate'])

    async def test_remote_browser_url_is_not_contacted(self):
        self.bad_browser = True
        tabs = await self.transport.tabs()
        self.assertNotIn('_browser_socket', tabs[0])
        self.assertTrue((await self.transport.evaluate(tabs[0], '1'))['applied'])
