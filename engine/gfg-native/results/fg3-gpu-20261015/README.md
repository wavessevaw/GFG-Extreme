# FG3 GPU software validation — 2026-10-15

**NOT COMPLETED. No Steam Deck acceptance or physical 90 Hz claim.**

These are raw local results for `codex/fg3-gpu`, based on `404829c`.
The runtime algorithm is GFG tile interpolation, not the CPU-fitting LMC path.
Removing CPU pixel transport is an architectural improvement; this does not
establish better game-image quality than the previous LMC engine.

Environment: Linux x86_64 cloud container, Mesa lavapipe/llvmpipe LLVM 19.1.7,
XCB on Xvfb `:93`, Vulkan validation layer, Vulkan headers v1.4.365.
This is not SteamOS, AMD hardware, Gamescope or a physical display.
Measured software-GPU times cannot be extrapolated to Deck performance.

- `core.txt`: 168 checks, zero failures, including standalone LMC worker.
- `python-contracts.txt`: 19 checks, including isolated install/rollback/off mode.
- `borrowed.txt`: a real application VkDevice with no optional features enabled;
  distinct t=1/3 and 2/3 outputs; static bit-exact output; BGRA output packing;
  textured-motion PSNR 37.125 / 35.835 dB on a synthetic reference;
  borrowed-device ownership; refusal of unsupported timeline/LMC paths.
- `observer*.txt`: independent test-only pixel readback, all pixels checked;
  4 real plus 6 synthetic WSI handoffs; UNORM/sRGB; 96×64 and 1280×800.
- `stress-*.txt`: 300 real calls at 96×64, 598 submitted/completed/handed-off
  intermediates, no bypasses; no application queue drain between frames.
- `recreate-*.txt`: three swapchains, 96×64 → 112×72 → 128×80, including
  creating the replacement with oldSwapchain before retiring the previous one.
- `resume-*.txt`: temporary GPU-mode disable, then fresh-history warmup.
  Only the final adjacent pair generates two outputs: no interpolation across
  the missed capture.
- `installed-artifact.txt`: actual packaged ELF installed in an isolated HOME,
  then exercised through its launcher with Vulkan validation.
- `packaged-source-build.txt`: corresponding source extracted from that private
  archive builds the Temporal library and native layer, including the required
  `te_lmc.inc`. The rebuilt ELF matches the packaged ELF byte for byte.

`forward` and `reverse` mean native:validation and validation:native. Neither
order reports Vulkan validation errors. Source files are identified separately
in `source-sha256.json`; this directory is excluded from packaged sources.

## Remaining work, not merely missing test evidence

The backend has no virtual swapchain or asynchronous presentation worker.
Its synchronous FIFO present path can affect the game's real-frame cadence.
A bounded GPU ring does not remove WSI backpressure or prove low latency.
Queue changes bypass generation and reset history; this branch has not run a
real multi-queue application test. Resize testing above covers only XCB/lavapipe.

Game-quality comparisons, occlusion/HUD/fine-detail acceptance, real-FPS
retention, independent physical scanout, input latency, power, Proton/Gamescope,
suspend/resume, Decky 3× controls and 30-minute acceptance A–F remain incomplete.
No binary has been published and main has not been changed.
