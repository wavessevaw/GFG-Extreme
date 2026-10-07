"""1.0.10: removing GFG's Flatpak overrides must not leave negations behind."""
import logging
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = tempfile.mkdtemp(prefix="gfg-flatpak-home-")
sys.modules.setdefault("decky", decky)

from gfg_plugin.flatpak_service import FlatpakService  # noqa: E402


class OverrideCleanupTests(unittest.TestCase):
    def test_only_gfg_negations_are_dropped(self):
        with tempfile.TemporaryDirectory() as home:
            svc = FlatpakService()
            svc.user_home = Path(home)
            path = Path(home) / ".local/share/flatpak/overrides/org.example.App"
            path.parent.mkdir(parents=True)
            path.write_text(
                "[Context]\n"
                "filesystems=!/gfg/dll;!/gfg/conf.toml:ro;/home/deck/Games;!/user/own;\n"
                "unset-environment=VK_ADD_IMPLICIT_LAYER_PATH;MY_OWN;\n\n"
                "[Environment]\n"
                "VK_ADD_IMPLICIT_LAYER_PATH=\n"
                "MANGOHUD=1\n"
            )
            svc._clean_override_negations("org.example.App", ["/gfg/dll", "/gfg/conf.toml"],
                                          ["VK_ADD_IMPLICIT_LAYER_PATH"])
            text = path.read_text()
            self.assertIn("filesystems=/home/deck/Games;!/user/own;", text)
            self.assertIn("unset-environment=MY_OWN;", text)
            self.assertNotIn("VK_ADD_IMPLICIT_LAYER_PATH", text)
            self.assertIn("MANGOHUD=1", text)

    def test_missing_override_file_is_fine(self):
        svc = FlatpakService()
        svc.user_home = Path(tempfile.mkdtemp())
        svc._clean_override_negations("org.none", ["/x"], ["Y"])


if __name__ == "__main__":
    unittest.main()
