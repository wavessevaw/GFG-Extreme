<!-- codex-fg3-coordination -->
Continuation against issue #132 and PR #133. PR #133 is the integration base:
`claude/native-gpu-bridge` at `8e3f58c16ea8a7fcd11462518f90bd19fe29094f`.
The working branch `codex/fg3-integration` is a fast-forward descendant of it.
Stable `main` is untouched.

I read the PR and its latest owner task (`issuecomment-6205050293`, 2026-10-16).
It requests a reproducible installable **experimental test package**, package
integrity and provenance, a tested exact rollback/uninstall path, full CI, and
one-command local diagnostics. It explicitly rejects public release status or
software-only evidence as hardware acceptance.

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
feature and present-ID chains are copied before modification. The optional
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
