# GFG Extreme 4.0.0-sr.5 — four-real-frame inverse candidate

Install the inner ZIP through Decky Loader, reinstall Gamescope Kedavra in Setup and reboot.
Enable Graphics → Super Resolution → Auto. The frontend sets Steam Properties maximum game
resolution to 1024x640 and the internal-display override before RunGame on a 1280x800 display.
Focus is forced in the effective pipeline; disabling SR restores the saved preference.
Actual source/output dimensions are checked by the engine; only 1024x640 to 1280x800 SDR is eligible.

The four-frame inverse uses four distinct actual source textures from Kedavra's six-frame ring,
not synthetic FG output as an observation. Motion fields and local subpixel registration map
the observations to the displayed real or generated phase. A regularized local inverse solves
64 observations for 25 output unknowns with a Focus-derived spatial prior. Low confidence,
cuts, insufficient distinct sampling phases, invalid alpha, or missing history fall back to
spatial SR.3. The displayed-frame label "4-frame Inverse SR" confirms the dispatch, not that
every tile passed confidence gating. One extra high-resolution dispatch, 8 local PCG iterations.
The existing ring is also captured/analyzed with FG off when SR is selected (extra GPU cost).
Other post effects/AA currently select the spatial fallback to preserve their semantics.
For testing use Look Off and AA Off; Focus is automatic.

CPU-model results are from five photographs, synthetic shifted observations, approximate Focus,
and known alignment. They are not native game or Deck GPU measurements. The device must be
tested for motion artifacts, 5-pixel tile boundaries, confidence coverage and GPU timing.
SR.2, SR.3 and single-frame SR.4 remain separate rollback packages.
