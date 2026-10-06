import asyncio
import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.activity_log import ActivityLog, journal_ui_calls  # noqa: E402


class ActivityLogTests(unittest.TestCase):
    def test_ui_actions_are_journaled_and_polls_are_not(self):
        with tempfile.TemporaryDirectory() as temp:
            log = ActivityLog(Path(temp) / "activity.jsonl", clock=lambda: 5.0)

            class Fake:
                activity = log
                async def set_governor_enabled(self, profile_name, enabled):
                    return {"success": True, "enabled": enabled}
                async def get_governor_status(self):
                    return {"success": True}
                async def delete_profile(self, name):
                    raise RuntimeError("boom")

            journal_ui_calls(Fake, lambda p: p.activity)
            plugin = Fake()
            asyncio.run(plugin.set_governor_enabled("mako", True))
            asyncio.run(plugin.get_governor_status())
            with self.assertRaises(RuntimeError):
                asyncio.run(plugin.delete_profile(name="x"))
            lines = [json.loads(l) for l in (Path(temp) / "activity.jsonl").read_text().splitlines()]
            self.assertEqual([l["kind"] for l in lines], ["set_governor_enabled", "delete_profile"])
            self.assertEqual(lines[0]["args"], {"profile_name": "mako", "enabled": True})
            self.assertTrue(lines[0]["success"])
            self.assertEqual(lines[1]["error"], "boom")
            self.assertEqual(len(log.since(5.0)), 2)
            self.assertEqual(log.since(6.0), [])

    def test_governor_journals_state_changes_and_tdp_writes(self):
        from test_governor_service import GovernorServiceTests
        with tempfile.TemporaryDirectory() as temp:
            svc = GovernorServiceTests.make_service(None, Path(temp))
            log = ActivityLog(Path(temp) / "activity.jsonl")
            svc.activity = log
            svc.set_enabled("Game", True)
            asyncio.run(svc._iteration())
            asyncio.run(svc._iteration())
            states = [json.loads(l) for l in log.since(0)]
            self.assertEqual([s["kind"] for s in states], ["state"])
            self.assertEqual(states[0]["state"], "PAUSED")
            svc._journal_power("tdp-write", requested_w=12.0, success=False, error="Permission denied")
            last = json.loads(log.since(0)[-1])
            self.assertEqual((last["kind"], last["error"]), ("tdp-write", "Permission denied"))


if __name__ == "__main__":
    unittest.main()
