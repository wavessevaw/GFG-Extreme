"""GFG Frame OS policy: input sensor, real-frame injection, energy broker, scene changes."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.frame_os.input_sensor import ABS_RX, EV_ABS, EV_KEY, EVENT, InputState  # noqa: E402
from gfg_plugin.frame_os.policy import EnergyBroker, InjectionPolicy, boost_level  # noqa: E402
from gfg_plugin.frame_os.scene import SceneChangeDetector  # noqa: E402


def ev(t, etype, code, value):
    return EVENT.pack(int(t), int((t % 1) * 1e6), etype, code, value)


class InputSensorTests(unittest.TestCase):
    def test_flick_reads_as_camera_motion_and_decays(self):
        s = InputState()
        s.feed(ev(10.0, EV_ABS, ABS_RX, 30000))
        self.assertGreater(s.snapshot(10.0)["camera"], 0.8)
        s.feed(ev(10.1, EV_ABS, ABS_RX, 0))          # stick released
        self.assertEqual(s.snapshot(11.0)["camera"], 0.0)

    def test_button_rate_and_idle(self):
        s = InputState()
        s.feed(b"".join(ev(5 + i * 0.25, EV_KEY, 304, 1) for i in range(8)))   # 4 presses/s
        snap = s.snapshot(6.8)
        self.assertGreaterEqual(snap["action"], 0.9)
        self.assertAlmostEqual(s.snapshot(30.0)["idle_s"], 30.0 - 6.75, places=1)

    def test_partial_and_unknown_events_are_safe(self):
        s = InputState()
        self.assertEqual(s.feed(b"\x00" * (EVENT.size - 1)), 0)
        self.assertEqual(s.feed(ev(1, 0x02, 0, 5)), 1)                         # EV_REL ignored
        self.assertEqual(s.snapshot(2.0)["idle_s"], float("inf"))


class InjectionTests(unittest.TestCase):
    def test_boost_level_is_one_step_up(self):
        self.assertEqual(boost_level(90, 30, 3.0), 45.0)
        self.assertEqual(boost_level(60, 30, 2.0), 40.0)       # 60 / 1.5
        self.assertEqual(boost_level(90, 90, 3.0), 90)         # nothing above native

    def test_camera_flick_boosts_then_returns_to_calm(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        calm = {"camera": 0.0, "action": 0.0, "idle_s": 1.0}
        self.assertEqual(p.tick(0.0, calm).level, "calm")
        d = p.tick(0.1, {"camera": 0.9, "action": 0.0, "idle_s": 0.0})
        self.assertEqual((d.level, d.real_hz, d.output_hz), ("boost", 45.0, 90))
        self.assertEqual(p.tick(1.0, calm).level, "boost", "held: no flicker")
        self.assertEqual(p.tick(2.0, calm).level, "calm")

    def test_idle_rests_and_input_wakes(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        self.assertEqual(p.tick(0, {"idle_s": 25.0}).level, "rest")
        self.assertEqual(p.tick(1, {"idle_s": 0.0, "camera": 0.0}).level, "calm")

    def test_scene_change_buys_a_short_burst(self):
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        self.assertEqual(p.tick(0, {"idle_s": 1}, scene_change=True).level, "boost")
        self.assertEqual(p.tick(1.5, {"idle_s": 1}).level, "calm")


class BrokerTests(unittest.TestCase):
    def test_boosts_are_paid_from_calm_savings_only(self):
        broker = EnergyBroker(calm_w=10.0, boost_extra_w=4.0, premium=0.0)
        p = InjectionPolicy(output_hz=90, calm_real_hz=30, broker=broker)
        flick = {"camera": 0.9, "idle_s": 0.0}
        # no savings yet: refused
        self.assertEqual(p.tick(0.0, flick, draw_w=10.0).reason, "energy-bank-empty")
        t = 0.0
        for _ in range(40):                       # 4 s of calm play at 8 W: 8 J banked
            t += 0.1
            p.tick(t, {"idle_s": 1.0}, draw_w=8.0)
        self.assertAlmostEqual(broker.bank_j, 8.0, delta=0.3)
        d = p.tick(t + 0.1, flick, draw_w=8.0)
        self.assertEqual((d.level, d.tdp_w), ("boost", 14.0))
        t += 0.1
        levels = []
        for _ in range(40):                       # boosting at 14 W drains 4 J/s: ~2 s
            t += 0.1
            levels.append(p.tick(t, flick, draw_w=14.0).level)
        self.assertIn("calm", levels[-10:], "bank empty: boost stops")
        self.assertEqual(broker.bank_j, 0.0)

    def test_bank_is_capped_and_rest_cuts_power(self):
        broker = EnergyBroker(calm_w=10.0, max_bank_s=2.0)
        for i in range(100):
            broker.tick(i * 0.1, 2.0, "rest")
        self.assertEqual(broker.bank_j, 20.0)
        self.assertEqual(broker.tdp_for("rest"), 6.0)


class SceneChangeTests(unittest.TestCase):
    def test_cost_jump_is_one_event(self):
        d = SceneChangeDetector()
        self.assertFalse(any(d.tick(i * 0.1, 15.0) for i in range(20)))
        self.assertTrue(d.tick(2.1, 24.0))
        self.assertFalse(d.tick(2.2, 24.5), "refractory")
        self.assertFalse(any(d.tick(2.3 + i * 0.1, 24.0) for i in range(30)), "new normal")


if __name__ == "__main__":
    unittest.main()


class PremiumTests(unittest.TestCase):
    def test_premium_funds_boosts_even_when_calm_play_uses_its_cap(self):
        broker = EnergyBroker(calm_w=10.0, premium=0.05)
        for i in range(101):
            broker.tick(i * 0.1, 10.0, "calm")          # calm play right at its cap
        self.assertAlmostEqual(broker.bank_j, 5.0, delta=0.05)   # 0.5 W x 10 s


class SimulationTests(unittest.TestCase):
    def test_frame_os_buys_real_frames_where_the_camera_moves(self):
        from gfg_plugin.frame_os.simulate import compare
        for seed in (1, 2, 3, 7):
            c = compare(seed)
            self.assertGreater(c["frame_os"]["real_fps_in_motion"], c["governor"]["real_fps_in_motion"] + 3)
            self.assertLess(c["frame_os"]["avg_w"], c["governor"]["avg_w"] * 1.15, "energy premium bounded")


class FakeReader:
    def __init__(self):
        self.state = InputState()
        self.available = False

    def poll(self):
        return 0

    def close(self):
        pass


class ControlChannelTests(unittest.TestCase):
    def test_layout_matches_control_h(self):
        from gfg_plugin.frame_os import control_channel as c
        header = (ROOT / "engine/gfg-pacer/src/control.h").read_text()
        if "GFG_CTL_VERSION 2u" not in header:
            self.skipTest("layer still on v1")
        self.assertIn(f"{c.SIZE} bytes", header)

    def test_policy_roundtrip_and_telemetry_read(self):
        import tempfile
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            ch = c.ControlChannel(Path(tmp) / "ctl")
            self.assertTrue(ch.write_policy(enabled=True, real_hz=45.0, mode="shadow", generation=7))
            raw = (Path(tmp) / "ctl").read_bytes()
            self.assertEqual(len(raw), c.SIZE)
            self.assertEqual(c.HEADER.unpack_from(raw, 0)[:3], (c.MAGIC, c.VERSION, c.SIZE))
            self.assertEqual(c.SEQ.unpack_from(raw, c.POLICY_SEQ_OFF)[0] % 2, 0)
            enabled, _ts, _pace, mode, hz, _m, _w, gen, _r = c.POLICY.unpack_from(raw, c.POLICY_OFF)
            self.assertEqual((enabled, mode, hz, gen), (1, 2, 45.0, 7))
            # the layer publishes telemetry
            buf = bytearray(raw)
            c.TELEMETRY.pack_into(buf, c.TELEMETRY_OFF, 120, 118, 1, 12.0, 15.0, 1.5, 4.0, 24.0, 33.3, 35.0,
                                  123456789, 7, 0)
            c.SEQ.pack_into(buf, c.TELEMETRY_SEQ_OFF, 2)
            (Path(tmp) / "ctl").write_bytes(bytes(buf))
            ch.close()
            t = c.ControlChannel(Path(tmp) / "ctl").read_telemetry()
            self.assertEqual((t["frames"], t["freshness_ms"], t["applied_generation"]), (120, 24.0, 7))


class RunnerTests(unittest.TestCase):
    def make(self, tmp, mode):
        from gfg_plugin.frame_os.control_channel import ControlChannel
        from gfg_plugin.frame_os.runner import FrameOsRunner
        reader = FakeReader()
        r = FrameOsRunner(ControlChannel(Path(tmp) / "ctl"), clock=lambda: 0.0, reader_factory=lambda: reader)
        r.configure(enabled=True, mode=mode, output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
        return r, reader

    def published_hz(self, tmp):
        from gfg_plugin.frame_os import control_channel as c
        raw = (Path(tmp) / "ctl").read_bytes()
        return c.POLICY.unpack_from(raw, c.POLICY_OFF)

    def test_observe_reports_would_boost_but_publishes_calm(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r, reader = self.make(tmp, "observe")
            reader.state.feed(ev(0.0, EV_ABS, ABS_RX, 32000))
            status = r.tick(0.0)
            self.assertEqual(status["decision"]["level"], "calm")       # no bank yet
            r.policy.broker.bank_j = 50.0
            reader.state.feed(ev(0.1, EV_ABS, ABS_RX, 31000))
            status = r.tick(0.1)
            self.assertEqual((status["decision"]["level"], status["acting"]), ("boost", False))
            self.assertEqual(self.published_hz(tmp)[4], 30.0)
            self.assertEqual(self.published_hz(tmp)[3], 1, "observe mode")
            self.assertEqual(r.tdp_offset_w, 0.0)

    def test_act_publishes_the_boost_and_its_watts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r, reader = self.make(tmp, "act")
            r.policy.broker.bank_j = 50.0
            reader.state.feed(ev(0.0, EV_ABS, ABS_RX, 32000))
            r.tick(0.0)
            enabled, _t, _p, mode, hz, _m, _w, gen, _ = self.published_hz(tmp)
            self.assertEqual((enabled, mode, hz), (1, 0, 45.0))
            self.assertEqual(r.tdp_offset_w, 4.0)
            self.assertEqual(gen, r.generation)

    def test_disable_and_close_turn_the_layer_off(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r, _ = self.make(tmp, "act")
            r.tick(0.0)
            r.configure(enabled=False, mode="act", output_hz=90, calm_real_hz=30, max_multiplier=3, calm_w=10)
            r.tick(0.1)
            self.assertEqual(self.published_hz(tmp)[0], 0)
            r.close()
            self.assertEqual(self.published_hz(tmp)[0], 0)
