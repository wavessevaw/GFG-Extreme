# GSF Frame Output Engine (FOE): ownership-first architecture

Status: **research branch, stage 0 contract implemented**, not a playable release.
Stable GFG remains untouched. No GPU frame-generation or physical OLED scanout
claim is supported by the present stage.

## Why LAB.1–LAB.4 failed

The game and the Vulkan layer shared the same real swapchain. The layer
intercepted `vkQueuePresentKHR`, called a bounded async worker and tried to
add synthetic acquisitions/presents to the swapchain owned by the game.
When WSI `Present` was blocked for many milliseconds, the game could not
reacquire an image promptly. A larger timing buffer in LAB.4 made it worse,
not better. The counter of synthetic WSI presents does not mean a smooth
displayed stream. The original user test experienced stuttering.

By contrast a HUD only draws over the compositor's already chosen real
frame; it does not become the owner of final frame sequencing.

## Required pipeline

```text
game render GPU  --> private offscreen game images (PROXY SWAPCHAIN)
                                    |
                              GPU copy/sync
                                    v
                        held real A, held real B
                                    |
                 independent GSF GPU interpolation
                                    |
              output owner: real A -> synthetic AB -> real B
                                    |
                      real WSI swapchain (Gamescope)
                                    |
                              displayed scanout
```

**Key isolation:** The game must not hold the compositor's output
swapchain image while GSF computes/paces. Thus an ordinary wrapper around
`vkQueuePresentKHR` of an existing real game swapchain is NOT sufficient.
A production solution must virtualize the game's swapchain or integrate with
the compositor. The proxy path needs independent real Vulkan render images
with valid memory, image usage, format/color space, queue ownership,
external sync and known recreation semantics. The compositor surface gets its
own independent acquired images.

The test queue uses numeric `surface_id` tokens representing offscreen,
already-owned image objects; it intentionally cannot retain real application
`VkSwapchainKHR` images. Supplying an ID for a synthetic packet is legal only
after a real image is allocated and the GPU has produced content into it.
Never count a packet as displayed merely because it was scheduled.

### Lifetime invariants

1. Exactly one output owner calls `vkQueuePresentKHR` for the REAL display
   swapchain. The game and GSF cannot independently present into it.
2. `real A`, `real B` and `synthetic AB` live in private independent images;
   the game can continue rendering next source frames independently.
3. The output queue preserves `A, A½, B` order. There is no one-frame
   synthetic prediction: the artificial image needs both A and B.
4. A synthetic image missing its readiness deadline is SKIPPED. It must
   never force an original real image to miss its own presentation.
5. Real images are never silently discarded by the queue. Capacity pressure
   is reported to the Vulkan adapter, which must manage resources without
   blocking game submissions indefinitely or losing synchronization.
6. A load, scene cut, resize, device loss or a large source timestamp gap
   retires dependent synthetic pairs. It must not join two different epochs.
7. Per-image acquire and release semaphores, app present IDs/fences,
   vkWaitForPresent(2) and swapchain destruction are preserved or explicitly
   and safely failed open. No forged semaphore completion and no reuse
   of still-in-flight image memory.
8. All timings and counters separate GPU computation, output WSI submission,
   WSI acknowledgment, compositor display and **observed scanout**. Only the
   latter proves visible frames.
9. Added latency is explicitly bounded and measured, not concealed.
10. Unsupported games or WSI shapes bypass FOE and retain normal output.
    This requires a tested fallback, never an automatic destructive swapchain
    modification.

### Important Vulkan implementation questions (stage 1 blockers)

- Can the game use ordinary layer-owned `VkImage` render targets returned by
  a virtual `vkGetSwapchainImagesKHR`, with correct render pass/layout
  semantics? What about swapchain-special image usage and queue family
  transfers? Prototype this on Vulkan XCB before touching Steam Deck games.
