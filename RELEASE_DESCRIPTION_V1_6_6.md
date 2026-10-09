## GFG Extreme 1.6.6: native frame timing and stall-shield controls

### Available in Extreme
- **Frame timing** and **Stall shield** controls on the home booster card and Settings → Diagnostics.
- Preferences are saved independently per game profile. Changing them republishes the native policy without resetting the operating point, power search or current cadence.
- Frame timing retains its existing default. Shield is opt-in. Both require Frame OS Act; choosing them does not silently unlock Act.
- Active status requires live native telemetry, matching policy acknowledgement and support/active bits. An old layer requests restart/upgrade. Paused gameplay, shadow/observe, learned timing disablement and A/B control windows are represented explicitly.
- Failed saves keep the previous preference and show an error.

Frame timing adjusts when the layer starts a frame. Shield reanchors late-frame pacing instead of adding catch-up waiting. Neither status is a percentage measurement of input-to-photon latency, and shield cannot remove a game loading or shader-compilation stall.

### Validation
Backend tests cover persistence failure, per-profile isolation, native acknowledgement, old layers, paused/A/B/game-disabled states and policy republishing. Browser tests exercise successful independent toggles and a failed save. Full CI also checks native Frame OS/HUD, ABI, build consistency, HUD cost and release packaging.

### Remaining work
Process/fan primitives from 1.6.5 still need Governor activation. Download pausing, memory tuning, reverse power allocation, game-specific ignored scaling, Act starvation and ghosting quality improvements remain in development.

### Install
Download **GFG-Extreme-v1_6_6.zip** and install through Decky Loader (Install from zip). Relaunch the game to load updated native layers. Enable Act, then select the desired controls on the Extreme card or in Diagnostics.

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
