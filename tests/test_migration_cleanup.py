import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import Clock  # noqa: F401

from gfg_plugin import coexist, legacy_cleanup, migration, settings


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class FakeTools:
    def __init__(self):
        self.calls = []

    def run(self, tool, *args):
        self.calls.append((tool, *args))
        if tool == "flatpak" and args[0] == "list":
            return True, "org.freedesktop.Platform.VulkanLayer.makorender/x86_64/24.08\norg.other/x86_64/1"
        return True, ""


class MigrationTest(unittest.TestCase):
    def make_legacy(self, home):
        leg = home / ".config/mako-render"
        write(leg / "conf.toml", 'version = 1\n\n[[profile]]\nname = "mako"\nmultiplier = 3\nadaptive = false\n\n'
                                 '[[profile]]\nname = "elden"\nadaptive = true\n\n[[profile]]\nname = "proc"\nmultiplier = 2\n')
        write(leg / "profile-wrapper-settings.json", json.dumps({"version": 1, "profiles": {
            "mako": {"external_vulkan_layer": "vkbasalt", "vkbasalt_shader": "vibrance", "vkbasalt_sharpening": "cas",
                     "vkbasalt_sharpness": 0.4}, "elden": {"fg_backend": "gfg"}, "proc": {}}}))
        write(leg / "profile-metadata.json", json.dumps({"version": 1, "profiles": {
            "mako": {"display_name": "stable"}, "elden": {"display_name": "Elden Ring", "steam_app_id": "1245620"},
            "proc": {"display_name": "Some exe"}}}))
        write(leg / "gfg-governor.json", json.dumps({"schema": 1, "profiles": {
            "mako": {"enabled": True, "mode": "budget", "autopilot_preference": "battery",
                     "hud": {"enabled": False, "position": "top-right"}},
            "elden": {"enabled": True, "mode": "extreme"}}}))
        write(leg / "gfg-game-models.json", "{}")
        return leg

    def test_convert_backup_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            self.make_legacy(home)
            write(home / ".local/bin/gfg", "#!/bin/sh\nmako stuff\n")
            data = home / ".config/gfg-extreme"
            s = settings.Settings(data / "settings.json")
            m = migration.Migration(home, data, clock=lambda: 1_700_000_000)
            self.assertTrue(m.needed(s))
            report = m.run(s)
            p = s.data["profiles"]
            self.assertEqual((p["default"]["fg"], p["default"]["objective"]), ("x3", "battery"))
            self.assertEqual(p["default"]["filters"]["sharpen"], "cas")
            self.assertEqual((p["app:1245620"]["fg"], p["app:1245620"]["objective"], p["app:1245620"]["name"]),
                             ("auto", "autopilot", "Elden Ring"))
            self.assertEqual(s.data["autopilot"]["preference"], "battery")
            self.assertEqual(s.data["hud"], {"enabled": False, "position": "top-right", "detail": "standard"})
            self.assertEqual([x["name"] for x in report["skipped"]], ["Some exe"])
            self.assertTrue(any("Learned TDP" in n for n in report["notes"]))
            with zipfile.ZipFile(report["backup"]) as z:
                names = z.namelist()
            self.assertIn("config/mako-render/conf.toml", names)
            self.assertIn(".local/bin/gfg", names)
            self.assertTrue((home / ".config/mako-render/conf.toml").exists(), "2.x settings stay for a rollback")
            self.assertFalse(migration.Migration(home, data).needed(settings.Settings(data / "settings.json")))

    def test_fallback_toml(self):
        parsed = migration._parse_toml('[[profile]]\nname = "a"\nmultiplier = 3\nadaptive = true\n')
        self.assertEqual(parsed["profile"][0]["multiplier"], 3)


