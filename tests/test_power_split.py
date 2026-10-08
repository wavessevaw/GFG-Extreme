"""Smart power split: CPU clock cap logic, its actuator and the root helper's limits."""
import json
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

    def test_helper_refuses_out_of_range_cpu_values(self):
        helper = privileged_power.spawn_helper()
        try:
            with self.assertRaisesRegex(OSError, "value-out-of-range"):
                helper.write(Path("/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"), 50)
        finally:
            helper.close()


if __name__ == "__main__":
    unittest.main()
