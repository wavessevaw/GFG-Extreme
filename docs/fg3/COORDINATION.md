<!-- codex-fg3-coordination -->
Continuation against issue #132 and PR #133. PR #133 is the integration base:
`claude/native-gpu-bridge` at `8e3f58c16ea8a7fcd11462518f90bd19fe29094f`.
The working branch `codex/fg3-integration` is a fast-forward descendant of it.
Stable `main` is untouched.

## Actual-device generation and remaining losses — 2026-10-16 07:16 UTC

The next owner-supplied Witcher 3 capture matches the `internal.3` ELF hash
`a09d5e366f6281e2c3483f272f7059de7b9493e37b0869275c5318edef81bc71`.
Its final cumulative snapshot is **3806 real / 3080 synthetic / 4522 skipped /
0 layer errors**. Thus the present metadata compatibility fix has enabled
synthetic WSI handoffs on the actual SteamOS/RADV device. This is **1.809 API
handoffs per real**, with only **40.52%** of synthetic opportunities handed
off, not 3× delivery or physical FPS. Five bridges were created. There were
911 transport-ring busy events, 1202 zero-timeout image acquire misses and
468 history holds including the five initial frames; TE-busy was zero.
App-owned IDs disable synthetic ID instrumentation, so completion/scanout
cadence remains unobserved. CPU present-call median/p95 was 329.9/690.3 µs
(layer-owned 307.5/651.5 µs); these are not GPU cost or input latency. GPU
timestamps were not captured. The raw archive remains outside Git.

The current changes fix a concrete resource selection error: indexing the
transport ring by app-frame modulo can pick a newer pending slot after a
skip while an older slot is free. Reservations now advance independently of
skipped app frames and scan all slots with nonblocking fence polls. Ring
depth and swapchain image count are unchanged. This can remove avoidable
misses, not actual GPU saturation; the old log cannot quantify that subset.

The same-device initial/gap path previously synthesized two full-size hold
outputs which native WSI never displayed. It now submits history only. TE's
zero-output path signals the requested analysis-completion timeline value;
the next source copy still waits on real GPU completion. The opt-in shared-FD
path retains its previous hold behavior. New diagnostics expose mutually
exclusive output-loss counts per bridge, reservations rescued by another
slot, history-only submissions, and sampled completed GPU timestamp intervals
to both outputs with LMC stage means. There are no additional GPU waits on
the present path; the LMC query read no longer uses QUERY_RESULT_WAIT_BIT.
GPU timestamps include scheduling gaps and exclude game rendering, transport
copies and physical scanout. A report explicitly states when GPU cost is
unknown; API multipliers are never labelled displayed FPS.

Local software validation passed: 30 native Python tests; both 168-check core
modes; borrowed-device zero-output timeline/history→generation regression;
both Proton maintenance1 layer orders (8 real/14 synthetic/0 skipped, all app
fences complete); injected skip recovery (30/36/22, disjoint losses 6 ring +
6 TE + 10 history); record/submit/index recovery with app fences; independent
WSI content/order checks for tiles and GPU LMC. No synchronization-validation
errors were recorded. GPU timestamps in those logs are software llvmpipe
measurements, not Deck performance. Remote CI is a separate pending check.
`internal.4` is a test-package version only. The independent output worker, deadlines, image
availability/backpressure under Gamescope, physical cadence, quality, power,
latency and long-duration acceptance remain open. Do not merge or release.

I read the PR and its latest owner task (`issuecomment-6205050293`, 2026-10-16).
It requests a reproducible installable **experimental test package**, package
integrity and provenance, a tested exact rollback/uninstall path, full CI, and
one-command local diagnostics. It explicitly rejects public release status or
software-only evidence as hardware acceptance.

## New actual-device failure — 2026-10-16 02:36 UTC

The owner supplied a SteamOS 3.8.28 / RADV Witcher 3 diagnostic capture whose
installed ELF SHA-256 matches the delivered `9ec5d5b` local package. Its final
process snapshot is **3503 real API presents, 0 synthetic, 6996 skipped**, with
no TE-busy, ring-busy, acquire-not-ready or hold events. Five bridge
initializations occurred; the first took 2733.04 ms. These are initialization
and passthrough observations, not successful Deck FG or generation cost.

The present-path guard accepted only an empty pNext or a singleton ID node.
The published DXVK presenter (research snapshot
`e8c80a8d1cdaa0ad21516bf64d9cb073cb57eec3`, not asserted to be the installed
Proton version) builds multi-node fence/mode/ID/damage chains. The capture did
not record node types, so their exact installed combination is unknown.
The corrected path copies known real metadata, retains app fences for real
only, expands damage, preserves the bridge's FIFO contract and diagnoses
unsupported chains with their numeric structure types. App-owned present IDs
and waits now remain in the application's namespace; synthetic calls omit
optional IDs. Layer-owned ID tracing is used only when the app has no ID
namespace. Unknown metadata can therefore pass through with correct app waits.

