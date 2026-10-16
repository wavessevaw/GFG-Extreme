# Active assignment — not a completion report

Owner mandate: #132, 30 real → 90 physically displayed FPS on Steam Deck OLED,
1280×800 / 90 Hz, usable dynamic quality, bounded latency and preserved real
FPS. No claim of delivery until physical acceptance, quality/power/latency,
10-minute dynamic and 30-minute stability evidence. No main merge or public
release. PR #133 requests an expiring Actions artifact for an experimental
test package. Session end is not task completion.

## Published state and collaboration

- `codex/fg3-gpu` / `2ba97b4` preserves the previous session's complete source
  and raw software logs. Pushed and verified remotely; not the product base.
- `codex/fg3-integration` is based on PR #133 (`8e3f58c` originally), preserving
  that transport's public function signatures and present-ID hook interfaces.
  `2d35262` adds application-device TE, both layer dispatch orders, caller-owned
  timeline, BGRA shader packing and a core TRANSFER-read synchronization fix.
- PR #133's implementing agent acknowledged direct ownership coordination:
  The other agent subsequently exhausted its token budget (PR comment,
  2026-10-15 16:47 UTC). Codex is now sole implementer and owns ALL remaining
  transport, monitor, shared-fd self-test, deadline/drop, acceptance and
  SteamOS/Gamescope tasks. Do not wait for that agent or its unpublished code.
  It explicitly authorized integrating this branch into the existing #133
  branch while preserving stable main and rollback.
- Direct api.github.com is blocked by this executor's network (403). Git push
  and public GitHub HTML work. The scoped `fg3-coordination.yml` posts/updates
  `docs/fg3/COORDINATION.md` in PR #133. PR creation with its GITHUB_TOKEN was
  rejected (403); use published commits/compare for technical review. Do not
  pretend a draft PR exists. The owner is not the message courier.

## Current findings and exact next work

1. Keep the passing same-device path; repeat GPU tests after meaningful edits.
   The old relay mode reproduced VUID 03268 and has now been removed. Shared-fd
   mode is explicit; any failed capability/import check prevents GPU bridge
   activation and retains the real present. llvmpipe lacks semaphore-FD import,
   so the shared-fd self-test success path remains untested. CPU-fit LMC split
   submissions also remain outside the validated same-device package path.
2. C1 recovery fixes are in the branch. Record-failure fallback
   copies the retained real image (duplicate kind D, not synthetic), re-chains
   its real-ready semaphore, then forwards the original. Unrecoverable acquire
   failures forward real and request OUT_OF_DATE / swapchain retirement.
   Three fault-injection cases and independent WSI-pixel observation pass under
   software synchronization validation.
3. GPU LMC fit is implemented and its 168 core checks pass. Earlier GPU kernels
   exist at `7f445f2`:
   lmc_layers.comp, lmc_irls.comp, lmc_palette.comp, lmc_plane.glsl and the host
   dispatch sequence in te_lmc.inc. Current kernels have better coalesced
   statistics/search/orphan passes; retain them. Do not restore a worker that
   submits to the application queue from another thread. Keep CPU-fit LMC as
   reference. Do not mislabel old FIT_WAIT GPU work as excluded CPU time.
4. Current FIFO bridge queues G1, G2, then R inside each real present call on
   the application's queue; it has no independent output worker, and software
   handoff count is not proof of 90 Hz scanout. Do not add an async worker
   without serializing every host access to the app queue, retaining per-job
   images, copying all pNext payloads, bounding stale work, and proving
   destruction/drain behavior. App-owned present IDs/waits are preserved and
   synthetics omit optional IDs; layer-owned tracing is separate. Caller-owned
   metadata chains remain immutable. The optional present-wait
   monitor uses zero-timeout polling and a per-swapchain mutex shared with
   application acquire/present/wait calls to honor Vulkan external
   synchronization, with 1 ms between polls. The Deck layer order
   and actual KMS/panel cadence remain unknown.
5. Hardware acceptance remains pending: this cloud executor has no
   authenticated Deck endpoint. The inventory zip contains device metadata,
   not a connection. Do not invent endpoints or claim hardware results, and do
   not ask the owner to relay patches or repeat manual test steps. Continue
   independent engineering and keep the physical tests visible as unverified.

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

An actual Deck Witcher 3 diagnostic uploaded on 2026-10-16 02:36 UTC shows the
delivered `9ec5d5b` package initialized but did not generate: real=3503,
synthetic=0, skipped=6996 (last cumulative snapshot after five swapchains).
`docs/fg3/COORDINATION.md` records the present-chain compatibility fix and
corrected report selection. The capture does not log exact pNext node types;
do not invent them or claim the new `internal.3` package passed on Deck.

Inventory: Galileo, SteamOS 3.8.28 (20260922.1), glibc 2.41,
Mesa 26.0.0-devel d246f60ddf / RADV VANGOGH, kernel
6.18.50-valve2-1-neptune-618-gc7289a96b14d. No current authenticated remote
executor. The DLL and private extracted data remain outside git and must not
be distributed. Existing synthetic/software tests are never acceptance.


