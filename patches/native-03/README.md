# GFG Native FG: Patch 03, Steam Deck 1 FPS frame-stall hotfix

Standalone patch for installed GFG Native FG native.1 + Patch 02.
**NOT** a GitHub release. Does not touch stable GFG Extreme.

## Deck results motivating this fix

1280×800, format 44, swapchain flags 0xc0:
- Own TE8 tiles engine successfully generates synthetic frames.
- Reported TE8 wait around 4.5–5.5 ms, not a full-frame 1-second delay.
- 130 real frames, 129 submitted synthetic frames, only 100 distinct.
- 1 FPS reported. Suspected Vulkan WSI synchronization stalls; **no proof
  of the exact blocking Vulkan call yet**.

## Changes

- Remove per-synthetic-frame blocking `vkQueueWaitIdle`. Replace
  single present-ready semaphore with **one per swapchain image**:
  reuse only after image reacquisition and the GPU acquire wait,
  following Khronos swapchain semaphore reuse guidance.
- Skip synthetic present if `distinct=0`, reducing WSI pressure.
- Add frame-time watchdog: `GFG_NATIVE_MAX_FRAME_MS=100` by default.
  If the layer spends over 100 ms on a real present, or on the capture,
  compute, synthetic or real-present path, generation is permanently
  disabled **for that swapchain**, and original real frames continue.
  The game should not remain indefinitely throttled by an expensive
  optional layer. Optional budget: `GFG_NATIVE_MAX_FRAME_MS=60` etc
  (supported 20..2000 ms), but changing it isn't necessary for this test.
- Print `[gfg-native] timing capture_ms=... pre_real_ms=... total_ms=...`
  on slow frames and `watchdog disabled generator stage=...` on bypass.
- Keep protected/unrecognised swapchain flags rejected and preserve
  the original app's present-ID/wait protocol.

This patch improves the presentation synchronization. It is **not**
a GPU-only transport; CPU readback/upload and synchronous TE still exist,
and 60 FPS is not promised. Do not treat it as a stable release.

## Install
Close the game. Extract ZIP and run inside the extracted folder:

```bash
bash apply.sh
```

Existing Steam launch options remain unchanged.

## Rollback
```bash
bash rollback.sh
```

## After test
Send `~/gfg-native-test.log` and observed FPS. Important:
- `generated=...` and `candidate distinct=...`
- `timing capture_ms=... pre_real_ms=... total_ms=...`
- `watchdog disabled generator stage=...` if shown
- `CPU bridge retired ... bypasses=...`

If watchdog kicks in, original game FPS should return, even though
generated frame output is then disabled. This is an intentionally safe
failsafe while we evolve towards asynchronous GPU transport.

Synchronization reference:
https://docs.vulkan.org/guide/latest/swapchain_semaphore_reuse.html