The report previously selected the first retirement (real=1) and first timing
sample instead of the latest snapshots. It now reports real=3503 / synthetic=0
for this capture and distinguishes initialization from observed generation.
The uploaded raw capture stays outside Git; only these technical findings and
non-identifying test fixtures are published.

Local software validation of the new maintenance1 + damage path passed both
layer orders with 8 real / 14 synthetic / 0 skipped, all 8 app present fences
completed, and zero synchronization-validation errors. Record/submit/index
fault tests with app fences and independent WSI pixel observers also passed.
The read-only metadata tests cover both ID versions and tail-ID handling.
CI explicitly reports a maintenance1 fence-path skip on older ICDs while
still testing incremental present. The later device rerun above observed
synthetic handoffs, but did not satisfy hardware acceptance.

## Published package and CI checkpoint — 2026-10-16

The first package-upload attempt failed because generated Vulkan validation
log names contained `:`, which GitHub Actions refuses in artifact paths.
Commit `26c66b57921ab571c0c178c7b03dd71de363f2e1` normalizes layer-order log
filenames while preserving their contents. The [push run](https://github.com/wavessevaw/GFG-Extreme/actions/runs/38837568874)
passed all build, WSI, synchronization, package, install, rollback, uninstall,
source-rebuild, no-DLL and upload steps. The same-commit [PR run](https://github.com/wavessevaw/GFG-Extreme/actions/runs/38837576059)
passed its checks; artifact upload is intentionally push-only.

The push run contains the seven-day **internal experimental** artifact
`GFG-Native-FG-experimental-26c66b57921ab571c0c178c7b03dd71de363f2e1`
(489 KB; Actions artifact SHA-256
`6d8d6b8db5dfe3ecb94d5247c323feeb5dc7498892556b180274e2051ab5342a`). It
includes the installable package and software validation logs. Its logs and
manifest explicitly label the llvmpipe environment; they do not measure Steam
Deck scanout or performance. This closes the package-CI upload issue only.
Issue #132 remains NOT DELIVERED pending the mandatory OLED, cadence, quality,
latency, power, dynamic-play and stability evidence.

The same-device Vulkan path is the default; the known host-relay path that
triggered `VUID-vkQueuePresentKHR-pWaitSemaphores-03268` is removed. Shared-fd
remains opt-in with capability checks and a bidirectional timeline startup
self-test. Unsupported paths preserve the game's real present. Application
feature chains are copied before modification. Application present-ID/wait
namespaces are preserved; optional layer-owned ID tracing is separate. The optional
present-wait monitor now performs zero-timeout polling, sharing a per-swapchain
host mutex with acquire, QueuePresent and application waits; the previous 100 ms
parallel wait violated Vulkan's swapchain external-synchronization contract
and could stall frame submission. Monitor timing is Vulkan present completion,
not KMS scanout.

GPU LMC is implemented as `GFG_NATIVE_ALGO=lmc-gpu`, with no CPU model
readback/fit worker or delayed queue submission. Tile and GPU-LMC software
tests verify generated pixel distinction and ordering, but procedural scene
comparisons have a small walk/HUD regression and do not establish game quality.
Current FIFO handoffs queue G1, G2, R from each real present; an independent
output worker/deadline profile is not implemented or accepted. Pinned upstream
Gamescope source indicates a per-window FPS cap can restrict FIFO commits and
its `pixel_out` is predicted timing. The actual SteamOS package/version and
GFG/Gamescope layer order are unknown.

SteamOS recovery/package hosts returned proxy HTTP-tunnel 403 before any bytes;
no recovery image was selected or downloaded and no image hash or SteamOS
package match is claimed. A nested Gamescope configure stopped at missing X11
development metadata. `docs/fg3/STEAMOS_DEEP_AUDIT.md` and raw evidence record
these limits. No Deck endpoint is authenticated in this cloud executor, so
physical 90 Hz OLED scanout, image quality, latency, power, 10-minute dynamic
quality and 30-minute stability remain unverified.

Do not merge to `main`, publish a release, or call #132 complete. The local
package and software checks are only a reproducible experiment candidate; the
latest committed checkpoint's Actions result and the hardware acceptance
gates must be reported separately.

Latest raw software evidence: [`docs/fg3/evidence/software-checkpoint-20261016.txt`](evidence/software-checkpoint-20261016.txt). It records 21 native Python regression tests, 168 CPU and 168 GPU-LMC core checks, both WSI layer orders, fail-closed negative tests, and local package install/runtime/diagnostic/rollback/uninstall. The ZIP was built from a dirty worktree for local package exercise; it is not presented as the clean-commit Actions artifact.
