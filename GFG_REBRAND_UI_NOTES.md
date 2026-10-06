# GFG Extreme 4.0.0-gfg.1 — rebrand and Decky UI

## Product identity

- Product name: **GFG Extreme**.
- Decky header: **GFG // EXTREME** with a bolt mark.
- Release theme: **Redline**.
- Legacy MAKO artwork, shark branding, UI class names, local UI state keys, and old accent colors are not used by the Decky interface.
- Upstream `mako-*` paths, environment variables, Vulkan identifiers, RPC method names, renderer archive names, and Flatpak IDs are intentionally retained where they are compatibility contracts with the bundled renderer.

## Main control surface

The previous collection of independent switches is reduced to mode selectors:

- **Frame Generation Mode:** Off / Fixed multiplier / Adaptive Smooth / Adaptive Fractional.
- **Display Policy:** Standard / Automatic Dock · 60 FPS.
- **Scaling Mode:** Off / GFG Scaler / LS1 Quality / LS1 Performance.
- **Output Policy:** Standard upscale / Quality supersampling.
- **Shader Pipeline:** Off / Enabled.

Fine controls are moved into collapsed **Engine Tuning**, **Advanced Rendering**, **Compatibility**, **External Tools**, and **Manual Overrides** sections. This keeps the default screen focused on intent instead of implementation flags.

## Redline palette

The Decky interface uses only black/dark-neutral surfaces, red accents, and neutral white/gray text. The canonical accents are `#ff513d`, `#ff745f`, and `#ffc5bc`. Legacy cyan, teal, blue, green, and amber accents have been removed from the compiled UI bundle.
