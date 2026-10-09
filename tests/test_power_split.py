"""Smart power split: CPU clock cap logic, its actuator and the root helper's limits."""
import json
import os
from unittest.mock import patch
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin import power_split as ps  # noqa: E402
from gfg_plugin import privileged_power  # noqa: E402
from gfg_plugin.cpu_freq import CpuFreqActuator  # noqa: E402

LADDER = ps.levels_khz(3_500_000, 1_400_000)


def sample(real=30.0, top=40.0, gpu=95.0, mhz=1200.0, draw=9.0, tdp=9.0, target=30.0):
    return ps.Sample(real_fps=real, target_real=target, top_core_pct=top, gpu_busy_pct=gpu,
                     gpu_mhz=mhz, draw_w=draw, tdp_w=tdp)


def run(split, seconds, start=0.0, eligible=True, fn=None, **kw):
    t = start
    while t < start + seconds:
        split.step(t, eligible, fn(t, split) if fn else sample(**kw))
        t = round(t + 1.0, 3)
    return t


class LadderTests(unittest.TestCase):
    def test_steam_deck_ladder(self):
        self.assertEqual(LADDER, [3_500_000, 3_000_000, 2_400_000, 2_100_000, 1_800_000])
        self.assertEqual(ps.levels_khz(1_500_000), [1_500_000], "nothing to cap below the floor")


class PowerSplitTests(unittest.TestCase):
    def test_gpu_bound_game_steps_the_cpu_down_and_holds(self):
        s = ps.PowerSplit(LADDER)
        run(s, 200, top=30.0)
        self.assertGreaterEqual(s.level, 3)
        self.assertEqual(s.best_level, max(s.best_level, s.level))
        self.assertIn(s.phase, ("hold", "probe"))

    def test_settles_before_the_first_step(self):
        s = ps.PowerSplit(LADDER)
        run(s, ps.STEP_GAP_S - 1, top=30.0)
        self.assertEqual(s.level, 0)

    def test_busy_cpu_is_never_capped(self):
        s = ps.PowerSplit(LADDER)
        run(s, 300, top=75.0)
        self.assertEqual(s.level, 0, "75 % at 3.5 GHz would be ~88 % at 3.0 GHz")

    def test_not_gpu_or_power_bound_keeps_the_clock(self):
        s = ps.PowerSplit(LADDER)
        run(s, 300, top=30.0, gpu=50.0, draw=6.0, tdp=9.0)
        self.assertEqual(s.level, 0)

    def test_real_frame_dip_lifts_the_cap_at_once(self):
        s = ps.PowerSplit(LADDER)
        t = run(s, 120, top=30.0)
        self.assertGreater(s.level, 0)
        cap = s.step(t, True, sample(real=25.0, top=30.0))
        self.assertIsNone(cap)
        self.assertEqual((s.level, s.reason), (0, "real-frames-short"))
        # cooldown: no new step right away
        run(s, ps.COOLDOWN_S - 2, start=t + 1, top=30.0)
        self.assertEqual(s.level, 0)

    def test_cpu_near_its_limit_steps_back_up_and_remembers_the_failure(self):
        s = ps.PowerSplit(LADDER)
        t = run(s, ps.STEP_GAP_S + 1, top=30.0)
        self.assertEqual((s.level, s.phase), (1, "probe"))
        s.step(t, True, sample(top=95.0))
        self.assertEqual(s.level, 0)
        self.assertIn(1, s.failed)
        run(s, 300, start=t + 1, top=30.0)
        self.assertEqual(s.level, 0, "the failed level is not tried again within its TTL")

    def test_menu_or_loading_removes_the_cap(self):
        s = ps.PowerSplit(LADDER)
        t = run(s, 120, top=30.0)
        self.assertIsNotNone(s.cap_khz)
        self.assertIsNone(s.step(t, False, sample()))
        self.assertEqual(s.phase, "off")

    def test_switched_off(self):
        s = ps.PowerSplit(LADDER)
        s.enabled = False
        run(s, 200, top=30.0)
        self.assertEqual(s.level, 0)

    def test_remembered_level_is_the_first_stop(self):
        s = ps.PowerSplit(LADDER)
        s.start_level = 3
        run(s, ps.STEP_GAP_S + 1, top=20.0)
        self.assertEqual(s.level, 3)

    def test_ab_pairs_measure_gpu_clock_per_watt(self):
        s = ps.PowerSplit(LADDER)

        def game(t, split):
            # power-bound: the cap gives the GPU 10 % more clock at the same draw
            capped = split.cap_khz is not None
            return sample(top=30.0, mhz=1320.0 if capped else 1200.0)

        run(s, 900, fn=game)
        self.assertGreaterEqual(len(s.pairs), 3)
        self.assertAlmostEqual(s.pairs[-1]["gain"], 10.0, delta=0.5)
        self.assertAlmostEqual(s.pairs[-1]["mhz"], 10.0, delta=0.5)
        summary = s.summary()
        self.assertTrue(summary["measured"])
        self.assertGreater(summary["gain_low"], 0)

    def test_ab_aborts_when_the_governor_moves_the_watts(self):
        s = ps.PowerSplit(LADDER)
        run(s, 900, fn=lambda t, split: sample(top=30.0, tdp=9.0 if int(t) % 7 else 8.5,
                                               draw=9.0 if int(t) % 7 else 8.5))
        self.assertEqual(s.pairs, [])


