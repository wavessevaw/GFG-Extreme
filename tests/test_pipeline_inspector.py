"""Pipeline Inspector Saved -> Effective -> Actual verification."""
import json
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-inspector-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.pipeline_inspector import PipelineInspectorService, profile_manifest_key  # noqa: E402


def stat_text(pid: int, ppid: int, starttime: int) -> str:
    tail = ["S", str(ppid)] + ["0"] * 18 + [str(starttime)] + ["0"] * 20
    # tail[0]=field3, tail[19]=field22; adjust explicitly.
    tail[19] = str(starttime)
    return f"{pid} (game) " + " ".join(tail) + "\n"


class PipelineInspectorTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.proc = Path(tempfile.mkdtemp(prefix="gfg-proc-"))
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("game", "mako")["success"])
        self.inspector = PipelineInspectorService(self.svc, proc_root=self.proc)

    def tearDown(self):
        shutil.rmtree(self.proc, ignore_errors=True)

    def write_process(self, pid=1234, ppid=1, start=777, maps="", app_id="42"):
        d = self.proc / str(pid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "stat").write_text(stat_text(pid, ppid, start), encoding="utf-8")
        (d / "comm").write_text("game.exe\n", encoding="utf-8")
        (d / "maps").write_text(maps, encoding="utf-8")
        (d / "environ").write_bytes(f"SteamAppId={app_id}\0".encode())

    def write_manifest(self, pid=1234, start=777, app_id="42"):
        path = self.svc.runtime_state_dir / "launches" / f"{profile_manifest_key('game')}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema": 1, "timestamp": 1, "pid": pid, "starttime": start,
            "app_id": app_id, "profile": "game", "saved": {}, "effective": {}
        }), encoding="utf-8")

    def test_gfg_renderer_mapping_is_actual_truth(self):
        self.write_process(maps="7f00-7f01 r-xp 0 00:00 0 /home/deck/.local/lib/libmako-render.so\n")
        self.write_manifest()
        result = self.inspector.get_status("game")
        self.assertTrue(result["success"])
        self.assertTrue(result["actual"]["renderer_loaded"])
        self.assertEqual(result["actual"]["state"], "running")

    def test_pid_reuse_is_rejected_by_starttime(self):
        self.write_process(start=999, maps="/home/deck/.local/lib/libmako-render.so\n", app_id="")
        self.write_manifest(start=777, app_id="")
        result = self.inspector.get_status("game")
        self.assertFalse(result["actual"].get("launch_pid_valid", False))
        self.assertEqual(result["actual"]["state"], "ended")
        self.assertTrue(any("PID was reused" in reason for reason in result["mismatch_reasons"]))

    def test_double_fg_warning_requires_actual_proxy_mapping(self):
        self.write_process(maps=(
            "/home/deck/.local/lib/libmako-render.so\n"
            "/games/Test/dxgi.dll\n"
        ))
        self.write_manifest()
        result = self.inspector.get_status("game")
        self.assertTrue(result["double_fg_warning"])
        self.assertTrue(result["actual"]["optiscaler_proxy_loaded"])

    def test_optiscaler_reports_missing_actual_proxy(self):
        self.svc.update_profile_config_fields("game", {"fg_backend": "optiscaler"})
        self.write_process(maps="", app_id="42")
        self.write_manifest()
        result = self.inspector.get_status("game")
        self.assertTrue(any("OptiScaler was requested" in reason for reason in result["mismatch_reasons"]))

    def test_generated_wrapper_writes_launch_manifest(self):
        self.svc.set_current_profile("game")
        wrapper = Path(self.svc.mako_script_path)
        env = {"PATH": os.environ["PATH"], "HOME": HOME, "MAKO_PROFILE": "game", "SteamAppId": "4242"}
        __import__("subprocess").run([str(wrapper), "true"], env=env, check=True)
        path = self.svc.runtime_state_dir / "launches" / f"{profile_manifest_key('game')}.json"
        self.assertTrue(path.is_file())
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["profile"], "game")
        self.assertEqual(manifest["app_id"], "4242")
        self.assertGreater(manifest["pid"], 0)
        self.assertGreaterEqual(manifest["starttime"], 0)
        self.assertEqual(manifest["saved"]["fg_backend"], "gfg")

    def test_saved_effective_reason_names_external_backend(self):
        self.svc.update_profile_config_fields(
            "game", {"fg_backend": "native", "frame_generation_enabled": True, "automatic_dock_mode": True}
        )
        result = self.inspector.get_status("game")
        reasons = " ".join(result["mismatch_reasons"])
        self.assertIn("backend=native", reasons)
        self.assertIn("Automatic Dock", reasons)


if __name__ == "__main__":
    unittest.main()