class CleanupTest(unittest.TestCase):
    def test_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "home"
            sysroot = Path(d) / "sys"
            write(home / ".local/share/mako-render/lib/libmako-render.so", "x")
            write(home / ".local/share/vulkan/implicit_layer.d/VkLayer_MAKO_render.json", "{}")
            write(home / ".local/share/vulkan/implicit_layer.d/VkLayer_LSFGVK_frame_generation.json", "{}")
            write(home / ".local/share/vulkan/implicit_layer.d/MangoHud.json", "{}")
            write(home / ".local/bin/gfg", "#!/bin/sh\nold\n")
            write(home / ".local/share/flatpak/overrides/com.game", "[Environment]\nMAKO_CONFIG=/x\nKEEP=1\n")
            cpu = sysroot / "sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
            write(cpu, "1600000\n")
            write(home / ".config/mako-render/runtime-state/cpu-cap.json", json.dumps(
                {"/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq": {"initial": 3500000, "written": 1600000}}))
            tools = FakeTools()
            c = legacy_cleanup.LegacyCleanup(home, tools=tools, sys_root=sysroot)
            self.assertFalse(c.pending()["clean"])
            self.assertTrue(c.pending()["user_lsfg_layer"])
            result = c.run()
            self.assertTrue(result["ok"], result)
            self.assertEqual(cpu.read_text().strip(), "3500000")
            self.assertFalse((home / ".local/share/mako-render").exists())
            self.assertFalse((home / ".local/share/vulkan/implicit_layer.d/VkLayer_MAKO_render.json").exists())
            self.assertTrue((home / ".local/share/vulkan/implicit_layer.d/MangoHud.json").exists())
            self.assertTrue((home / ".local/share/vulkan/implicit_layer.d/VkLayer_LSFGVK_frame_generation.json").exists())
            self.assertEqual((home / ".local/bin/gfg").read_text(), legacy_cleanup.SHIM)
            self.assertTrue(os.access(home / ".local/bin/gfg", os.X_OK))
            self.assertEqual((home / ".local/share/flatpak/overrides/com.game").read_text().strip(), "[Environment]\nKEEP=1")
            self.assertIn(("flatpak", "uninstall", "--user", "--noninteractive", "-y",
                           "org.freedesktop.Platform.VulkanLayer.makorender/x86_64/24.08"), tools.calls)
            self.assertTrue(c.pending()["clean"])

    def test_cpu_changed_by_player_stays(self):
        with tempfile.TemporaryDirectory() as d:
            home, sysroot = Path(d) / "home", Path(d) / "sys"
            cpu = sysroot / "sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
            write(cpu, "2800000\n")
            write(home / ".config/mako-render/runtime-state/cpu-cap.json", json.dumps(
                {"/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq": {"initial": 3500000, "written": 1600000}}))
            legacy_cleanup.LegacyCleanup(home, tools=FakeTools(), sys_root=sysroot).recover_system_state()
            self.assertEqual(cpu.read_text().strip(), "2800000")

    def test_shim_runs_the_game(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            shim = Path(d) / "gfg"
            shim.write_text(legacy_cleanup.SHIM)
            shim.chmod(0o755)
            out = subprocess.run([str(shim), "echo", "game started"], capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), "game started")


class CoexistTest(unittest.TestCase):
    def test_find_and_take_over(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "home"
            write(home / "homebrew/plugins/KEDAVRA/plugin.json", json.dumps({"name": "GSF Kedavra"}))
            write(home / "homebrew/plugins/KEDAVRA/package.json", json.dumps({"version": "1.1.2"}))
            write(home / "homebrew/plugins/Other/plugin.json", json.dumps({"name": "Other"}))
            write(home / ".local/share/kedavra/settings.json", json.dumps({"hud": True, "base_fps": 30}))
            c = coexist.Coexistence(home, var_root=Path(d) / "var", version="3.0.0")
            st = c.status()
            self.assertEqual([p["version"] for p in st["standalone"]], ["1.1.2"])
            self.assertTrue(st["standalone_hud"])
            r = c.take_over()
            self.assertFalse(json.loads((home / ".local/share/kedavra/settings.json").read_text())["hud"])
            self.assertTrue(r["taken_over"])
            self.assertEqual(len(list((home / ".local/share/kedavra").glob("settings.before-gfg-*.json"))), 1)
