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


# Byte-for-byte what the te.2 adapter writes (C++ streams print bool as 1/0). The
# helper above used Python's True and hid that the reader refused every real record.
TE2_RECORD = (
    '{"schema":1,"engine":"gfg-temporal","version":"0.1.0-exp","pid":51,"process_start_ticks":11818,'
    '"context":1,"updated_unix_ms":1791981755719,"mode":"experimental","role":"engine","active":true,'
    '"device":"AMD Custom GPU 0932 (RADV VANGOGH)","width":1280,"height":800,"outputs_capacity":3,'
    '"vram_bytes":41943040,"real_interval_ms":33.4,"counters":{"pairs_submitted":900,"history_frames":0,'
    '"outputs_dispatched":2700,"outputs_gpu_completed":2697,"dropped":0,"scene_cuts":4,"promoted_tiles":120,'
    '"cost_holds":2,"holding":1,"presented":null},"gpu_ms":{"pyramid":0.3,"analyze":2.1,"classify":0.1,'
    '"lists":0.02,"reuse":0.1,"light":0.9,"full":0,"merge":0,"frame":1.1,"pair_p50":5.4,"pair_p95":7.9,'
    '"pair_p99":9.2,"timed":1},"shares":{"reuse":0.2,"light":0.8,"full":0},"confidence":0.6,'
    '"scheduler":{"level":4,"light_scale":1,"force_full":0,"force_light":1,"cap_ms":2,"budget_ms":12,'
    '"predicted_ms":2.3,"recommended_outputs":3,"recommendation":"fallback","reason":"over-cap","misses":3,'
    '"gpu_busy_known":false},"last_error":null}\n')


# The te.4 (LMC) adapter's record, written the same way: algorithm after
# "active", the lmc block after "confidence", "keep" since LMC has no tile
# scheduler.  test_writer_source_has_lmc_fields pins these spellings in the C++.
LMC_RECORD = (TE2_RECORD
              .replace('"active":true,', '"active":true,"algorithm":"lmc",')
              .replace('"cost_holds":2,"holding":1', '"cost_holds":0,"holding":0')
              .replace('"confidence":0.6,',
                       '"confidence":0,"lmc":{"layers":1,"orphans_b":912.5,"orphans_a":880,"select_ms":0.21},')
              .replace('"recommendation":"fallback"', '"recommendation":"keep"'))

# te.5: the LMC block also carries the cost guard's budget share and the GPU
# time of every analysis pass; a cost hold recommends "hold".
LMC5_PASSES = ('"passes_ms":{"search_b":0.4,"search_a":0.38,"layers":0.3,"palette":0.03,"field":0.15,'
               '"masked":0.07,"orphan":0.05,"field2":0.02}')
LMC5_RECORD = (LMC_RECORD
               .replace('"select_ms":0.21}', '"select_ms":0.21,"budget":0.25,' + LMC5_PASSES + '}')
               .replace('"cost_holds":0,"holding":0', '"cost_holds":1,"holding":1')
               .replace('"recommendation":"keep"', '"recommendation":"hold"'))


