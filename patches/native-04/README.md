# GFG Native FG Patch 04: isolate the 500 ms stall

**A binary patch, not a new release.** Installs on the existing
GFG Native FG independent Vulkan layer, including when Patch 03 is installed.

### Device log findings

- First real frame, before any synthetic present: ~505–545 ms.
- Vulkan readback fence: 0.27–0.39 ms.
- TE8 reported `te_context_idle` wait: 2.6–2.7 ms.
- Thus the old `stage=synthetic-present` label is **misleading**:
  the first frame was blocked in a different part of the CPU->TE8 path.
- Separate swapchains repeatedly reinitialize TE8 and retrigger this stall.
- `generated=0` for this test. There is no confirmed smooth output.

### What Patch 04 changes

- Prints detailed per-stage TE8 profiling:
  `[gfg-native] TE stages frame=0 upload_ms=... submit_ms=... wait_ms=... download_ms=... total_ms=... pid=...`.
- Separately measures CPU preprocessing:
  `[gfg-native] CPU convert frame=... invalidate_ms=... rgba_to_rgb_ms=...`.
- Logs TE8 setup time and process ID.
- Renames watchdog stage from misleading `synthetic-present` to
  `before-real-present`.
- When any swapchain in a process triggers the 100 ms performance
  watchdog, other swapchains in that **same process** skip creating
  the costly CPU bridge. Prints:
  `[gfg-native] process breaker: skip CPU bridge on new swapchain pid=...`.
- Keeps the Patch 03 improvements: per-image present semaphores,
  duplicate suppression, slow-frame fallback.
- Does NOT falsely claim that TE8's CPU transport is now fast.
  This patch provides exact profiling and stops *repeated*
  reinitialization stalls in a process, while we identify the expensive step.

### Install and rollback
Exit game, extract ZIP, open Konsole in the extracted folder:

```bash
bash apply.sh
```

The installed original layer is saved as `libVkLayer_gfg_native.so.before-patch-04`.
To undo:

```bash
bash rollback.sh
```

Keep your existing Steam launch parameters.
Read `~/gfg-native-test.log` and send the first few `TE stages`,
`CPU convert`, and `watchdog` lines along with observed game FPS.
If different processes have different `pid=` values, the per-process
breaker cannot cover them. Correct diagnosis then requires a different
architecture or an opt-in cross-process policy.
