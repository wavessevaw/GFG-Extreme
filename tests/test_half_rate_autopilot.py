"""Steam Half Rate Shading opt-in actuator and Autopilot arbitration tests."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.autopilot.half_rate import HalfRateShading, SteamVrsBackend
from gfg_plugin.autopilot.arbiter import Arbiter
from gfg_plugin.autopilot.planner import View, decide


class StaticBackend:
    def __init__(self, initial="1x1", *, fail=False):
        self.mode = initial
        self.fail = fail
        self.writes = []

    def read(self):
        return self.mode

    def write(self, value):
        self.writes.append(value)
        if self.fail:
            raise OSError("simulated Steam file error")
        self.mode = value


class HalfRateTests(unittest.TestCase):
    def test_off_by_default_even_for_heavily_loaded_gpu(self):
        v = View(30, 60, 33, 90, 95, 55, 1500, 65, 14, 15,
                 True, 9, False, shading_available=True, shading_consent=False)
        self.assertNotEqual(decide(v).action, "OPTIMIZE_SHADING")

    def test_explicit_opt_in_can_trial_vrs_for_gpu_bound_game(self):
        v = View(30, 60, 33, 90, 95, 55, 1500, 65, 14, 15,
                 True, 9, False, shading_available=True, shading_consent=True)
        d = decide(v)
        self.assertEqual(d.action, "OPTIMIZE_SHADING")
        self.assertEqual(d.tool, "half-rate-shading")

    def test_files_are_in_place_and_restore_original(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "radv_vrs.test"
            p.write_text("1x1\n")
            p.chmod(0o600)
            actor = HalfRateShading(SteamVrsBackend(fixed_path=p))
            self.assertTrue(actor.status()["available"])
            ino = p.stat().st_ino
            self.assertTrue(actor.enable_trial()["applied"])
            self.assertEqual(p.read_text(), "2x2")
            self.assertEqual(p.stat().st_ino, ino)
            self.assertTrue(actor.restore()["restored"])
            self.assertEqual(p.read_text(), "1x1")

    def test_restart_recovers_only_the_same_steam_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "radv_vrs.test"
            receipt = root / "receipt.json"
            p.write_text("1x1")
            p.chmod(0o600)
            first = HalfRateShading(SteamVrsBackend(fixed_path=p), receipt_path=receipt)
            self.assertTrue(first.enable_trial()["applied"])
            self.assertTrue(receipt.exists())
            second = HalfRateShading(SteamVrsBackend(fixed_path=p), receipt_path=receipt)
            self.assertEqual(second.phase, "restore-pending")
            self.assertTrue(second.restore()["restored"])
            self.assertEqual(p.read_text(), "1x1")
            self.assertFalse(receipt.exists())
            p.write_text("2x2")
            p.chmod(0o600)
            receipt.write_text('{"original":"1x1","session_path":"/tmp/a-previous-session"}')
            third = HalfRateShading(SteamVrsBackend(fixed_path=p), receipt_path=receipt)
            self.assertFalse(third.owned)
            self.assertEqual(p.read_text(), "2x2")

    def test_rollback_never_changes_the_next_steam_session(self):
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "radv_vrs.old"
            newer = Path(d) / "radv_vrs.new"
            for path, mode in ((old, "1x1"), (newer, "2x2")):
                path.write_text(mode)
                path.chmod(0o600)
            backend = SteamVrsBackend(fixed_path=old)
            actor = HalfRateShading(backend)
            self.assertTrue(actor.enable_trial()["applied"])
            backend.fixed_path = newer  # Gamescope/Steam switched its VRS file
            result = actor.restore()
            self.assertTrue(result.get("yielded"))
            self.assertEqual(newer.read_text(), "2x2")
            self.assertFalse(actor.owned)

    def test_user_enabled_shading_is_not_modified(self):
        backend = StaticBackend("2x2")
        actor = HalfRateShading(backend)
        self.assertFalse(actor.enable_trial()["applied"])
        self.assertEqual(backend.writes, [])

    def test_external_disable_is_not_overwritten(self):
        backend = StaticBackend()
        actor = HalfRateShading(backend)
        self.assertTrue(actor.enable_trial()["applied"])
        backend.mode = "1x1"
        result = actor.restore()
        self.assertTrue(result["yielded"])
        self.assertEqual(backend.writes, ["2x2"])

    def test_failed_write_must_not_claim_applied(self):
        actor = HalfRateShading(StaticBackend(fail=True))
        self.assertFalse(actor.enable_trial()["applied"])
        self.assertFalse(actor.owned if actor.backend.read() == "1x1" else False)

    def test_failed_restore_blocks_followup_trials(self):
        backend = StaticBackend()
        actor = HalfRateShading(backend)
        self.assertTrue(actor.enable_trial()["applied"])
        backend.fail = True
        self.assertFalse(actor.restore()["restored"])
        self.assertEqual(actor.phase, "restore-pending")
        self.assertEqual(actor.enable_trial()["reason"], "already-owned")

    def test_nonmatching_vrs_value_does_not_get_rewritten(self):
        actor = HalfRateShading(StaticBackend("2x1"))
        self.assertFalse(actor.status()["available"])
        self.assertFalse(actor.enable_trial()["applied"])

    def test_arbiter_serializes_shading_with_gpu_clock_and_power(self):
        a = Arbiter()
        a.begin("half-rate-shading", "gpu-shader-limited", 0,
                {"real": 30, "output": 60, "sample_seq": 1, "session": "game"})
        self.assertTrue(a.freeze_tdp)
        self.assertEqual(a.admit("OPTIMIZE_GPU_CLOCK", 1), "busy")
        self.assertEqual(a.admit("OPTIMIZE_POWER", 1), "busy")
        a.mark_restore_pending("failed to restore", tool="half-rate-shading")
        self.assertEqual(a.admit("OPTIMIZE_SHADING", 20), "busy")

    def test_improvement_must_be_proven(self):
        a = Arbiter()
        a.begin("half-rate-shading", "test", 0, {"real": 30, "output": 60,
                 "sample_seq": 1, "session": "game", "frametime_p95": 33})
        evidence = {"samples": 7, "span_s": 4, "real": 30,
                    "output": 60, "sample_seq": 2, "session": "game",
                    "frametime_p95": 33}
        self.assertEqual(a.judge(3, evidence), "wait")
        evidence["sample_seq"] = 3
        self.assertEqual(a.judge(12, evidence), "rollback")
        self.assertGreater(a.blocked_until.get("OPTIMIZE_SHADING", 0), 12)


if __name__ == "__main__":
    unittest.main()
