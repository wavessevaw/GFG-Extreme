<!-- codex-fg3-coordination -->
Continuation against issue #132 and PR #133. PR #133 is the integration base:
`claude/native-gpu-bridge` at `8e3f58c16ea8a7fcd11462518f90bd19fe29094f`.
The working branch `codex/fg3-integration` is a fast-forward descendant of it.
Stable `main` is untouched.

I read the PR and its latest owner task (`issuecomment-6205050293`, 2026-10-16).
It requests a reproducible installable **experimental test package**, package
integrity and provenance, a tested exact rollback/uninstall path, full CI, and
one-command local diagnostics. It explicitly rejects public release status or
software-only evidence as hardware acceptance. The branch now includes the
package/diagnostic changes and CI artifact upload for pushes to this branch;
there is no artifact URL or green remote CI claim until that Actions run
completes.

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
