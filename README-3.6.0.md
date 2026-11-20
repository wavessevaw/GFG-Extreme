# What's new in GFG-Extreme 3.6.0

- **Cleaner camera reversals.** The generator tracks changes in camera speed across real frames and uses their actual timestamps. In the 1280×800 Courtyard reversal test at ×3, blocks with large errors fell from 4.46% in Courtyard 3 to 3.44% in Courtyard 4. [Scene and measurements](https://github.com/wavessevaw/GFG-Extreme/tree/95398f2f795bbf08b8e8f1533af2e54d2c415e03/docs/courtyard4)
- **More definition in dark detail.** Kedavra Focus deepens softened stitches, fur and fine dark lettering in SDR. Use **Graphics → Kedavra Focus**, with frame generation on or off. [Images and motion comparisons](https://github.com/wavessevaw/GFG-Extreme/tree/53c40ff8bb422b1671d8dcce1ec0a116beeeb381/docs/focus-dark-detail)
- **Steadier HUD and pacing.** The engine protects stationary HUD strokes on every SDR pair. At 90 Hz the scheduler checks the source cadence before advancing a ready real frame after a hitch. Automatic 30→60 ×2 continues to work at 60 Hz.
- **Colour filters follow your profile.** Vibrance, Levels Plus and other selected colour effects stay active in Quality, Balanced, Battery and Autopilot. The GFG overlay yields to the Steam interface.

Install **GFG-Extreme-v3_6_0.zip** in Decky, reinstall Gamescope in Setup and restart the Deck. To roll back, install the [previous official package](https://github.com/wavessevaw/GFG-Extreme/releases/tag/v3.5.0), reinstall its Gamescope and restart.

The comparisons use software Vulkan. Focus can accentuate existing interpolation errors. Steam Deck GPU time, latency and game-specific results for this build remain unmeasured.
