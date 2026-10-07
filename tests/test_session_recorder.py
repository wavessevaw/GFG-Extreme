import asyncio, json, sys, tempfile, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.session_recorder import (  # noqa: E402
    SessionRecorder, compact_status, desktop_dir, probe_game_processes, probe_power_sensors)


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
        self.assertIsNone(rec["budget"])
        rec = compact_status({"budget": {"phase": "locked", "thermal": "hot", "thermal_deferred": True, "rejected": []}})
        self.assertEqual((rec["budget"]["phase"], rec["budget"]["thermal_deferred"]), ("locked", True))
        self.assertNotIn("rejected", rec["budget"])

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
                self.assertIn("summary.txt", names)
                self.assertIn(b"GFG Extreme log summary", z.read("summary.txt"))
                self.assertIn("timeline.jsonl", names)
                self.assertIn("self_test.json", names)
                self.assertEqual(z.read("diagnostics-present-diagnostics.log"), b"new renderer line\n")
                self.assertIn(b'"real": 45', z.read("timeline.jsonl"))
                checks = {c["check"]: c["ok"] for c in json.loads(z.read("self_test.json"))}
                self.assertTrue(checks["overlay config published (active.conf)"])
            self.assertFalse(rec.status()["recording"])

    def test_bundle_has_launch_manifest_and_diagnostics_checks(self):
        async def scenario(rec):
            await rec.start("game")
            await asyncio.sleep(0.1)
            return await rec.stop()
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rec, diag = self.make(home)
            launches = home / "cfg" / "rt" / "launches"; launches.mkdir(parents=True)
            (launches / "abc.json").write_text('{"schema":1}\n')
            diag.with_name(diag.name + ".1").symlink_to(diag)
            result = asyncio.run(scenario(rec))
            with zipfile.ZipFile(result["file"]) as z:
                self.assertIn("launch-manifests/abc.json", z.namelist())
                checks = {c["check"]: c for c in json.loads(z.read("self_test.json"))}
            self.assertFalse(checks["Governor diagnostics marker present"]["ok"])
            rotation = checks["diagnostics log rotation writable by wrapper"]
            self.assertFalse(rotation["ok"])
            self.assertIn("present-diagnostics.log.1", rotation["detail"])

    def test_probe_finds_wrapped_vulkan_game_and_mangohud(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = Path(temp)
            def fake(pid, env, maps):
                d = proc / str(pid); d.mkdir()
                (d / "environ").write_bytes(b"\0".join(f"{k}={v}".encode() for k, v in env.items()) + b"\0")
                (d / "maps").write_text(maps)
                (d / "comm").write_text("game.exe\n")
            vk = "7f00 r-xp 0 0:0 1 /usr/lib/libvulkan.so.1\n"
            fake(10, {"MAKO_CONFIG": "/c.toml", "MANGOHUD_CONFIGFILE": "/a.conf", "HOME": "/h"},
                 vk + "7f01 r-xp 0 0:0 2 /usr/lib/mangohud/libMangoHud.so\n")
            fake(11, {"MAKO_CONFIG": "/c.toml"}, vk)
            fake(12, {"HOME": "/h"}, vk)  # not launched through the wrapper
            fake(13, {"MAKO_CONFIG": "/c.toml"}, "")  # wrapper shell, no Vulkan
            found = probe_game_processes(proc)
            self.assertEqual([p["pid"] for p in found], [10, 11])
            self.assertTrue(found[0]["mangohud_loaded"])
            self.assertFalse(found[1]["mangohud_loaded"])
            self.assertEqual(found[0]["env"], {"MAKO_CONFIG": "/c.toml", "MANGOHUD_CONFIGFILE": "/a.conf"})

    def test_bundle_has_game_processes_and_launch_manifests(self):
        async def scenario(rec):
            await rec.start("game")
            await asyncio.sleep(0.2)
            return await rec.stop()
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rec, _ = self.make(home)
            rec.process_probe = lambda: [{"pid": 1, "mangohud_loaded": False}]
            rec.hud_enabled = lambda profile: profile == "game"
            launches = home / "cfg" / "rt" / "launches"; launches.mkdir(parents=True)
            (launches / "abc.json").write_text("{}")
            result = asyncio.run(scenario(rec))
            with zipfile.ZipFile(result["file"]) as z:
                self.assertEqual(json.loads(z.read("game-processes.json")), [{"pid": 1, "mangohud_loaded": False}])
                self.assertIn("launch-manifests/abc.json", z.namelist())
                checks = {c["check"]: c["ok"] for c in json.loads(z.read("self_test.json"))}
                self.assertTrue(checks["in-game overlay switched on for this profile"])
                self.assertIn("host MangoHud Vulkan layer present", checks)

    def test_power_sensors_probe_and_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "hwmon"
            h = root / "hwmon3"; h.mkdir(parents=True)
            (h / "name").write_text("amdgpu\n")
            (h / "power1_cap").write_text("18000000\n")
            (h / "power1_average").write_text("15100000\n")
            (root / "hwmon0").mkdir()  # no power files: skipped
            found = probe_power_sensors(root)
            self.assertEqual(len(found), 1)
            self.assertEqual((found[0]["name"], found[0]["power1_cap"], found[0]["power1_average"]),
                             ("amdgpu", "18000000", "15100000"))
            self.assertEqual(compact_status({"power": {"draw_w": 15.1, "observed_fast_w": 21.0}})["apu_w"], 15.1)

            async def scenario(rec):
                await rec.start("game")
                (h / "power1_cap").write_text("20000000\n")  # someone rewrote the cap
                return await rec.stop()
            home = Path(temp) / "home"; home.mkdir()
            rec, _ = self.make(home)
            rec.power_probe = lambda: probe_power_sensors(root)
            result = asyncio.run(scenario(rec))
            with zipfile.ZipFile(result["file"]) as z:
                sensors = json.loads(z.read("power-sensors.json"))
            self.assertEqual(sensors["start"][0]["power1_cap"], "18000000")
            self.assertEqual(sensors["end"][0]["power1_cap"], "20000000")

    def test_check_setup_gives_advice_for_every_failed_check(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rec, _ = self.make(home)
            (home / "cfg" / "hud" / "active.conf").unlink()
            result = rec.check_setup("game")
            self.assertTrue(result["success"])
            self.assertEqual(result["total"], len(result["checks"]))
            failed = {c["check"]: c for c in result["checks"] if not c["ok"]}
            self.assertIn("overlay config published (active.conf)", failed)
            for check in failed.values():
                self.assertTrue(check["advice"], check["check"])
            self.assertEqual(result["failed"], len(failed))

    def test_stop_without_start_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            rec, _ = self.make(Path(temp))
            self.assertFalse(asyncio.run(rec.stop())["success"])


if __name__ == "__main__":
    unittest.main()
