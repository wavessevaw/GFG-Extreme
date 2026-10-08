import struct, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from py_modules.gfg_plugin import hud_rings

SAMPLE = {"fps": 90, "real": 45, "target": 90, "tdp": 15, "limit": 15, "battery_min": 125, "battery_pct": 72,
          "frame_os": {"mode": "act", "estimate": False, "level": "boost", "response": 47, "frames": 50, "energy": 9,
                       "active": True, "verified_boost": True, "actual_real": 45, "actual_ratio": 2.0}}


class RingHudTests(unittest.TestCase):
    def test_presets_choose_their_rings(self):
        labels = lambda p: [i.get("label") or i.get("text") or i["kind"] for i in hud_rings.items_for(SAMPLE, p)]
        self.assertEqual(labels("minimal"), ["FPS/90", "TDP CAP"])
        self.assertEqual(labels("standard"), ["FPS/90", "TDP CAP", "sep", "AGE EST", "REAL GAIN", "CAP CUT", "BOOST 45R x2"])
        self.assertEqual(labels("detailed"), ["FPS/90", "TDP CAP", "BATTERY", "sep", "AGE EST", "REAL GAIN", "CAP CUT", "BOOST 45R x2"])
        self.assertEqual([i.get("label") for i in hud_rings.items_for({**SAMPLE, "frame_os": None}, "standard")],
                         ["FPS/90", "TDP CAP"])


    def test_requested_boost_never_claims_it_was_delivered(self):
        sample = dict(SAMPLE)
        sample["frame_os"] = {**SAMPLE["frame_os"], "verified_boost": False}
        self.assertEqual(hud_rings.items_for(sample, "standard")[-1]["text"], "VERIFYING")
        sample["frame_os"] = {**sample["frame_os"], "active": False}
        self.assertEqual([item["text"] for item in hud_rings.items_for(sample, "standard")
                          if item["kind"] == "tag"], [])
        sample["frame_os"] = {**SAMPLE["frame_os"], "level": "calm"}
        self.assertEqual(hud_rings.items_for(sample, "standard")[-1]["text"], "CALM")
        sample["frame_os"] = {**SAMPLE["frame_os"], "level": "rest"}
        self.assertEqual(hud_rings.items_for(sample, "standard")[-1]["text"], "REST")

    def test_status_badge_distinguishes_estimates_and_unavailable_act(self):
        data = {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "mode": "observe", "active": False}}
        items = hud_rings.items_for(data, "standard")
        self.assertEqual(items[-1]["text"], "OBSERVE EST")
        data["frame_os"] = {**data["frame_os"], "mode": "shadow"}
        self.assertEqual(hud_rings.items_for(data, "standard")[-1]["text"], "SHADOW EST")
        data["frame_os"] = {**data["frame_os"], "mode": "act"}
        self.assertEqual(hud_rings.items_for(data, "standard")[-1]["text"], "ACT WAIT")
        self.assertEqual(hud_rings.items_for(data, "minimal")[-1]["label"], "TDP CAP")

    def test_benefit_text_and_colour(self):
        items = {i.get("label"): i for i in hud_rings.items_for(SAMPLE, "standard")}
        self.assertEqual(items["AGE EST"]["text"], "−47%")
        self.assertEqual(items["REAL GAIN"]["text"], "+50%")
        self.assertEqual(items["CAP CUT"]["opacity"], 0.45)            # not the live benefit in boost
        r, g, _b = hud_rings.effect_color(50, 50)
        self.assertGreater(g, r)                                        # full benefit is green
        r, g, _b = hud_rings.effect_color(-5, 50)
        self.assertGreater(r, g)                                        # worse is red
        est = {i.get("label"): i for i in hud_rings.items_for(
            {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "estimate": True}}, "standard")}
        self.assertEqual(est["AGE EST"]["rgb"], hud_rings.GREY)

    def test_render_is_opaque_panel_with_transparent_corners(self):
        for scale in hud_rings.SCALES[:2]:
            w, h, px = hud_rings.render(SAMPLE, "standard", scale)
            self.assertEqual(len(px), w * h * 4)
            self.assertEqual(px[3], 0)                                  # rounded corner skipped
            mid = ((h // 2) * w + 2) * 4
            self.assertEqual(px[mid + 3], 255)
            self.assertTrue(all(a in (0, 255) for a in px[3::4]))      # the layer does no blending

    def test_write_overlay_header_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, extent = Path(tmp) / "hud.raw", Path(tmp) / "hud.extent"
            extent.write_text("1920 1200")
            self.assertTrue(hud_rings.write_overlay(SAMPLE, preset="minimal", position="top-right", seq=7,
                                                    path=path, extent_path=extent))
            raw = path.read_bytes()
            magic, version, w, h, corner, margin, seq, _ = struct.unpack("<8I", raw[:32])
            self.assertEqual((magic, version, corner, margin, seq), (hud_rings.MAGIC, 1, 1, 18, 7))
            self.assertEqual(len(raw), 32 + w * h * 4)
            hud_rings.write_overlay(None, preset="minimal", position="top-left", seq=8, path=path,
                                    extent_path=extent)
            self.assertEqual(struct.unpack("<8I", path.read_bytes()[:32])[2:4], (0, 0))

    def test_scale_follows_swapchain_height(self):
        self.assertEqual(hud_rings.scale_for(800), 1.0)
        self.assertEqual(hud_rings.scale_for(1200), 1.5)
        self.assertEqual(hud_rings.scale_for(2160), 3.0)

    def test_zero_fps_is_not_missing_telemetry(self):
        items = hud_rings.items_for({**SAMPLE, "fps": 0, "real": 0}, "minimal")
        self.assertEqual(items[0]["text"], "0")
        self.assertEqual(items[0]["sub"], "0 REAL")

    def test_geometry_background_and_glyph_caches_are_reused(self):
        hud_rings._ring_geometry.cache_clear()
        hud_rings._panel.cache_clear()
        hud_rings._glyph_alpha.cache_clear()
        hud_rings.render(SAMPLE, "standard", 1.0)
        geometry = hud_rings._ring_geometry.cache_info().misses
        panel = hud_rings._panel.cache_info().misses
        glyphs = hud_rings._glyph_alpha.cache_info().misses
        hud_rings.render(SAMPLE, "standard", 1.0)
        self.assertEqual(hud_rings._ring_geometry.cache_info().misses, geometry)
        self.assertEqual(hud_rings._panel.cache_info().misses, panel)
        self.assertEqual(hud_rings._glyph_alpha.cache_info().misses, glyphs)

    def test_cached_background_is_not_modified_by_render(self):
        first = hud_rings.render(SAMPLE, "minimal")
        hud_rings.render({**SAMPLE, "fps": 20, "tdp": 4}, "minimal")
        self.assertEqual(hud_rings.render(SAMPLE, "minimal"), first)

    def test_failed_atomic_write_leaves_previous_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hud.raw"
            path.write_bytes(b"previous")
            with patch.object(hud_rings.os, "replace", side_effect=OSError("busy")):
                self.assertFalse(hud_rings.write_overlay(None, preset="minimal",
                                 position="top-left", seq=2, path=path))
            self.assertEqual(path.read_bytes(), b"previous")


if __name__ == "__main__":
    unittest.main()
