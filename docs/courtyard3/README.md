# Courtyard 3 candidate

GFG 3.5.0 with Kedavra a253ec0. Colour and style effects now follow the saved profile in Quality, Balanced, Battery and Autopilot. Under sustained GPU pressure, the existing budget can reduce AA and optional sharpening. This may cost GPU time in heavy games with effects enabled. HDR grades retain their existing restrictions.

The engine checks motion against stationary two-colour features on every SDR pair, including one-pixel outlines. The GFG overlay yields when the Steam UI is the base layer. A new HUD texture is submitted for upload when required, including with generation off. The installed package includes the plugin, runtime, benchmark, recovery code and licenses. Historical research scripts and build files stay in the source repository.

## Verification

The JSON files use identical unscaled 1280×800 inputs on lavapipe. The HUD logs report mean and worst per-frame RGB absolute error on all opaque crosshair pixels across seven source pairs, separately for each generated phase. For reproduction, build Kedavra at a253ec0, set KFG_HARD_X2=1 and KFG_DETAIL_SEQUENCE_OUT to an existing directory, and run kfg_vktest with --hard --size 1280x800 --scene h_courtyard (then h_courtyard_reversal). Pass the frame directory and scene name to kedavra/tools/check_hud_sequence.py. Use the same harness and SPIR-V from Courtyard 2 for the baseline. Translucent HUDs over moving content and input latency still need device testing.

Install the inner ZIP using Decky, reinstall Gamescope from GFG Setup and restart the Deck. Verify a stationary sight during a camera turn in each display mode. Open and close the Steam menu with the plugin HUD visible. In SDR, select Vibrance and Levels Plus, switch between performance modes and check the same scene under GPU load. Compare frame pacing with the same profile and power limit. To roll back, install the GFG 3.5.0 ZIP and reinstall its Gamescope from Setup, then restart.
