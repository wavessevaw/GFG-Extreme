# GFG Native FG: independent engine migration

Status: **experimental bridge, NOT a standalone finished Vulkan layer**.

There are now two separate tracks:
- `src/layer.c` is a **new, standalone GFG Vulkan loader/WSI layer**. It
  negotiates possible transfer-capable swapchains and forwards the game's real
  presentations unchanged. **It does NOT capture or generate frames yet.**
  No MAKO/DLL code is linked into this layer. Its manifest is off by default.
- `bootstrap.py` is the *transitional* no-DLL path for the already working
  Temporal Engine while the independent WSI path is developed.

This first implementation step makes GFG Temporal Engine (TE8) start without
opening or finding the licensed Lossless.dll *when the exclusive Experimental
mode is selected*. The existing public GPL MAKO WSI/presentation code is still
used as a transitional transport; it is not renamed, hidden or claimed as our
own. Off/Observe/Shadow retain the original behaviour and DLL requirement.

## What changed

- The native Experimental backend initializes a temporary Vulkan instance
  solely to select the game's physical GPU, then creates GFG TE's own Vulkan
  compute device. It **does not construct** DLL-backed InstanceImpl.
- Context rejection can never instantiate LSFG as fallback. The renderer must
  preserve the real-game presentation when native initialization fails.
- Optional licensed spatial-scaling discovery is suppressed in exclusive
  native mode; it uses SDR8/default source layout first.
- Backend capability reports are null-safe where the DLL backend does not exist.

This is intentionally a *transitional step*, not fulfilment of the final
no-MAKO requirement. MAKO's open WSI acquisition, image copy, sync, generated
image presentation, swapchain retirement, and pacing still need replacement.
Do not remove the existing renderer until GFG owns those boundaries and device
evidence shows presentation correctness.

## Build and smoke test

From the repository:

```sh
python3 -m unittest discover -s tests -p test_native_no_dll_bootstrap.py
python3 -m unittest discover -s tests -p test_native_layer_foundation.py
make -C engine/gfg-native smoke VULKAN_HEADERS=/path/to/Vulkan-Headers/include
python3 scripts/build_frame_fusion.py --native-no-dll \
    --work /tmp/gfg-native-bridge --headers /path/to/Vulkan-Headers/include
python3 scripts/check_native_independence.py \
    --source /tmp/gfg-native-bridge/source
```

The independent layer can be exercised only as a WSI **pass-through**:
`GFG_NATIVE_FG=1` enables swapchain eligibility negotiation and
`GFG_NATIVE_TRACE=1` reports it. Do not deploy the layer alongside the
normal generator yet; it does not own image-history or presentation.
Its `VkLayer_gfg_native.json` must be installed next to the built .so
in a controlled Vulkan loader path before using it.

The normal Frame Fusion build remains unchanged unless
`--native-no-dll` is provided. Release packaging is **not** updated here.
No independent binary or installable release is claimed.

## Acceptance still outstanding

1. Run a controlled native Experimental game with **no** Lossless.dll on the
   filesystem; trace file opens and verify no DLL/model access. Also verify
   library dependencies and build provenance.
2. 30 real to 60 actual delivered frames on a Deck; Vulkan validation clean.
3. Failure injection (import refusal, device lost, swapchain recreation)
   preserves original frames and does not reopen LSFG.
4. Implement and build a separate `VK_LAYER_GFG_native` with GFG-owned
   image lifetime, presentation, synchronization, admission, and pacing.
5. Remove the transitional MAKO renderer dependency entirely; test clean
   SteamOS startup, both LCD/OLED where available.

Failure to satisfy any item must NOT be reported as full native independence.

The Vulkan loader smoke exercises instance/device creation, selection and
queue dispatch on a real Vulkan ICD. It does not test swapchain presentation.

## Independent CPU-generation path (now implemented)

The opt-in `GFG_NATIVE_CPU_BRIDGE=1` path (built with `ENABLE_TE=1`)
performs application image capture, TE8 host-I/O synthesis and a distinct
WSI acquire/present for every generated image. It is the first **fully
MAKO-free runtime**; the older `bootstrap.py` path remains a separate
transitional reference. TE8 `tiles` is the default for device-trial
reliability, while `GFG_NATIVE_ALGO=lmc` explicitly opts in to LMC.
The CPU transfer path is not cost-optimised and requires Deck testing.

An installable standalone native trial archive can be generated with
`scripts/package_native_fg.py` once WSI synthesis tests pass.

## GPU-resident transport (`GFG_NATIVE_GPU_BRIDGE=1`, reference implementation)

`src/gpu_bridge.c` replaces the CPU round trip for 3x generation (two TE8
outputs per real frame, t = 1/3 and 2/3, presented G1, G2, then the real
frame). It takes precedence over `GFG_NATIVE_CPU_BRIDGE=1` and never falls back
to it. Steady state has no CPU pixel access and no CPU wait on the present
thread: TE8's images are imported into the game's device (OPAQUE_FD), and a
timeline semaphore orders the game queue and TE8. That timeline is shared by
fd when the driver has `VK_KHR_external_semaphore_fd`; without it (lavapipe)
a relay thread forwards the values.

- The layer adds `VK_KHR_external_memory_fd`, `VK_KHR_external_semaphore_fd`
  (when supported) and `timelineSemaphore` to the game's device. Requires
  Vulkan 1.2; otherwise the game's frames pass through unchanged.
- Candidate swapchains get `minImageCount + 2` images.
- Variables: `GFG_NATIVE_GPU_INFLIGHT` (1..4, default 2),
  `GFG_NATIVE_GPU_SYNC=relay` (force relay mode), `GFG_NATIVE_TIMING=1`
  (CPU time inside vkQueuePresentKHR), and `GFG_NATIVE_PRESENT_TRACE=1`
  (layer-owned present IDs + `present_done` monitor, experimental).
- Test-only variables: `GFG_NATIVE_GPU_BRIDGE_VERIFY=1` and
  `GFG_NATIVE_GPU_BRIDGE_INJECT_SKIP=K`.
- `make wsi-smoke-gpu` runs on lavapipe/Xvfb, with the validation layer below
  this one. Its results are SIMULATED: they say nothing about Steam Deck
  pacing, latency or scanout.
