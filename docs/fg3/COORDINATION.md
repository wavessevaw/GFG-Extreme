<!-- codex-fg3-coordination -->

## P0 launch recovery on current main (2.1.5)

The owner reports every game exits immediately, also with `gfg-native --off`.
This is NOT established as a GPU failure. Removing the entire GFG Steam prefix
is the recovery path when the executable itself is absent. No new user logs requested.

Merged actual upstream main 516b734 (2.1.5), preserving Governor emergency-quality
and loading-transition fixes alongside the fixed-target experiment guard. The
previous integrated archive used 2.1.2-te.8 and is withdrawn below.

Implemented: native component staging at plugin startup, executable readiness,
visible install errors/build/Steam command, initial Off marker matching the UI,
idempotent installs preserving previous-version rollback, inherited native layer
removal in --off, telemetry-directory failure no longer blocking games, and
option-aware passthrough after uninstall/first rollback. A separate real defect
in CreateDevice retry restores consumed loader LINK_INFO before real-only retry
(34be414); this is not claimed as the user's crash cause.

Software checks so far: full merged backend 1351 tests (1 skipped), frontend121
screens, native device/queue/clock/metadata contracts,17 full-pipeline checks
including actual x2/x3 pixel observation and validation in both layer orders.
Latest readiness/rollback regressions19 pass. Final exact-archive checks and a
2.1.5-gsf.7 experimental package follow this source checkpoint.
Hardware remains NOT TESTED; no connected Deck endpoint or /dev/dri in this cloud.
No 90-FPS, SteamOS runtime or all-games-fixed claim is made.



## Withdrawn internal.6 — do not install

Source commit:f7d007998f137697d1a186af1afc79c3255a6ef8.
- Integrated Decky:docs/fg3/artifacts/GFG-Extreme-GSF-0.0.0-fg3-internal.6.zip
- Component:docs/fg3/artifacts/GFG-Native-FG-v0_0_0-fg3-internal_6.zip
- Checksums:docs/fg3/artifacts/SHA256SUMS.txt
- Acceptance:docs/fg3/evidence/gsf-package-1_1-acceptance.json

Actual extracted archive installed, launched a Vulkan WSI diagnostic with VVL0errors,
produced pairs.jsonl/report.md, removed retired status and rolled back successfully.
Rebuild from the included source produced byte-identical production ELF.
These are installable experiments, not a stable release or OLED90FPS acceptance.

## P0 implementation 1.1 — source checkpoint for PR133

The baseline architecture is retained. Inventory covers the actual237-file diff
at5782aa9 (not the stale-main411-file estimate). Source-time pair scheduling,
independent G1/G2 admission, x2 midpoint/x3 thirds, exact GPU RGB duplicate gate,
per-output control-header readiness and bounded age-preserving worker are implemented.
Display-budget exclusions suppress the corresponding GPU output; G2-only uses one
reconstruction at2/3 with a valid V+2 timeline signal.

Native GSF is a separate opt-in UI/RPC/module/launcher, with checksum-verified
component staging and Off/2/3. No new power control; no hidden foreign FG fallback.
GOOGLE timing is provisioned only when advertised, private/app namespaces stay
separate, refresh can be queried, and GFG is explicitly above FROG Gamescope WSI.
Real Gamescope/compositor/DRM execution remains untested; packet tests are not
hardware proof. See NATIVE_GSF_IMPLEMENTATION_1_1.md and HARDWARE_ACCEPTANCE_1_1.md.

Software:17 full-path checks pass,183 core assertions, native contracts,62 targeted
backend checks and118 browser screens. An additional4 WSI checks pass against the
actual ABI-targeted production ELF (x3/x2/recreate/unknown metadata, VVL0errors).
Host ELF requiring glibc2.38 was rejected; a signed-package glibc2.31 SDK build
requires symbols only through2.17 and loads with the actual2.31 loader.

