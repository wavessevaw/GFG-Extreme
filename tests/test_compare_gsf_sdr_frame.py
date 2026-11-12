"""Analytical checks for the explicitly defined SDR frame metrics."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import compare_gsf_sdr_frame as compare


class SdrMetricsTest(unittest.TestCase):
    def test_identical_frame_has_infinite_psnr_and_unit_ssim(self):
        frame = bytes((i * 19) % 256 for i in range(8 * 8 * 3))
        result = compare.frame_metrics(frame, frame, 8, 8)
        self.assertEqual(result["mse_rgb"], 0)
        self.assertIsNone(result["psnr_db"])
        self.assertTrue(result["psnr_infinite"])
        self.assertAlmostEqual(result["ssim_luma_8x8"], 1.0, places=12)

    def test_constant_black_and_white_have_known_values(self):
        black, white = bytes(8 * 8 * 3), bytes([255]) * (8 * 8 * 3)
        result = compare.frame_metrics(black, white, 8, 8)
        self.assertAlmostEqual(result["psnr_db"], 0.0, places=12)
        expected = (0.01 * 255) ** 2 / (255 ** 2 + (0.01 * 255) ** 2)
        self.assertAlmostEqual(result["ssim_luma_8x8"], expected, places=12)

    def test_inverted_checkerboard_has_known_negative_ssim(self):
        truth = bytes(channel for i in range(64) for channel in ([0] * 3 if i % 2 == 0 else [255] * 3))
        inverted = bytes(255 - value for value in truth)
        result = compare.frame_metrics(truth, inverted, 8, 8)
        c2 = (0.03 * 255) ** 2
        variance = 255 ** 2 / 4
        self.assertAlmostEqual(result["ssim_luma_8x8"], (c2 - 2 * variance) / (c2 + 2 * variance), places=12)

    def test_bad_dimensions_and_ppm_are_rejected(self):
        with self.assertRaises(ValueError):
            compare.frame_metrics(bytes(8 * 7 * 3), bytes(8 * 7 * 3), 8, 7)
        with self.assertRaises(ValueError):
            compare.pixels_from_ppm(b"P6\n8 8\n255\n")


if __name__ == "__main__":
    unittest.main()
