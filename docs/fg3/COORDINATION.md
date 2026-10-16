<!-- codex-fg3-coordination -->
# P0 direction change acknowledged — 2026-10-16

Authoritative latest directive:
https://github.com/wavessevaw/GFG-Extreme/pull/133#issuecomment-6212340968

No release or merge. Uncommitted async/HDR work is preserved as a research
checkpoint, not promoted to product status. The prepared release-publishing job
has been removed before any push; no new tag/release was created. Main is intact.

Stop extending a novel FG pipeline without demonstrated reference advantage.
Next work: verify concrete Steam Deck reference implementations, licenses,
versions/install paths and actual evidence; compare capture, motion, synthesis,
pacing, WSI, HDR/modes and display. Record a traceable behavior specification and
minimal independent vertical slice in docs/fg3/REFERENCE_REIMPLEMENTATION.md.
Continue the official SteamOS-image inspection obligation without substituting
an OS essay for the generator work. No hardware success is asserted.

Checkpoint evidence and limitations:
- internal.4 074536Z: 7339 real / 4051 synthetic / 10613 skipped WSI calls.
- 082931Z: no bridge; Witcher requests MAILBOX + packed10 HDR (format 64).
- Bounded worker, queue host serialization, private render-wait gates, immutable
  metadata, ordered lifecycle draining, opt-in FIFO negotiation and FP16 HDR
  synthesis are in the checkpoint; none have new physical Deck acceptance.
- 31 native Python checks pass. Both core modes: 168 checks, 0 failures each.
- Both layer orders: normal/idle/recreate/unknown/forced-MAILBOX/fallback,
  record/submit/index faults and independent G1/G2/R WSI pixel tests passed
  locally before the final redundant same-queue wait cleanup.
- HDR packed10/FP16 static roundtrip passes all 1024 levels for supported format
  64, including GPU LMC after an edge-coordinate fix. Format 58 lacks BLIT_DST
  on this software ICD and is explicitly refused, not reported supported.
- Async internal readback verification triggers WRITE_AFTER_PRESENT in old
  validation 1.4.309. A fresh validator (4b1aed23) did not report that hazard,
  but found two Workgroup ArrayStride shader defects from old glslang. Padding
  shared arrays to avoid layout-type aliasing is committed for follow-up
  validation; neither the current full CI nor the final revalidation is claimed
  passing. Keep this distinction visible. No ready/usable package claim.

CI for this branch:
https://github.com/wavessevaw/GFG-Extreme/actions/workflows/gfg-native-no-dll.yml

## Checkpoint and reference follow-up

Published checkpoint: e121fca. Native CI failed in bounded async output:
https://github.com/wavessevaw/GFG-Extreme/actions/runs/38895664221
The coordination post succeeded:
https://github.com/wavessevaw/GFG-Extreme/actions/runs/38895664202

Source-backed comparison is now in docs/fg3/REFERENCE_REIMPLEMENTATION.md.
Important correction: lower MAILBOX can belong to the Gamescope WSI transport;
a downstream FIFO override alone is not a demonstrated fix. MAKO's published
4.5.0 source separates lower MAILBOX, compositor FIFO and per-output deadlines.
AMD's open v1.1.4 Vulkan presenter uses distinct queues but requests one generated
frame, so it is not a ready 3x algorithm. HDR FP16 roundtrip does not establish
correct PQ-domain dynamic interpolation. Do not publish this checkpoint.

Post-checkpoint local validation after Workgroup padding: fresh VVL cold run
8 real / 12 synthetic / 2 skipped, zero validation errors; warm run 8/14/0,
zero validation errors. The cold deadline drop is not hidden. These do not
resolve the failed remote CI or physical Deck acceptance.
