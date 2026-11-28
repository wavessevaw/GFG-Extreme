# Native Super Resolution · candidate evidence

The selected spatial filter places the centre of each output pixel on the original game surface, reconstructs a bounded cubic surface on smooth spans, and follows the lower-contrast diagonal on edges. A local curvature correction compensates for the area covered by a source pixel. It reuses the same 12 texels and is limited by the colour range around the pixel. Solid or transparent cells take the four-sample path. Focus runs once on the chosen low-resolution frame; the final composite applies the same SR geometry to real and generated layers. Native input bypasses the scaler. The current integration keeps the existing source-sized FG warp. A fully fused motion-compensated 800p warp is unimplemented.

Mean luma SSIM against independent 800p renders is shown below. Each pair gives Kedavra SR / Gamescope FSR 1 kernel replay at its default sharpening. Higher is closer to the reference.

| Input and scene | FG Off | ×2 sequence | ×3 sequence |
| --- | ---: | ---: | ---: |
| 480p courtyard, camera reversal | .9483 / .9298 | .8373 / .8212 | .8074 / .7925 |
| 500p courtyard, camera reversal | .9561 / .9393 | .8363 / .8209 | .8078 / .7932 |
| 480p Freedoom Phase 2 demo | .8487 / .8212 | .7665 / .7398 | .6790 / .6550 |
| 500p Freedoom Phase 2 demo | .9021 / .8823 | .7950 / .7711 | .6916 / .6686 |

The 500p photo chart reached 30.80 dB / .9587 against 28.29 dB / .9294 for FSR 1. Luma SSIM uses nonoverlapping 8×8 windows. PSNR measures RGB; identical images are capped at 120 dB in the table generator. LPIPS adds a different view. On the photo chart at 480p the final SR distance was about .0606 versus .0574 for FSR 1, and at 500p it was .0541 versus .0548. Lower is closer. Differences on a single chart are insufficient to establish a perceptual preference. Bilinear scored higher SSIM on Freedoom, consistent with the difficulty of matching pixel-quantised textures and HUD across actual game resolutions. No reconstruction can recover all missing thin geometry.

The original candidate, plus footprint gains .10 and .18, used identical input samples. The .18 gain reduced 500p photo LPIPS from .0776 to .0541 and improved both sampled generated phases. See controls.json for the original and softer competitor settings, and variants.json for the gain trials. The shipped gain is .18. The trial compensated the footprint only within the local bounds. It introduces no new texture fetches.

On the 500p Freedoom ×3 sequence, doing motion analysis at 500p and reconstructing the selected frame gave 22.09 dB and temporal luminance-change MAE 13.54. Scaling before high-resolution FG gave 22.05 dB and 13.65. The equivalent 480p ×2 comparison gave 23.93 / 7.65 versus 23.52 / 9.57. A separate spatial-history experiment on eight real 500p frames used motion-compensated translation, rejection by luma residual and local bounds. It changed mean PSNR from 26.06 to 26.07 dB and worsened temporal error from 2.39 to 2.46 levels. It did not justify a runtime history allocation. Dense per-pixel temporal SR remains open.

Software Vulkan timestamps (CPU llvmpipe, four driver workers, 19 samples after dropping the first at each size) for 500p gave median 13.65 ms for SR and 25.52 ms for EASU plus RCAS. The replay has different workgroup layouts from the hardware compositor. These values are kernel regression data only. Physical GPU cost including compositing and FG, 0.3–0.5 ms target, input latency, frame pacing, temperature and energy remain unverified. A headless launch of the packaged compositor reached Vulkan device selection and stopped at the missing VK_KHR_external_semaphore_fd extension on this software driver. Steam library launch timing, actual XWayland negotiation, HDR fallback, dock behaviour and restore on a Deck remain hardware checks.

[Freedoom comparison image](freedoom.png) · [Freedoom motion clip](freedoom.mp4) · [Photo comparison](photo.png) · [Procedural courtyard clip](motion.mp4) · [Full resolution matrix](metrics.json) · [Game and architecture matrix](freedoom.json) · [Unaggregated software timings](software-timing.json) · [Reproduction and device protocol](../../tools/native_sr/README.md)
