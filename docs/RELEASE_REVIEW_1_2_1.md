# Review of 1.2.0 and validation scope for 1.2.1

Reviewed baseline: release v1.2.0 (`43d3078e2e8784c6d0aca3203de957c16aa92f40`), with the subsequent release-status change at `0b3138deb48659469bfeea073de75d76bb56ba22`.

## Confirmed defects addressed

| Trigger in 1.2.0 | Correction |
| --- | --- |
| Hold a stick without changing its position for more than 20 seconds | Treat held axes as activity, so the idle policy does not lower the game cadence/power |
| Input node returns EOF/ENODEV, or relay reports zero devices | Drop dead descriptors, discard partial records and clear stale activity |
| Control policy write fails, then the requested cadence stays unchanged | Record publication only after success; retry failed heartbeats with a full policy |
| Disable/re-enable Frame OS with the same Governor point | Reset policy, energy bank, backoff, scene detector and reader state |
| TDP control is gained/lost without changing cadence | Create/remove the energy broker with power ownership |
| Runner stops, or mmap fails after opening the control file | Release owned mappings/descriptors |
| Release workflow runs concurrently with CI | Run native tests in the release job before packaging/publishing |
| Version differs from 1.2.0 | Verify pacer and HUD payloads for every newly published ZIP |

Regression coverage: `tests/test_frame_os_release_regressions.py` (11 tests).

## Automated validation

The branch CI runs the complete Python suite and generated-config check, native pacer scheduler/control tests, pacer/HUD ABI and mock-driver integration, Vulkan layer ordering, a clean frontend build comparison and Chromium smoke tests. The release job repeats these gates before packaging, checks Flatpak payload hashes, builds the native layers from the release commit, verifies packaged layer files and generates SHA256SUMS.

Use the GitHub Actions runs for the final release commit as the authoritative pass/fail evidence; this document describes coverage, not a substitute for successful runs.

## Limits

This review used repository source and GitHub Actions; no Steam Deck, physical controller, real GPU or interactive Decky installation was available. Host mocks do not validate real Vulkan-driver synchronization, actual input-to-photon latency, energy savings, suspend/resume, HDR appearance or Flatpak Frame OS/Rings operation. No hardware certification or measured performance gain is claimed. Existing 1.2.0 artifacts are not rewritten.
