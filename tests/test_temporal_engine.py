"""GFG Temporal Engine integration: setting, launcher, native status, Autopilot exclusion, log export."""
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(ROOT / "tests"))

from gfg_plugin import temporal_engine as te  # noqa: E402
from gfg_plugin.governor_service import GovernorService  # noqa: E402
from gfg_plugin.log_report import temporal_engine_summary, findings  # noqa: E402
from gfg_plugin.session_recorder import compact_temporal  # noqa: E402
from test_governor_service import FakeConfig, FakeDisplay, FakePower  # noqa: E402

LIVE = lambda pid: 77  # noqa: E731  process start ticks of a "running" game


def engine_record(**over):
    record = {
        "schema": 1, "engine": "gfg-temporal", "version": "0.1.0-exp", "pid": 4242, "process_start_ticks": 77,
        "context": 1, "updated_unix_ms": 1000, "mode": "shadow", "role": "engine", "active": True,
        "device": "AMD Custom GPU 0405 (RADV VANGOGH)", "width": 1280, "height": 800, "outputs_capacity": 2,
        "vram_bytes": 64 * 1024 * 1024, "real_interval_ms": 33.3,
        "counters": {"pairs_submitted": 100, "history_frames": 300, "outputs_dispatched": 200,
                     "outputs_gpu_completed": 198, "dropped": 4, "scene_cuts": 1, "promoted_tiles": 12,
                     "presented": None},
        "gpu_ms": {"pyramid": 0.1, "analyze": 0.9, "classify": 0.02, "lists": 0.01, "reuse": 0.01, "light": 0.1,
                   "full": 0.6, "merge": 0, "frame": 0.8, "pair_p50": 2.4, "pair_p95": 3.1, "pair_p99": 3.5,
                   "timed": True},
        "shares": {"reuse": 0.3, "light": 0.3, "full": 0.4}, "confidence": 0.85,
        "scheduler": {"level": 0, "light_scale": 1.0, "force_full": 0, "budget_ms": 14.1, "predicted_ms": 3.0,
                      "recommended_outputs": 2, "recommendation": "keep", "reason": "none", "misses": 0,
                      "gpu_busy_known": False},
        "last_error": None}
    record.update(over)
    return record


class StatusValidation(unittest.TestCase):
    def test_engine_record_round_trip(self):
        out = te.normalize_status(engine_record())
        self.assertEqual(out["counters"]["outputs_gpu_completed"], 198)
        self.assertIsNone(out["counters"]["presented"])

    def test_rejects_invented_facts(self):
        bad = engine_record()
        bad["counters"] = {**bad["counters"], "presented": 10}
        with self.assertRaises(ValueError):
            te.normalize_status(bad)
        bad = engine_record()
        bad["counters"] = {**bad["counters"], "outputs_gpu_completed": 500}
        with self.assertRaises(ValueError):
            te.normalize_status(bad)
        for broken in ({"schema": 2}, engine_record(mode="off"), engine_record(active="yes"),
                       engine_record(shares={"reuse": 2, "light": 0, "full": 0}),
                       engine_record(scheduler={**engine_record()["scheduler"], "recommendation": "boost"})):
            with self.assertRaises(ValueError):
                te.normalize_status(broken)

    def test_fallback_record(self):
        out = te.normalize_status({"schema": 1, "engine": "gfg-temporal", "version": "0.1.0-exp", "pid": 1,
                                   "process_start_ticks": 2, "context": 3, "updated_unix_ms": 4,
                                   "mode": "experimental", "role": "fallback", "active": False, "device": "x",
                                   "width": 1, "height": 1, "eligible": False,
                                   "fallback_reason": "encoding-not-sdr8"})
        self.assertEqual(out["fallback_reason"], "encoding-not-sdr8")


class Summary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, record):
        (self.dir / name).write_text(json.dumps(record))

    def test_states_keep_requested_and_applied_apart(self):
        self.assertEqual(te.summarize("off", [])["state"], "off")
        waiting = te.summarize("shadow", [])
        self.assertEqual(waiting["state"], "waiting-for-game")
        self.assertFalse(waiting["applied"])
        self.write("a.json", engine_record())
        self.write("dead.json", engine_record(pid=99, process_start_ticks=1, context=9))
        self.write("junk.json", "{not json")
        contexts = te.read_contexts([self.dir], live_check=lambda pid: 77 if pid == 4242 else None)
        self.assertEqual(len(contexts), 1, "dead process and invalid files are ignored")
        s = te.summarize("shadow", contexts)
        self.assertEqual(s["state"], "shadow-measuring")
        self.assertTrue(s["applied"])
        self.assertIsNone(s["presented"])
        self.assertFalse(s["verified_on_hardware"])
        self.assertEqual(s["completion_ratio"], 0.99)
        self.assertTrue(te.blocks_experiments(s))
        compact = te.compact(s)
        self.assertEqual(compact["recommendation"], "keep")
        self.assertIn("gpu_ms", compact)

    def test_fallback_is_reported_with_reason(self):
        record = engine_record(role="fallback", active=False, eligible=False, mode="experimental",
                               fallback_reason="no-external-semaphore-fd")
        for k in ("counters", "gpu_ms", "shares", "scheduler"):
            record.pop(k)
        self.write("f.json", record)
        s = te.summarize("experimental", te.read_contexts([self.dir], live_check=LIVE))
        self.assertEqual(s["state"], "fallback")
        self.assertEqual(s["fallback_reasons"], ["no-external-semaphore-fd"])
        self.assertFalse(te.blocks_experiments(s))


