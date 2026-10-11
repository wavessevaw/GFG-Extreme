"""Governor runtime overlay: Saved is never written; failures never corrupt."""
import hashlib
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))
TEMP_HOME = tempfile.mkdtemp(prefix="gfg-overlay-home-")
decky = types.ModuleType("decky")
decky.logger = logging.getLogger("decky-test")
decky.DECKY_USER_HOME = TEMP_HOME
sys.modules.setdefault("decky", decky)
HOME = sys.modules["decky"].DECKY_USER_HOME

from gfg_plugin.config_schema import ConfigurationManager  # noqa: E402
from gfg_plugin.configuration import ConfigurationService  # noqa: E402
from gfg_plugin.governor_overlay import (  # noqa: E402
    LAUNCH_HEADER,
    LIVE_FIELDS,
    OverlayStore,
    PointNotApplicable,
    base_deltas,
    overlay_path,
    parse_launch_line,
    point_deltas,
)

P45 = {"key": "45x2", "target_output_fps": 90, "base_target_fps": 45, "multiplier": 2, "render_scale_pct": 100}
P30 = {"key": "30x3", "target_output_fps": 90, "base_target_fps": 30, "multiplier": 3, "render_scale_pct": 100}
N90 = {"key": "native90", "target_output_fps": 90, "base_target_fps": 90, "multiplier": 1, "render_scale_pct": 100}
P30S90 = {"key": "30x3-s90", "target_output_fps": 90, "base_target_fps": 30, "multiplier": 3, "render_scale_pct": 90}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OverlayTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(HOME, ignore_errors=True)
        os.makedirs(HOME)
        self.svc = ConfigurationService()
        self.assertTrue(self.svc.create_profile("game", "mako")["success"])
        self.assertTrue(self.svc.create_profile("other", "mako")["success"])
        self.store = OverlayStore(self.svc.config_dir, self.svc.build_governor_overlay_text, owner_pid=4242)
        self.saved = self.svc.get_profile_config("game")["config"]

    def profile_of(self, text, name):
        data = ConfigurationManager.parse_toml_content_multi_profile(text)
        return data["profiles"][name]

    def test_overlay_applies_deltas_to_one_profile_and_never_touches_saved(self):
        before = sha(self.svc.config_file_path)
        rec = self.store.write("game", point_deltas(P30, self.saved, scale_capable=False, scale_ready=False), point_key="30x3")
        self.assertEqual(sha(self.svc.config_file_path), before)
        text = Path(rec.path).read_text()
        game = self.profile_of(text, "game")
        self.assertEqual((game["multiplier"], game["base_fps_cap"], game["adaptive"], game["frame_generation_enabled"]), (3, 30, False, True))
        other = self.profile_of(text, "other")
        saved_other = self.svc.get_profile_config("other")["config"]
        for key in ("multiplier", "base_fps_cap", "adaptive", "target_fps"):
            self.assertEqual(other[key], saved_other[key])
        # Saved profile fields are unchanged on disk.
        self.assertEqual(self.svc.get_profile_config("game")["config"], self.saved)

    def test_header_lease_and_revision_increment(self):
        r1 = self.store.write("game", {}, point_key="base")
        r2 = self.store.write("game", point_deltas(P45, self.saved, scale_capable=False, scale_ready=False), point_key="45x2")
        self.assertEqual((r1.revision, r2.revision), (1, 2))
        first = Path(r2.path).read_text().splitlines()[0]
        self.assertTrue(first.startswith(LAUNCH_HEADER))
        self.assertEqual(parse_launch_line(first[len(LAUNCH_HEADER):]), {"scaling": 0, "rev": 2, "owner": 4242})
        released = self.store.write("game", {}, point_key="released", released=True)
        self.assertEqual(self.store.read_header("game")["owner"], 0)
        self.assertEqual(released.revision, 3)

    def test_revision_survives_store_restart(self):
        self.store.write("game", {})
        self.store.write("game", {})
        fresh = OverlayStore(self.svc.config_dir, self.svc.build_governor_overlay_text, owner_pid=1)
        self.assertEqual(fresh.write("game", {}).revision, 3)

    def test_atomic_write_failure_keeps_previous_overlay_intact(self):
        self.store.write("game", point_deltas(P45, self.saved, scale_capable=False, scale_ready=False), point_key="45x2")
        path = overlay_path(self.svc.config_dir, "game")
        good = path.read_text()

        def boom(src, dst):
            raise OSError("disk full")
        failing = OverlayStore(self.svc.config_dir, self.svc.build_governor_overlay_text, owner_pid=4242, replace=boom)
        with self.assertRaises(OSError):
            failing.write("game", point_deltas(P30, self.saved, scale_capable=False, scale_ready=False))
        self.assertEqual(path.read_text(), good)
        leftovers = [p for p in path.parent.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_native_point_disables_fg_without_changing_saved_multiplier(self):
        d = point_deltas(N90, self.saved, scale_capable=False, scale_ready=False)
        self.assertFalse(d["frame_generation_enabled"])
        self.assertEqual(d["multiplier"], int(self.saved["multiplier"]))
        self.assertEqual(d["base_fps_cap"], 90)

    def test_fractional_x15_uses_pinned_adaptive_mode(self):
        point = {"key": "60x1.5", "target_output_fps": 90, "base_target_fps": 60, "multiplier": 1.5, "render_scale_pct": 100}
        d = point_deltas(point, self.saved, scale_capable=False, scale_ready=False)
        self.assertEqual((d["adaptive"], d["target_fps"], d["base_fps_cap"]), (True, 90, 60))
        self.assertFalse(d["adaptive_auto_base_fps_cap"])
        self.assertFalse(d["adaptive_stable_cadence"])
        self.assertEqual(d["adaptive_max_multiplier"], 2)
        self.assertTrue(d["frame_generation_enabled"])
        self.assertTrue(set(d) <= LIVE_FIELDS | {"multiplier"})
        # the projection must accept it without silently normalising anything
        self.store.write("game", d, point_key="60x1.5")

    def test_quarter_step_fractions_are_expressible_up_to_x3(self):
        for m, base in ((1.25, 72), (1.75, 51), (2.25, 40), (2.5, 36), (2.75, 33)):
            point = {"key": f"{base}x{m:g}", "target_output_fps": 90, "base_target_fps": base,
                     "multiplier": m, "render_scale_pct": 100}
            d = point_deltas(point, self.saved, scale_capable=False, scale_ready=False)
            self.assertEqual((d["adaptive"], d["base_fps_cap"], d["target_fps"]), (True, base, 90))
            self.assertEqual(d["adaptive_max_multiplier"], max(2, int(-(-m // 1))))
            self.store.write("game", d, point_key=point["key"])  # projection accepts it unchanged

    def test_multipliers_outside_one_to_four_are_not_expressible(self):
        for m in (0.5, 0.75, 4.5, 5):
            point = {"key": "x", "target_output_fps": 90, "base_target_fps": 36, "multiplier": m, "render_scale_pct": 100}
            with self.assertRaises(PointNotApplicable):
                point_deltas(point, self.saved, scale_capable=False, scale_ready=False)

    def test_x5_is_never_expressible_x4_is_the_last_resort(self):
        bad = dict(P30, multiplier=5)
        with self.assertRaises(PointNotApplicable):
            point_deltas(bad, self.saved, scale_capable=False, scale_ready=False)
        x4 = point_deltas(dict(P30, multiplier=4, base_target_fps=23), self.saved,
                          scale_capable=False, scale_ready=False)
        self.assertEqual((x4["multiplier"], x4["adaptive"], x4["base_fps_cap"]), (4, False, 23))

    def test_fractions_above_x3_use_adaptive_with_ceiling_four(self):
        p = dict(P30, multiplier=3.5, base_target_fps=26)
        d = point_deltas(p, self.saved, scale_capable=False, scale_ready=False)
        self.assertEqual((d["adaptive"], d["adaptive_max_multiplier"], d["base_fps_cap"]), (True, 4, 26))

    def test_scaled_point_requires_launch_provisioned_engine(self):
        with self.assertRaises(PointNotApplicable) as ctx:
            point_deltas(P30S90, self.saved, scale_capable=False, scale_ready=False)
        self.assertEqual(ctx.exception.reason, "scaling-engine-not-provisioned-at-launch")
        # Capability claimed but neither Saved scaling nor scale-ready: still refused.
        with self.assertRaises(PointNotApplicable):
            point_deltas(P30S90, self.saved, scale_capable=True, scale_ready=False)

    def test_scale_ready_base_provisions_engine_and_scaled_point_is_live(self):
        base = base_deltas(self.saved, scale_ready=True)
        self.assertEqual(base["scaling_enabled"], True)
        rec = self.store.write("game", base, point_key="base")
        self.assertTrue(rec.scaling_provisioned)
        self.assertEqual(self.store.read_header("game")["scaling"], 1)
        d = point_deltas(P30S90, self.saved, scale_capable=True, scale_ready=True)
        self.assertNotIn("scaling_enabled", d)  # process-static: never toggled live
        self.assertAlmostEqual(d["scaling_factor"], 1.111, places=3)
        rec2 = self.store.write("game", {**base, **d}, point_key="30x3-s90")
        self.assertTrue(rec2.scaling_provisioned)

    def test_scale_ready_refused_with_wsi_chain(self):
        saved = dict(self.saved, gamescope_wsi_compatibility=True)
        with self.assertRaises(PointNotApplicable):
            base_deltas(saved, scale_ready=True)

    def test_user_scaling_is_respected_as_reference(self):
        saved = dict(self.saved, scaling_enabled=True, scaling_factor=1.5, scaling_method="ls1")
        d = point_deltas(P30S90, saved, scale_capable=True, scale_ready=False)
        self.assertAlmostEqual(d["scaling_factor"], 1.667, places=3)
        saved_hi = dict(saved, scaling_factor=1.9)
        with self.assertRaises(PointNotApplicable) as ctx:
            point_deltas(P30S90, saved_hi, scale_capable=True, scale_ready=False)
        self.assertEqual(ctx.exception.reason, "scaling-factor-limit")

    def test_silently_clamped_delta_is_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.build_governor_overlay_text("game", {"base_fps_cap": 99999})

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.build_governor_overlay_text("missing", {})

    def test_saved_fingerprint_changes_when_saved_changes(self):
        before = self.svc.saved_config_fingerprint()
        self.svc.update_profile_config_fields("game", {"multiplier": 4})
        self.assertNotEqual(self.svc.saved_config_fingerprint(), before)


if __name__ == "__main__":
    unittest.main()
