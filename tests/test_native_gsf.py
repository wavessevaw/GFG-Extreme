"""Independent generator settings, real launcher selection and honest live status."""
import hashlib
import asyncio
import shutil
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
decky = types.ModuleType('decky')
decky.logger = logging.getLogger('native-gsf-test')
decky.DECKY_USER_HOME = '/tmp/gfg-unused-native-gsf-home'
sys.modules.setdefault('decky', decky)
from gfg_plugin import native_gsf
from gfg_plugin.configuration import ConfigurationService

class NativeGsfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gfg-native-gsf-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        with patch('gfg_plugin.base_service.resolve_user_home', return_value=self.home):
            self.config = ConfigurationService()
        self.assertTrue(self.config.create_profile('native-test', 'mako')['success'])
        self.assertTrue(self.config.set_current_profile('native-test')['success'])
        self.runtime = self.config.runtime_state_dir
        self.log = logging.getLogger('native-gsf-test')

    def run_wrapper(self, **extra):
        env = dict(os.environ, HOME=str(self.home), MAKO_PROFILE='native-test')
        env.update(extra)
        result = subprocess.run(['bash', str(self.config.mako_script_path), '/usr/bin/env'],
                                env=env, capture_output=True, text=True, check=True)
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line), result.stderr

    def install_fixture(self):
        # This fixture checks shell selection, never Vulkan or GPU behaviour.
        root = self.home / '.local/share/gfg-native'
        root.mkdir(parents=True)
        (root / 'VkLayer_gfg_native.json').write_text('{}')
        (root / 'libVkLayer_gfg_native.so').write_bytes(b'launcher selection fixture')

    def test_default_off_and_marker_validation(self):
        self.assertEqual(native_gsf.requested(self.runtime), 'off')
        self.assertFalse(native_gsf.set_mode(self.runtime, 'invalid', self.log)['success'])
        self.assertTrue(native_gsf.set_mode(self.runtime, '2', self.log)['success'])
        self.assertEqual(native_gsf.requested(self.runtime), '2')
        self.assertEqual((self.runtime / native_gsf.MARKER).stat().st_mode & 0o777, 0o600)

    def test_launcher_uses_native_x2_and_x3_without_other_engine(self):
        self.install_fixture()
        for mode in ('2', '3'):
            native_gsf.set_mode(self.runtime, mode, self.log)
            env, _ = self.run_wrapper()
            self.assertEqual(env['GFG_NATIVE_MODE'], mode)
            self.assertEqual(env['GFG_NATIVE_ALGO'], 'gsf')
            self.assertEqual(env['GFG_NATIVE_FORCE_FIFO'], '0')
            self.assertEqual(env['GFG_NATIVE_ASYNC'], '1')
            self.assertEqual(env['DISABLE_MAKO'], '1')
            self.assertIn('VK_LAYER_GFG_native', env['VK_INSTANCE_LAYERS'])
            self.assertNotIn('GFG_TEMPORAL_ENGINE', env)
            self.assertNotIn('ENABLE_MAKO', env)

    def test_missing_component_is_explicit_real_only(self):
        native_gsf.set_mode(self.runtime, '3', self.log)
        env, stderr = self.run_wrapper()
        self.assertEqual(env['DISABLE_MAKO'], '1')
        self.assertEqual(env['DISABLE_GFG_NATIVE_FG'], '1')
        self.assertNotIn('GFG_NATIVE_GPU_BRIDGE', env)
        self.assertIn('real-only fallback', stderr)

    def test_off_removes_inherited_native_activation(self):
        self.install_fixture()
        native_gsf.set_mode(self.runtime, 'off', self.log)
        env, _ = self.run_wrapper(GFG_NATIVE_GPU_BRIDGE='1', GFG_NATIVE_FG='1',
                                  VK_INSTANCE_LAYERS='VK_LAYER_GFG_native')
        self.assertNotIn('GFG_NATIVE_GPU_BRIDGE', env)
        self.assertEqual(env['DISABLE_GFG_NATIVE_FG'], '1')
        self.assertNotIn('VK_LAYER_GFG_native', env.get('VK_INSTANCE_LAYERS', ''))

    def test_bundled_install_is_checksum_verified_and_preserves_prior_files(self):
        package = self.home / 'bundled';package.mkdir()
        for name in ('install.sh', 'gfg-native.sh', 'diagnose.sh'):
            shutil.copy2(ROOT / 'engine/gfg-native/package' / name, package / name)
        for name in ('libVkLayer_gfg_native.so', 'VkLayer_gfg_native.json', 'accept_report.py'):
            (package / name).write_bytes(b'installer fixture, not a Vulkan test')
        (package / 'SHA256SUMS.txt').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
            for p in sorted(package.iterdir())))
        self.assertTrue(native_gsf.stage_packaged(self.home, package)['success'])
        installed = self.home / '.local/share/gfg-native/libVkLayer_gfg_native.so'
        previous = installed.read_bytes()
        (package / 'libVkLayer_gfg_native.so').write_bytes(b'corrupt')
        self.assertFalse(native_gsf.stage_packaged(self.home, package)['success'])
        self.assertEqual(installed.read_bytes(), previous)

    def test_missing_bundle_and_launcher_cannot_report_success(self):
        missing = self.home / "no-bundle"
        self.assertFalse(native_gsf.stage_packaged(self.home, missing)["success"])
        self.install_fixture()
        result = native_gsf.status(self.runtime, self.home)
        self.assertFalse(result["installed"])
        self.assertFalse(result["launcher_ready"])
        self.assertIsNone(result["launch_command"])

    def test_missing_launcher_rejects_x3_without_changing_mode(self):
        from gfg_plugin.governor_service import GovernorService
        svc = GovernorService.__new__(GovernorService)
        svc.configuration = self.config
        installer = native_gsf.stage_packaged
        with patch('gfg_plugin.native_gsf.stage_packaged', side_effect=lambda home:
                   installer(home, self.home / 'missing')):
            result = svc.set_native_gsf('3')
        self.assertFalse(result['success'])
        self.assertEqual(native_gsf.requested(self.runtime), 'off')

    def test_integrated_staging_initializes_off_and_preserves_later_choice(self):
        from gfg_plugin.governor_service import GovernorService
        package = self.home / 'bundle'; package.mkdir()
        for name in ('install.sh', 'gfg-native.sh', 'diagnose.sh'):
            shutil.copy2(ROOT / 'engine/gfg-native/package' / name, package / name)
        for name in ('libVkLayer_gfg_native.so', 'VkLayer_gfg_native.json', 'accept_report.py'):
            (package / name).write_bytes(b'installer fixture, not a Vulkan test')
        (package / 'MANIFEST.json').write_text('{"version":"0.0.0-fg3-internal.7"}\n')
        (package / 'SHA256SUMS.txt').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
            for p in sorted(package.iterdir())))
        svc = GovernorService.__new__(GovernorService)
        svc.configuration, svc.log = self.config, self.log
        installer = native_gsf.stage_packaged
        with patch('gfg_plugin.native_gsf.stage_packaged', side_effect=lambda home: installer(home, package)):
            self.assertTrue(svc.prepare_native_gsf()['success'])
            self.assertEqual((self.runtime / native_gsf.MARKER).read_text(), 'off\n')
            status = svc.native_gsf_status()
            self.assertTrue(status['launcher_ready'])
            self.assertEqual(status['component_version'], '0.0.0-fg3-internal.7')
            result = subprocess.run([str(self.home / '.local/bin/gfg-native'), '/usr/bin/env'],
                                    env=dict(os.environ, HOME=str(self.home)), capture_output=True, text=True, check=True)
            self.assertIn('DISABLE_GFG_NATIVE_FG=1\n', result.stdout)
            self.assertNotIn('GFG_NATIVE_GPU_BRIDGE=1\n', result.stdout)
            native_gsf.set_mode(self.runtime, '3', self.log)
            self.assertTrue(svc.prepare_native_gsf()['success'])
            self.assertEqual(native_gsf.requested(self.runtime), '3')

    def test_startup_stages_native_even_when_legacy_renderer_is_unsupported(self):
        from gfg_plugin.plugin import Plugin
        plugin = Plugin.__new__(Plugin)
        calls = []
        plugin.governor_service = SimpleNamespace(prepare_native_gsf=lambda:
            calls.append('stage-native') or {'success': True})
        plugin.installation_service = SimpleNamespace(current_package_host_compatibility=lambda:
            calls.append('legacy-check') or ('unsupported', False, 'legacy-incompatible'))
        plugin.configuration_service = SimpleNamespace(enforce_unsupported_host_passthrough_if_needed=lambda: False)
        plugin.flatpak_service = SimpleNamespace(disable_incompatible_host_overrides=lambda: {'success': True})
        asyncio.run(plugin._main())
        self.assertEqual(calls, ['stage-native', 'legacy-check'])

    def test_status_requires_live_pid_and_matching_start_time(self):
        folder = self.home / '.local/state/gfg-native/status'
        folder.mkdir(parents=True)
        stat = Path('/proc/self/stat').read_text()
        start = int(stat[stat.rfind(')')+2:].split()[19])
        record = dict(schema=1, engine='gfg-native-gsf', pid=os.getpid(), generation=1,
                      process_start_ticks=start, updated_unix_ms=int(time.time()*1000),
                      real_wsi_accepted=3, generated_wsi_accepted=2)
        path = folder / 'context.json';path.write_text(json.dumps(record))
        status = native_gsf.status(self.runtime, self.home)
        self.assertEqual(len(status['contexts']), 1)
        self.assertIsNone(status['physical_displayed_fps'])
        self.assertEqual(status['hardware_acceptance'], 'NOT TESTED')
        record['process_start_ticks'] += 1;path.write_text(json.dumps(record))
        self.assertEqual(native_gsf.status(self.runtime, self.home)['contexts'], [])
        record['process_start_ticks'] = start;record['updated_unix_ms'] = 1
        path.write_text(json.dumps(record))
        self.assertEqual(native_gsf.status(self.runtime, self.home)['contexts'], [])

if __name__ == '__main__':
    unittest.main()
