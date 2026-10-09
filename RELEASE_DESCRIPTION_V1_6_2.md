## GFG Extreme 1.6.2: both power caps stay within the ceiling

### Fixed
- **Fast PPT respects the same ceiling as slow PPT.** An inherited fast/slow ratio could previously leave the short-duration cap above Extreme's 15 W ceiling (or your lower limit). Explicit budget ceilings now bound both channels. Fractional Extreme limits are rounded down. Your original caps are restored when GFG releases control.
- **Scale evidence belongs to the game.** Runtime-state confirmation checks the live process PID and start ticks. Steam container PIDs are resolved through NSpid; a fresh file from another process no longer confirms or rejects your game's scale. Missing identity leaves the scale unconfirmed.
- **Text HUD shows confirmed scale.** In Extreme it displays the applied scale, or sc? while unknown, instead of presenting a requested scale as applied.
- Runtime-state reads remain bounded even if a file grows during the read.

### Power-control compatibility
An explicit PPT ceiling requires a verified writer for both fast and slow caps. GFG uses its sysfs/root-helper path for these writes. A manager-only installation that cannot control both channels declines the write instead of risking a short boost above the limit.

### Validation
Regression coverage includes fast/slow ceilings, fractional limits, restore, hardware minimums, manager-only refusal, container identity, PID reuse, unrelated runtime records and requested/applied HUD state. Automated release checks cover the backend, native Frame OS/HUD, frontend and packaged archive. Physical Deck validation is not claimed.

### Install
Download GFG-Extreme-v1_6_2.zip and install it over your current version through Decky Loader (Install from zip). Settings, profiles and learned game data are preserved.

### Verify your download
SHA-256: `<sha256>` (also in SHA256SUMS.txt).
