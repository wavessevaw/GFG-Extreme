# GFG Extreme 4.0.0-gfg.2

## Upgrade from gfg.1

Existing profiles remain valid. A missing `fg_backend` becomes `gfg`; the experimental legacy value `lsfg` is normalized to `gfg`. Existing Frame Generation, Automatic Dock, Scaling, and Shader values are not rewritten when another Frame Generation backend is selected.

The public Frame Generation backends are:

- `gfg` — GFG Engine owns Frame Generation.
- `optiscaler` — GFG Engine Frame Generation is disabled at launch and a user-supplied OptiScaler proxy DLL can be selected or auto-detected.
- `native` — the game owns Frame Generation; GFG Extreme performs no external FG injection.
- `off` — GFG Extreme runs no Frame Generation path.

Scaling and Shaders remain independent in every backend. Automatic Dock is effective only for the `gfg` backend, while its saved profile value is preserved for later reuse.

## OptiScaler

GFG Extreme does not download, install, copy, patch, or inject OptiScaler outside Wine's normal DLL override mechanism. Auto Detect checks, in order: `dxgi.dll`, `winmm.dll`, `d3d12.dll`, `version.dll`, `wininet.dll`, `winhttp.dll`, and `dbghelp.dll` in the game's working directory. Existing same-proxy `WINEDLLOVERRIDES` entries are preserved and reported as externally controlled.

Reference used for the supported proxy names: OptiScaler official Manual Installation wiki, https://github.com/optiscaler/OptiScaler/wiki/Manual-Installation

## Known limitations

- OptiScaler readiness is based on the most recent wrapper launch probe. Before the first launch, the UI reports `Not evaluated yet`.
- Auto Detect relies on the launch working directory containing the game's proxy DLL. An unusual launcher that changes the working directory may require selecting a proxy explicitly or setting its Wine override externally.
- `Game Native` does not detect or configure DLSS/FSR/XeSS Frame Generation inside the game.
- Automatic Dock still uses the hardening.2 polling/snapshot model; DRM event monitoring and a runtime Dock overlay are intentionally deferred.
- The bundled Renderer and Flatpak payloads are unchanged. The pre-existing remote-binary publication metadata mismatch remains a packaging concern: the custom bundled host Renderer hash does not match the upstream GitHub `render-v4.0.0` host archive currently referenced by `remote_binary.url`.
