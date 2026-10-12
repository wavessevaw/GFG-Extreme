"""Exercise actual export and mapped-file evidence, including stale installed files."""
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.frame_fusion import summarize
from gfg_plugin.log_report import analyze
from gfg_plugin.renderer_identity import _hash_file, mapped_renderer_files, process_start_ticks
from gfg_plugin.session_recorder import compact_status, probe_game_processes


def context(frames=4, **overrides):
    return {"pid": 25, "process_start_ticks": 50, "context": 123, "role": "frame-generation",
        "updated_unix_ms": 100, "state_revision": 2, "phase": "active", "reason": "applied",
        "frame_generation_active": True, "spatial_scaling": {
            "active": True, "activation_supported": True, "active_method": "mako", "requested_method": "mako",
            "pipeline": "pre-frame-generation", "source_width": 852, "source_height": 532,
            "presentation_width": 1280, "presentation_height": 800, "inactive_reason": None},
        "frame_fusion": {"supported": True, "requested": True, "prepared_inputs": 2,
            "recorded_frames": frames, "avoided_source_copies": frames}, **overrides}


class FusionDiagnosticsTests(unittest.TestCase):
    def test_compact_record_preserves_native_facts_and_dimensions(self):
        status = summarize(True, [context()])
        record = compact_status({"frame_fusion": status})
        self.assertTrue(record["frame_fusion"]["path_observed"])
        native = record["frame_fusion"]["contexts"][0]
        self.assertEqual(native["spatial_scaling"]["source_width"], 852)
        self.assertEqual(native["spatial_scaling"]["presentation_width"], 1280)
        self.assertEqual(native["frame_fusion"]["avoided_source_copies"], 4)
        self.assertEqual(native["eligibility"], "direct-path-observed")
        self.assertFalse(status["gain_measured"])

    def test_context_export_bounded_prioritizes_observed_and_keeps_rejection_reason(self):
        inactive = context(spatial_scaling={"active": False,
            "inactive_reason": "application-extent-override-no-source-presentation-split"})
        current = [dict(inactive, context=i, updated_unix_ms=500+i) for i in range(20)] + [context()]
        status = summarize(True, current)
        self.assertEqual((len(status["contexts"]), status["contexts_total"], status["contexts_truncated"]), (16, 21, 5))
        self.assertEqual(status["contexts"][0]["eligibility"], "direct-path-observed")
        self.assertEqual(status["contexts"][1]["eligibility"], "scaling-inactive")
        self.assertIn("no-source-presentation-split", status["contexts"][1]["spatial_scaling"]["inactive_reason"])

    def test_prepared_and_restart_are_not_submitted_work(self):
        self.assertEqual(summarize(True, [context(frames=0)])["contexts"][0]["eligibility"], "prepared-awaiting-submit")
        disabled = context(frame_fusion={"supported": True, "requested": False, "prepared_inputs": 0,
            "recorded_frames": 0, "avoided_source_copies": 0})
        state = summarize(True, [disabled])
        self.assertEqual(state["state"], "restart-required")
        self.assertFalse(state["path_observed"])

    def test_bundle_keeps_last_live_context_after_game_exit_and_writes_identity(self):
        from test_session_recorder import RecorderTests
        async def scenario(rec, state):
            with patch("gfg_plugin.session_recorder.SAMPLE_SECONDS", 0.01):
                await rec.start("game")
                await asyncio.sleep(0.04)
                state["frame_fusion"] = summarize(True, [])
                await asyncio.sleep(0.03)
                return await rec.stop()
        with tempfile.TemporaryDirectory() as temp:
            rec, _ = RecorderTests().make(Path(temp))
            state = {"frame_fusion": summarize(True, [context()])}
            rec.status_provider = lambda: state
            rec.process_probe = lambda: [{"pid": 25, "process_start_ticks": 50,
                "env": {"GFG_FRAME_FUSION": "1"}, "renderer_files": [{"path": "/mako/lib/libmako-render.so",
                    "state": "verified", "elf_bits": 64, "sha256": "a"*64, "basis": "mapped-file"}]}]
            manifest = Path(temp)/"manifest.json"
            manifest.write_text(json.dumps({"schema": 1, "source": {"commit": "pinned"},
                "native_libraries": {"lib/libmako-render.so": "a"*64}, "default_enabled": False}))
            rec.renderer_manifest = manifest
            result = asyncio.run(scenario(rec, state))
            self.assertTrue(result["success"], result)
            with zipfile.ZipFile(result["file"]) as bundle:
                rows = [json.loads(l) for l in bundle.read("timeline.jsonl").splitlines()]
                self.assertTrue(any((r.get("frame_fusion") or {}).get("path_observed") for r in rows))
                snapshot = json.loads(bundle.read("frame-fusion-contexts.json"))
                self.assertTrue(snapshot["available"])
                self.assertEqual(snapshot["last_live_sample"]["status"]["contexts"][0]["pid"], 25)
                identity = json.loads(bundle.read("renderer-identity.json"))
                self.assertTrue(identity["processes"][0]["renderer_files"][0]["matches_plugin_manifest"])
                self.assertEqual(identity["processes"][0]["launch_fusion"], "1")
                self.assertIn(b"Frame Fusion:", bundle.read("summary.txt"))

    def test_report_does_not_sum_repeated_counter_snapshots(self):
        fusion = summarize(True, [context(frames=7)])
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("timeline.jsonl", "\n".join(json.dumps({"t": t, "frame_fusion": fusion}) for t in range(4)))
        data.seek(0)
        with zipfile.ZipFile(data) as z:
            result = analyze(z)["frame_fusion"]
        self.assertEqual(result["maximum_avoided_copies_snapshot"], 7)
        self.assertEqual(result["observed_samples"], 4)
        self.assertFalse(result["gain_measured"])

    def test_legacy_ui_request_reports_missing_evidence(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("timeline.jsonl", '{"t":1,"state":"LOCKED"}\n')
            z.writestr("activity.jsonl", json.dumps({"kind": "set_governor_frame_fusion", "args": {"enabled": True}}))
        data.seek(0)
        with zipfile.ZipFile(data) as z:
            result = analyze(z)
        self.assertFalse(result["frame_fusion"]["available"])
        self.assertTrue(any("native status was not captured" in line for line in result["findings"]))

    def test_probe_captures_launch_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = Path(temp)/"25"; proc.mkdir()
            (proc/"environ").write_bytes(b"MAKO_CONFIG=/c.toml\0GFG_FRAME_FUSION=1\0")
            (proc/"maps").write_text("7f00 r-xp 0 0:0 1 /usr/lib/libvulkan.so.1\n")
            (proc/"comm").write_text("game.exe")
            self.assertEqual(probe_game_processes(Path(temp))[0]["env"]["GFG_FRAME_FUSION"], "1")

    def test_process_identity_handles_parentheses_in_command(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = Path(temp)
            (proc/"stat").write_text("25 (game (worker)) " + " ".join(["S"]+["0"]*18+["12345"]+["0"]*4))
            self.assertEqual(process_start_ticks(proc), 12345)

    def test_identity_mismatch_and_32_bit_are_separate_from_package_match(self):
        from test_session_recorder import RecorderTests
        with tempfile.TemporaryDirectory() as temp:
            rec, _ = RecorderTests().make(Path(temp))
            manifest = Path(temp)/"manifest.json"
            manifest.write_text(json.dumps({"schema": 1,
                "native_libraries": {"lib/libmako-render.so": "a"*64}}))
            rec.renderer_manifest = manifest
            library = {"path": "/mako/lib/libmako-render.so", "state": "verified",
                "elf_bits": 64, "sha256": "b"*64}
            result = rec._renderer_identity([{"pid": 1, "renderer_files": [library]}])
            self.assertFalse(result["processes"][0]["renderer_files"][0]["matches_plugin_manifest"])
            result = rec._renderer_identity([{"pid": 1, "renderer_files": [dict(library, elf_bits=32)]}])
            self.assertIsNone(result["processes"][0]["renderer_files"][0]["matches_plugin_manifest"])

    def test_missing_manifest_is_unknown_and_does_not_break_export(self):
        from test_session_recorder import RecorderTests
        with tempfile.TemporaryDirectory() as temp:
            rec, _ = RecorderTests().make(Path(temp))
            rec.renderer_manifest = Path(temp)/"missing.json"
            result = rec._renderer_identity([{"pid": 1, "renderer_files": [{
                "path": "/mako/lib/libmako-render.so", "state": "unavailable"}]}])
            self.assertIsNotNone(result["manifest_error"])
            self.assertIsNone(result["expected_plugin_manifest"])
            self.assertIsNone(result["processes"][0]["renderer_files"][0]["matches_plugin_manifest"])


@unittest.skipUnless(hasattr(os, "major"), "Linux mapped file device identities")
class MappedRendererTests(unittest.TestCase):
    def fixture(self, root):
        library = root/"libmako-render.so"
        data = b"\x7fELF\x02\x01"+b"\0"*12+b"\x3e\0"+b"native fixture"
        library.write_bytes(data)
        proc = root/"25"; proc.mkdir()
        st = library.stat()
        line = f"1000-2000 r-xp 0 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {library}\n"
        return library, proc, line, data

    def test_mapped_inode_hash_matches_actual_file_and_cache_tracks_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            library, proc, line, data = self.fixture(Path(temp))
            result = mapped_renderer_files(proc, line)[0]
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(result["basis"], "mapped-path-inode")
            library.write_bytes(data+b"changed")
            changed = mapped_renderer_files(proc, line)[0]
            self.assertNotEqual(changed["sha256"], result["sha256"])

    def test_installed_replacement_never_claimed_as_loaded_library(self):
        with tempfile.TemporaryDirectory() as temp:
            library, proc, line, _ = self.fixture(Path(temp))
            old = library.with_name("old.so"); library.rename(old)
            library.write_bytes(b"replacement")
            result = mapped_renderer_files(proc, line)[0]
            self.assertEqual(result["state"], "unavailable")
            self.assertNotIn("sha256", result)

    def test_deleted_mapping_uses_old_map_file_instead_of_new_install(self):
        with tempfile.TemporaryDirectory() as temp:
            library, proc, line, data = self.fixture(Path(temp))
            old = library.with_name("old.so"); library.rename(old)
            library.write_bytes(b"replacement")
            (proc/"map_files").mkdir()
            (proc/"map_files"/"1000-2000").symlink_to(old)
            result = mapped_renderer_files(proc, line.rstrip()+" (deleted)\n")[0]
            self.assertEqual(result["basis"], "mapped-file")
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())

    def test_non_elf_mapping_is_not_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            library, proc, line, _ = self.fixture(Path(temp))
            library.write_bytes(b"not an ELF file"*3)
            result = mapped_renderer_files(proc, line)[0]
            self.assertEqual(result["state"], "unavailable")


if __name__ == "__main__":
    unittest.main()
