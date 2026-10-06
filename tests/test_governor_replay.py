import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gfg_governor_replay", ROOT / "tools" / "gfg_governor_replay.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GovernorReplayTests(unittest.TestCase):
    def test_stable_45x2_replay(self):
        result = mod.run(ROOT / "tests/replay/stable_45x2.jsonl")
        self.assertEqual(result["decision"]["point"]["key"], "45x2")
        self.assertTrue(result["decision"]["proven"])

    def test_stable_native_replay(self):
        result = mod.run(ROOT / "tests/replay/stable_native_90.jsonl")
        self.assertEqual(result["decision"]["point"]["key"], "native90")

    def test_dock_replay(self):
        result = mod.run(ROOT / "tests/replay/stable_dock_60.jsonl", external=True)
        self.assertEqual(result["decision"]["point"]["key"], "30x2")