class SplitMemoryTests(unittest.TestCase):
    def test_useless_split_is_switched_off_at_the_next_session_and_rechecked_later(self):
        m = ps.SplitMemory()
        for _ in range(2):
            m.start_session()
            split = ps.PowerSplit(LADDER)
            split.pairs = [{"gain": g} for g in (0.1, -0.2, 0.0, 0.2, -0.1)]
            split.best_level = 2
            m.record(split)
        self.assertTrue(m.start_session())
        self.assertTrue(m.ruled_out)
        self.assertEqual(m.level, 2)
        for _ in range(ps.RECHECK_SESSIONS - 1):
            self.assertTrue(m.start_session(), "off for RECHECK_SESSIONS sessions")
        self.assertFalse(m.start_session())
        self.assertEqual((m.pairs, m.level), ([], 0))

    def test_a_helping_split_stays(self):
        m = ps.SplitMemory()
        for _ in range(3):
            m.start_session()
            split = ps.PowerSplit(LADDER)
            split.pairs = [{"gain": g} for g in (6.0, 8.0, 7.0, 5.0)]
            m.record(split)
        self.assertFalse(m.start_session())

    def test_damaged_record_loads(self):
        m = ps.SplitMemory({"level": "x", "pairs": [1.0, float("nan"), "y"], "off": None, "sessions": None})
        self.assertEqual((m.level, m.pairs, m.sessions), (0, [1.0], 0))
        self.assertEqual(ps.SplitMemory(json.loads(json.dumps(m.to_record()))).pairs, [1.0])


