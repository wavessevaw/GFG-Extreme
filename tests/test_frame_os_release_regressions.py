"""Regression coverage for failures found while reviewing GFG Extreme 1.2.0."""
import errno
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.frame_os.control_channel import ControlChannel
from gfg_plugin.frame_os.input_sensor import (
    ABS_RX, ABS_X, EV_ABS, EVENT, STATUS_TYPE, EvdevReader, InputState,
)
from gfg_plugin.frame_os.policy import InjectionPolicy
from gfg_plugin.frame_os.runner import FrameOsRunner


class InputRegressionTests(unittest.TestCase):
    def test_held_sticks_do_not_trigger_idle_rest(self):
        for axis in (ABS_X, ABS_RX):
            with self.subTest(axis=axis):
                state = InputState()
                state.event(10.0, EV_ABS, axis, 30000)
                snapshot = state.snapshot(40.0)
                self.assertEqual(snapshot["idle_s"], 0.0)
                policy = InjectionPolicy(output_hz=90, calm_real_hz=30)
                self.assertNotEqual(policy.tick(40.0, snapshot).level, "rest")
                state.event(41.0, EV_ABS, axis, 0)
                self.assertEqual(policy.tick(70.0, state.snapshot(70.0)).level, "rest")

    def test_no_devices_clears_held_activity(self):
        state = InputState()
        state.event(10.0, EV_ABS, ABS_RX, 30000)
        state.event(11.0, STATUS_TYPE, 0, 0)
        self.assertEqual(state.snapshot(12.0), {"camera": 0.0, "action": 0.0, "idle_s": float("inf")})

    def test_eof_removes_owned_fd_and_partial_record(self):
        read_fd, write_fd = os.pipe()
        os.set_blocking(read_fd, False)
        reader = EvdevReader(fds=[read_fd])
        try:
            os.write(write_fd, EVENT.pack(10, 0, EV_ABS, ABS_RX, 30000) + b"x")
            reader.poll()
            self.assertIn(read_fd, reader._rest)
            os.close(write_fd)
            write_fd = None
            reader.poll()
            self.assertFalse(reader.available)
            self.assertEqual(reader._rest, {})
            self.assertEqual(reader.state.snapshot(40)["camera"], 0)
            with self.assertRaises(OSError):
                os.fstat(read_fd)
        finally:
            reader.close()
            if write_fd is not None:
                os.close(write_fd)

    def test_eof_does_not_close_borrowed_fd(self):
        read_fd, write_fd = os.pipe()
        os.set_blocking(read_fd, False)
        reader = EvdevReader(fds=[read_fd], owned=False, source="relay")
        os.close(write_fd)
        try:
            reader.poll()
            self.assertFalse(reader.available)
            os.fstat(read_fd)
        finally:
            reader.close()
            os.close(read_fd)

    def test_unplug_error_is_not_reported_available(self):
        reader = EvdevReader(fds=[123], owned=False)
        with patch("gfg_plugin.frame_os.input_sensor.os.read", side_effect=OSError(errno.ENODEV, "unplugged")):
            reader.poll()
        self.assertFalse(reader.available)


class RunnerRegressionTests(unittest.TestCase):
    def runner(self, path):
        return FrameOsRunner(ControlChannel(path), reader_factory=lambda: EvdevReader())

    def configure(self, runner, enabled=True, calm_w=10):
        runner.configure(enabled=enabled, mode="act", output_hz=90,
                         calm_real_hz=30, max_multiplier=3, calm_w=calm_w)

    def test_failed_publication_is_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.runner(Path(temp) / "control")
            self.configure(runner)
            try:
                with patch.object(runner.channel, "write_policy", return_value=False):
                    self.assertFalse(runner.tick(1)["acknowledged"])
                    self.assertIsNone(runner._published)
                runner.tick(2)
                self.assertIsNotNone(runner._published)
                self.assertTrue(runner.channel.heartbeat())
            finally:
                runner.close()

    def test_failed_heartbeat_republishes_full_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.runner(Path(temp) / "control")
            self.configure(runner)
            try:
                runner.tick(1)
                with patch.object(runner.channel, "heartbeat", return_value=False):
                    runner.tick(2)
                self.assertIsNone(runner._published)
                with patch.object(runner.channel, "write_policy", wraps=runner.channel.write_policy) as write:
                    runner.tick(3)
                    write.assert_called_once()
            finally:
                runner.close()

    def test_new_session_discards_energy_and_boost_backoff(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.runner(Path(temp) / "control")
            self.configure(runner)
            try:
                runner.tick(1)
                old_policy = runner.policy
                runner.policy.broker.bank_j = 100
                runner.policy._boost_blocked_until = 99999
                self.configure(runner, enabled=False)
                runner.tick(2)
                self.configure(runner)
                self.assertIsNot(runner.policy, old_policy)
                self.assertEqual(runner.policy.broker.bank_j, 0)
                self.assertLess(runner.policy._boost_blocked_until, 0)
                self.assertIsNone(runner.reader)
                self.assertEqual(runner.last, {})
            finally:
                runner.close()

    def test_power_ownership_changes_update_broker(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.runner(Path(temp) / "control")
            try:
                self.configure(runner, calm_w=None)
                self.assertIsNone(runner.policy.broker)
                self.configure(runner, calm_w=12)
                self.assertEqual(runner.policy.broker.calm_w, 12)
                self.configure(runner, calm_w=None)
                self.assertIsNone(runner.policy.broker)
            finally:
                runner.close()

    def test_close_releases_mapping_and_fd(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.runner(Path(temp) / "control")
            self.configure(runner)
            runner.tick(1)
            fd = runner.channel._fd
            runner.close()
            self.assertIsNone(runner.channel._map)
            self.assertIsNone(runner.channel._fd)
            self.assertFalse(runner.enabled)
            with self.assertRaises(OSError):
                os.fstat(fd)
            runner.close()


class ChannelRegressionTests(unittest.TestCase):
    def test_mapping_failure_closes_opened_fd(self):
        with tempfile.TemporaryDirectory() as temp:
            channel = ControlChannel(Path(temp) / "control")
            real_open = os.open
            opened = []

            def capture(*args, **kwargs):
                fd = real_open(*args, **kwargs)
                opened.append(fd)
                return fd

            with patch("gfg_plugin.frame_os.control_channel.os.open", side_effect=capture), patch(
                "gfg_plugin.frame_os.control_channel.mmap.mmap",
                side_effect=OSError(errno.ENOMEM, "mapping failed"),
            ):
                self.assertFalse(channel.open())
            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])
            self.assertTrue(channel.open(), "recovery after a transient failure")
            channel.close()


if __name__ == "__main__":
    unittest.main()
