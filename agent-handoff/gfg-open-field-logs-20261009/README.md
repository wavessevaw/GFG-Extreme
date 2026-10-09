# GFG Open: handoff of original field logs (8–9 October 2026)

**Purpose:** Transfer the exact user-supplied ZIP archives to the next engineering agent. **NO CODE CHANGES IN THIS BRANCH.** Do not merge this data-only branch into the public release branch; it exists so an agent can fetch the recordings directly with Git.

## User-reported defect

Steam Deck OLED: the overlay reported around **90 FPS** while the image felt like **30–40 FPS**. The owner requested an actual code fix, **not further experimental releases that depend on their repeated manual testing**. They also requested removal of the universal Extreme 15 W cap: retain device-specific, inherited fast/slow PPT and hardware safety limits (already merged in PR #90 and included in v1.6.10). Do not ask them for another log just to defer the fix.

Additional field recording: **2026-10-09 23:09:50** (${name}, 123902 bytes); examine independently without assuming it proves smoothness fixed.

These recordings cover versions and configurations that changed during testing; inspect `plugin.log`, `summary.txt`, `profile.json`, and `open-performance/*.json` **per individual archive** instead of attributing all records to a single stable build.

## Original ZIPs

All original files are included byte-for-byte. Every SHA-256 and Git blob SHA-1 was checked against the uploaded original. Two 21:39:55 archives are identical (same Git blob stored once).

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| [GFG-Extreme-log-20261008-182048.zip](./GFG-Extreme-log-20261008-182048.zip) | 385258 | `fe5d00eb4d6a07428a870199f9c53799f9b0b20571afbd8814089e33d31fc894` |
| [GFG-Extreme-log-20261008-204140.zip](./GFG-Extreme-log-20261008-204140.zip) | 313224 | `2e4ac191a843c819a8a981d1c7100ba11331a09a9fc7c47b0ef3d248d825380e` |
| [GFG-Extreme-log-20261008-220150.zip](./GFG-Extreme-log-20261008-220150.zip) | 31037 | `0e3b58973ba8fb903f33570e9390f7bbb39c98f9ddd22469271076cfc655d684` |
| [GFG-Extreme-log-20261009-192552.zip](./GFG-Extreme-log-20261009-192552.zip) | 164063 | `29a5517d0a6a297ec7a33063444fbbb5a7149746f57f32ec0b6599b2d1752dad` |
| [GFG-Extreme-log-20261009-203639.zip](./GFG-Extreme-log-20261009-203639.zip) | 738165 | `671bfa53583a056659edec2783cfbfae234168f7f334a5417add7639de4a37d1` |
| [GFG-Extreme-log-20261009-213955.zip](./GFG-Extreme-log-20261009-213955.zip) | 98124 | `3ad88386f23af46e017571cef85e3abb86bc4ec4245a3f72b51af2b870ff7533` |
| [GFG-Extreme-log-20261009-213955(1).zip](./GFG-Extreme-log-20261009-213955(1).zip) | 98124 | `3ad88386f23af46e017571cef85e3abb86bc4ec4245a3f72b51af2b870ff7533` |
| [GFG-Extreme-log-20261009-230950.zip](./GFG-Extreme-log-20261009-230950.zip) | 123902 | `b8f4fad63e6f5960ea1113c5b3fb2619ffe12fd3b6f9ef35fa7cf60b04a7c535` |

To verify after checkout:
```sh
cd agent-handoff/gfg-open-field-logs-20261009
sha256sum *.zip
```

## Context for the next agent (observations, not a claimed final root cause)

1. The Oct 9 logs contain fixed-plan output near 90 FPS while **real/source FPS was about 30**. The later session shows **GFG Open falling to `passthrough=true`**, 4 recovery attempts and 0 recoveries.
2. Under `passthrough`, `engine/gfg-open/shaders/compose.comp` writes the current real frame into intermediate output images. Those images can be counted as delivered output without representing distinct motion. Inspect whether this is occurring during the user's complaint, rather than equating submitted frames with unique displayed frames.
3. There are MAKO generated-image acquire-timeout / quarantine diagnostics and relatively long acquire waits. These are evidence to investigate, **not proof that Vulkan FIFO is missing**. In the pinned MAKO code, the ordered SDR path already configures `VK_PRESENT_MODE_FIFO_KHR` and filters dynamic MAILBOX overrides; verify the *runtime* transport choice and end-to-end timing.
4. Changes in v1.6.9 introduced GPU-budget guarded recovery. v1.6.10 keeps the validated shader algorithms and adds sticky `last_active_gpu_ms` and `last_failed_probe_gpu_ms`; do not misread a cheap 0.2–0.3 ms fallback sample as the actual interpolation cost.
5. Two attempted shader-search optimizations were **reverted** after actual Vulkan regression tests detected wrong 10-pixel optical flow and large-motion interpolation image errors. No performance/smoothness fix has yet been validated on device.
6. Verify actual present/display cadence, number of *unique* generated frames, source-copy and output reuse, semaphores, compositor synchronization, and the cost of real GPU interpolation. Add deterministic tests and simulation before claiming the problem resolved.

## Relevant GitHub work

- [PR #89](https://github.com/wavessevaw/GFG-Extreme/pull/89): earlier guarded recovery.
- [PR #90](https://github.com/wavessevaw/GFG-Extreme/pull/90): device-specific Extreme power cap.
- [PR #91](https://github.com/wavessevaw/GFG-Extreme/pull/91): v1.6.10, logs and latest handoff context in the PR discussion.
- [Release v1.6.10](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v1.6.10): diagnostic candidate, **not a verified smoothness fix**.

This branch is intentionally left unmerged for the next agent to inspect. Never modify or overwrite another agent's branch.