- Intercept and maintain the complete virtual swapchain API: create, get
  images, acquire(1/2), present, destroy, image fences, present IDs/waits,
  VK_EXT_swapchain_maintenance1, incremental present, HDR metadata, surface
  capabilities and swapchain recreation. An unknown pNext must not be passed
  blindly with a fake swapchain handle to the real ICD.
- Real output WSI must be the **only** hardware presentation surface.
  A HUD overlay is insufficient; a dedicated Vulkan output renderer must
  own and present the fullscreen reconstructed image.
- Only allow Gamescope packed10 experimentation after PR #151's Vulkan
  physical-device dispatcher change passes regression on real hardware.
  The current LAB.3/LAB.4 packed10 safety gate remains in place.

## Implemented in stage 0

- `engine/gfg-native/src/output_owner_queue.h`: bounded ordered queue
  of private real and synthetic surface tokens, held latest real, gap
  resets, stale synthetic drop, non-dropping real backpressure.
- `engine/gfg-native/tests/output_owner_queue.c`: exact A -> Ahalf -> B
  sequence, GPU-not-ready fallback, end-of-scene flush, replay of an
  836 ms load gap, and full-queue retry preserving the actual real image.
- `make -C engine/gfg-native output-owner-contract`: reproducible
  C11 standalone test (no Vulkan runtime, no physical display).

## Stage 1A: standalone Vulkan owned-image -> output swapchain pixel probe

Source: `engine/gfg-native/tests/output_visual_probe.c`.
This is **now implemented as a standalone real Vulkan XCB program**, with
three separately allocated real GPU `VkImage` objects (private producer
surfaces, colors red/green/blue). On each output, it:
1. Acquires a WSI image from a single output swapchain.
2. Copies the chosen private GPU image using `vkCmdCopyImage`.
3. Optionally copies one pixel of the output swapchain image into a staging
   buffer and verifies channel values on the CPU **before WSI present**.
4. Submits/presents in known red (real A), green (diagnostic placeholder for
   A-half) and blue (real B) order using that one output swapchain.

CI invokes `GFG_FOE_VISUAL_VERIFY=1 GFG_FOE_VISUAL_FRAMES=9
GFG_FOE_VISUAL_INTERVAL_MS=0 xvfb-run .../output-visual-probe`
and checks all nine Vulkan WSI handoffs and real GPU pixel readbacks.

**The green image is just a test pattern**. This is not interpolation, not
a captured gaming frame, not integration with Gamescope, and not proof of
physical scanout. The test deliberately does not run as an injected layer.
Until it passes and a separate proxy-swapchain exists, old GSF output paths
stay unchanged. Never advertise this as a playable LAB.5.

Build with:
```sh
make -C engine/gfg-native output-owner-contract output-visual-probe
```
Requires a working Vulkan/XCB environment for the second binary. Default
`output-visual-probe` opens a colored test window; set
`GFG_FOE_VISUAL_INTERVAL_MS` and `GFG_FOE_VISUAL_FRAMES` as desired.

### Stage 1 acceptance: visual output proof, NOT frame generation

Build one standalone Vulkan producer/compositor with a private source-image
ring and a separate real WSI output swapchain. Give A, Ahalf, B unambiguously
different pixel patterns and read back/order-check before WSI. Test fullscreen
on X11/Xwayland, under Gamescope, real 90 Hz. Display high-speed footage or
real present-timing proof, not aggregate output numbers. Verify the game
render path is actually isolated before introducing live game interception.

### Stage 2 acceptance: game interception

Proxy swapchain for a single opt-in known-safe game; copy A/B with GPU-only
synchronization; return game's private image to its acquire pool; generate
AB using native TE shared-flow and hand all three to the sole output owner.
Validate exact pixel order, real-frame fairness, scene transitions and input
latency. No release until failsafe/rollback and long-running on-device proof.

## How to work

Review past native branches (#133, #145, #147, #149, #151) and LAB.1–LAB.4
evidence before adding a live Vulkan adapter. Do not revive LAB.4's
buffer-without-swapchain-isolation. Branch PR remains draft until hardware
pixel sequence, WSI ordering and Game Mode safety are verified.
