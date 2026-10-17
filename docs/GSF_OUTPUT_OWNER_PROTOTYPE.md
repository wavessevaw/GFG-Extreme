# GSF: Output-owner transport prototype (2026-10-17)

**Development branch only. Does not install any Vulkan layer, change the stable
2.1.6 plugin, or claim that generation is working on the Steam Deck.**

## Evidence and why the old path cannot be treated as working

Four user-uploaded diagnostics from LAB.4: at 07:03 UTC Desktop x2
3,820 real and 1,125 synthetic *WSI handoffs*; 706 bounded-mailbox
backpressure events, 128 stale jobs and an output worker median 27.95 ms.
At 07:12 UTC Desktop x3 3,274 real and 2,247 synthetic WSI handoffs with
440 backpressure events. The user reports jerky motion and missing/real
frames. Physical scanout and uniqueness of intermediate frames were never
observed. Two Gaming Mode captures were real-only due to 10-bit Gamescope
protection (not a working frame generator).

The current layer copies the game's swapchain into temporal history and
independently acquires/presents generated images on **the same game swapchain**;
it subsequently presents the game image. Even when the API calls are ordered,
the FIFO WSI can block, creating a queue backlog that delays the source. It
is not a genuine separation of game rendering and final output ownership.

## Checked reference: MAKO, not hypothetical LSFG.dll internals

See [MAKO real_frames.cpp](https://github.com/eugeniosegala/MAKO/blob/main/engine/mako-render/src/swapchain/present/real_frames.cpp),
function `Swapchain::submitSourceCopy`. A real image is blitted into a
separate GPU `sourceImage`, with explicit layout barriers and timeline
signaling. See [generated_frames.cpp](https://github.com/eugeniosegala/MAKO/blob/main/engine/mako-render/src/swapchain/present/generated_frames.cpp):
MAKO acquires additional swapchain images, copies generated textures and
issues `vkQueuePresentKHR` before a final original present. This confirms
the MAKO Vulkan WSI integration but **not** the proprietary Windows
Lossless Scaling capture implementation.

## Architecture

```text
real input swapchain (game; NEVER independently displayed)
    |  capture real GPU frame and signal ready fence
    v
source cache: pinned A, B until retired by the owner
    |  A+B -> GPU interpolation -> true output-ready fence
    v
GFG output_owner (single authority)
    |  A (real) -> A½ (synthetic, optional) -> B (real)
    v
private output swapchain/window -> Gamescope -> physical screen
```

The private output surface is a **hard prerequisite**. Merely overlaying the
generated texture on top of a normally presented game image would create two
unsynchronized outputs. An external window also needs a supported frame
capture route in Gamescope, a no-recursion guarantee and compositor surface
prioritization. These capabilities must be proved rather than presumed.

### Implemented in this branch

`engine/gfg-native/src/output_owner.h` implements a Vulkan-independent
reference ticket contract:

* The first real capture A is held until B exists, then A/AB/B are
  scheduled on a shared ordered output lattice. Following real C yields
  BC/C, never duplicate B.
* Late/invalid GPU synthetic or scene discontinuity: drop **only synthetic**;
  schedule the next real frame promptly. No additional delay to try to
  salvage an outdated generated image.
* Bounded real display latency for generation, 90Hz budget checks and
  monotonic output timestamps, with a flush of the only real frame on exit.
* Caller retains **source image memory and readiness fences** until the
  owner has actually submitted and retired output tickets.
* Structured tickets contain input IDs and presentation due times.
  Tickets are not WSI calls, and successful tickets are not scanout proof.

`make -C engine/gfg-native output-owner` tests real/synthetic chronological
ordering, a 30FPS→60Hz case, recovery after a 836ms pause changing from
27→38FPS at 90Hz, missing/cut GPU work, a source rate too fast to generate
at 90Hz and single-frame flush.

### Not yet implemented / hard merge gate

1. Private output swapchain/surface in SteamOS Gaming Mode (Gamescope), with
   the original input swapchain **prevented from displaying twice**.
2. GPU texture lifetime ownership, imported sync, app-semaphore consumption
   and full WSI swapchain recreation without deadlock.
3. Match game-source FPS after entering and leaving menus/loads without
   backlog; measure not just API counts but an external **pixel-sequence**
   observer. The observer must see colors A, A½, B, ... in physical order.
4. No dropped/stolen real frames and additional input latency inside a
   documented user-configured budget. Regression against LAB.3/LAB.4.
5. Gamescope 10-bit compatibility must clear independent Vulkan dispatcher
   integration tests. PR #151 fixes one borrowed-device dispatch bug, but
   the packed10 protection stays enabled until tested on actual hardware.

**Do not present this branch as a downloadable, working GSF release.**
