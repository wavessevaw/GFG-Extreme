# GFG Extreme 2.1.0 — Frame Fusion Core preview

Experimental prerelease. The stable release remains 2.0.3.

Frame Fusion Core can share compatible real or generated frame buffers with the MAKO scaler, removing one redundant source-image copy while preserving the existing fallback. It supports native x86_64 SDR with the open MAKO scaler and an actual resolution split. The feature defaults off and is enabled in Settings → Diagnostics → Frame Fusion; install the updated engine and restart the game.

The package includes a source-built native renderer fork, immutable upstream and patch provenance, native image/copy/synchronization checks, and a standalone GPU proof tool. UI and exported diagnostics distinguish requested settings from observed processing. No whole-device energy or Steam Deck FPS improvement is claimed yet.

Flatpak, 32-bit, LS1 and HDR use their previous paths. Shared LSFG motion analysis and full Frame Fusion are not part of this preview. Physical Deck and game validation remains required.

SHA-256: `<sha256>`
