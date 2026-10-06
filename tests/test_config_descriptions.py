import logging, sys, tempfile, types, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
decky = types.ModuleType("decky"); decky.logger = logging.getLogger("t"); decky.DECKY_USER_HOME = tempfile.mkdtemp()
sys.modules.setdefault("decky", decky)
from gfg_plugin.config_schema import ConfigurationManager as M  # noqa: E402


class DescriptionTests(unittest.TestCase):
    def test_every_field_has_a_description(self):
        desc = M.get_field_descriptions()
        self.assertEqual(set(desc), set(M.get_field_names()))
        self.assertTrue(all(isinstance(v, str) and v for v in desc.values()))


if __name__ == "__main__":
    unittest.main()