class CpuFreqActuatorTests(unittest.TestCase):
    def make(self, temp, scaling=3_500_000, policies=2):
        root = Path(temp) / "cpufreq"
        for i in range(policies):
            d = root / f"policy{i}"
            d.mkdir(parents=True)
            (d / "cpuinfo_max_freq").write_text("3500000\n")
            (d / "cpuinfo_min_freq").write_text("1400000\n")
            (d / "scaling_max_freq").write_text(f"{scaling}\n")
        marker = Path(temp) / "state" / "cpu-cap.json"
        return root, CpuFreqActuator(root=root, helper=lambda: None, access=lambda p, m: True, marker=marker)

    def read(self, root, i=0):
        return int((root / f"policy{i}" / "scaling_max_freq").read_text())

    def test_cap_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            self.assertTrue(a.claim())
            self.assertEqual(a.max_khz, 3_500_000)
            self.assertTrue(a.set_cap_khz(2_400_000))
            self.assertEqual((self.read(root, 0), self.read(root, 1)), (2_400_000, 2_400_000))
            self.assertTrue(a.marker.exists())
            self.assertTrue(a.restore())
            self.assertEqual(self.read(root), 3_500_000)
            self.assertFalse(a.marker.exists())

    def test_never_above_the_users_own_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp, scaling=2_800_000)
            a.claim()
            self.assertEqual(a.max_khz, 2_800_000)
            a.set_cap_khz(3_000_000)
            self.assertEqual(self.read(root), 2_800_000)
            a.restore()
            self.assertEqual(self.read(root), 2_800_000)

    def test_outside_change_pauses_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            a.set_cap_khz(2_400_000)
            (root / "policy0" / "scaling_max_freq").write_text("2000000\n")   # PowerTools
            self.assertFalse(a.set_cap_khz(2_100_000))
            self.assertTrue(a.external_change)
            self.assertFalse(a.restore())
            self.assertEqual(self.read(root), 2_000_000)
            self.assertEqual(self.read(root, 1), 3_500_000, "other owned policies must recover")

    def test_crashed_session_is_recovered_at_the_next_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            a.set_cap_khz(2_100_000)            # the plugin dies here
            b = CpuFreqActuator(root=root, helper=lambda: None, access=lambda p, m: True, marker=a.marker)
            self.assertTrue(b.discover())
            self.assertEqual(self.read(root), 3_500_000)
            self.assertFalse(a.marker.exists())

    def test_crash_recovery_leaves_an_outside_value_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            a.set_cap_khz(2_100_000)
            (root / "policy0" / "scaling_max_freq").write_text("1800000\n")
            b = CpuFreqActuator(root=root, helper=lambda: None, access=lambda p, m: True, marker=a.marker)
            b.discover()
            self.assertEqual(self.read(root, 0), 1_800_000)
            self.assertEqual(self.read(root, 1), 3_500_000)

    def fail_policy_write(self, policy, value=None):
        original = Path.write_text
        def write(path, text, *args, **kwargs):
            if path.parent.name == policy and path.name == "scaling_max_freq":
                if value is None or str(value) == text.strip():
                    raise OSError("CPU policy busy")
            return original(path, text, *args, **kwargs)
        return patch.object(Path, "write_text", write)

    def test_partial_first_cap_is_restored_even_without_committed_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            with self.fail_policy_write("policy1"):
                self.assertFalse(a.set_cap_khz(2_100_000))
            self.assertIsNone(a.cap_khz)
            self.assertTrue(a.restore_pending)
            self.assertEqual(self.read(root, 0), 2_100_000)
            self.assertTrue(a.restore())
            self.assertEqual([self.read(root, i) for i in range(2)], [3_500_000, 3_500_000])
            self.assertFalse(a.marker.exists())

    def test_crash_during_a_second_cap_recovers_both_old_and_new_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim(); a.set_cap_khz(2_400_000)
            with self.fail_policy_write("policy1"):
                self.assertFalse(a.set_cap_khz(2_100_000))
            self.assertEqual([self.read(root, i) for i in range(2)], [2_100_000, 2_400_000])
            b = CpuFreqActuator(root=root, helper=lambda: None, access=lambda *_: True, marker=a.marker)
            b.discover()
            self.assertEqual([self.read(root, i) for i in range(2)], [3_500_000, 3_500_000])
            self.assertFalse(b.restore_pending)

    def test_failed_crash_recovery_keeps_undo_and_blocks_a_new_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim(); a.set_cap_khz(2_100_000)
            b = CpuFreqActuator(root=root, helper=lambda: None, access=lambda *_: True, marker=a.marker)
            with self.fail_policy_write("policy1", 3_500_000):
                b.discover()
                self.assertTrue(b.restore_pending)
                self.assertTrue(a.marker.exists())
                self.assertFalse(b.claim(), "a leftover GFG cap is not the user's limit")
            self.assertEqual(self.read(root, 0), 3_500_000)
            self.assertEqual(self.read(root, 1), 2_100_000)
            self.assertTrue(b.claim(), "retry completes undo before claiming")
            self.assertEqual(b.initial[root / "policy1" / "scaling_max_freq"], 3_500_000)
            self.assertFalse(a.marker.exists())

    def test_recovery_requires_readback_not_just_a_successful_write_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim(); a.set_cap_khz(2_100_000)
            b = CpuFreqActuator(root=root, helper=lambda: None, access=lambda *_: True, marker=a.marker)
            original = Path.write_text
            def ignored(path, text, *args, **kwargs):
                if path.name == "scaling_max_freq":
                    return len(text)
                return original(path, text, *args, **kwargs)
            with patch.object(Path, "write_text", ignored):
                b.discover()
                self.assertTrue(b.restore_pending)
                self.assertTrue(a.marker.exists())
                self.assertFalse(b.claim())
            self.assertTrue(b.restore())
            self.assertEqual(self.read(root), 3_500_000)

    def test_no_frequency_write_without_a_saved_undo_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            original = Path.write_text
            def full_disk(path, text, *args, **kwargs):
                if path.name == "cpu-cap.json.tmp":
                    raise OSError("disk full")
                return original(path, text, *args, **kwargs)
            with patch.object(Path, "write_text", full_disk):
                self.assertFalse(a.set_cap_khz(2_100_000))
            self.assertEqual([self.read(root, i) for i in range(2)], [3_500_000, 3_500_000])
            self.assertIn("marker", a.error)

    def test_unreadable_recovery_marker_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.marker.parent.mkdir(parents=True)
            a.marker.write_text("{")
            a.discover()
            self.assertTrue(a.restore_pending)
            self.assertFalse(a.claim())
            self.assertEqual(a.marker.read_text(), "{")
            self.assertEqual(self.read(root), 3_500_000)

    def test_successful_helper_reply_with_late_readback_stays_owned(self):
        class LateReadback:
            pending = None
            def write(self, path, value):
                self.pending = (path, value)  # accepted, but sysfs has not changed
            def restore_cpu(self, path, value):
                if self.pending and self.pending[0] == path:
                    self.pending = None  # ordered undo supersedes our accepted write
                path.write_text(f"{value}\n")
        for lands in (False, True):
            with self.subTest(lands=lands), tempfile.TemporaryDirectory() as temp:
                root, a = self.make(temp, policies=8)
                helper = LateReadback()
                a._helper = lambda: helper
                events = []
                a.journal = lambda kind, **fields: events.append(kind)
                with patch("gfg_plugin.cpu_freq.allowed_cpu_path", side_effect=lambda p: p):
                    self.assertTrue(a.claim())
                    self.assertFalse(a.set_cap_khz(3_000_000))
                    self.assertTrue(a.restore_pending)
                    self.assertIsNone(a.cap_khz)
                    if lands:
                        path, value = helper.pending
                        path.write_text(f"{value}\n")
                        self.assertEqual(a.status()["observed_policy_caps_khz"]["policy0"], 3_000_000)
                    self.assertTrue(a.restore())
                    self.assertFalse(a.external_change)
                    self.assertFalse(a.restore_pending)
                    self.assertNotIn("cpu-cap-external-change", events)
                    self.assertEqual([self.read(root, i) for i in range(8)], [3_500_000]*8)
                    self.assertFalse(a.marker.exists())
                    self.assertIsNone(helper.pending)

    def test_late_helper_cap_remains_ours_and_can_be_restored(self):
        class Late:
            once = True
            def write(self, path, value):
                if self.once:
                    self.once = False
                    raise privileged_power.HelperTimeout("reply late")
                path.write_text(f"{value}\n")
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp, policies=1)
            late = Late()
            a._helper = lambda: late
            with patch.object(privileged_power, "allowed_cpu_path", side_effect=lambda p: p), \
                 patch("gfg_plugin.cpu_freq.allowed_cpu_path", side_effect=lambda p: p):
                a.claim()
                self.assertFalse(a.set_cap_khz(2_100_000))
                (root / "policy0" / "scaling_max_freq").write_text("2100000\n")
                self.assertTrue(a.restore())
                self.assertFalse(a.external_change)
                self.assertEqual(self.read(root), 3_500_000)
                self.assertFalse(a.marker.exists())

    def test_live_external_change_to_a_previous_cap_is_not_reclaimed(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim(); a.set_cap_khz(2_400_000); a.set_cap_khz(2_100_000)
            (root / "policy0" / "scaling_max_freq").write_text("2400000\n")
            self.assertFalse(a.set_cap_khz(1_800_000))
            self.assertEqual(self.read(root, 0), 2_400_000)
            self.assertEqual(self.read(root, 1), 3_500_000)

    def test_failed_commit_still_keeps_the_write_ahead_undo(self):
        with tempfile.TemporaryDirectory() as temp:
            root, a = self.make(temp)
            a.claim()
            original, count = Path.write_text, [0]
            def fail_commit(path, text, *args, **kwargs):
                if path.name == "cpu-cap.json.tmp":
                    count[0] += 1
                    if count[0] == 2:
                        raise OSError("disk full during journal commit")
                return original(path, text, *args, **kwargs)
            with patch.object(Path, "write_text", fail_commit):
                self.assertFalse(a.set_cap_khz(2_100_000))
            self.assertTrue(a.marker.exists())
            self.assertTrue(a.restore_pending)
            self.assertTrue(a.restore())
            self.assertEqual([self.read(root, i) for i in range(2)], [3_500_000, 3_500_000])

    def test_no_cpufreq(self):
        with tempfile.TemporaryDirectory() as temp:
            a = CpuFreqActuator(root=Path(temp) / "none", helper=lambda: None, access=lambda p, m: True)
            self.assertFalse(a.discover())
            self.assertFalse(a.claim())
            self.assertFalse(a.set_cap_khz(2_000_000))


class HelperPathTests(unittest.TestCase):
    def test_only_scaling_max_freq_is_allowed(self):
        ok = "/sys/devices/system/cpu/cpufreq/policy3/scaling_max_freq"
        self.assertEqual(privileged_power.allowed_cpu_path(ok), ok)
        for bad in ("/sys/devices/system/cpu/cpufreq/policy3/scaling_min_freq",
                    "/sys/devices/system/cpu/cpufreq/policy3/../../../../../etc/passwd",
                    "/sys/devices/system/cpu/cpufreq/policy3/scaling_governor", "/tmp/scaling_max_freq"):
            self.assertIsNone(privileged_power.allowed_cpu_path(bad), bad)
        self.assertIsNone(privileged_power.allowed_cap_path(ok), "not a TDP cap")

    def test_helper_restores_its_cpu_caps_when_the_plugin_is_gone(self):
        values = {"a": 2_100_000, "b": 1_800_000, "c": 3_500_000}
        writes = []
        restored = privileged_power.restore_cpu_caps(
            {"a": (3_500_000, 2_100_000), "b": (3_500_000, 2_100_000), "c": (3_500_000, 3_500_000)},
            read=values.get, write=lambda p, v: writes.append((p, v)))
        self.assertEqual(restored, ["a"], "b was changed by someone else, c was never capped")
        self.assertEqual(writes, [("a", 3_500_000)])

    def serve_cpu_requests(self, requests, values, write_fn=None, ledger=None):
        name = "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
        def write_value(path, value):
            values[path] = value
            if write_fn:
                write_fn(path, value)
        req_read, req_write = os.pipe()
        rep_read, rep_write = os.pipe()
        ledger = {} if ledger is None else ledger
        try:
            os.write(req_write, requests.encode())
            os.close(req_write); req_write = None
            with patch.object(privileged_power, "_read_value", side_effect=values.get), \
                 patch.object(privileged_power, "_write_value", side_effect=write_value):
                privileged_power._serve_loop(req_read, rep_write, ledger)
            os.close(rep_write); rep_write = None
            replies = os.read(rep_read, 4096).decode()
            return ledger, replies
        finally:
            for fd in (req_read, req_write, rep_read, rep_write):
                if fd is not None:
                    os.close(fd)

    def test_helper_rebases_original_after_an_outside_cpu_change(self):
        p = "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
        values = {p: 3_500_000}
        def outside(path, value):
            if value == 2_400_000:
                values[path] = 2_000_000
        ledger, replies = self.serve_cpu_requests(f"{p} 2400000\n{p} 1800000\n", values, outside)
        self.assertEqual(replies, "ok\nok\n")
        self.assertEqual(ledger[p], (2_000_000, 1_800_000))
        privileged_power.restore_cpu_caps(ledger, read=values.get, write=lambda p, v: values.update({p: v}))
        self.assertEqual(values[p], 2_000_000, "helper exit must preserve the new user's limit")

    def test_helper_does_not_undo_a_replayed_crash_restore_on_exit(self):
        p = "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
        values = {p: 2_100_000}
        ledger, replies = self.serve_cpu_requests(f"restore-cpu {p} 3500000\n", values)
        self.assertEqual(replies, "ok\n")
        self.assertEqual(values[p], 3_500_000)
        self.assertEqual(ledger, {})
        self.assertEqual(privileged_power.restore_cpu_caps(ledger, read=values.get, write=lambda *_: None), [])

    def test_helper_restore_does_not_overwrite_an_outside_change(self):
        p = "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"
        values = {p: 2_000_000}
        ledger, replies = self.serve_cpu_requests(f"restore-cpu {p} 3500000\n", values,
                                                ledger={p: (3_500_000, 2_100_000)})
        self.assertIn("external-cpu-change", replies)
        self.assertEqual(values[p], 2_000_000)

    def test_restore_cpu_command_cannot_write_a_ppt_cap(self):
        p = "/sys/devices/pci0000:00/0000:00:08.1/0000:04:00.0/hwmon/hwmon3/power1_cap"
        values = {p: 15_000_000}
        ledger, replies = self.serve_cpu_requests(f"restore-cpu {p} 20000000\n", values)
        self.assertIn("path-not-allowed", replies)
        self.assertEqual(values[p], 15_000_000)
        self.assertEqual(ledger, {})

    def test_helper_refuses_out_of_range_cpu_values(self):
        helper = privileged_power.spawn_helper()
        try:
            with self.assertRaisesRegex(OSError, "value-out-of-range"):
                helper.write(Path("/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"), 50)
        finally:
            helper.close()


if __name__ == "__main__":
    unittest.main()
