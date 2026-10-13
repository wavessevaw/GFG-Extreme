"""GFG's own reversible Steam Gaming Mode theme; no CSS Loader dependency.

Only the local Steam CEF debugging endpoint is used. The RPC never accepts
JavaScript, stylesheets, URLs, or filesystem paths from the frontend.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .package_paths import PLUGIN_ROOT

ASSETS = PLUGIN_ROOT / 'themes' / 'gfg-shell'
POLL_S = 3.0
LEASE_MS = 15000
SHARED_TITLES = ('SP', 'Steam', 'SharedJSContext', 'Steam Shared Context presented by Valve\u2122')
OVERLAY_PREFIXES = ('QuickAccess', 'MainMenu', 'SteamKeyboard')
LOG = logging.getLogger(__name__)


def target_kind(tab: dict) -> str | None:
    """Only Steam's known Gaming Mode CDP pages; never external/store pages.

    On an actual Deck the visible Big Picture and sidebar CEF windows have
    about:blank?createflags= / about:blank?browserviewpopup= addresses.
    The shared React context instead has a steamloopback.host address.
    Both kinds are necessary, but each has a deliberately narrow title/URL pair.
    """
    if not isinstance(tab, dict) or tab.get('type') != 'page':
        return None
    title = tab.get('title', '')
    raw_url = tab.get('url', '')
    if not isinstance(title, str) or not isinstance(raw_url, str):
        return None
    url = urlparse(raw_url)
    path = unquote(url.path)
    if url.scheme == 'about' and path == 'blank' and not url.fragment:
        keys = parse_qs(url.query, keep_blank_values=True)
        if title == 'Steam Big Picture Mode' and 'createflags' in keys:
            return 'main'
        if title.startswith(OVERLAY_PREFIXES) and 'browserviewpopup' in keys:
            return 'overlay'
        return None
    if url.scheme != 'https' or url.hostname != 'steamloopback.host':
        return None
    if title in SHARED_TITLES and (
        path == '/index.html' or path.startswith('/routes/') or 'Valve Steam Gamepad' in path
    ):
        return 'shared'
    if title == 'Steam Big Picture Mode' and 'Valve Steam Gamepad' in path:
        return 'main'
    if title.startswith(OVERLAY_PREFIXES) and 'Valve Steam Gamepad' in path:
        return 'overlay'
    return None


def allowed_target(tab: dict) -> bool:
    return target_kind(tab) is not None


def allowed_socket(url: str, *, browser=False) -> bool:
    try:
        p = urlparse(url)
        return (p.scheme == 'ws' and p.hostname in ('localhost', '127.0.0.1', '::1')
                and p.port == 8080 and p.path.startswith('/devtools/browser/' if browser else '/devtools/page/')
                and p.username is None and p.password is None)
    except ValueError:
        return False


class SteamTransport:
    def __init__(self):
        self.target_count = 0
        self.target_titles: list[str] = []

    async def _command(self, ws, ident, method, params, session_id=None):
        import aiohttp
        request = {'id': ident, 'method': method, 'params': params}
        if session_id:
            request['sessionId'] = session_id
        await ws.send_json(request)
        async for message in ws:
            if message.type != aiohttp.WSMsgType.TEXT:
                continue
            value = json.loads(message.data)
            if value.get('id') != ident:
                continue
            if value.get('error'):
                raise OSError('Steam debugging command failed: ' + method)
            return value.get('result', {})
        raise OSError('Steam UI connection closed')

    async def tabs(self) -> list[dict]:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            # Browser targets include CEF windows not exposed by the legacy /json list.
            try:
                async with session.get('http://127.0.0.1:8080/json/version', allow_redirects=False) as response:
                    if response.status != 200:
                        raise OSError('Steam browser endpoint unavailable')
                    info = await response.json(content_type=None)
                socket = info.get('webSocketDebuggerUrl', '')
                if not allowed_socket(socket, browser=True):
                    raise ValueError('Not a local Steam browser socket')
                async with session.ws_connect(socket) as ws:
                    reply = await self._command(ws, 1, 'Target.getTargets', {})
                data = reply.get('targetInfos')
                if not isinstance(data, list) or len(data) > 128:
                    raise ValueError('Unexpected Steam UI target list')
                self.target_count = len(data)
                self.target_titles = [str(t.get('title', ''))[:72] for t in data if isinstance(t, dict)][:16]
                return [dict(t, _browser_socket=socket) for t in data
                        if isinstance(t, dict) and allowed_target(t)]
            except (OSError, ValueError, aiohttp.ClientError):
                pass  # Older CEF builds still expose per-page debugging sockets.
            async with session.get('http://127.0.0.1:8080/json', allow_redirects=False) as response:
                if response.status != 200:
                    raise OSError('Steam UI endpoint unavailable')
                data = await response.json(content_type=None)
                if not isinstance(data, list) or len(data) > 128:
                    raise ValueError('Unexpected Steam UI target list')
                self.target_count = len(data)
                self.target_titles = [str(t.get('title', ''))[:72] for t in data if isinstance(t, dict)][:16]
                return [t for t in data if isinstance(t, dict) and allowed_target(t)]

    async def evaluate(self, tab: dict, script: str) -> dict:
        import aiohttp
        browser = bool(tab.get('_browser_socket'))
        socket = tab.get('_browser_socket') if browser else tab.get('webSocketDebuggerUrl', '')
        if not allowed_target(tab) or not allowed_socket(socket, browser=browser):
            raise ValueError('Not a local Steam Gaming Mode target')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.ws_connect(socket) as ws:
                session_id = None
                if browser:
                    attached = await self._command(ws, 1, 'Target.attachToTarget',
                        {'targetId': tab['targetId'], 'flatten': True})
                    session_id = attached.get('sessionId')
                    if not session_id:
                        raise OSError('Steam did not attach its UI window')
                result = await self._command(ws, 2, 'Runtime.evaluate', {
                    'expression': script, 'returnByValue': True, 'awaitPromise': False,
                    'userGesture': True}, session_id)
                if result.get('exceptionDetails'):
                    raise OSError('Steam rejected the theme operation')
                answer = result.get('result', {}).get('value')
                if not isinstance(answer, dict):
                    raise OSError('Steam theme did not acknowledge the operation')
                return answer
        raise OSError('Steam UI connection closed')


class SteamShell:
    def __init__(self, settings_path: Path, *, transport=None, assets: Path = ASSETS):
        self.settings_path = Path(settings_path)
        self.transport = transport or SteamTransport()
        self.assets = Path(assets)
        self.enabled = False
        self._error = None
        self._targets: list[dict] = []
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()
        self._task = None
        self._stopping = False
        self._dirty = True
        self._last_diagnostic = None
        self._load()

    def _load(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding='utf-8'))
            self.enabled = isinstance(data, dict) and data.get('enabled') is True
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self._error = 'Theme settings could not be read; standard Steam appearance retained.'

    def _save(self, enabled: bool):
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.gfg-shell-', dir=self.settings_path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump({'version': 1, 'enabled': enabled}, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, self.settings_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def script(self, enabled: bool, *, role: str = 'shared') -> str:
        if role not in ('shared', 'main', 'overlay'):
            raise ValueError('Unsupported Steam window role')
        runtime = (self.assets / 'runtime.js').read_text(encoding='utf-8')
        css = (self.assets / 'shell.css').read_text(encoding='utf-8') if enabled else ''
        payload = {'enabled': enabled, 'css': css, 'targetRole': role, 'leaseMs': LEASE_MS,
                   'revision': hashlib.sha256(css.encode()).hexdigest()[:16]}
        return '(' + runtime + ')(' + json.dumps(payload, ensure_ascii=True) + ')'

    def status(self) -> dict[str, Any]:
        active = [t for t in self._targets if t.get('applied')]
        return {'success': True, 'enabled': self.enabled, 'active': bool(active),
                'state': 'active' if active else 'waiting' if self.enabled else 'off',
                'engine': 'gfg-shell', 'requires_css_loader': False,
                'targets': list(self._targets), 'error': self._error,
                'coverage': sorted({s for t in active for s in t.get('surfaces', [])}),
                'lease_seconds': LEASE_MS // 1000, 'build': 'shell-fix-4',
                'discovered_targets': getattr(self.transport, 'target_count', None),
                'discovered_titles': getattr(self.transport, 'target_titles', [])}

    async def set_enabled(self, enabled: bool) -> dict:
        if type(enabled) is not bool:
            return {'success': False, 'error': 'A boolean is required'}
        async with self._lock:
            try:
                # Validate bundled assets before committing an enabled preference.
                self.script(enabled)
                self._save(enabled)
            except (OSError, ValueError) as e:
                return {'success': False, 'error': str(e)}
            self.enabled = enabled
            self._dirty = True
            await self._sync_locked()
        self._wake.set()
        return self.status()

    async def sync(self):
        async with self._lock:
            await self._sync_locked()

    async def _sync_locked(self, *, removing=False):
        enabled = self.enabled and not removing
        try:
            # Validate assets before discovery, then pick a per-window runtime
            # authorization; about:blank is never allowed for shared contexts.
            self.script(enabled)
            tabs = await asyncio.wait_for(self.transport.tabs(), timeout=4)
            tabs = [t for t in tabs if allowed_target(t)]
            async def apply(tab):
                try:
                    script = self.script(enabled, role=target_kind(tab))
                    result = await asyncio.wait_for(self.transport.evaluate(tab, script), timeout=4)
                    return {'title': tab.get('title', 'Steam'), 'role': target_kind(tab), **result}
                except Exception:
                    return {'title': tab.get('title', 'Steam'), 'applied': False,
                            'error': 'Steam UI target is not responding'}
            self._targets = await asyncio.gather(*(apply(t) for t in tabs[:16]))
            self._error = None
            if enabled:
                if not tabs:
                    count = getattr(self.transport, 'target_count', 0)
                    titles = ', '.join(getattr(self.transport, 'target_titles', [])[:6]) or 'none'
                    self._error = f'No supported Steam Gaming Mode window among {count} CEF targets (titles: {titles}).'
                elif any(t.get('error') for t in self._targets):
                    self._error = 'Steam UI connection failed for one or more windows.'
                elif not any(t.get('applied') for t in self._targets):
                    reasons = sorted({str(t.get('role', 'unknown')) + ': ' +
                                      str(t.get('reason', 'unknown')) +
                                      (' (DOM nodes: ' + str(t.get('dom_nodes')) + ')'
                                       if t.get('dom_nodes') is not None else '')
                                      for t in self._targets})
                    self._error = 'Steam connected, but appearance was not applied: ' + ', '.join(reasons)
            self._dirty = False
        except Exception as error:
            self._targets = []
            self._error = ('Steam connection unavailable (' + type(error).__name__ +
                           '). GFG will reconnect automatically.') if enabled else None
        diagnostic = (enabled, self._error, tuple((t.get('title'), t.get('applied'), t.get('reason')) for t in self._targets))
        if diagnostic != self._last_diagnostic:
            LOG.info('GFG SteamOS shell-fix-4: enabled=%s targets=%s error=%s', enabled, self._targets, self._error)
            self._last_diagnostic = diagnostic

    async def start(self):
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.create_task(self._run())

    async def _run(self):
        while not self._stopping:
            self._wake.clear()
            if self.enabled or self._dirty:
                await self.sync()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=POLL_S if self.enabled else 60)
            except asyncio.TimeoutError:
                pass

    async def stop(self):
        self._stopping = True
        self._wake.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # No startup scripts or Steam files are changed. If Steam disappeared,
        # the independent JS lease removes our style once its event loop resumes.
        async with self._lock:
            await self._sync_locked(removing=True)

