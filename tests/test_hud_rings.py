import struct, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from py_modules.gfg_plugin import hud_rings

SAMPLE = {"fps": 90, "real": 45, "target": 90, "tdp": 15, "limit": 15, "maximum_tdp": 15, "battery_min": 125, "battery_pct": 72,
          "frame_os": {"estimate": False, "level": "boost", "response": 47, "frames": 50, "energy": 9,
                       "active": True, "verified_boost": True, "actual_real": 45, "actual_ratio": 2.0}}


class RingHudTests(unittest.TestCase):
    def test_presets_choose_their_rings(self):
        labels = lambda p: [i.get("label") or i.get("text") or i["kind"] for i in hud_rings.items_for(SAMPLE, p)]
        self.assertEqual(labels("minimal"), ["FPS", "TDP"])
        self.assertEqual(labels("standard"), ["FPS", "TDP", "sep", "RESP", "FRAMES", "ENERGY", "BOOST 45R x2"])
        self.assertEqual(labels("detailed"), ["FPS", "TDP", "BATTERY", "sep", "RESP", "FRAMES", "ENERGY", "BOOST 45R x2"])
        self.assertEqual([i.get("label") for i in hud_rings.items_for({**SAMPLE, "frame_os": None}, "standard")],
                         ["FPS", "TDP", None, "ENERGY"])


    def test_an_ab_window_is_named_instead_of_calm(self):
        data = {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "ab": True}}
        self.assertEqual(hud_rings.items_for(data, "standard")[-1]["text"], "A/B")
        data["frame_os"]["active"] = False
        self.assertNotIn("A/B", [i.get("text") for i in hud_rings.items_for(data, "standard")])
        hud_rings.render(data, "detailed", 1.0)          # every glyph exists in the atlas

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

    def test_extreme_tag_names_only_a_confirmed_render_scale(self):
        data = {**SAMPLE, "frame_os": None, "extreme": {"render_pct": 80}}
        self.assertEqual(hud_rings.items_for(data, "standard")[-1]["text"], "EXT 80%")
        data["extreme"] = {"render_pct": None}             # requested or full resolution: no number
        self.assertEqual(hud_rings.items_for(data, "standard")[-1]["text"], "EXT")
        self.assertNotIn("tag", [i["kind"] for i in hud_rings.items_for(data, "minimal")])
        hud_rings.render({**data, "extreme": {"render_pct": 90}}, "detailed", 1.0)

    def test_energy_number_saves_cap_and_arc_is_battery(self):
        for cap, expected in ((15, "0%"), (12, "20%"), (12.75, "15%"), (0, "100%"), (20, "0%")):
            data = {**SAMPLE, "energy_tdp": cap, "maximum_tdp": 15}
            ring = next(i for i in hud_rings.items_for(data, "standard") if i.get("label") == "ENERGY")
            self.assertEqual(ring["text"], expected)
            self.assertAlmostEqual(ring["frac"], .72)
            self.assertEqual(ring["rgb"], hud_rings.battery_color(72))
            self.assertEqual(ring["opacity"], 1)
        for bad in (None, True, float("nan"), float("inf"), -1):
            self.assertIsNone(hud_rings.energy_savings_pct(bad, 15))

    def test_benefit_text_and_colour(self):
        items = {i.get("label"): i for i in hud_rings.items_for(SAMPLE, "standard")}
        self.assertEqual(items["RESP"]["text"], "−47%")
        self.assertEqual(items["FRAMES"]["text"], "+50%")
        self.assertEqual(items["ENERGY"]["opacity"], 1.0)             # independent of Frame OS
        r, g, _b = hud_rings.effect_color(50, 50)
        self.assertGreater(g, r)                                        # full benefit is green
        r, g, _b = hud_rings.effect_color(-5, 50)
        self.assertGreater(r, g)                                        # worse is red
        est = {i.get("label"): i for i in hud_rings.items_for(
            {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "estimate": True}}, "standard")}
        self.assertEqual(est["RESP"]["rgb"], hud_rings.GREY)

    def test_render_is_opaque_panel_with_transparent_corners(self):
        for scale in hud_rings.SCALES[:2]:
            w, h, px = hud_rings.render(SAMPLE, "standard", scale)
            self.assertEqual(len(px), w * h * 4)
            self.assertEqual(px[3], 0)                                  # rounded corner skipped
            mid = ((h // 2) * w + 2) * 4
            self.assertEqual(px[mid + 3], 255)
            self.assertTrue(all(a in (0, 255) for a in px[3::4]))      # the layer does no blending

    def test_tdp_charger_and_charge_colors_in_every_preset(self):
        for preset in ("minimal", "standard", "detailed"):
            for pct in (0, 15, 40, 65, 100, None):
                data = {**SAMPLE, "battery_pct": pct, "external_power": True}
                plugged = hud_rings.items_for(data, preset)[1]
                unplugged = hud_rings.items_for({**data, "external_power": False}, preset)[1]
                self.assertEqual(plugged["rgb"], hud_rings.battery_color(100))
                self.assertEqual((plugged["text"], plugged["frac"]), (unplugged["text"], unplugged["frac"]))
        low = hud_rings.tdp_color(15, False)
        mid = hud_rings.tdp_color(40, False)
        high = hud_rings.tdp_color(65, False)
        self.assertGreater(low[0], low[1])
        self.assertEqual(mid[0], mid[1])
        self.assertGreater(high[1], high[0])
        self.assertEqual(hud_rings.tdp_color(None, False), hud_rings.GREY)

    def test_plug_event_invalidates_cached_visuals_without_changing_energy(self):
        data = {**SAMPLE, "battery_pct": 20, "external_power": False}
        plugged = {**data, "external_power": True}
        self.assertNotEqual(hud_rings.visual_key(data, "standard", "top-left", 1),
                            hud_rings.visual_key(plugged, "standard", "top-left", 1))
        energy = lambda d: next(i for i in hud_rings.items_for(d, "standard") if i.get("label") == "ENERGY")
        self.assertEqual(energy(data), energy(plugged))
        self.assertNotEqual(hud_rings.render(data, "minimal")[2], hud_rings.render(plugged, "minimal")[2])

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

    def test_energy_independent_of_frame_os_and_charge_threshold(self):
        energy = lambda d: next(i for i in hud_rings.items_for(d, "standard") if i.get("label") == "ENERGY")
        for level in ("rest", "calm", "boost"):
            ring = energy({**SAMPLE, "energy_tdp": 15, "maximum_tdp": 20,
                           "frame_os": {**SAMPLE["frame_os"], "level": level, "estimate": True, "energy": -50}})
            self.assertEqual((ring["text"], ring["frac"], ring["opacity"]), ("25%", .72, 1))
        self.assertEqual(energy({**SAMPLE, "frame_os": None})["frac"], .72)
        for pct in (50, 51, 100):
            r, g, b = energy({**SAMPLE, "battery_pct": pct})["rgb"]
            self.assertGreater(g, r)
            self.assertGreater(g, b)
        self.assertEqual(hud_rings.battery_color(50), hud_rings.battery_color(100))
        for pct in (0, 5, 15):
            r, g, _ = energy({**SAMPLE, "battery_pct": pct})["rgb"]
            self.assertGreater(r, g)
        self.assertNotEqual(hud_rings.battery_color(25), hud_rings.battery_color(50))

    def test_unknown_energy_inputs_are_not_invented(self):
        ring = next(i for i in hud_rings.items_for({"tdp": 12}, "standard") if i.get("label") == "ENERGY")
        self.assertEqual((ring["text"], ring["frac"], ring["rgb"]), ("—", 0, hud_rings.GREY))

    def test_invalid_numbers_and_zero_tdp_do_not_break_any_preset(self):
        for bad in (float("nan"), float("inf"), True, "bad", -1):
            data = {key: bad for key in ("fps", "real", "target", "tdp", "limit", "battery_min", "battery_pct", "maximum_tdp")}
            data["frame_os"] = {"response": bad, "frames": bad}
            for preset in ("minimal", "standard", "detailed"):
                hud_rings.render(data, preset)
        self.assertEqual(hud_rings.items_for({"tdp": 0}, "minimal")[1]["text"], "0W")

    def test_charging_battery_keeps_detailed_ring_with_charge_text(self):
        data = {**SAMPLE, "battery_min": None, "battery_pct": 72}
        battery = next(i for i in hud_rings.items_for(data, "detailed") if i.get("label") == "BATTERY")
        self.assertEqual((battery["text"], battery["frac"]), ("72%", .72))

    def test_explicitly_unmeasured_effect_is_not_a_claim(self):
        data = {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "measured": {"response": False, "frames": False}}}
        rings = {i.get("label"): i for i in hud_rings.items_for(data, "standard")}
        self.assertEqual((rings["RESP"]["text"], rings["RESP"]["rgb"]), ("−47%", hud_rings.GREY))
        self.assertEqual((rings["FRAMES"]["text"], rings["FRAMES"]["rgb"]), ("+50%", hud_rings.GREY))

if __name__ == "__main__":
    unittest.main()


class AtlasCoverageTests(unittest.TestCase):
    def test_every_printed_character_has_a_glyph(self):
        # field bug: "BOOST 45R x2" rendered as "BOOST 45R 2" (no lowercase x in the atlas)
        atlas = hud_rings._atlas()
        glyphs = set(atlas["lab@1.0"]["glyphs"]) & set(atlas["val@1.0"]["glyphs"])
        variants = [SAMPLE, {**SAMPLE, "battery_min": 45},
                    {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "actual_ratio": 2.5}},
                    {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "ab": True}},
                    {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "level": "rest"}},
                    {**SAMPLE, "frame_os": {**SAMPLE["frame_os"], "verified_boost": False}},
                    {**SAMPLE, "extreme": {"render_pct": 80}}]
        for data in variants:
            for preset in ("minimal", "standard", "detailed"):
                for item in hud_rings.items_for(data, preset):
                    for text in (item.get("text"), item.get("sub"), item.get("label")):
                        missing = set(text or "") - glyphs
                        self.assertFalse(missing, f"{text!r} needs glyphs {missing}")
