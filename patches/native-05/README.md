# GFG Native FG Patch 05: GPU→CPU memory readback fix

Independent *hotfix*, NOT a new GitHub release or GFG Extreme stable update.

## Root cause from Steam Deck logs
1280x800, BGRA8 UNORM:
- GPU image copy fence: ~0.34 ms
- CPU `rgba_to_rgb` conversion: **520.17 ms**
- TE8 full upload/submit/compute: **4.66 ms**
- Original memory selection prioritized `HOST_COHERENT` but did not
  prioritize `HOST_CACHED`. On Vulkan, coherent-but-uncached (write-combined)
  CPU memory is extremely expensive for millions of byte-sized reads.

## Changes
- Choose a `HOST_VISIBLE | HOST_CACHED` Vulkan memory type for
  GPU readback whenever supported (including non-coherent types).
- Use `vkInvalidateMappedMemoryRanges` before CPU read on non-coherent
  memory; `vkFlushMappedMemoryRanges` after upload.
- First bulk-copy the mapped 4-byte-per-pixel image to a normal malloc
  buffer with `memcpy`, then BGRA/RGBA→RGB in that CPU-cached buffer.
  Output uses the reverse cached pack and one bulk memcpy to GPU staging.
- Report `staging memory ... host_cached=...`,
  `memcpy_from_gpu_ms`, `swizzle_ms`, and
  `memcpy_to_gpu_ms` separately.
- Retains Patch 04 watchdog (100 ms per-frame), per-process breaker,
  Patch 03 per-image semaphores, and duplicate suppression.

No promised speed increase until tested on Steam Deck. If this device has
no CPU-cached compatible Vulkan memory, the fallback still uses bulk
memcpy instead of millions of uncached pixel reads. The watchdog will
still disable FG if the capture is too slow.

## Install
Quit the game. Extract patch ZIP and open Konsole in extracted folder:

```bash
bash apply.sh
```

The script checks SHA256 of the binary, retains the previous installed
library as `libVkLayer_gfg_native.so.before-patch-05` and does not
modify GFG Extreme, Steam, game files, or launch options.

## Rollback
```bash
bash rollback.sh
```

## Device test
Keep the same Steam launch command:
`GFG_NATIVE_TRACE=1 ~/.local/bin/gfg-native %command% > "$HOME/gfg-native-test.log" 2>&1`.

From the log, check:
- `staging memory type=... flags=... host_cached=... coherent=...`
- `CPU convert frame=0 ... rgba_to_rgb_ms=... memcpy_from_gpu_ms=... swizzle_ms=...`
- `TE stages frame=0 ... total_ms=...`
- `generated=...` and `watchdog disabled ...`

These distinguish slow memory transfer from color packing and shader work.
Source: Vulkan specification, host cached readback types:
https://docs.vulkan.org/spec/latest/chapters/memory.html
