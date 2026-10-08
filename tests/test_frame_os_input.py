import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.frame_os import input_relay  # noqa: E402
from gfg_plugin.frame_os.input_sensor import EV_ABS, EV_KEY, EVENT, ABS_RX, EvdevReader  # noqa: E402
from gfg_plugin.frame_os.runner import FrameOsRunner  # noqa: E402

PAD_ABS = "3001b"            # X Y RX RY (+Z RZ, HAT) -> bits 0,1,3,4 set
PAD_KEY = "7fdb000000000000 0 0 0 0"   # BTN_SOUTH (0x130) region set
KEYBOARD_ABS = "0"


def rec(t, etype, code, value):
    return EVENT.pack(int(t), int((t % 1) * 1e6), etype, code, value)


class GamepadDetectionTests(unittest.TestCase):
    def fake_sys(self, root, devices):
        for name, (title, abs_caps, key_caps) in devices.items():
            caps = root / name / "device" / "capabilities"
            caps.mkdir(parents=True)
            (caps / "abs").write_text(abs_caps + "\n")
            (caps / "key").write_text(key_caps + "\n")
            (root / name / "device" / "name").write_text(title + "\n")

    def test_virtual_pad_found_keyboard_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_sys(root, {
                "event3": ("Steam Deck", PAD_ABS, PAD_KEY),
                "event9": ("Microsoft X-Box 360 pad 0", PAD_ABS, PAD_KEY),
                "event1": ("AT Translated Set 2 keyboard", KEYBOARD_ABS, "ffffffff"),
                "mouse0": ("not an event node", PAD_ABS, PAD_KEY),
            })
            found = input_relay.gamepad_event_nodes(root, Path("/dev/input"))
            self.assertEqual(sorted(p.name for p in found), ["event3", "event9"])
            self.assertEqual(found[Path("/dev/input/event9")], "Microsoft X-Box 360 pad 0")

    def test_capability_parsing(self):
        self.assertTrue(input_relay.is_gamepad(PAD_ABS, PAD_KEY))
        self.assertFalse(input_relay.is_gamepad("3", PAD_KEY))         # no right stick
        self.assertFalse(input_relay.is_gamepad(PAD_ABS, "0"))         # no face buttons
        self.assertFalse(input_relay.is_gamepad("zz", PAD_KEY))

    def test_only_sticks_and_buttons_are_forwarded(self):
        data = rec(1.0, EV_ABS, ABS_RX, 20000) + rec(1.0, 0x00, 0, 0) + rec(1.0, EV_KEY, 0x130, 1) + rec(1.0, 0x04, 4, 9)
        out = input_relay.filter_records(data)
        self.assertEqual(len(out), 2 * EVENT.size)


class RelayPipeTests(unittest.TestCase):
    def test_gamepad_set_hotplug_and_filtering(self):
        with tempfile.TemporaryDirectory() as temp:
            fifo = Path(temp) / "event9"
            os.mkfifo(fifo)
            nodes = {fifo: "Microsoft X-Box 360 pad 0"}
            pads = input_relay.GamepadSet(scan=lambda: dict(nodes))
            pads.rescan(0.0)
            self.assertEqual(list(pads.names.values()), ["Microsoft X-Box 360 pad 0"])
            writer = os.open(str(fifo), os.O_WRONLY | os.O_NONBLOCK)
            os.write(writer, rec(1.0, EV_ABS, ABS_RX, 100) + rec(1.0, 0x00, 0, 0))
            self.assertEqual(len(pads.read_ready(0.1)), EVENT.size)
            nodes.clear()
            pads.rescan(1.0)                  # within RESCAN_S: unchanged
            self.assertEqual(len(pads.fds), 1)
            pads.rescan(5.0)                  # unplugged
            self.assertEqual(len(pads.fds), 0)
            os.close(writer)
            pads.close()

    def test_reader_handles_split_records_and_status(self):
        r, w = os.pipe()
        os.set_blocking(r, False)
        reader = EvdevReader(fds=[r], owned=False, source="relay")
        payload = input_relay.status_record(2) + rec(10.0, EV_ABS, ABS_RX, 30000) + rec(10.0, EV_KEY, 0x130, 1)
        os.write(w, payload[:30])                      # ends mid-record
        reader.poll()
        os.write(w, payload[30:])
        reader.poll()
        status = reader.status()
        self.assertEqual((status["source"], status["gamepads"], status["events"]), ("relay", 2, 2))
        self.assertGreater(reader.state.snapshot(10.05)["camera"], 0.5)
        reader.close()                                 # not owned: the shared relay fd stays open
        os.write(w, b"x")
        self.assertEqual(os.read(r, 1), b"x")
        os.close(r)
        os.close(w)

    def test_runner_retries_when_no_gamepad_yet(self):
        made = []

        class Empty:
            available = False
            state = __import__("gfg_plugin.frame_os.input_sensor", fromlist=["InputState"]).InputState()

            def poll(self):
                return 0

            def status(self):
                return {"source": "none", "gamepads": 0, "events": 0}

            def close(self):
                pass

        def factory():
            made.append(1)
            return Empty()

        channel = type("C", (), {"read_telemetry": lambda self: {}, "write_policy": lambda self, **k: True,
                                 "heartbeat": lambda self: True, "reset": lambda self: None, "_map": None})()
        runner = FrameOsRunner(channel=channel, reader_factory=factory)
        runner.configure(enabled=True, mode="observe", output_hz=90, calm_real_hz=30, max_multiplier=3, calm_w=None)
        runner.tick(100.0)
        runner.tick(101.0)
        self.assertEqual(len(made), 1)
        runner.tick(106.0)
        self.assertEqual(len(made), 2)
        self.assertEqual(runner.last["input_sensor"]["source"], "none")
        self.assertIsNone(runner.last["input_sensor"]["idle_s"])


if __name__ == "__main__":
    unittest.main()
