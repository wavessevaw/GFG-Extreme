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
        self.assertEqual(p.tick(0, {"idle_s": 25.0}).level, "calm", "gamepad silence is not proof of AFK")
        self.assertEqual(p.tick(0, {"idle_s": 25.0, "idle_verified": True}).level, "rest")
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


def layer_publishes(path, *, last_ns, pid, frames=120, engine=b"DXVK"):
    """What the layer does: telemetry + writer_pid under the seqlock."""
    from gfg_plugin.frame_os import control_channel as c
    buf = bytearray(path.read_bytes())
    c.TELEMETRY.pack_into(buf, c.TELEMETRY_OFF, frames, 118, 1, 12.0, 15.0, 1.5, 4.0, 24.0, 33.3, 35.0,
                          last_ns, 7, 0, 20.5, 0.25, last_ns + 20_000_000, 0, 0, engine)
    c.SEQ.pack_into(buf, c.TELEMETRY_SEQ_OFF, 2)
    c.HEADER.pack_into(buf, 0, c.MAGIC, c.VERSION, c.SIZE, pid)
    path.write_bytes(bytes(buf))     # same inode: the open mapping sees it


class ControlChannelTests(unittest.TestCase):
    def test_layout_matches_control_h(self):
        from gfg_plugin.frame_os import control_channel as c
        header = (ROOT / "engine/gfg-pacer/src/control.h").read_text()
        self.assertIn(f"GFG_CTL_VERSION {c.VERSION}u", header)
        self.assertIn(f"{c.SIZE} bytes", header)
        self.assertIn(f"{c.POLICY.size} bytes", header)
        self.assertIn(f"{c.TELEMETRY.size} bytes", header)
        self.assertIn(f"@{c.TELEMETRY_SEQ_OFF}", header)
        self.assertIn(f"@{c.TELEMETRY_OFF}", header)

    def test_policy_roundtrip_and_telemetry_read(self):
        import os
        import tempfile
        import time
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ctl"
            ch = c.ControlChannel(path)
            before = time.monotonic_ns()
            self.assertTrue(ch.write_policy(enabled=True, real_hz=45.0, mode="shadow", generation=7))
            raw = path.read_bytes()
            self.assertEqual(len(raw), c.SIZE)
            self.assertEqual(c.HEADER.unpack_from(raw, 0)[:3], (c.MAGIC, c.VERSION, c.SIZE))
            self.assertEqual(c.SEQ.unpack_from(raw, c.POLICY_SEQ_OFF)[0] % 2, 0)
            enabled, _ts, _pace, mode, hz, _m, _w, gen, _r, written = c.POLICY.unpack_from(raw, c.POLICY_OFF)
            self.assertEqual((enabled, mode, hz, gen), (1, 2, 45.0, 7))
            self.assertTrue(before <= written <= time.monotonic_ns())
            layer_publishes(path, last_ns=time.monotonic_ns(), pid=os.getpid())
            t = ch.read_telemetry()
            self.assertEqual((t["frames"], t["freshness_ms"], t["applied_generation"]), (120, 24.0, 7))
            self.assertEqual((t["present_hold_ms"], t["acquire_block_ms"], t["engine"], t["passthrough"]),
                             (20.5, 0.25, "DXVK", False))
            self.assertTrue(t["live"])

    def test_live_needs_a_recent_present_and_a_running_writer(self):
        import os
        import tempfile
        import time
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ctl"
            ch = c.ControlChannel(path)
            ch.open()
            layer_publishes(path, last_ns=time.monotonic_ns() - 2_000_000_000, pid=os.getpid())
            self.assertFalse(ch.read_telemetry()["live"], "presented 2 s ago")
            layer_publishes(path, last_ns=time.monotonic_ns(), pid=0)
            self.assertFalse(ch.read_telemetry()["live"], "no writer")
            child = os.fork()
            if child == 0:
                os._exit(0)
            os.waitpid(child, 0)
            layer_publishes(path, last_ns=time.monotonic_ns(), pid=child)
            self.assertFalse(ch.read_telemetry()["live"], "writer exited")
            self.assertTrue(c.pid_alive(1))  # PermissionError (not root) or alive (root): alive either way

    def test_first_open_in_a_process_recreates_the_file(self):
        import os
        import tempfile
        import time
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ctl"
            old = c.ControlChannel(path)                        # a Governor that crashed while acting
            old.write_policy(enabled=True, real_hz=45.0, mode="act", generation=3)
            layer_publishes(path, last_ns=time.monotonic_ns(), pid=os.getpid(), frames=999)
            inode = path.stat().st_ino
            fresh = c.ControlChannel(path)                      # the next Governor process
            t = fresh.read_telemetry()
            self.assertEqual((t["frames"], t["live"]), (0, False))
            self.assertEqual(c.POLICY.unpack_from(path.read_bytes(), c.POLICY_OFF)[0], 0, "old act policy gone")
            self.assertNotEqual(path.stat().st_ino, inode, "new inode: the layer remaps")
            old.close()

    def test_old_version_files_are_replaced(self):
        import tempfile
        from gfg_plugin.frame_os import control_channel as c
        for version, size in ((1, 136), (2, 176)):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ctl"
                raw = bytearray(size)
                c.HEADER.pack_into(raw, 0, c.MAGIC, version, size, 1234)
                path.write_bytes(bytes(raw))
                ch = c.ControlChannel(path)
                self.assertTrue(ch.write_policy(enabled=True, real_hz=30.0))
                raw = path.read_bytes()
                self.assertEqual(c.HEADER.unpack_from(raw, 0), (c.MAGIC, c.VERSION, c.SIZE, 0))
                self.assertEqual(len(raw), c.SIZE)
                ch.close()

    def test_heartbeat_rewrites_only_the_timestamp(self):
        import tempfile
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ctl"
            ch = c.ControlChannel(path)
            self.assertFalse(ch.heartbeat(), "nothing written yet")
            ch.write_policy(enabled=True, real_hz=30.0, mode="observe", generation=4)
            first = c.POLICY.unpack_from(path.read_bytes(), c.POLICY_OFF)
            self.assertTrue(ch.heartbeat())
            second = c.POLICY.unpack_from(path.read_bytes(), c.POLICY_OFF)
            self.assertEqual(first[:9], second[:9])
            self.assertGreater(second[9], first[9])


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
            # without the Governor's executor (adaptive overlay) act keeps the point's cadence and watts
            _e, _t, _p, _mode, hz, _m, _w, _g, _, _x = self.published_hz(tmp)
            self.assertEqual((hz, r.tdp_offset_w), (30.0, 0.0))
            r.executor_active = True
            reader.state.feed(ev(0.05, EV_ABS, ABS_RX, 30000))
            r.tick(0.1)
            enabled, _t, _p, mode, hz, _m, _w, gen, _, _written = self.published_hz(tmp)
            self.assertEqual((enabled, mode, hz), (1, 0, 45.0))
            self.assertEqual(r.tdp_offset_w, 4.0)
            self.assertEqual(gen, r.generation)

    def test_acknowledged_only_from_live_telemetry(self):
        import os
        import tempfile
        import time
        from gfg_plugin.frame_os import control_channel as c
        with tempfile.TemporaryDirectory() as tmp:
            r, _ = self.make(tmp, "observe")
            r.tick(0.0)
            path = Path(tmp) / "ctl"
            layer_publishes(path, last_ns=time.monotonic_ns() - 5_000_000_000,
                                                pid=os.getpid())
            buf = bytearray(path.read_bytes())          # ack the current generation, but stale
            c.TELEMETRY.pack_into(buf, c.TELEMETRY_OFF, *(c.TELEMETRY.unpack_from(buf, c.TELEMETRY_OFF)[:11]),
                                  r.generation, *(c.TELEMETRY.unpack_from(buf, c.TELEMETRY_OFF)[12:]))
            path.write_bytes(bytes(buf))
            self.assertFalse(r.tick(0.1)["acknowledged"])
            buf = bytearray(path.read_bytes())
            values = list(c.TELEMETRY.unpack_from(buf, c.TELEMETRY_OFF))
            values[10] = time.monotonic_ns()
            c.TELEMETRY.pack_into(buf, c.TELEMETRY_OFF, *values)
            path.write_bytes(bytes(buf))
            self.assertTrue(r.tick(0.2)["acknowledged"])

    def test_every_tick_is_a_heartbeat(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r, _ = self.make(tmp, "observe")
            r.tick(0.0)
            first = self.published_hz(tmp)[9]
            r.tick(0.1)                                 # nothing changed: same policy, new timestamp
            self.assertGreater(self.published_hz(tmp)[9], first)

    def test_re_enable_starts_a_fresh_file(self):
        import os
        import tempfile
        import time
        with tempfile.TemporaryDirectory() as tmp:
            r, _ = self.make(tmp, "observe")
            r.tick(0.0)
            path = Path(tmp) / "ctl"
            layer_publishes(path, last_ns=time.monotonic_ns(), pid=os.getpid(), frames=500)
            r.configure(enabled=True, mode="observe", output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
            self.assertEqual(r.tick(0.1)["telemetry"]["frames"], 500, "still enabled: same file")
            r.configure(enabled=False, mode="observe", output_hz=0, calm_real_hz=0, max_multiplier=1, calm_w=None)
            r.tick(0.2)
            r.configure(enabled=True, mode="observe", output_hz=90, calm_real_hz=30, max_multiplier=3.0, calm_w=10.0)
            status = r.tick(0.3)
            self.assertEqual((status["telemetry"]["frames"], status["acknowledged"]), (0, False))

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


class ActExecutorTests(unittest.TestCase):
    def test_rest_cadence_is_x4_at_90_and_calm_when_too_low(self):
        from gfg_plugin.frame_os.policy import InjectionPolicy
        self.assertEqual(InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=4).rest_real_hz, 22.5)
        # field log: a renderer with capacity x3 cannot rest at x4 (output fell to 60)
        self.assertEqual(InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=3).rest_real_hz, 30)
        self.assertEqual(InjectionPolicy(output_hz=60, calm_real_hz=30, max_multiplier=4).rest_real_hz, 30)  # 15 < 20
        p = InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=4)
        d = p.tick(100.0, {"camera": 0, "action": 0, "idle_s": 30.0, "idle_verified": True})
        self.assertEqual((d.level, d.real_hz), ("rest", 22.5))

    def test_injection_deltas(self):
        from gfg_plugin.governor_overlay import injection_deltas
        fixed = {"adaptive": False, "multiplier": 3, "target_fps": 90, "base_fps_cap": 30, "frame_generation_enabled": True}
        out = injection_deltas(fixed, 90, 45, 22.5)
        self.assertEqual((out["adaptive"], out["base_fps_cap"], out["adaptive_max_multiplier"]), (True, 45, 4))
        self.assertEqual(out["multiplier"], 3)
        self.assertIsNone(injection_deltas({**fixed, "adaptive": True}, 90, 45, 22.5))       # fractional point
        self.assertIsNone(injection_deltas({**fixed, "multiplier": 1, "frame_generation_enabled": False}, 90, 45, 22.5))
        self.assertIsNone(injection_deltas(fixed, 90, 30, 22.5))                             # no headroom
        self.assertEqual(injection_deltas(fixed, 90, 80, 22.5)["base_fps_cap"], 45)           # <= output / 2
        x2 = injection_deltas({**fixed, "multiplier": 2, "base_fps_cap": 45}, 90, 60, 45)
        self.assertIsNone(x2, "45x2: boost cap would equal calm")


