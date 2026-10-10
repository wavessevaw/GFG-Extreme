import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.memory import AutopilotMemory


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MigrationTests(unittest.TestCase):
    def test_schema_zero_drops_unproven_lessons_and_leaves_other_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            models = root / "gfg-game-models.json"
            settings = root / "settings.json"
            models.write_text('{"extreme": true, "mode": "extreme"}')
            settings.write_text('{"mode": "extreme", "flow_scale": 0.8}')
            before = (digest(models), digest(settings))
            memory = root / "gfg-autopilot-memory.json"
            memory.write_text(json.dumps({
                "schema": 0,
                "games": {
                    "game-a": {"lessons": [
                        {"knob": "power_cap", "value": 15, "verdict": "ACCEPT", "learned": True},
                        {"knob": "flow_scale", "value": 0.5, "verdict": "INCONCLUSIVE", "learned": False},
                    ]},
                    "game-b": "corrupt",
                },
            }))
            store = AutopilotMemory(memory)
            body = json.loads(memory.read_text())
            self.assertEqual(body["schema"], 1)
            lessons = body["games"]["game-a"]["lessons"]
            self.assertEqual(len(lessons), 1)
            self.assertFalse(lessons[0]["verified"])
            self.assertNotIn("game-b", body["games"])
            self.assertEqual((digest(models), digest(settings)), before)
            self.assertEqual(store.warm({"app_id": "missing"}), ())

    def test_corrupt_store_does_not_raise_or_touch_extreme_settings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text('{"mode": "extreme"}')
            before = digest(settings)
            memory = root / "gfg-autopilot-memory.json"
            memory.write_text("{")
            store = AutopilotMemory(memory)
            self.assertEqual(store.games, {})
            self.assertEqual(digest(settings), before)
            self.assertEqual(memory.read_text(), "{")
