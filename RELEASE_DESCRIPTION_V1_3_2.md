## GFG Extreme 1.3.2: steadier Governor, no surprise 60 Hz

A reliability release on top of 1.3.1. Nothing new to set up: the same fully automatic Governor, with fewer ways to be fooled by a hiccup.

### Display
- Only an explicit *Target FPS* change can switch the screen's refresh rate. Picking a profile or saving unchanged settings never drops an OLED to 60 Hz.

### Frame OS
- Act gives up a MotionBoost only after a settled run of consecutive low frames, not after one renderer re-plan sample. Long Steam menus no longer lock Act out.
- Leaving a game or switching games clears the fast-FPS and Act stability state, so the next game starts clean.

### Governor
- **Fast TDP rescue needs fresh evidence.** Each fast raise needs a new renderer sample. A telemetry gap or a repeated FPS window can no longer stack up into a phantom raise.
- **Temporary frame-generation capacity loss is not a failure.** When Vulkan briefly has fewer generated-frame slots (game start, a swapchain rebuild), GFG steps down to what is available and comes back once the slots return and hold. The higher point is no longer blacklisted for 10 minutes. Real FPS or TDP failures keep their back-off.
- With zero generation slots GFG pauses safely instead of thrashing. It resumes only after the saved overlay settings are fully restored.
- **Warm starts never repeat a recent failure.** A point that recently failed at a given power is not restarted at the same or lower watts.
- Saved game history loads safely even when damaged: oversized numbers and NaN are dropped instead of breaking start-up.

### Install
Download `GFG-Extreme-v1_3_2.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept. Restart a running game so its layers update.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
