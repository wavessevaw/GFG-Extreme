import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.contracts import Bottleneck as B, Perception
from gfg_plugin.autopilot.coordinator import plan
from gfg_plugin.autopilot.experiments import TrialResult
from gfg_plugin.autopilot.memory import AutopilotMemory
from gfg_plugin.autopilot.optimizer import Candidate
from gfg_plugin.autopilot.policy import Action


GAME = {"app_id": "10", "panel": "internal", "hz": 90, "gpu": "deck", "backend": "gfg",
        "knob": "power_cap", "value": 15, "context": "scene"}
OTHER = {**GAME, "app_id": "11", "knob": "flow_scale", "value": 0.7}


def learned():
    window = {"real": 48, "output": 90}
    return TrialResult("ACCEPT", window, window, window, (5, 5, 5), 0.9, {}, "", learned=True)


def point(knob, value, real=49):
    return Candidate(knob, value, real, 90, 1, 12, 0.2, True, (), "window")


class MemoryTests(unittest.TestCase):
    def test_inconclusive_stale_and_unlearned_are_not_stored(self):
        with TemporaryDirectory() as directory:
            store = AutopilotMemory(Path(directory) / "memory.json")
            vague = TrialResult("INCONCLUSIVE", None, None, None, (), None, {}, "drift", learned=False)
            self.assertEqual(store.record(GAME, vague, 10), "not-learned")
            self.assertEqual(store.record(GAME, learned(), 10, stale=True), "stale")
            unlearned = TrialResult("ACCEPT", {"real": 1}, {"real": 1}, {"real": 1}, (1,), None, {}, "", learned=False)
            self.assertEqual(store.record(GAME, unlearned, 10), "not-learned")
            self.assertEqual(store.warm(GAME), ())
            self.assertFalse((Path(directory) / "memory.json").exists())

    def test_backoff_expires_and_does_not_cross_context(self):
        with TemporaryDirectory() as directory:
            store = AutopilotMemory(Path(directory) / "memory.json")
            store.block(GAME, now=10, seconds=30)
            self.assertEqual(store.view(GAME, 20, "scene").blocked, (("power_cap", 15),))
            self.assertEqual(store.view(GAME, 20, "menu").blocked, ())
            self.assertEqual(store.view(GAME, 50, "scene").blocked, ())

    def test_warm_start_is_not_verified_until_fresh_telemetry(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            store = AutopilotMemory(path)
            self.assertIsNone(store.record(GAME, learned(), 10))
            self.assertFalse(store.warm(GAME)[0]["verified"])
            self.assertFalse(store.confirm(GAME, "power_cap", 15, fresh=False))
            self.assertTrue(store.confirm(GAME, "power_cap", 15, fresh=True))
            self.assertTrue(store.verified_now(GAME, "power_cap", 15))
            reloaded = AutopilotMemory(path)
            self.assertFalse(reloaded.warm(GAME)[0]["verified"])
            self.assertFalse(reloaded.verified_now(GAME, "power_cap", 15))

    def test_backed_off_candidate_is_not_tried_again(self):
        with TemporaryDirectory() as directory:
            store = AutopilotMemory(Path(directory) / "memory.json")
            store.block(GAME, now=0, seconds=100)
            current = point("current", 0, real=45)
            decision = plan(Perception(B.GPU_LIMITED, (), 0.7, (), (), "ok", 0, 10, "game", False),
                            (point("power_cap", 15),), current, now=10, capabilities=("power_cap",),
                            memory=store.view(GAME, 10, "scene"))
            self.assertEqual(decision.action, Action.HOLD)
            self.assertIn(("power_cap", 15, "backed-off"), decision.rejected)

    def test_reset_removes_one_game_only(self):
        with TemporaryDirectory() as directory:
            store = AutopilotMemory(Path(directory) / "memory.json")
            store.record(GAME, learned(), 10)
            store.record(OTHER, learned(), 10)
            store.reset(GAME)
            self.assertEqual(store.warm(GAME), ())
            self.assertEqual(len(store.warm(OTHER)), 1)
