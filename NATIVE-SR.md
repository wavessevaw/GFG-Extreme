# GFG Extreme 4.0.0-sr.6 — cached four-frame inverse candidate

Install the inner Decky ZIP. Install the bundled Gamescope from Setup and reboot.
Super Resolution automatically sets Steam Properties maximum game resolution to 1024x640
on a 1280x800 display and forces Focus without overwriting the user's saved preference.
Only 1024x640 → 1280x800 SDR with Focus and no other post effects runs temporal reconstruction.

SR.5 ran a 25-variable, eight-iteration inverse solve on each displayed phase, starving FG
on a Deck. SR.6 separates the normal Focus, four-real-frame inverse, and inexpensive
cache reprojection pipelines. The solver runs once per real anchor, with four PCG
iterations and a bilinear halo. Its signed luma residual is cached with the real ring slot.
Generated phases reproject the two real-anchor residuals using the already calculated
pair selection; no generated frame is an inverse observation. GPU timestamp guard
suspends temporal processing after a composite exceeds its existing GPU budget.
Graphics distinguishes active cached reconstruction and GPU-limited spatial fallback.

CPU synthetic known-shift comparison on the same five images and two degradation models:
SR.3 32.47 dB, SR.5 eight steps 37.21 dB, SR.6 four steps + bilinear halo 35.47 dB.
This evaluates the local solver, NOT cache reprojection, game accuracy or Deck GPU time.
The 90-Hz/FG frame budget and coverage must be verified on device.
