"""Contact is intent, not a promise of delivered FPS. Exercise the complete input-to-policy path."""
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.frame_os.input_relay import DeckReportDecoder, MOTION_HEARTBEAT_S
from gfg_plugin.frame_os.input_sensor import DECK_MOTION_TYPE, EVENT, InputState
from gfg_plugin.frame_os.policy import EnergyBroker, InjectionPolicy
from gfg_plugin.session_recorder import compact_status


def report(touch=False, gyro=0, rx=0):
    packet = bytearray(64)
    packet[0], packet[2] = 1, 9
    packet[14] = 0x80 if touch else 0
    packet[30:32] = gyro.to_bytes(2, "little", signed=True)
    packet[52:54] = rx.to_bytes(2, "little", signed=True)
    return bytes(packet)


class ContactInputTests(unittest.TestCase):
    def setUp(self):
        self.decoder, self.sensor = DeckReportDecoder(), InputState()

    def sample(self, now, **values):
        self.sensor.feed(self.decoder.decode(report(**values), now))
        return self.sensor.snapshot(now)

    def test_contact_edge_held_and_release_are_distinct_from_button_presses(self):
        self.assertIs(self.sample(0)["right_stick_touch"], False)
        first = self.sample(.01, touch=True)
        self.assertEqual(first["touch_generation"], 1)
        self.assertTrue(first["right_stick_touch"])
        self.assertEqual(first["action"], 0)
        self.assertEqual(self.sample(.1, touch=True)["touch_generation"], 1)
        self.assertFalse(self.sample(.11)["right_stick_touch"])
        self.assertEqual(self.sample(.2, touch=True)["touch_generation"], 2)

    def test_gyro_scale_is_signed_and_sensor_motion_does_not_become_button_action(self):
        for raw in (16384, -16384):
            sensor = self.sample(1 if raw > 0 else 2, touch=True, gyro=raw)
            self.assertEqual(sensor["gyro_dps"], 1000.0)
            self.assertEqual(sensor["camera"], 0)
            self.assertEqual(sensor["action"], 0)

    def test_contact_lease_expires_and_clears_on_source_loss(self):
        self.sample(1, touch=True)
        self.assertIsNone(self.sensor.snapshot(1.36)["right_stick_touch"])
        self.assertFalse(self.sensor.snapshot(1.36)["touch_signal_fresh"])
        self.assertIsNone(self.sensor.snapshot(.99)["right_stick_touch"])
        self.sample(2, touch=True)
        self.sensor.clear_activity()
        self.assertIsNone(self.sensor.snapshot(2)["right_stick_touch"])

    def test_heartbeat_is_bounded_but_touch_edges_are_immediate(self):
        self.decoder.decode(report(), 1)
        for i in range(1, 40):
            self.assertEqual(self.decoder.decode(report(), 1+i/1000), b"")
        self.assertEqual(len(self.decoder.decode(report(), 1+MOTION_HEARTBEAT_S+.001)), EVENT.size)
        self.assertEqual(len(self.decoder.decode(report(touch=True), 1.06)), EVENT.size)
        self.assertEqual(len(self.decoder.decode(report(), 1.061)), EVENT.size)

    def test_invalid_reports_and_motion_records_cannot_establish_contact(self):
        bad = bytearray(report(touch=True)); bad[2] = 4
        self.assertEqual(self.decoder.decode(bytes(bad), 0), b"")
        self.assertEqual(self.decoder.decode(report(touch=True)[:55], 0), b"")
        for code, value in ((2, 0), (1, -1), (1, 4000001)):
            self.sensor.event(0, DECK_MOTION_TYPE, code, value)
        self.assertIsNone(self.sensor.snapshot(0)["right_stick_touch"])


class TouchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.decoder, self.sensor = DeckReportDecoder(), InputState()
        self.policy = InjectionPolicy(90, 30, broker=EnergyBroker(10, bank_j=100))
        self.policy.configure_touch_boost(True)

    def tick(self, now, touch=True, gyro=0, rx=0, **kw):
        self.sensor.feed(self.decoder.decode(report(touch=touch, gyro=gyro, rx=rx), now))
        return self.policy.tick(now, self.sensor.snapshot(now), **kw)

    def test_touch_starts_before_any_stick_motion(self):
        d = self.tick(0)
        self.assertEqual((d.level, d.reason, d.real_hz, d.output_hz), ("boost", "stick-touch", 45, 90))
        self.assertEqual(self.policy.touch_requests, 1)

    def test_new_setting_defaults_off_and_does_not_change_regular_boost(self):
        self.policy.configure_touch_boost(False)
        self.assertEqual(self.tick(0).level, "calm")
        self.assertEqual(self.tick(.2, rx=30000).level, "boost")

    def test_resting_finger_never_renews_the_half_second_pulse(self):
        self.tick(0)
        for now in (.1, .2, .3, .4):
            self.assertEqual(self.tick(now).level, "boost")
        self.assertEqual(self.tick(.51).level, "calm")
        self.assertEqual(self.tick(1).level, "calm")
        self.assertEqual(self.policy.touch_requests, 1)

    def test_gyro_motion_extends_only_while_contact_is_held(self):
        self.tick(0)
        for now in (.2, .4, .6, .8, 1):
            self.assertEqual(self.tick(now, gyro=500).reason, "stick-touch-motion")
        self.assertEqual(self.tick(1.1, touch=False, gyro=500).level, "boost")
        self.assertEqual(self.tick(1.31, touch=False, gyro=500).level, "calm")

    def test_sensor_loss_aborts_touch_without_waiting_for_pulse_expiry(self):
        self.tick(0)
        d = self.policy.tick(.36, self.sensor.snapshot(.36))
        self.assertEqual(d.level, "calm")
        self.assertFalse(self.policy.touch_intent)

    def test_resume_of_same_held_contact_does_not_retrigger_preboost(self):
        self.tick(0)
        self.policy.tick(.36, self.sensor.snapshot(.36))
        self.assertEqual(self.tick(.4).level, "calm")
        self.assertEqual(self.policy.touch_requests, 1)

    def test_menu_and_disabling_cancel_touch_without_resetting_shared_guards(self):
        self.tick(0)
        self.assertEqual(self.tick(.1, focused=False).level, "rest")
        self.assertFalse(self.policy.touch_intent)
        self.assertEqual(self.tick(.2, focused=True).level, "calm")
        self.policy.configure_touch_boost(False)
        self.assertEqual(self.tick(.4).level, "calm")

    def test_energy_and_ineffective_and_game_memory_guards_still_apply(self):
        for attribute, value, reason in (("boost_allowed", False, "boost-off-for-game"),
                ("_boost_blocked_until", 120, "boost-ineffective")):
            with self.subTest(attribute=attribute):
                self.setUp(); setattr(self.policy, attribute, value)
                d = self.tick(0)
                self.assertEqual((d.level, d.reason), ("calm", reason))
        self.setUp(); self.policy.broker.bank_j = 0
        self.assertEqual(self.tick(0).reason, "energy-bank-empty")

    def test_held_gyro_cannot_hold_boost_forever(self):
        for i in range(100):
            d = self.tick(i/10,gyro=500)
            if i >= 15:
                self.assertEqual(d.level,"calm")
        self.assertEqual(self.policy.touch_requests,1)

    def test_repeated_touch_chatter_is_debounced(self):
        self.tick(0); self.tick(.01, touch=False); self.tick(.02)
        self.assertEqual(self.policy.touch_requests, 1)
        self.tick(.2, touch=False); self.tick(.21)
        self.assertEqual(self.policy.touch_requests, 2)


