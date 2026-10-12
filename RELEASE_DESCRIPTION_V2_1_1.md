# GFG Extreme 2.1.1 — Frame Fusion diagnostic preview

Experimental prerelease. Stable remains 2.0.3. Fusion defaults off.

Fixes missing Frame Fusion evidence in exported recordings. Timeline samples now retain actual native status, publication counters, source/presentation dimensions and scaler constraints. The latest live contexts survive game exit in frame-fusion-contexts.json. Game process snapshots capture the Fusion launch setting; renderer-identity.json compares mapped MAKO file hashes with the plugin's expected manifest without treating a replaced installation as the running file. Unavailable identity remains unknown.

The plain-language summary distinguishes enabled settings, prepared inputs and observed direct work. Copy counters are snapshots, never a summed session total or an FPS/energy claim. Existing 2.1.0 logs with only the UI switch are explicitly inconclusive.

The native Fusion renderer and its immutable patch are unchanged from 2.1.0. Install this plugin update, keep or reinstall its matching engine, and restart the game after changing Fusion. Device performance and battery benefit still require an off/on comparison in a controlled scene; see docs/FRAME_FUSION.md.

SHA-256: `<sha256>`
