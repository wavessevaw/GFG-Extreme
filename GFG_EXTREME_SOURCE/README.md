# GFG Extreme source notes

The retired Predictive Frame Generation helper source is intentionally absent from the GFG Extreme release; this behavior was inherited from legacy extreme.5.

Automatic Dock is implemented in the Decky layer:

- `py_modules/gfg_plugin/gamescope_display.py` reads Gamescope active-display information and synchronizes exact supported refresh modes.
- `py_modules/gfg_plugin/plugin.py` owns the Dock state machine, persistent handheld snapshot, 60 FPS target policy, and restoration.
- `shared_config.py` stores the per-profile `automatic_dock_mode` switch as a Decky-only setting, so the upstream renderer never receives an unknown TOML key.

The bundled GFG Engine renderer retains the upstream MAKO 4.0.0 timestamp validation for binary compatibility. No extrapolation patch or additional predictive Vulkan layer is shipped.
