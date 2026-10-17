# GSF Output Engine: Steam Deck OLED hardware qualification (experimental)

**Status: hardware UNKNOWN.** The CPU+lavapipe/Xvfb tests in PR #154 have verified 120 original frames interleaved with 119 GPU A/B split diagnostic frames at a *software* 45→90 timing target. These are not optical-flow interpolation and do not prove that SteamOS Gamescope scanned out 239 physical OLED frames.

This kit is an **isolated experiment only**. It is not a stable GFG release, a Decky plugin, a Proton game patch, or a system Vulkan layer installation.

## What the kit contains

The successful `GSF Output Owner Contract (experimental)` GitHub Actions workflow uploads one downloadable artifact named `gsf-output-deck-test-kit-<commit SHA>`. Its unpacked directory contains:

- `libVkLayer_gfg_native.so` built **with test-only Output Engine hooks**;
- `VkLayer_gfg_native.json`, with the layer referenced by relative `library_path`;
- `loader-live-output`, the standalone XCB/Vulkan application;
- `deck-output-test.sh`, a cautious launcher;
- `SHA256SUMS`, `BUILD_INFO.txt` and this document.

**Do not copy the test library into** `/usr/share/vulkan/`, `/etc/vulkan/`, `~/.local/share/vulkan/`, the Steam runtime, or GFG's installed native directory. It must remain beside the launcher and be enabled only in the child's environment.

The binary is built on an Ubuntu x86_64 Actions runner, not on an actual Deck. SteamOS ABI, installed libraries and Vulkan Loader compatibility are **not guaranteed**. The launcher checks library resolution and refuses to run when it cannot load the binary. Never overwrite SteamOS libraries to work around an incompatibility.

## Running on Steam Deck

1. Download the kit from the successful GitHub Actions run linked to PR #154 and unpack it to a **user-writable** directory (for example `/home/deck/gsf-output-test/`).
2. First check files and runtime dependencies from a terminal:
   ```bash
   bash /home/deck/gsf-output-test/deck-output-test.sh --check
   ```
3. For an optional controlled nested Gamescope check, from **Desktop Mode** with working `gamescope` and XWayland:
   ```bash
   bash /home/deck/gsf-output-test/deck-output-test.sh --run --mode=nested --phase=both --frames=120
   ```
   This does **not** prove direct OLED DRM scanout, because it runs a nested compositor.
4. For the primary **Gaming Mode** experiment, add a **Non-Steam Game** pointing to `/usr/bin/bash`. Set Launch Options to the script in the unpacked kit, followed by `--run --mode=direct --phase=both --frames=120`, for example:
   ```text
   "/home/deck/gsf-output-test/deck-output-test.sh" --run --mode=direct --phase=both --frames=120
   ```
   Gaming Mode is expected to supply its own `DISPLAY` for XWayland. The script **never starts, terminates, restarts, replaces or reconfigures** the embedded Gamescope.
5. If Gaming Mode does not provide `DISPLAY`, the preflight refuses to run. This is a missing prerequisite, **not** permission to modify OS service units, force environment variables system-wide or bypass the guard.

No `sudo` and no read-only root filesystem changes. A failed run returns control to Steam; `timeout` limits the child test to 30 seconds. The launcher does not touch installed games or the Decky plugin.

## Expected presentation and proof

The baseline phase displays **8 originals** through ordinary Vulkan WSI without loading GFG. The output phase supplies **120 originals at 45Hz** and instructs the isolated layer to emit **119 separate GPU A/B split markers** at a nominal 90Hz via **one** real downstream output WSI. The app's image content cycles through distinguishable grayscale levels; a split frame has two different halves.

Software evidence requires all of:
- `GSF_LOADER_LIVE_INIT ... one_real_output=1` (no silent normal-WSI fallback);
- `GSF_LOADER_SPLIT_APP output_visible=239 original=120 intermediate=119 ... PASS`;
- `GSF_OUTPUT_PACER rate=90 emitted=239 originals=120 intermediate=119`;
- no Vulkan validation errors, crash, hang or unexpected exit.

**Physical OLED validation is separate.** Record the actual built-in panel with an external phone/camera in high-frame-rate mode, showing the baseline and experiment and ideally the SteamOS refresh-rate setting. Review the video for truly visible split frames in the correct order and record the panel's refresh mode. A Steam screenshot, Gamescope log, X11 GetImage result, or a success marker **cannot** on its own establish 90Hz physical scanout, correct latency or a Proton game's frame-generation performance.

### Qualification report checklist

| Gate | Required observation | Current |
| --- | --- | --- |
| Software Vulkan + X11 at 45→90 | 120 originals + 119 split frames, verified pixels | Proven in CI |
| Deck loader & hardware Vulkan ICD | Isolated test starts with actual Deck AMD driver | Unverified |
| Gamescope XWayland virtual output | Output markers and video show composited frame changes | Unverified |
| Built-in OLED | External capture proves genuinely shown split frames / 90Hz refresh | Unverified |
| HDR/packed10, resize, device loss | Guarded degradation / clean rollback | Unverified |
| Proton games and LMC synthesis | Frames from a real game and generated intermediates | Not implemented in this test |

### Logs and rollback

Logs are kept locally at `~/GFG-Output-Deck-Tests/<UTC date>-<PID>/`: `baseline.log`, `output.log`, `metadata.txt`, `QUALIFICATION_STATUS.txt`, optionally Vulkan and Gamescope version summaries. The launcher **never uploads logs or video**.

To terminate the experiment, close the test application or exit the Steam shortcut. No installed layer, global environment setting, Steam configuration, display mode or game profile has been changed by the script. To discard the experiment, delete the unpacked kit directory; logs may be deleted separately.

**Stop the project before a Deck release** if the output phase freezes, closes Gaming Mode, shows black pixels, reports validation failures or uses a different swapchain format. Do not bypass the fail-closed flags, force HDR10/packed10 support, or merge experimental PR #154 into the 2.1.6 stable branch on the basis of desktop CI.

## References

- Valve's Gamescope compositor: https://github.com/ValveSoftware/gamescope
- Current test implementation: `engine/gfg-native/src/test_loader_output_runtime.h`, `engine/gfg-native/tests/loader_live_output.c`
- Working branch: `experiment/gsf-offscreen-source-pool-20261017`
- Output contract PR #154: https://github.com/wavessevaw/GFG-Extreme/pull/154
