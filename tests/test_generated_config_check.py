import copy, importlib.util, sys, types, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "py_modules"))
spec = importlib.util.spec_from_file_location("check_generated_config", ROOT / "scripts" / "check_generated_config.py")
checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
import shared_config  # noqa: E402
from gfg_plugin import config_schema_generated as generated  # noqa: E402


class GeneratedConfigCheckTests(unittest.TestCase):
    def test_repository_is_consistent(self):
        self.assertEqual(checker.check(shared_config.CONFIG_SCHEMA_DEF, generated), [])
        self.assertEqual(checker.main(), 0)

    def test_added_schema_field_is_detected(self):
        schema = copy.deepcopy(shared_config.CONFIG_SCHEMA_DEF)
        schema["brand_new_field"] = {"fieldType": shared_config.ConfigFieldType.BOOLEAN, "default": False, "description": "x", "location": "toml"}
        problems = checker.check(schema, generated)
        self.assertTrue(any("brand_new_field" in p for p in problems))

    def test_type_drift_is_detected(self):
        schema = copy.deepcopy(shared_config.CONFIG_SCHEMA_DEF)
        schema["multiplier"]["fieldType"] = shared_config.ConfigFieldType.STRING
        self.assertTrue(any("multiplier" in p for p in checker.check(schema, generated)))

    def test_removed_schema_field_is_detected(self):
        schema = copy.deepcopy(shared_config.CONFIG_SCHEMA_DEF)
        del schema["gpu"]
        self.assertTrue(any("unknown field 'gpu'" in p for p in checker.check(schema, generated)))


if __name__ == "__main__":
    unittest.main()