class TouchRunnerTests(unittest.TestCase):
    def make(self, mode="act", executor=True):
        from test_frame_os_proof import FakeChannel, FakeReader
        from gfg_plugin.frame_os.runner import FrameOsRunner
        channel, reader = FakeChannel(), FakeReader()
        runner = FrameOsRunner(channel, reader_factory=lambda: reader)
        runner.configure(enabled=True, mode=mode, output_hz=90, calm_real_hz=30,
            max_multiplier=3, calm_w=10, touch_boost_enabled=True)
        runner.executor_active = executor
        runner.policy.broker.bank_j = 100
        runner.proof.enabled = False
        return runner, reader

    def test_request_ack_and_observed_cadence_are_separate_and_exported(self):
        runner, reader = self.make()
        reader.state.event(0, DECK_MOTION_TYPE, 1, 0)
        first = runner.tick(0)
        self.assertEqual(first["touch_boost"]["state"], "requested")
        self.assertFalse(first["touch_boost"]["submitted"])
        reader.state.event(.1, DECK_MOTION_TYPE, 1, 0)
        acknowledged = runner.tick(.1)
        self.assertTrue(acknowledged["touch_boost"]["submitted"])
        self.assertEqual(acknowledged["touch_boost"]["observed_real_hz"], 45)
        self.assertFalse(acknowledged["touch_boost"]["gain_measured"])
        row = compact_status({"frame_os": acknowledged})["frame_os"]
        self.assertEqual(row["touch_boost"], acknowledged["touch_boost"])
        self.assertTrue(row["input"]["right_stick_touch"])

    def test_observe_shadow_and_missing_executor_do_not_act_or_add_watts(self):
        for mode, executor, state in (("observe", True, "observe-only"),
                ("shadow", True, "observe-only"), ("act", False, "executor-unavailable")):
            with self.subTest(mode=mode, executor=executor):
                runner, reader = self.make(mode, executor)
                reader.state.event(0, DECK_MOTION_TYPE, 1, 0)
                status = runner.tick(0)
                self.assertEqual(status["published_real_hz"], 30)
                self.assertEqual(status["touch_boost"]["state"], state)
                self.assertFalse(status["touch_boost"]["submitted"])
                self.assertEqual(runner.tdp_offset_w, 0)

    def test_missing_sensor_is_explicit(self):
        runner, _ = self.make()
        status = runner.tick(0)
        self.assertEqual(status["touch_boost"]["state"], "sensor-unavailable")
        self.assertFalse(status["touch_boost"]["requested"])


class TouchSettingsTests(unittest.TestCase):
    def setUp(self):
        from test_extreme_frame_features import FeatureSettingsTests
        fixture = FeatureSettingsTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.service = fixture.service

    def test_touch_is_independent_per_profile_and_defaults_on(self):
        self.assertTrue(self.service.frame_os_features("Game")["touch_boost"])
        result = self.service.set_frame_os_feature("Game", "touch_boost", True)
        self.assertTrue(result["success"])
        self.assertTrue(result["features"]["touch_boost"])
        self.assertEqual((result["features"]["latency"], result["features"]["shield"]), (True, True))
        self.assertTrue(self.service.frame_os_features("Other")["touch_boost"])
        self.assertEqual(self.service._frame_os_mode("Game"), "act")
        self.service.set_frame_os_feature("Game","touch_boost",False)
        self.assertFalse(self.service.frame_os_features("Game")["touch_boost"])
        self.assertTrue(self.service.frame_os_features("Other")["touch_boost"])

    def test_bad_boolean_or_failed_save_never_enables_feature(self):
        for value in (1, "true", None):
            self.assertFalse(self.service.set_frame_os_feature("Game", "touch_boost", value)["success"])
        self.service._save_settings.side_effect = OSError("disk full")
        self.assertFalse(self.service.set_frame_os_feature("Game", "touch_boost", False)["success"])
        self.assertTrue(self.service.frame_os_features("Game")["touch_boost"])


class TouchReportTests(unittest.TestCase):
    def test_report_keeps_requests_distinct_and_never_sums_counter_snapshots(self):
        from gfg_plugin.log_report import analyze
        touch = {"enabled": True, "state": "submitted", "signal_fresh": True,
            "right_stick_touch": True, "requested": True, "submitted": True,
            "touch_requests": 7, "observed_real_hz": 30, "gain_measured": False}
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("timeline.jsonl", "\n".join(json.dumps({"t": n,
                "frame_os": {"mode": "act", "touch_boost": touch}}) for n in range(4)))
        data.seek(0)
        with zipfile.ZipFile(data) as z:
            summary = analyze(z)["stick_touch_boost"]
        self.assertEqual(summary["maximum_touch_requests_snapshot"], 7)
        self.assertEqual(summary["submitted_samples"], 4)
        self.assertFalse(summary["gain_measured"])

    def test_old_logs_explicitly_have_no_touch_evidence(self):
        from gfg_plugin.log_report import stick_touch_boost_summary
        self.assertFalse(stick_touch_boost_summary([{"frame_os": {"mode": "act"}}])["available"])
