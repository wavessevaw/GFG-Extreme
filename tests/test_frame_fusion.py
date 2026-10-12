"""Fusion requests, native evidence and restart behavior are distinct."""
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.frame_fusion import normalize, summarize


class EvidenceTests(unittest.TestCase):
    def native(self, prepared=2, frames=0, requested=True):
        return normalize({"schema": 1, "requested": requested, "prepared_inputs": prepared,
            "recorded_frames": frames, "avoided_source_copies": frames})

    def context(self, frames=0, requested=True):
        return {"phase": "active", "frame_generation_active": True,
            "spatial_scaling": {"active": True}, "frame_fusion": self.native(frames=frames, requested=requested)}

    def test_old_renderer_is_unsupported_not_observed(self):
        c = self.context(); c["frame_fusion"] = normalize(None)
        self.assertEqual(summarize(True, [c])["state"], "renderer-unsupported")
        self.assertFalse(summarize(True, [c])["path_observed"])

    def test_prepared_descriptors_are_not_work(self):
        s = summarize(True, [self.context()])
        self.assertEqual(s["state"], "prepared")
        self.assertFalse(s["path_observed"])

    def test_path_work_never_claims_power_gain(self):
        s = summarize(True, [self.context(frames=4)])
        self.assertTrue(s["path_observed"])
        self.assertFalse(s["gain_measured"])
        self.assertEqual(s["avoided_source_copies_at_last_publication"], 4)

    def test_disabling_requires_restart_of_old_process(self):
        s = summarize(False, [self.context(frames=4)])
        self.assertFalse(s["path_observed"])
        self.assertTrue(s["restart_required"])

    def test_enabling_does_not_change_old_launch(self):
        s = summarize(True, [self.context(requested=False)])
        self.assertEqual(s["state"], "restart-required")

    def test_transition_generation_off_and_scaling_off_hide_old_evidence(self):
        for key, value in (("phase", "draining"), ("frame_generation_active", False),
                           ("spatial_scaling", {"active": False})):
            c = self.context(frames=4); c[key] = value
            self.assertFalse(summarize(True, [c])["path_observed"])

    def test_invalid_counter_payloads_are_rejected(self):
        good = {"schema": 1, "requested": True, "prepared_inputs": 2,
            "recorded_frames": 1, "avoided_source_copies": 1}
        for update in ({"schema": True}, {"requested": "yes"}, {"prepared_inputs": 65},
                {"prepared_inputs": 0}, {"recorded_frames": -1}, {"recorded_frames": True},
                {"recorded_frames": 2**64}, {"avoided_source_copies": 2}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                normalize({**good, **update})


class NativeResolutionEvidenceTests(unittest.TestCase):
    def payload(self, transfers=5, format_=44, **changes):
        return {"schema": 2, "requested": True, "prepared_inputs": 0,
            "recorded_frames": 0, "avoided_source_copies": 0,
            "native_prepared_inputs": 2, "native_source_transfers": transfers,
            "native_conversion_blits_avoided": transfers if format_ == 44 else 0,
            "native_source_format": format_, "native_fallback_reason": "", **changes}

    def context(self, **changes):
        return {"phase": "active", "frame_generation_active": True,
            "spatial_scaling": {"active": False, "source_width": 1280,
                "source_height": 800, "presentation_width": 1280, "presentation_height": 800},
            "frame_fusion": normalize(self.payload()), **changes}

    def test_native_work_without_scaling_is_observed_without_copy_savings(self):
        state = summarize(True, [self.context()])
        self.assertEqual(state["state"], "observed")
        self.assertEqual(state["processing_path"], "native-input")
        self.assertEqual(state["native_source_transfers_at_last_publication"], 5)
        self.assertEqual(state["native_conversion_blits_avoided_at_last_publication"], 5)
        self.assertEqual(state["avoided_source_copies_at_last_publication"], 0)
        self.assertEqual(state["contexts"][0]["eligibility"], "native-path-observed")
        self.assertFalse(state["gain_measured"])

    def test_preparation_and_transition_do_not_claim_work(self):
        c = self.context(frame_fusion=normalize(self.payload(transfers=0)))
        state = summarize(True, [c])
        self.assertEqual(state["state"], "prepared")
        self.assertEqual(state["contexts"][0]["eligibility"], "native-prepared-awaiting-submit")
        self.assertFalse(state["path_observed"])
        for changes in ({"phase": "draining"}, {"frame_generation_active": False}):
            self.assertFalse(summarize(True, [self.context(**changes)])["path_observed"])

    def test_rgba_transfer_does_not_claim_channel_conversion_savings(self):
        c = self.context(frame_fusion=normalize(self.payload(format_=37)))
        self.assertEqual(summarize(True, [c])["native_conversion_blits_avoided_at_last_publication"], 0)

    def test_legacy_evidence_defaults_native_work_to_zero(self):
        native = normalize({"schema": 1, "requested": True, "prepared_inputs": 2,
            "recorded_frames": 5, "avoided_source_copies": 5})
        self.assertEqual(native["native_source_transfers"], 0)
        self.assertEqual(summarize(True, [EvidenceTests().context(frames=1)])["processing_path"], "spatial-input")

    def test_native_transport_rejects_inconsistent_evidence(self):
        for changes in ({"schema": 3}, {"native_source_transfers": True},
                {"native_prepared_inputs": 1}, {"native_prepared_inputs": 0},
                {"native_source_format": 50}, {"native_source_format": 37},
                {"native_conversion_blits_avoided": 4}, {"requested": False},
                {"prepared_inputs": 2}, {"native_fallback_reason": "x"*241},
                {"native_fallback_reason": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                normalize(self.payload(**changes))

    def test_fallback_reason_survives_export(self):
        native = normalize(self.payload(transfers=0, native_prepared_inputs=0,
            native_source_format=37, native_fallback_reason="native-source-format-not-shareable"))
        state = summarize(True, [self.context(frame_fusion=native)])
        self.assertEqual(state["state"], "pipeline-not-eligible")
        self.assertEqual(state["contexts"][0]["eligibility"], "native-source-format-not-shareable")


class SettingsTests(unittest.TestCase):
    def setUp(self):
        # Reuse fixture methods without inheriting its hundreds of test cases.
        from test_governor_runtime import RuntimeBase
        self.fixture = RuntimeBase()
        self.fixture.setUp()
        self.gov = self.fixture.svc

    def tearDown(self):
        self.fixture.tearDown()

    def test_default_on_and_explicit_launch_marker(self):
        self.assertTrue(self.gov.frame_fusion_enabled())
        marker = self.gov.configuration.runtime_state_dir / "frame-fusion.enabled"
        self.assertTrue(self.gov.set_frame_fusion(True)["success"])
        self.assertTrue(marker.is_file())
        self.assertTrue(json.loads(self.gov.settings_path.read_text())["frame_fusion"])
        self.assertTrue(self.gov.set_frame_fusion(False)["success"])
        self.assertFalse(marker.exists())

    def test_non_boolean_does_not_enable(self):
        self.assertFalse(self.gov.set_frame_fusion("true")["success"])
        self.assertTrue(self.gov.frame_fusion_enabled())

    def test_marker_failure_restores_previous_setting(self):
        with patch.object(self.gov, "_sync_frame_fusion_marker", side_effect=OSError("read only")):
            self.assertFalse(self.gov.set_frame_fusion(False)["success"])
        self.assertTrue(self.gov.frame_fusion_enabled())
        self.assertTrue(json.loads(self.gov.settings_path.read_text())["frame_fusion"])


class RuntimeLocationTests(unittest.TestCase):
    def test_governor_overlay_status_is_read_and_newest_identity_wins(self):
        import test_governor_runtime  # initializes the existing Decky fixture
        from gfg_plugin.runtime_state import RuntimeStateService
        from gfg_plugin.governor_overlay import OVERLAY_DIRNAME
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            svc = object.__new__(RuntimeStateService)
            svc.config_dir = root
            svc.runtime_state_dir = root / "runtime-state"
            svc.log = logging.getLogger("fusion-runtime-test")
            nested = root / OVERLAY_DIRNAME / "runtime-state"
            for folder in (svc.runtime_state_dir, nested):
                folder.mkdir(parents=True); (folder / "status.json").write_text("{}")
            other = root / "unowned" / "runtime-state"
            other.mkdir(parents=True); (other / "status.json").write_text("{}")
            def read(path):
                return {"pid": 1, "process_start_ticks": 50, "role": "frame-generation",
                    "context": 2, "updated_unix_ms": 20 if path.parent == nested else 10,
                    "state_revision": 1, "phase": "active",
                    "requested": {"name": "game"}, "applied": {"name": "game"}}
            with patch.object(svc, "_read_context", side_effect=read) as reader:
                status = svc.get_status("game")
            self.assertEqual(reader.call_count, 2)
            self.assertEqual(len(status["contexts"]), 1)
            self.assertEqual(status["contexts"][0]["updated_unix_ms"], 20)


@unittest.skipUnless(shutil.which("bash") and os.name == "posix", "real launch-wrapper requires Linux")
class WrapperTests(unittest.TestCase):
    def setUp(self):
        from test_governor_wrapper_overlay import WrapperOverlayTests
        self.fixture = WrapperOverlayTests()
        self.fixture.setUp()
        self.svc = self.fixture.svc

    def launch_value(self):
        env = {"PATH": os.environ["PATH"], "HOME": str(self.svc.user_home),
            "MAKO_PROFILE": "game", "GFG_FRAME_FUSION": "1"}
        run = subprocess.run(["bash", str(self.svc.mako_script_path), "/usr/bin/env"],
            env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return dict(line.split("=", 1) for line in run.stdout.splitlines() if "=" in line)["GFG_FRAME_FUSION"]

    def test_inherited_opt_in_is_removed_without_owned_marker(self):
        self.assertEqual(self.launch_value(), "0")

    def test_marker_enables_next_native_launch(self):
        marker = self.svc.runtime_state_dir / "frame-fusion.enabled"
        marker.parent.mkdir(parents=True, exist_ok=True); marker.write_text("enabled\n")
        self.assertEqual(self.launch_value(), "0", "legacy renderer has no live Autopilot scope")
        source = self.svc.local_share_dir.parent.parent / "gfg-fusion-source.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('{"autopilot_only":true}')
        self.assertEqual(self.launch_value(), "1")

    def test_flatpak_uses_baseline_even_with_marker(self):
        marker = self.svc.runtime_state_dir / "frame-fusion.enabled"
        marker.parent.mkdir(parents=True, exist_ok=True); marker.write_text("enabled\n")
        from gfg_plugin.constants import FLATPAK_IMPLICIT_LAYER_DIR
        directory = self.svc.user_home / "fusion-flatpak-test"
        directory.mkdir(parents=True, exist_ok=True)
        script = self.svc.mako_script_path
        script.write_text(script.read_text().replace(FLATPAK_IMPLICIT_LAYER_DIR, str(directory)))
        self.assertEqual(self.launch_value(), "0")
