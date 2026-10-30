"""Compare one SDR candidate frame to the pinned software-Vulkan reference.

Reports descriptive RGB PSNR and an explicitly defined 8x8 luminance SSIM variant.
No pass/fail quality threshold is applied. This is not a temporal, HDR, latency,
energy, perceptual-validation, or Steam Deck test.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

import verify_gsf_reference as reference


def pixels_from_ppm(data):
    if len(data) != reference.FRAME_SIZE or not data.startswith(reference.HEADER):
        raise ValueError("expected 1280x800 P6 RGB8 PPM with the captured header")
    return data[len(reference.HEADER):]


def frame_metrics(truth, image, width, height):
    if width <= 0 or height <= 0 or width % 8 or height % 8:
        raise ValueError("image dimensions must be positive multiples of eight")
    if len(truth) != width * height * 3 or len(image) != len(truth):
        raise ValueError("RGB frame size mismatch")
    mse = sum((a - b) ** 2 for a, b in zip(truth, image)) / len(truth)
    psnr = None if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    total, windows = 0.0, 0
    for top in range(0, height, 8):
        for left in range(0, width, 8):
            sx = sy = sxx = syy = sxy = 0.0
            for row in range(top, top + 8):
                for col in range(left, left + 8):
                    i = (row * width + col) * 3
                    x = (299 * truth[i] + 587 * truth[i + 1] + 114 * truth[i + 2]) / 1000.0
                    y = (299 * image[i] + 587 * image[i + 1] + 114 * image[i + 2]) / 1000.0
                    sx += x
                    sy += y
                    sxx += x * x
                    syy += y * y
                    sxy += x * y
            mx, my = sx / 64, sy / 64
            vx = max(0.0, sxx / 64 - mx * mx)
            vy = max(0.0, syy / 64 - my * my)
            cov = sxy / 64 - mx * my
            total += ((2 * mx * my + c1) * (2 * cov + c2) /
                      ((mx * mx + my * my + c1) * (vx + vy + c2)))
            windows += 1
    return {"mse_rgb": mse, "psnr_db": psnr, "psnr_infinite": mse == 0,
            "ssim_luma_8x8": total / windows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="verified original reference ZIP")
    parser.add_argument("candidate", help="candidate 1280x800 P6 RGB8 frame")
    parser.add_argument("--mode", choices=tuple(reference.PHASES), required=True)
    parser.add_argument("--scene", choices=reference.SCENES, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--candidate-revision", help="caller-supplied, not independently verified")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.phase not in reference.PHASES[args.mode]:
        parser.error("phase does not belong to selected mode")
    manifest = Path(__file__).resolve().parents[1] / "docs/baseline-3.2.2/gsf-sdr-reference-manifest.json"
    try:
        reference.verify_archive(args.archive, manifest)
        prefix = f"frames/{args.mode}/{args.scene}_t{args.phase}"
        with zipfile.ZipFile(args.archive) as archive:
            truth_file = archive.read(prefix + "_truth.ppm")
            baseline_file = archive.read(prefix + "_gen.ppm")
            truth = pixels_from_ppm(truth_file)
            baseline = pixels_from_ppm(baseline_file)
        candidate_file = Path(args.candidate).read_bytes()
        candidate = pixels_from_ppm(candidate_file)
        result = {
            "status": "UNVERIFIED", "evidence_class": "single SDR frame; baseline is software Vulkan, candidate provenance unverified",
            "scene": args.scene, "mode": args.mode, "phase": args.phase,
            "reference_archive_sha256": reference.ARCHIVE_SHA256,
            "truth_sha256": hashlib.sha256(truth_file).hexdigest(),
            "baseline_sha256": hashlib.sha256(baseline_file).hexdigest(),
            "candidate_sha256": hashlib.sha256(candidate_file).hexdigest(),
            "claimed_candidate_revision": args.candidate_revision,
            "baseline": frame_metrics(truth, baseline, 1280, 800),
            "candidate": frame_metrics(truth, candidate, 1280, 800),
            "method": "RGB code-value PSNR; mean SSIM over non-overlapping 8x8 BT.601 luma windows, population variance, K1=0.01, K2=0.03, L=255; no acceptance threshold",
            "limitations": "Single frames cannot establish temporal quality, HDR, perceptual quality, latency, energy, or real Steam Deck behavior. Candidate provenance, scene and phase alignment are not independently verified.",
        }
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"comparison failed: {exc}\n")
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