class Setting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.svc = GovernorService(FakeConfig(root), FakeDisplay(), logging.getLogger("te-test"))
        self.svc.power = FakePower()
        self.marker = root / "runtime-state" / te.MARKER_NAME

    def tearDown(self):
        self.tmp.cleanup()

    def test_off_by_default(self):
        self.assertEqual(self.svc.temporal_engine_mode(), "off")
        self.assertEqual(self.svc.get_status()["temporal_engine"]["state"], "off")

    def test_experimental_requires_consent(self):
        result = self.svc.set_temporal_engine("experimental", False)
        self.assertFalse(result["success"])
        self.assertEqual(self.svc.temporal_engine_mode(), "off")
        self.assertFalse(self.marker.exists())

    def test_modes_write_and_remove_marker(self):
        self.assertTrue(self.svc.set_temporal_engine("shadow")["relaunch_required"])
        self.assertEqual(self.marker.read_text(), "shadow\n")
        self.assertTrue(self.svc.set_temporal_engine("experimental", True)["success"])
        self.assertEqual(self.marker.read_text(), "experimental\n")
        self.svc.set_temporal_engine("off")
        self.assertFalse(self.marker.exists())
        self.svc.set_temporal_engine("experimental", True)
        self.svc.set_temporal_engine("off")
        self.svc._settings["temporal_engine"]["mode"] = "experimental"  # tampered: consent was dropped with off
        self.assertEqual(self.svc.temporal_engine_mode(), "off")

    def test_invalid_input(self):
        self.assertFalse(self.svc.set_temporal_engine("act")["success"])
        self.assertFalse(self.svc.set_temporal_engine("shadow", "yes")["success"])

    def test_engine_activity_blocks_actuator_trials(self):
        folder = self.svc.configuration.runtime_state_dir / te.STATUS_DIRNAME
        folder.mkdir(parents=True)
        (folder / "x.json").write_text(json.dumps(engine_record(pid=os.getpid(), process_start_ticks=te._process_start_ticks(os.getpid()))))
        self.svc.set_temporal_engine("shadow")
        self.svc._menu_since = None
        self.svc._menu_covering = lambda: False
        ready, reason = self.svc._autopilot_trial_ready({}, 90)
        self.assertEqual((ready, reason), (False, "temporal-engine-measuring"))


class LogExport(unittest.TestCase):
    def test_report_section_and_finding(self):
        s = te.summarize("shadow", [te.normalize_status(engine_record())])
        samples = [{"t": i, "temporal_engine": compact_temporal(s)} for i in range(3)]
        summary = temporal_engine_summary(samples)
        self.assertEqual(summary["active_samples"], 3)
        self.assertIsNone(summary["presented"])
        report = {"temporal_engine": summary, "samples": 0, "diagnostics": {}, "failed_checks": []}
        # findings() stops early on an empty timeline; the section itself is still exported
        self.assertIn("temporal_engine", report)
        self.assertIsNone(compact_temporal(None))


@unittest.skipUnless(shutil.which("bash") and os.name == "posix", "real launch-wrapper requires Linux")
class Wrapper(unittest.TestCase):
    def setUp(self):
        from test_governor_wrapper_overlay import WrapperOverlayTests
        self.fixture = WrapperOverlayTests()
        self.fixture.setUp()
        self.svc = self.fixture.svc

    def tearDown(self):
        cleanup = getattr(self.fixture, "tearDown", None)
        if cleanup:
            cleanup()

    def launch_value(self, inherited="experimental"):
        env = {"PATH": os.environ["PATH"], "HOME": str(self.svc.user_home), "MAKO_PROFILE": "game",
               "GFG_TEMPORAL_ENGINE": inherited}
        run = subprocess.run(["bash", str(self.svc.mako_script_path), "/usr/bin/env"], env=env,
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return dict(line.split("=", 1) for line in run.stdout.splitlines() if "=" in line).get("GFG_TEMPORAL_ENGINE")

    def test_inherited_value_is_dropped_without_marker(self):
        self.assertIsNone(self.launch_value())

    def test_marker_selects_mode_and_rejects_garbage(self):
        marker = self.svc.runtime_state_dir / te.MARKER_NAME
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("shadow\n")
        self.assertEqual(self.launch_value(), "shadow")
        marker.write_text("act; rm -rf /\n")
        self.assertIsNone(self.launch_value())


if __name__ == "__main__":
    unittest.main()
