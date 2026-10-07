## GFG Extreme 1.0.4

**A Deck that runs hot no longer gets pushed harder.**

### New
- **Heat-aware Battery and Balanced.** While the APU is *hot* or *heating up*, GFG does not try fewer generated frames. More real frames would mean more watts and more heat. It still tries lower watts and still protects the game when a scene gets heavier. The skipped quality step is tried again once the Deck has cooled. The home screen shows **"Cooling · N W"**, Details shows a *Heat* row, and the in-game overlay adds **HOT** (Standard and Detailed).
- **Last session, extended.** Besides time, FPS and watts, the summary now shows the hottest temperature, how long the APU was warm and how often frametime stuttered.
- **Better logs.** `summary.txt` now reports how long the APU was hot or heating, how often quality was held back for heat, and the share of samples with frametime stutter. Every timeline row also records the Battery engine's phase, the point being verified, the heat state, the engine's current ratio limit and recently failed points.

### Under the hood
- Checking that the renderer applied a setting now lives in its own module (`governor_confirmation.py`) instead of inside the 1,700-line service. Behaviour is unchanged and covered by the same tests.
- Known limitations updated: heat thresholds (item 27), fractional-point resolution time (item 26).

Everything from 1.0.3 is included.

### Install
Download `GFG-Extreme-v1_0_4.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