class SteamUiRestTests(unittest.TestCase):
    def test_steam_ui_rests_at_once(self):
        from gfg_plugin.frame_os.policy import InjectionPolicy
        p = InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=4)
        d = p.tick(10.0, {"camera": 0.9, "action": 0, "idle_s": 0.0}, focused=False)
        self.assertEqual((d.level, d.reason, d.real_hz), ("rest", "steam-ui", 22.5))
        self.assertEqual(p.tick(10.1, {"camera": 0.9, "action": 0, "idle_s": 0.0}, focused=True).level, "boost")

    def test_observer_tracks_gamescope_focus(self):
        import tempfile
        from pathlib import Path
        from gfg_plugin.governor_telemetry import TelemetryObserver
        obs = TelemetryObserver(Path(tempfile.gettempdir()) / "none.log")
        self.assertIsNone(obs.game_focused)
        h = "I MAKO Renderer: present diagnostics: operation=gamescope-focus context=1 state="
        obs.consume_line(h + "steam-ui return_sequence=1 resumed=0 generation_suspended=1", now=1.0)
        self.assertFalse(obs.game_focused)
        obs.consume_line(h + "game return_sequence=1 resumed=1 generation_suspended=0", now=2.0)
        self.assertTrue(obs.game_focused)


class BoostProofTests(unittest.TestCase):
    def test_undelivered_boost_backs_off(self):
        from gfg_plugin.frame_os.policy import InjectionPolicy, BOOST_BACKOFF_S
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        moving = {"camera": 0.9, "action": 0, "idle_s": 0.0}
        t = 100.0
        self.assertEqual(p.tick(t, moving).level, "boost")
        for _ in range(40):                       # 4 s of boost, the layer still sees 30 real
            t += 0.1
            p.note_delivered(t, 30.0)
            p.tick(t, moving)
        d = p.tick(t + 0.1, moving)
        self.assertEqual((d.level, d.reason), ("calm", "boost-ineffective"))
        self.assertEqual(p.tick(t + BOOST_BACKOFF_S + 1, moving).level, "boost")

    def test_delivered_boost_keeps_going(self):
        from gfg_plugin.frame_os.policy import InjectionPolicy
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        moving = {"camera": 0.9, "action": 0, "idle_s": 0.0}
        t = 100.0
        p.tick(t, moving)
        for _ in range(60):
            t += 0.1
            p.note_delivered(t, 44.5)
            self.assertEqual(p.tick(t, moving).level, "boost")