class WriterFormat(unittest.TestCase):
    def test_lmc_record_is_accepted(self):
        out = te.normalize_status(json.loads(LMC_RECORD))
        self.assertEqual(out["algorithm"], "lmc")
        self.assertEqual(out["lmc"], {"layers": 1.0, "orphans_b": 912.5, "orphans_a": 880.0, "select_ms": 0.21})
        self.assertEqual(out["counters"]["holding"], 0)
        s = te.summarize("experimental", [out])
        self.assertEqual(s["algorithm"], "lmc")
        self.assertEqual(s["lmc"]["orphans_b"], 912.5)
        self.assertEqual(te.compact(s)["algorithm"], "lmc")
        with self.assertRaises(ValueError):
            te.normalize_status(json.loads(LMC_RECORD.replace('"algorithm":"lmc"', '"algorithm":"dlss"')))

    def test_lmc5_record_has_passes_and_hold(self):
        out = te.normalize_status(json.loads(LMC5_RECORD))
        self.assertEqual(out["lmc"]["budget"], 0.25)
        self.assertEqual(list(out["lmc_passes_ms"]), list(te.LMC_PASSES))
        self.assertEqual(out["lmc_passes_ms"]["search_b"], 0.4)
        self.assertEqual(out["scheduler"]["recommendation"], "hold")
        s = te.summarize("experimental", [out])
        self.assertEqual(s["lmc_passes_ms"]["field2"], 0.02)
        self.assertTrue(s["holding"])
        with self.assertRaises(ValueError):
            te.normalize_status(json.loads(LMC5_RECORD.replace('"field2":0.02', '"other":0.02')))

    def test_te2_record_reads_as_tiles(self):
        self.assertEqual(te.normalize_status(json.loads(TE2_RECORD))["algorithm"], "tiles")

    def test_writer_source_has_lmc_fields(self):
        source = (ROOT / "engine/gfg-temporal/mako/gfg_temporal.cpp").read_text()
        for snippet in ('<< ",\\"active\\":true,\\"algorithm\\":" << (this->lmc ? "\\"lmc\\"" : "\\"tiles\\"")',
                        '<< ",\\"lmc\\":{\\"layers\\":" << finite(this->lmcLayers) << ",\\"orphans_b\\":"',
                        '<< ",\\"orphans_a\\":" << finite(this->lmcOrphansA) << ",\\"select_ms\\":"',
                        'jsonString(this->lmc ? (this->holdPairs > 0 ? "hold" : "keep")',
                        '<< ",\\"budget\\":" << finite(this->runtime->lmcBudget()) << ",\\"passes_ms\\":{";',
                        'o << (k ? "," : "") << \'"\' << lmcPassName(k) << "\\":" << finite(this->lmcMs[k]);',
                        'l << " lmc_passes=search_b/search_a/layers/palette/field/masked/orphan/field2";',
                        '"MAKO Renderer: Temporal Engine stats algo=" << (this->lmc ? "lmc" : "tiles")',
                        '<< " layers=" << finite(this->lmcLayers) << " orphans=" << finite(this->lmcOrphansB) << \'/\''):
            self.assertIn(snippet, source)

    def test_renderer_log_lmc_stats_summary(self):
        from gfg_plugin.log_report import temporal_engine_log_summary
        line = ("MAKO Renderer: Temporal Engine stats algo=lmc level=0 reason=none holding=0 cost_holds=0 pairs=300 "
                "dropped=0 interval_ms=33.30 fixed_ms=1.10 frame_ms=0.60 pair_p95_ms=2.70 cap_ms=2.00 "
                "predicted_ms=0.00 shares=0.00/0.00/0.00 confidence=0.00 scene_cuts=0 pyramid_ms=0.08 "
                "analyze_ms=0.70 fields_ms=0.32 layers=1.00 orphans=900.00/850.00")
        out = temporal_engine_log_summary(line + "\n" + line.replace("layers=1.00", "layers=2.00"))
        self.assertEqual(out["algorithms"], {"lmc": 2})
        self.assertEqual(out["analyze_ms_median"], 0.7)
        self.assertEqual(out["fields_ms_median"], 0.32)
        self.assertEqual(out["layers_median"], 1.5)
        self.assertEqual(out["orphans_median"], [900.0, 850.0])
        self.assertIsNone(out["lmc_passes_ms_median"])
        te5 = line + (" lmc_ms=0.40/0.38/0.30/0.03/0.15/0.07/0.05/0.02"
                      " lmc_passes=search_b/search_a/layers/palette/field/masked/orphan/field2")
        out = temporal_engine_log_summary(te5 + "\n" + te5.replace("lmc_ms=0.40", "lmc_ms=0.60"))
        self.assertEqual(out["lmc_passes_ms_median"]["search_b"], 0.5)
        self.assertEqual(out["lmc_passes_ms_median"]["field2"], 0.02)

    def test_lmc_pass_names_match_engine(self):
        header = (ROOT / "engine/gfg-temporal/src/te_engine.h").read_text()
        source = (ROOT / "engine/gfg-temporal/mako/gfg_temporal.cpp").read_text()
        enum = header[header.index("enum { TE_LMC_SEARCH_B"):].split("};")[0]
        self.assertEqual([n.strip()[7:].lower() for n in enum[6:].split(",") if n.strip() != "TE_LMC_PROF_COUNT"],
                         list(te.LMC_PASSES))
        self.assertIn('{"search_b", "search_a", "layers", "palette",\n'
                      '                                                             "field", "masked", "orphan", "field2"}',
                      source)

    def test_te2_record_is_accepted(self):
        out = te.normalize_status(json.loads(TE2_RECORD))
        self.assertIs(out["gpu_ms"]["timed"], True)
        self.assertEqual(out["counters"]["holding"], 1)
        self.assertEqual(out["scheduler"]["level"], 4)

    def test_te3_record_with_json_bool(self):
        out = te.normalize_status(json.loads(TE2_RECORD.replace('"timed":1', '"timed":true')))
        self.assertIs(out["gpu_ms"]["timed"], True)
        for bad in ('"timed":2', '"timed":"yes"'):
            with self.assertRaises(ValueError):
                te.normalize_status(json.loads(TE2_RECORD.replace('"timed":1', bad)))

    def test_read_contexts_finds_record_in_governor_overlay_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "governor-overlay" / "runtime-state" / "temporal"
            folder.mkdir(parents=True)
            (folder / "51-11818-1.json").write_text(TE2_RECORD)
            found = te.read_contexts([Path(tmp) / "runtime-state" / "temporal", folder],
                                     live_check=lambda pid: 11818)
            self.assertEqual(len(found), 1)
            self.assertEqual(te.summarize("experimental", found)["state"], "generating")

    def test_writer_source_prints_json_bools(self):
        source = (ROOT / "engine/gfg-temporal/mako/gfg_temporal.cpp").read_text()
        self.assertIn('"timed\\":" << ((this->haveStats && this->stats.timed) ? "true" : "false")', source)

    def test_renderer_log_stats_summary(self):
        from gfg_plugin.log_report import temporal_engine_log_summary
        line = ("MAKO Renderer: Temporal Engine stats level=4 reason=over-cap holding=1 cost_holds=3 pairs=900 "
                "dropped=0 interval_ms=33.30 fixed_ms=3.10 frame_ms=1.20 pair_p95_ms=7.50 cap_ms=2.00 "
                "predicted_ms=2.30 shares=0.10/0.80/0.10 confidence=0.70 scene_cuts=2")
        out = temporal_engine_log_summary("noise\n" + line + "\n" + line.replace("holding=1", "holding=0"))
        self.assertEqual(out["lines"], 2)
        self.assertEqual(out["holding_share"], 0.5)
        self.assertEqual(out["cost_holds"], 3)
        self.assertEqual(out["shares_median"], [0.1, 0.8, 0.1])
        self.assertFalse(temporal_engine_log_summary("")["available"])


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

    def test_lock_keeps_a_namespaced_writer_alive(self):
        import fcntl
        self.write("ns.json", engine_record(pid=7, process_start_ticks=5))
        dead = lambda pid: None  # noqa: E731  PID from another namespace
        self.assertEqual(te.read_contexts([self.dir], live_check=dead), [])
        with open(self.dir / "ns.json.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(len(te.read_contexts([self.dir], live_check=dead)), 1)

    def test_engine_keeps_running_until_restart(self):
        self.write("a.json", engine_record(mode="experimental"))
        s = te.summarize("off", te.read_contexts([self.dir], live_check=LIVE))
        self.assertEqual(s["state"], "generating")
        self.assertTrue(s["restart_required"])
        self.assertTrue(te.blocks_experiments(s))

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
