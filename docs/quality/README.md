# Experimental bounded reconstruction build

Based on GFG 3.2.2 (`92b557f678d118ae97948673c26e2498b7a28467`).
Engine: `a79e041e8f0eea69ae147e89079162ce325b890f` in wavessevaw/GSF_Kedavra,
a local improvement of its exact stable pin, not a wholesale 1.4.4 upgrade.

The separate Quality workflow builds an installable Decky ZIP as an Actions
artifact; it does not publish or replace the stable release. The stable release
workflow remains unchanged. This branch is experimental and has not passed
Steam Deck performance, frame pacing or latency acceptance.

## Actual change

Five-tap sharp reconstruction now stays within its local sample range, reducing
ringing on fractional motion. No extra samples, buffers or passes. Existing
motion estimation, frame scheduling, settings, UI and source support remain.
The engine benchmark adds mean/P95 per-pass times and saves source frames.
See engine `docs/quality/AUDIT.md` and `VALIDATION.md` for evidence and limits.

## Install and rollback

Back up Decky settings and retain the official 3.2.2 ZIP before testing.
Download `GFG-quality-test-build` from the successful Quality Actions run;
extract its outer artifact ZIP, verify SHA256SUMS.txt, then install the inner
GFG-Extreme ZIP using Decky Settings → Developer → Install Plugin from ZIP.
Use Setup → Update/Install engine and reboot when requested. Confirm Setup
reports the installed runtime matching the plugin before testing.

To return to 3.2.2, use Setup → Remove/restore stock engine and reboot, then
install the official GFG-Extreme-v3_2_2.zip, install its engine and reboot.
Existing automatic boot recovery remains available. If Gaming Mode fails,
use the project's existing recovery procedure; do not overwrite system files
by hand. No settings-schema changes are introduced by this candidate.

## Acceptance

Software correctness is necessary, not sufficient. Compare baseline and
candidate on Deck using matched workloads and A/B/A runs, GPU mean/P95/P99,
KMS pacing, missed intervals, both x3 phases, LCD/OLED 60/90 Hz and latency.
Do not label this candidate stable until hardware and real-content checks pass.
Full next-generation specification remains incomplete.