class ReviewFixTests(unittest.TestCase):
    def test_no_input_seen_is_calm_not_rest(self):
        from gfg_plugin.frame_os.policy import InjectionPolicy
        p = InjectionPolicy(output_hz=90, calm_real_hz=30)
        d = p.tick(100.0, {"camera": 0, "action": 0, "idle_s": float("inf")})
        self.assertEqual(d.level, "calm")

    def test_relay_writes_whole_records_only(self):
        import os
        from gfg_plugin.frame_os import input_relay
        from gfg_plugin.frame_os.input_sensor import EVENT
        self.assertEqual(input_relay.PIPE_CHUNK % EVENT.size, 0)
        r, w = os.pipe()
        os.set_blocking(w, False)
        payload = EVENT.pack(1, 0, 3, 3, 100) * 5000          # far more than the pipe holds
        self.assertTrue(input_relay.write_records(w, payload))
        os.set_blocking(r, False)
        got = b""
        while True:
            try:
                chunk = os.read(r, 65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            got += chunk
        self.assertEqual(len(got) % EVENT.size, 0)
        self.assertGreater(len(got), 0)
        os.close(r)
        self.assertFalse(input_relay.write_records(w, payload))  # reader gone
        os.close(w)

    def test_focus_resets_with_a_new_session(self):
        import tempfile
        from pathlib import Path
        from gfg_plugin.governor_telemetry import TelemetryObserver
        obs = TelemetryObserver(Path(tempfile.gettempdir()) / "none.log")
        obs.game_focused = False
        obs._reset_session()
        self.assertIsNone(obs.game_focused)


class RestPowerTests(unittest.TestCase):
    def test_rest_without_a_cadence_drop_keeps_more_watts(self):
        from gfg_plugin.frame_os.policy import EnergyBroker, InjectionPolicy
        x4 = InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=4, broker=EnergyBroker(calm_w=13.0))
        x3 = InjectionPolicy(output_hz=90, calm_real_hz=30, max_multiplier=3, broker=EnergyBroker(calm_w=13.0))
        idle = {"camera": 0, "action": 0, "idle_s": 30.0}
        self.assertEqual(x4.tick(1.0, idle).tdp_w, 13.0 * 0.6)
        d = x3.tick(1.0, idle)
        self.assertEqual((d.real_hz, d.tdp_w), (30, 13.0 * 0.85))