## New GPU LMC and package checkpoint

TE_ALGO_LMC_GPU=2 / GFG_NATIVE_ALGO=lmc-gpu restores the repository's 7f445f2
GPU RANSAC/IRLS/palette solvers, retaining current coalesced flow/stats/orphan
passes and cost tiers. No fit thread, model staging/readback or delayed queue
submission in this mode. It works on a borrowed device with no optional
features enabled, except that the native bridge enables its timeline. All
output signals are submitted before WSI calls. BGRA packing is in LMC compose.

GPU fitting now matches CPU LMC_FIT_SUB=2 and deterministic 512-point hypothesis
ranking; floating-point IRLS still differs from CPU double precision. A first
3-scene/8-pair comparison exists in /tmp/gfg-integration-*-lmc-quality.json:
GPU mean FLIP ≈0.0408/0.0296/0.0370 vs CPU ≈0.0408/0.0296/0.0366 on
specular/sword/walk. Small HUD/walk regression remains; NOT quality acceptance.
Those scenes are under /workspace/.gfg-bench-scenes (Godot 4.4.1). Do not claim
these procedural scenes are games or physical Deck output. GPU model time is
kept IN GPU totals and labelled gpu_model, never excluded as CPU fit_wait.

Package/install/rollback code and 4 tests were brought forward from the
preserved source branch, adapted to GFG_NATIVE_GPU_BRIDGE and lmc-gpu. Default
GPU binary no longer compiles cpu_bridge.c; ENABLE_CPU_BRIDGE=1 explicitly
builds the legacy regression. Full source includes .inc and GPU solvers.
Internal package only, hardware_acceptance=false; an expiring Actions artifact
is configured on pushes to this branch, with no release publication.
CI restores loader/pass-through, CPU UNORM/sRGB, bootstrap, private package,
installed GPU runtime, rollback/uninstall and byte-identical source rebuild,
in addition to GPU/sync/fault checks. The package includes build environment
and exact commands; Actions upload is configured to include validation logs.
Do not remove mandatory regression gates. Raw local verification is captured
in [`software-checkpoint-20261016.txt`](evidence/software-checkpoint-20261016.txt);
its ZIP is explicitly marked dirty-worktree evidence, not the CI artifact.

## SteamOS and Gamescope source audit

Read-only upstream checkout: /workspace/gfg-research-sources/gamescope,
2b5cf191d1047d6895516a834de8a72ac1c342f3 (2026-10-13). It is NOT proven to
match the installed SteamOS build; package index access returned 403 and the
uploaded device report lacks Gamescope's package version.

Findings from that pinned source: its WSI forces underlying MAILBOX and
implements FIFO through the gamescope-swapchain protocol. steamcompmgr's
handle_done_commits_* admits at most one FIFO commit/window per vblank;
window_refresh_cycle includes the Gamescope app FPS limiter. Thus a 30 FPS
Gamescope limiter can cap FG outputs as well. The new timing protocol itself
labels pixel_out as PREDICTED scanout, with zero timestamps on dropped commits.
DRMBackend.cpp page_flip_handler obtains the actual KMS vblank timestamp,
updates visible framebuffer IDs and wakes the compositor. Vulkan present-wait
or predicted pixel_out alone is not physical scanout evidence. Need explicit
frame/commit→KMS visibility correlation or an independent physical observer.
No nested Gamescope build has been completed yet. Dependencies include pinned
wlroots, liftoff, vkroots, Wayland/X11/SDL and optional DRM; preserve exact
submodule commits if building. Do not replace the owner's SteamOS compositor.

`docs/fg3/STEAMOS_DEEP_AUDIT.md` records the bounded source audit and the
SteamOS recovery/package-host probe. All five official hosts failed before an
HTTP response with proxy 403; no recovery image was downloaded and no hash or
package match is claimed. Meson/Ninja were available, but the nested configure
stopped at missing X11 metadata; no Gamescope build is claimed. `pixel_out` in
the pinned source is predicted presentation time; KMS page-flip has a separate
timestamp and no complete present-ID/framebuffer correlation. The monitor fix
above does not change that evidence boundary.

## Diagnostic test package checkpoint

The PR #133 owner comment `issuecomment-6205050293` asks for a reproducible
experimental installable package, tested rollback/uninstall, full CI, a
checksum and one-command diagnostics, explicitly not a public release or
hardware acceptance. The integration branch now contains `--diagnose`, a
private local archive/report, install/rollback/uninstall coverage, and a
seven-day GitHub Actions artifact upload on pushes to this branch only. The
report clearly labels physical display and KMS scanout unobserved. The package
must be built from the committed checkpoint and CI artifact; no artifact link
or green remote CI is claimed until Actions completes. Diagnostic app
stdout/stderr can contain private paths and stays local unless a user chooses
to share it.
