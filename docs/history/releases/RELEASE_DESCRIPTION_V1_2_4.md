## GFG Extreme 1.2.4

**Official stable release.** Governor and Frame OS safeguards based on a real Steam Deck OLED diagnostic recording from October 8, 2026.

### Balanced: recover from a 60 FPS output trap on a 90 Hz OLED
- Fixed a dead end where a `45 real ×2` target actually rendered only ~30 real FPS and produced ~60 FPS on the 90 Hz display.
- If a confirmed Balanced point is short of its real **and** output targets, is not stalled, and measured APU draw is below the TDP cap, the guard may trade generated-frame ratio for the next **feasible fixed-ratio point** (such as `30x3`), rather than holding at 60 indefinitely or raising watts unnecessarily.
- Respects the 30-real-FPS minimum in Balanced, measured renderer generation capacity, existing rollback/verification safeguards, and 60 Hz LCD/Dock behavior.

### Quality: quicker recovery from unproductive renderer transitions
- The Quality search can now reject a renderer-applied trial early when a full, fresh observation window confirms **both** a mismatched multiplier and a severely starved output.
- It still waits for genuine renderer-applied evidence; unavailable or stale data is not taken as proof of failure.
- Quality's power optimizer now checks **measured output FPS as well as real FPS**: a point cannot be accepted at 60/90 FPS just because its capped real stream is healthy. At the power ceiling it rejects persistently under-delivering points and resumes searching.
- This reduces prolonged low-output searches; it does **not** promise every game can reach 90 FPS at native or high-quality ratios.

### Experimental Frame OS Act: stop repeated FPS collapses
- After **two** verified injection-induced output-starvation rollbacks in one Governor session, automatic Act **renderer injection** is locked out for that session instead of retrying indefinitely.
- The normal Governor/renderer point remains active. Observe and Shadow modes are not affected; Act can be explicitly re-armed by the user.
- Diagnostics now expose `frame_os.starvation_yields` and `frame_os.output_starvation_lockout`.
- This is a **safety fallback**, not proof of MotionBoost improvement. The experimental Act mode requires further hardware A/B validation.

### Diagnostics and verification
- Version metadata updated consistently in the plugin log, session recorder, and analyzer (the previous 1.2.3 bundle still announced 1.2.2 in one location).
- Regression tests added for the Balanced 60 FPS trap, Quality applied-state mismatch and Frame OS Act repeated-starvation prevention.
- All changes preserve the Saved profile and TDP restoration guarantees.

### Install
Download `GFG-Extreme-v1_2_4.zip` and install with Decky Loader → **Install from zip**. Restart a game after installing so its Vulkan layers and launch wrapper update.

### Limitations
Automated CI tests are not a substitute for real Steam Deck validation. The game must actually deliver enough real frames for its selected output point; FPS is not guaranteed by software alone.

### Verify your download
SHA-256: `<sha256>` (also in `SHA256SUMS.txt`).