class BenefitTests(unittest.TestCase):
    def feed(self, meter, seconds, **kw):
        t = getattr(meter, "_t", 0.0)
        for _ in range(int(seconds * 10)):
            t += 0.1
            meter.add(t, **kw)
        meter._t = t

    def test_act_rings_from_measurements(self):
        from gfg_plugin.frame_os.benefit import BenefitMeter
        m = BenefitMeter()
        base = dict(acting=True, output_hz=90, calm_real_hz=30, boost_real_hz=45, calm_w=13.0)
        self.feed(m, 50, level="calm", tdp_w=13.0,
                  telemetry={"live": True, "freshness_ms": 13.0, "present_interval_p50_ms": 33.3}, **base)
        self.feed(m, 10, level="boost", tdp_w=17.0,
                  telemetry={"live": True, "freshness_ms": 13.0, "present_interval_p50_ms": 22.2}, **base)
        self.feed(m, 30, level="rest", tdp_w=7.8,
                  telemetry={"live": True, "freshness_ms": 13.0, "present_interval_p50_ms": 33.3}, **base)
        s = m.summary()
        self.assertTrue(s["ready"])
        self.assertFalse(s["estimate"])
        self.assertAlmostEqual(s["response_pct"], 48.0, delta=1.0)    # 25.2 ms baseline -> 13 ms
        self.assertAlmostEqual(s["frames_pct"], 50.0, delta=1.0)
        self.assertAlmostEqual(s["energy_pct"], 100 * (30 * 5.2 - 10 * 4.0) / (90 * 13.0), delta=0.5)

    def test_observe_estimates_and_not_ready_early(self):
        from gfg_plugin.frame_os.benefit import BenefitMeter
        m = BenefitMeter()
        kw = dict(acting=False, level="calm", output_hz=90, calm_real_hz=30, boost_real_hz=45, calm_w=13.0,
                  tdp_w=13.0, telemetry={"live": True, "freshness_ms": 25.0, "present_interval_p50_ms": 33.3})
        self.feed(m, 1, **kw)
        self.assertIsNone(m.summary()["response_pct"])
        self.feed(m, 3, **kw)
        s = m.summary()
        self.assertTrue(s["estimate"])
        self.assertAlmostEqual(s["frames_pct"], 50.0)
        self.assertGreater(s["response_pct"], 0)

    def test_spending_more_than_saving_is_negative(self):
        from gfg_plugin.frame_os.benefit import BenefitMeter
        m = BenefitMeter()
        self.feed(m, 70, acting=True, level="boost", output_hz=90, calm_real_hz=30, boost_real_hz=45,
                  calm_w=13.0, tdp_w=17.0, telemetry={"live": True, "freshness_ms": 13.0, "present_interval_p50_ms": 33.3})
        s = m.summary()
        self.assertLess(s["energy_pct"], 0)
        self.assertAlmostEqual(s["frames_pct"], 0.0, delta=1.0)
