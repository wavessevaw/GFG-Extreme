"""Extreme (1.6) policy: the stock-power ceiling, sharpening, renderer acknowledgement, capabilities."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin import extreme as ex  # noqa: E402
from gfg_plugin.governor_overlay import PointNotApplicable, point_deltas  # noqa: E402
from gfg_plugin.governor_power import SteamDeckPowerActuator  # noqa: E402
from gfg_plugin.governor_telemetry import TelemetryObserver  # noqa: E402

SPATIAL = ("I MAKO Renderer: spatial scaling active: source=1024x640; factor=1.25; effective_factor=1.25; "
           "requested_method=ls1; active_method=ls1; sharpness=0.3; ls1_model_variant=quality; "
           "role=frame-generation; pipeline=pre-frame-generation; placement_reason=native")
SWAPCHAIN = ("I MAKO Renderer: present diagnostics: operation=swapchain-context-create context=1 pid=4372 "
             "role=frame-generation swapchain=0x1 width=1280 height=800 application_width={aw} "
             "application_height={ah} frame_generation_width=1280 frame_generation_height=800 "
             "spatial_pipeline=pre-frame-generation replacement=1")


class CeilingTests(unittest.TestCase):
    def test_stock_15_w_on_any_deck(self):
        self.assertEqual(ex.power_ceiling(None, None)["ceiling_w"], 15.0)
        self.assertEqual(ex.power_ceiling(20.0, 20.0), {"ceiling_w": 15.0, "source": "stock-limit", "user_w": 20.0})

    def test_a_lower_player_limit_wins_and_is_never_raised(self):
        self.assertEqual(ex.power_ceiling(12.0, 15.0), {"ceiling_w": 12.0, "source": "your-limit", "user_w": 12.0})
        self.assertEqual(ex.power_ceiling(15.0, 15.0)["source"], "stock-limit")
        self.assertEqual(ex.power_ceiling(float("nan"), 10.0)["ceiling_w"], 10.0)

    def test_the_actuator_clamps_every_write_to_the_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hwmon = root / "hwmon" / "hwmon0"
            hwmon.mkdir(parents=True)
            for name, value in (("power1_label", "fastPPT"), ("power2_label", "slowPPT"),
                                ("power1_cap", "24000000"), ("power2_cap", "20000000"),
                                ("power1_cap_min", "3000000"), ("power2_cap_min", "3000000"),
                                ("power1_cap_max", "30000000"), ("power2_cap_max", "25000000")):
                (hwmon / name).write_text(value + "\n")
            act = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon")
            self.assertTrue(act.discover()["available"])
            act.claim()                          # an unlocked BIOS default of 20 W
            act.set_ceiling_w(ex.power_ceiling(20.0, 25.0)["ceiling_w"])
            act.set_tdp_w(19.0)                  # e.g. an Act boost on top of 15 W
            self.assertEqual(int((hwmon / "power2_cap").read_text()), 15_000_000)
            act.restore_if_owned()
            self.assertEqual(int((hwmon / "power2_cap").read_text()), 20_000_000, "the player's value back")


class SharpnessTests(unittest.TestCase):
    def test_table_and_player_correction(self):
        self.assertEqual(ex.sharpness_for(90, {}), (0.15, "table"))
        self.assertEqual(ex.sharpness_for(80, {}, 0.1), (0.4, "table"))
        self.assertEqual(ex.sharpness_for(80, {}, 9), (0.6, "table"), "correction is clamped to +-0.3")
        self.assertEqual(ex.sharpness_for(100, {}), (None, "native"))

    def test_never_sharpen_twice_and_never_touch_the_players_scaling(self):
        filters = {"external_vulkan_layer": "vkbasalt", "vkbasalt_sharpening": "cas"}
        self.assertEqual(ex.sharpness_for(80, filters), (0.0, "vkbasalt-sharpening"))
        self.assertEqual(ex.sharpness_for(80, {"vkbasalt_sharpening": "cas"}), (0.3, "table"),
                         "vkBasalt not selected: its CAS does not run")
        self.assertEqual(ex.sharpness_for(80, {"scaling_enabled": True}), (None, "profile-scaling"))

    def test_overlay_carries_sharpening_with_the_scaled_point_only(self):
        point = {"key": "45x2@80", "multiplier": 2, "target_output_fps": 90, "base_target_fps": 45,
                 "render_scale_pct": 80}
        deltas = point_deltas(point, {"multiplier": 2}, scale_capable=True, scale_ready=True, sharpness=0.3)
        self.assertEqual((deltas["scaling_factor"], deltas["scaling_sharpness"]), (1.25, 0.3))
        native = dict(point, key="45x2", render_scale_pct=100)
        self.assertNotIn("scaling_sharpness",
                         point_deltas(native, {"multiplier": 2}, scale_capable=True, scale_ready=True, sharpness=0.3))
        with self.assertRaises(PointNotApplicable):
            point_deltas(point, {"multiplier": 2}, scale_capable=True, scale_ready=True, sharpness=1.5)


class EvidenceTests(unittest.TestCase):
    def test_spatial_scaler_report(self):
        record = ex.parse_spatial_active(SPATIAL)
        self.assertEqual((record["source"], record["sharpness"], record["effective_factor"]), ((1024, 640), 0.3, 1.25))
        self.assertEqual(ex.render_pct(record), 80.0)
        self.assertIsNone(ex.parse_spatial_active("I MAKO Renderer: present diagnostics: operation=x"))

    def test_swapchain_extent(self):
        fields = TelemetryObserver.parse_fields(SWAPCHAIN.format(aw=1152, ah=720))
        record = ex.swapchain_extent(fields)
        self.assertEqual(ex.render_pct(record), 90.0)
        self.assertIsNone(ex.swapchain_extent({"width": "1280"}))

    def test_acknowledgement_takes_the_newest_report_only(self):
        older = ex.swapchain_extent(TelemetryObserver.parse_fields(SWAPCHAIN.format(aw=1024, ah=640)))
        newer = ex.swapchain_extent(TelemetryObserver.parse_fields(SWAPCHAIN.format(aw=1280, ah=800)))
        self.assertIsNotNone(ex.scale_acknowledged([older], 80))
        self.assertIsNone(ex.scale_acknowledged([older, newer], 80), "the game went back to full size")
        self.assertIsNone(ex.scale_acknowledged([], 80))
        squeezed = {"source": (1024, 800), "output": (1280, 800)}
        self.assertIsNone(ex.render_pct(squeezed), "a non-uniform extent proves nothing")

    def test_sharpness_acknowledgement(self):
        record = ex.parse_spatial_active(SPATIAL)
        self.assertTrue(ex.sharpness_acknowledged([record], 0.3))
        self.assertFalse(ex.sharpness_acknowledged([record], 0.4))
        self.assertIsNone(ex.sharpness_acknowledged([], 0.3), "not reported is not confirmed")

    def test_observer_keeps_scaling_evidence_in_order(self):
        observer = TelemetryObserver(Path("/nonexistent"), time_fn=lambda: 1.0)
        observer.consume_line(SWAPCHAIN.format(aw=1280, ah=800))
        mark = observer.event_seq
        observer.consume_line(SPATIAL)
        observer.consume_line(SWAPCHAIN.format(aw=1024, ah=640))
        after = observer.scaling_after(mark)
        self.assertEqual([r["kind"] for r in after], ["spatial-active", "swapchain"])
        self.assertEqual(ex.render_pct(observer.latest_scaling), 80.0)
        for _ in range(100):
            observer.consume_line(SPATIAL)
        self.assertLessEqual(len(observer.scaling_after(0)), observer.MAX_SCALING_EVIDENCE, "bounded")


# From a Deck log (1.6.0): the game kept its full-size swapchain whatever the scaler advertised.
POLICY_OFF = ("MAKO Renderer: spatial scaling swapchain policy: role=frame-generation; requested=1280x800; "
              "surface_current=1280x800; surface_extent_mode=fixed; supersampling=0; advertised_source=766x478; "
              "advertised_presentation=1280x800; actual_source=1280x800; actual_presentation=1280x800; "
              "policy_revision=2; selected_source=0x0; extent_selected=0; "
              "inactive_reason=application-extent-override-no-source-presentation-split; admission_retry_eligible=0; "
              "source_presentation_split=0; active=0")


class SwapchainPolicyTests(unittest.TestCase):
    def test_the_game_ignoring_the_scale_is_read_from_the_renderer(self):
        record = ex.parse_swapchain_policy(POLICY_OFF)
        self.assertEqual((record["active"], record["source"], record["advertised"]), (False, (1280, 800), (766, 478)))
        self.assertEqual(record["reason"], ex.GAME_IGNORES_SCALE)
        self.assertIsNone(ex.scale_acknowledged([record], 80))
        self.assertEqual(ex.scale_refused([record]), ex.GAME_IGNORES_SCALE)
        on = ex.parse_swapchain_policy(POLICY_OFF.replace("actual_source=1280x800", "actual_source=1024x640")
                                       .replace("active=0", "active=1"))
        self.assertIsNotNone(ex.scale_acknowledged([record, on], 80))
        self.assertIsNone(ex.scale_refused([record, on]))

    def test_the_observer_keeps_policy_reports(self):
        observer = TelemetryObserver(Path("/nonexistent"), time_fn=lambda: 1.0)
        observer.consume_line(POLICY_OFF)
        self.assertEqual(observer.latest_scaling["kind"], "swapchain-policy")


class RuntimeStateTests(unittest.TestCase):
    def doc(self, pid, active=True, sw=1024, sh=640, updated=2_000_000_000_000):
        return {"schema_version": 5, "pid": pid, "process_start_ticks": 1, "role": "frame-generation",
                "updated_unix_ms": updated, "spatial_scaling": {
                    "active": active, "activation_supported": True, "inactive_reason": None,
                    "source_width": sw, "source_height": sh, "presentation_width": 1280,
                    "presentation_height": 800, "requested_method": "ls1", "active_method": "ls1",
                    "effective_factor": 1.25}}

    def write(self, root, name, doc):
        folder = Path(root) / ex.RUNTIME_STATE_DIRNAME
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(doc))

    def test_only_the_games_fresh_records_count(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write(temp, "4372-1-7.json", self.doc(4372))
            self.write(temp, "99-1-1.json", self.doc(99, sw=640, sh=400))          # another process
            self.write(temp, "4372-1-8.json", self.doc(4372, updated=1_000))         # before the request
            (Path(temp) / ex.RUNTIME_STATE_DIRNAME / "broken.json").write_text("{")
            records = ex.read_runtime_states([temp], [4372], since_unix_s=1_900_000_000)
            self.assertEqual(len(records), 1)
            self.assertEqual(ex.render_pct(records[0]), 80.0)
            self.assertIsNotNone(ex.scale_acknowledged(records, 80))
            self.assertEqual(ex.read_runtime_states([Path(temp) / "missing"], [4372]), [])

    def test_a_container_pid_falls_back_to_fresh_records(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write(temp, "12-1-7.json", self.doc(12))                 # PID inside pressure-vessel
            self.write(temp, "13-1-7.json", self.doc(13, updated=1_000))  # stale
            records = ex.read_runtime_states([temp], [4372], since_unix_s=1_900_000_000)
            self.assertEqual([r["pid"] for r in records], [12])

    def test_an_inactive_scaler_proves_full_resolution_only(self):
        off = ex.runtime_state_evidence(self.doc(1, active=False))
        self.assertIsNone(ex.scale_acknowledged([off], 80))
        self.assertIs(ex.scale_acknowledged([off], 100), off)
        self.assertIsNone(ex.runtime_state_evidence({"pid": 1}))


class CapabilityTests(unittest.TestCase):
    def facts(self, **extra):
        base = {"running": True, "scale_pct": 100, "scale_ack": True, "scale_provisioned": True,
                "split": {"setting": True, "available": True}, "act": {"consent": True, "enabled": True,
                                                                         "pacer_live": True}}
        base.update(extra)
        return {b["id"]: b for b in ex.booster_states(base)}

    def test_nine_directions_unverified_ones_stay_unavailable(self):
        states = self.facts()
        self.assertEqual(list(states), list(ex.BOOSTERS))
        for ident in ("quiet", "cooling", "memory", "latency", "shield"):
            self.assertEqual(states[ident]["state"], "unavailable")
            self.assertTrue(states[ident]["reason"])

    def test_upscale_states(self):
        self.assertEqual(self.facts(scale_provisioned=False)["upscale"]["state"], "restart_required")
        self.assertEqual(self.facts(scale_pct=80, scale_ack=False)["upscale"]["state"], "waiting")
        active = self.facts(scale_pct=80, scale_ack=True, sharpness=0.3, sharpness_ack=None)["upscale"]
        self.assertEqual((active["state"], active["render_pct"], active["sharpness"]), ("active", 80, None))
        self.assertEqual(self.facts(cpu_bound=True)["upscale"]["reason"], "cpu-bound-full-resolution")
        self.assertEqual(self.facts(scale_blocked="profile-scaling")["upscale"]["state"], "unavailable")

    def test_act_needs_consent_and_the_pacer(self):
        self.assertEqual(self.facts(act={"consent": False})["act"]["state"], "off")
        self.assertEqual(self.facts(act={"consent": True, "enabled": True, "pacer_live": False})["act"]["state"],
                         "restart_required")
        self.assertEqual(self.facts(act={"consent": True, "enabled": True, "pacer_live": True,
                                         "injecting": True})["act"]["state"], "active")

    def test_gain_has_no_number_before_proof(self):
        gain = ex.gain_unavailable()
        self.assertEqual((gain["kind"], gain["percent"], gain["baseline"]), ("unavailable", None, "balanced"))

    def test_session_states(self):
        kw = dict(enabled=True, running=True, overlay_active=True, paused=False, request=False,
                  verifying_scale=False, phase="locked", restart_required=False)
        self.assertEqual(ex.session_state(**kw), "ACTIVE")
        self.assertEqual(ex.session_state(**{**kw, "enabled": False}), "OFF")
        self.assertEqual(ex.session_state(**{**kw, "overlay_active": False}), "RESTART_REQUIRED")
        self.assertEqual(ex.session_state(**{**kw, "verifying_scale": True, "request": True}), "VERIFY")
        self.assertEqual(ex.session_state(**{**kw, "phase": "upgrade"}), "TUNE")
        self.assertEqual(ex.session_state(**{**kw, "phase": "settle"}), "BASELINE")


if __name__ == "__main__":
    unittest.main()
