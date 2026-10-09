"""Resource leases must restore identity-scoped changes without fighting other tools."""
import os
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))

from gfg_plugin.extreme_resources import ProcessResources, FanResources, managed_process


def proc_stat(path, ticks):
    path.mkdir(parents=True, exist_ok=True)
    (path / "stat").write_text("20 (game with spaces) S " + "0 " * 18 + str(ticks) + "\n")


class ProcessResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        self.pid, self.ticks = 20, 400
        game = self.proc / "20"
        proc_stat(game, self.ticks)
        (game / "environ").write_bytes(b"GFG_MANAGED_GAME=1\0SteamAppId=1\0")
        (game / "oom_score_adj").write_text("25\n")
        proc_stat(game / "task" / "20", 400)
        self.values = {20: 2}
        self.now = 0
        self.marker = self.root / "undo.json"
        self.resource = self.make()

    def make(self):
        return ProcessResources(os.getuid(), proc=self.proc,
            get_nice=lambda tid: self.values[tid],
            set_nice=lambda tid, value: self.values.__setitem__(tid, value),
            clock=lambda: self.now, marker=self.marker)

    def test_requires_exact_managed_marker_and_process_identity(self):
        self.assertTrue(managed_process(self.proc, 20, 400, os.getuid()))
        self.assertFalse(managed_process(self.proc, 20, 401, os.getuid()))
        (self.proc / "20" / "environ").write_bytes(b"GFG_MANAGED_GAME=10\0")
        with self.assertRaises(OSError):
            self.resource.apply(20, 400, True, True)
        self.assertEqual(self.values[20], 2)

    def test_lease_expiry_restores_thread_priority_and_oom_preference(self):
        self.resource.apply(20, 400, True, True)
        self.assertEqual(self.values[20], -5)
        self.assertEqual((self.proc / "20" / "oom_score_adj").read_text().strip(), "-100")
        self.now = 21
        self.resource.expire()
        self.assertEqual(self.values[20], 2)
        self.assertEqual((self.proc / "20" / "oom_score_adj").read_text().strip(), "25")
        self.assertFalse(self.resource.deadlines)

    def test_new_thread_inherited_priority_is_restored(self):
        self.resource.apply(20, 400, True, False)
        proc_stat(self.proc / "20" / "task" / "21", 500)
        self.values[21] = -5
        self.resource.apply(20, 400, True, False)
        self.resource.restore((20, 400))
        self.assertEqual(self.values, {20: 2, 21: 2})

    def test_external_changes_are_preserved(self):
        self.resource.apply(20, 400, True, True)
        self.values[20] = 7
        (self.proc / "20" / "oom_score_adj").write_text("100")
        self.resource.restore((20, 400))
        self.assertEqual(self.values[20], 7)
        self.assertEqual((self.proc / "20" / "oom_score_adj").read_text(), "100")

    def test_reused_pid_is_never_restored(self):
        self.resource.apply(20, 400, True, True)
        proc_stat(self.proc / "20", 800)
        self.values[20] = 4
        self.resource.restore((20, 400))
        self.assertEqual(self.values[20], 4)

    def test_new_helper_replays_persisted_undo(self):
        self.resource.apply(20, 400, True, True)
        recovered = self.make()
        self.assertEqual(self.values[20], 2)
        self.assertFalse(recovered.nice)
        self.assertEqual((self.proc / "20" / "oom_score_adj").read_text().strip(), "25")

    def test_partial_write_failure_keeps_undo_for_retry(self):
        self.resource.set_nice = lambda tid, value: (_ for _ in ()).throw(OSError("write failed"))
        with self.assertRaises(OSError):
            self.resource.apply(20, 400, True, False)
        self.assertTrue(self.marker.exists())
        self.assertTrue(self.resource.nice)
        recovered = self.make()
        self.assertFalse(recovered.nice)
        self.assertEqual(self.values[20], 2)


class Manager:
    def __init__(self):
        self.state, self.fail, self.calls = 1, False, []

    def query(self):
        return self.state

    def set(self, state):
        self.calls.append(state)
        if self.fail:
            return False, "failed"
        self.state = state
        return True, "ok"


class FanResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.marker = Path(self.temp.name) / "fan.json"
        self.manager = Manager()
        self.now = 0
        self.fan = FanResources(self.manager, self.marker, lambda: self.now)

    def test_expiry_returns_original_oem_controller(self):
        self.fan.apply()
        self.assertEqual(self.manager.state, 0)
        self.now = 21
        self.fan.expire()
        self.assertEqual(self.manager.state, 1)
        self.assertFalse(self.marker.exists())

    def test_crash_journal_recovers_controller(self):
        self.fan.apply()
        FanResources(self.manager, self.marker)
        self.assertEqual(self.manager.state, 1)
        self.assertFalse(self.marker.exists())

    def test_external_change_is_preserved_and_not_reclaimed(self):
        self.fan.apply()
        self.manager.state = 1
        with self.assertRaisesRegex(OSError, "externally"):
            self.fan.apply()
        with self.assertRaisesRegex(OSError, "externally"):
            self.fan.apply()
        self.assertEqual(self.manager.calls, [0])

    def test_unconfirmed_write_blocks_until_undo_succeeds(self):
        self.manager.fail = True
        with self.assertRaises(OSError):
            self.fan.apply()
        self.assertTrue(self.fan.pending)
        self.assertTrue(self.marker.exists())
        self.manager.fail = False
        self.assertTrue(self.fan.restore())
        self.assertFalse(self.marker.exists())

    def test_preexisting_firmware_control_needs_no_restore(self):
        self.manager.state = 0
        self.fan.apply()
        self.fan.expire(force=True)
        self.assertEqual(self.manager.calls, [])
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
