# GFG Extreme 2.2.0 — Native Fusion preview

Frame Fusion now has a path for games rendering at the display's native resolution, including games that ignore a requested render scale. On compatible native 64-bit SDR8 games, the renderer preserves BGRA/RGBA input layout and uses a same-format source copy. BGRA no longer needs a full-frame conversion to RGBA before the existing frame generator.

The two history images and source transfer remain necessary. This change removes a conversion step; it does not claim fewer source copies, more real FPS or measured battery savings. The frame generator's model, output encoding and scheduling stay unchanged.

Enable **Settings → Diagnostics → Frame Fusion**, install the bundled updated engine and restart the game. Fusion remains off by default. Unsupported layouts and unavailable sharing fall back to the regular path. Flatpak, 32-bit and HDR use their existing engine paths.

Diagnostics distinguish native transfers and avoided BGRA conversions from Core's removed scaling-input copies. Native-resolution work can be reported when scaling is inactive. The log export retains engine identity, launch setting, dimensions, fallback reasons and the last live context. Publication snapshots are never added together as session totals.

Automated checks cover the production renderer, portable policies, source bytes/alpha, logical RGBA/BGRA sampling, two-frame history isolation, transfer command counts, Vulkan synchronization, Python diagnostics, frontend behavior and final package provenance. Steam Deck/RADV, licensed model execution, suspend/resume and battery comparisons still require device testing. This preview leaves 2.0.3 as the latest stable release.
