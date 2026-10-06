import asyncio, json, sys, tempfile, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.session_recorder import SessionRecorder, compact_status, desktop_dir  # noqa: E402


class RecorderTests(unittest.TestCase):
    def make(self, home):
        cfg = home / "cfg"; (cfg / "hud").mkdir(parents=True)
        (cfg / "hud" / "active.conf").write_text("fps\n")
        diag = cfg / "present-diagnostics.log"; diag.write_text("old line\n")
        (cfg / "events.jsonl").write_text("")
        wrapper = home / "gfg"; wrapper.write_text("hud/active.conf mako_governor_overlay")
        status = {"state": "LOCKED", "enabled": True,
                  "telemetry": {"summary": {"real": {"median": 45}, "output": {"median": 90}, "multiplier": {"median": 2}}, "snapshot": {"available": True}}}
        rec = SessionRecorder(user_home=home, config_dir=cfg, runtime_state_dir=cfg / "rt", wrapper_path=wrapper,
                              status_provider=lambda: status, events_path=cfg / "events.jsonl",
                              diagnostics_paths=[diag], saved_config_path=cfg / "none.json", layer_files={})
        return rec, diag

    def test_compact_status_reads_service_shape(self):
        rec = compact_status({"telemetry": {"summary": {"real": {"median": 45}, "output": {"median": 90}}}})
        self.assertEqual((rec["real"], rec["output"]), (45, 90))

    def test_record_and_export_to_desktop(self):
        async def scenario(rec, diag):
            self.assertTrue((await rec.start("game"))["success"])
            diag.write_text("old line\nnew renderer line\n")
            await asyncio.sleep(0.2)
            return await rec.stop()
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rec, diag = self.make(home)
            result = asyncio.run(scenario(rec, diag))
            self.assertTrue(result["success"], result)
            out = Path(result["file"])
            self.assertEqual(out.parent, desktop_dir(home))
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
                self.assertIn("timeline.jsonl", names)
                self.assertIn("self_test.json", names)
                self.assertEqual(z.read("diagnostics-present-diagnostics.log"), b"new renderer line\n")
                self.assertIn(b'"real": 45', z.read("timeline.jsonl"))
                checks = {c["check"]: c["ok"] for c in json.loads(z.read("self_test.json"))}
                self.assertTrue(checks["overlay config published (active.conf)"])
            self.assertFalse(rec.status()["recording"])

    def test_stop_without_start_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            rec, _ = self.make(Path(temp))
            self.assertFalse(asyncio.run(rec.stop())["success"])


if __name__ == "__main__":
    unittest.main()