The90Hz lavapipe trace is a negative performance result, not the product target:
45real/28generated WSI acceptances, no physical scanout.26 G1 skips retained a G2;
5 lower-refresh cases dispatched/presented G2 alone with zero validation errors.
Original failures and before/after traces are preserved in the1.1 evidence ZIP.

C hardware and D practical acceptance: NOT TESTED. No /dev/dri or connected Deck
endpoint. No stable release or claim of30→90OLED. Next work requires actual
SteamOS/Gamescope timing/DRM and optical uniqueness/latency evidence; inspect
single-queueG1-copy-afterG2, real-game contention, missed renderer cut and PQ quality.
No new algorithm comparison or PSNR sweep is authorized merely to fill this gap.

# Architecture accepted; GSF native implementation — 2026-10-16

The owner's latest P0 directive closes comparative research and prioritizes a
working full pipeline. No new PSNR experiment series. No release/merge/main change.

**One architecture:** GPU-resident two-source interpolation, shared hierarchical
motion analysis, adaptive geometric refinement, separate t=1/3 and 2/3 visibility,
bounded asynchronous output and per-output deadlines. GSF is the chosen backend;
full projective fitting is a GPU confidence-triggered path within that backend.
No user architecture choice, proprietary DLL or game depth/MV requirement.

Accepted decision, confidence, alternatives, component ownership and exact next
engineering barriers: docs/fg3/ARCHITECTURE_DECISION_1_0.md.
Closed experiments, including failures: docs/fg3/SHARED_FLOW_PROTOTYPE.md and
`docs/fg3/evidence/gsf-research-20261016.zip`.

Implemented code:
- 26416e2: poor affine agreement triggers full GPU projective fit; fast-turn
  probe recovered from −0.426 to approximately −0.002 dB against GPU LMC.
- de48b0d: app GPU capture → borrowed-device GSF → G1/G2 → async G1/G2/R WSI.
  Per-output absolute deadlines, one-source lookahead, late resync, bounded
  readiness/acquire waits, explicit deadline drops, rate-dependent stale budget.
  Pacing waits run only in the worker; metadata fallback stays synchronous.
  Coherent launcher: scripts/run_gfg_gsf.sh, default target 90 host clock.
- 7108ce5: reproducible full-pipeline check script and per-image render-finished
  semaphores in the test app, fixing VUID-00067 with validation above GFG.

- 1151078 / 852b7ca: cut/hold endpoint copies excluded from native synthetic credit;
  real-only fallback when no output worker exists. Source 9522288 has the final harness.

**Verified software functionality, not Deck acceptance:** thirteen full-path checks
pass under fresh VVL, both layer orders: 182 core assertions, borrowed device,
independent actual G1/G2/R pixel/order/spacing observation, recreate, queue idle,
unknown metadata, cut-credit exclusion and real-only fallback without worker. 31 Python regressions and both 168-check LMC baselines pass.
Historical fixture configured output clock9Hz, but its source3Hz description was wrong (the old app paced33ms); four real+six distinct synthetic with
~111 ms minimum host handoff spacing. 90 Hz software attempts missed deadlines and
are archived as failures. No interpolation/scanout success is inferred from CI.

Evidence: docs/fg3/evidence/gsf-native-acceptance.json and gsf-native-acceptance.zip.
Run: scripts/check_gsf_pipeline.py (native/core/validation paths required).
The native CI now has a separate GSF functional step and preserves its logs even
if later legacy checks fail. Latest remote CI success is not claimed.

Remaining barriers in implementation order:
1. Gamescope lower-MAILBOX/compositor-FIFO future-deadline contract. Current
   native slice supports ordinary FIFO; blanket FIFO substitution is not chosen.
2. Correct HDR linear/PQ processing, source/compute/presenter queue provisioning,
   actual game contention/power budget, and a cut heuristic that missed renderer cut.
3. Physical 30 real → 90 distinct OLED/SteamOS acceptance: Gamescope commits linked
   to DRM flips and preferably optical observation. Current cloud has no /dev/dri
   and no connected Deck endpoint. This is an explicit hardware blocker.

Do not promote this opt-in implementation to release or claim physical 90 FPS.
