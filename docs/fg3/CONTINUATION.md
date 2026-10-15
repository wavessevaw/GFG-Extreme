# Active assignment — not a completion report

Owner mandate: #132, 30 real → 90 physically displayed FPS on Steam Deck OLED,
1280×800 / 90 Hz, usable dynamic quality, bounded latency and preserved real
FPS. No claim of delivery until physical acceptance, quality/power/latency,
10-minute dynamic and 30-minute stability evidence. No main merge or public
experimental binaries. Session end is not task completion.

## Published state and collaboration

- `codex/fg3-gpu` / `2ba97b4` preserves the previous session's complete source
  and raw software logs. Pushed and verified remotely; not the product base.
- `codex/fg3-integration` is based on PR #133 (`8e3f58c` originally), preserving
  that transport's public function signatures and present-ID hook interfaces.
  `2d35262` adds application-device TE, both layer dispatch orders, caller-owned
  timeline, BGRA shader packing and a core TRANSFER-read synchronization fix.
- PR #133's implementing agent acknowledged direct ownership coordination:
  Codex owns transport/core/quality; the other agent owns present monitor,
  shared-fd self-test, deadline/drop policy, acceptance capture/report/runner,
  and the targeted SteamOS/Gamescope source spike. Read new PR comments before
  further overlapping changes. Never replace its branch wholesale.
- Direct api.github.com is blocked by this executor's network (403). Git push
  and public GitHub HTML work. The scoped `fg3-coordination.yml` posts/updates
  `docs/fg3/COORDINATION.md` in PR #133. PR creation with its GITHUB_TOKEN was
  rejected (403); use published commits/compare for technical review. Do not
  pretend a draft PR exists. The owner is not the message courier.

## Current findings and exact next work

1. Keep the passing same-device path; repeat GPU tests after meaningful edits.
   The old relay mode reproduces VUID 03268. Its failure evidence is preserved.
   A timeline host signal in a relay thread is not a submitted resolving GPU
   signal. CPU-fit LMC split submissions also require this audit in fd mode.
2. Finish regression and publish recovery fixes for C1. Record-failure fallback
   copies the retained real image (duplicate kind D, not synthetic), re-chains
   its real-ready semaphore, then forwards the original. Unrecoverable acquire
   failures forward real and request OUT_OF_DATE / swapchain retirement.
   Three fault-injection cases and independent WSI-pixel observation pass.
3. Implement explicit GPU LMC fit, evaluate against CPU LMC before selecting
   final quality/performance settings. Earlier GPU kernels exist at `7f445f2`:
   lmc_layers.comp, lmc_irls.comp, lmc_palette.comp, lmc_plane.glsl and the host
   dispatch sequence in te_lmc.inc. Current kernels have better coalesced
   statistics/search/orphan passes; retain them. Do not restore a worker that
   submits to the application queue from another thread. Keep CPU-fit LMC as
   reference. Do not mislabel old FIT_WAIT GPU work as excluded CPU time.
4. Implement/integrate asynchronous paced output with the other agent's
   Gamescope findings. Current back-to-back FIFO presents are NOT final 90 Hz
   pacing. Any worker using the app queue requires host synchronization with
   ALL app queue API calls, retained per-job outputs and copied pNext payloads;
   do not introduce races or unbounded stale jobs. Current public pNext remap
   mutates caller-owned structures and also needs immutable-chain review.
5. Resolve target-hardware access via authorized integration. Both sessions
   currently report no authenticated Deck endpoint. The user's inventory zip
   contains only artifacts.json/report.json, not a connection. Do not invent
   endpoints or claim hardware results. Ask for existing authorized executor
   through PR coordination, not repeated owner installs. Continue independent
   engineering while this remains unavailable.

## Reproduction in the current cloud workspace

Worktree: `/workspace/GFG-Extreme-integration`. Original preserved worktree:
`/workspace/GFG-Extreme`. No root AGENTS.md. No external MAKO source needs edits.
Vulkan headers: `/workspace/.gfg-vulkan/vkh/include`; Xvfb `:93`.
Rootless tools/sysroot: `/workspace/.gfg-tools/bin`,
`/workspace/.gfg-sysroot/usr/bin`, `/workspace/.gfg-sysroot/usr/lib/x86_64-linux-gnu`.

Build core with PATH including those bins:
`make -C engine/gfg-temporal BUILD=/workspace/.gfg-integration-core VK_CFLAGS=-I/workspace/.gfg-vulkan/vkh/include -j2 all lib`.
Build native with LIBRARY_PATH/CPATH pointing to the sysroot:
`make -C engine/gfg-native ENABLE_TE=1 BUILD=/workspace/.gfg-integration-native TE_LIB=/workspace/.gfg-integration-core/libgfg-temporal.a VULKAN_HEADERS=/workspace/.gfg-vulkan/vkh/include layer /workspace/.gfg-integration-native/wsi-gpu-smoke /workspace/.gfg-integration-native/borrowed-device /workspace/.gfg-integration-native/gpu-wsi-observer`.

Runtime: DISPLAY=:93; VK_ICD_FILENAMES points to sysroot
`share/vulkan/icd.d/lvp_icd.json`; LD_LIBRARY_PATH points to sysroot lib dir;
VK_LAYER_PATH includes native build plus sysroot `share/vulkan/explicit_layer.d`.
GFG_NATIVE_FG=1 GFG_NATIVE_GPU_BRIDGE=1 GFG_NATIVE_GPU_SYNC=same-device
GFG_NATIVE_ALGO=tiles GFG_TEST_VALIDATION=1 GFG_TEST_EXPECT_GPU=1;
test both `VK_LAYER_GFG_native:VK_LAYER_KHRONOS_validation` and reverse order.
Use GFG_NATIVE_GPU_BRIDGE_VERIFY=1 for test-only readback. It is not the runtime
pixel path and is not physical display observation. Fault tests use
GFG_NATIVE_GPU_FAULT=record|submit|index, GFG_TEST_FRAMES=2,
GFG_TEST_EXPECT_FAULT=1, GFG_TEST_ALLOW_SKIPS=1; submit/index also expect
GFG_TEST_EXPECT_RECREATE=1. Actual packaged/native/core CI has no public uploads.

## Hardware facts, not performance evidence

Inventory: Galileo, SteamOS 3.8.28 (20260922.1), glibc 2.41,
Mesa 26.0.0-devel d246f60ddf / RADV VANGOGH, kernel
6.18.50-valve2-1-neptune-618-gc7289a96b14d. No current authenticated remote
executor. The DLL and private extracted data remain outside git and must not
be distributed. Existing synthetic/software tests are never acceptance.
