# GFG Extreme 4.0.0-gfg.3.1

Small correctness release on top of gfg.3.

## Fixed

- OptiScaler `WINEDLLOVERRIDES` conflict detection is now case-insensitive for DLL names. `DXGI=b`, `DxGi=b`, and `dxgi=b` are treated as the same proxy, while the original user override string is preserved byte-for-byte.
- Name-only OptiScaler discovery no longer reports `Ready`. When a supported proxy-named DLL is found without `OptiScaler.ini`, runtime status is `unverified`, because the DLL could belong to ReShade or another proxy-based tool.
- The Decky UI now describes all discovery locations used by gfg.3: beside the launched game executable, under `STEAM_COMPAT_INSTALL_PATH`, and the working directory.
- Documentation version references updated to gfg.3.1.

## Unchanged

Renderer, Flatpak payloads, backend ownership, Automatic Dock hardening, Gamescope/Wayland code, and configuration locking are unchanged.
