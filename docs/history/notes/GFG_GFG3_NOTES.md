# GFG Extreme 4.0.0-gfg.3

Bug-fix release for the OptiScaler Frame Generation backend. No schema, UI, Renderer, or Flatpak payload changes.

## Why OptiScaler generation did not work in gfg.2

1. **Proxy discovery only looked in the launch working directory.** Steam starts the wrapper in the game's install root, while OptiScaler's proxy DLL sits beside the game executable (for example `Binaries/Win64`). Auto Detect therefore reported `proxy-not-found`, no Wine override was exported, Wine kept loading its built-in `dxgi`, and OptiScaler never ran. Because the backend had already disabled GFG Engine Frame Generation, the result was no Frame Generation at all. An explicitly selected proxy had the same flaw: it was applied only when the file existed in the working directory.
2. **File names were matched case-sensitively** (`DXGI.dll` or `Dxgi.DLL` was invisible on Linux).
3. **The readiness status was never written.** The service generated the wrapper through a path that did not pass the runtime-state directory, so the status writer was not emitted and the UI stayed at `Not evaluated yet` forever, hiding failure 1.

## What changed

- Discovery searches, in order: a folder holding `OptiScaler.ini` next to a proxy DLL (candidate folders are those of `*.exe` launch arguments, then the working directory); a bounded (depth 6, 3 s) search for `OptiScaler.ini` under `STEAM_COMPAT_INSTALL_PATH`; finally the first proxy name present in a candidate folder.
- Names match case-insensitively. Paths with spaces and glob characters are handled; launch arguments are untouched.
- An explicitly chosen proxy is always applied (native-then-builtin is harmless when the DLL is absent) and reported `proxy-not-found` if it could not be verified.
- An existing same-proxy `WINEDLLOVERRIDES` entry still wins and is reported as `external-override`.
- The status file now also records the folder and the discovery method; `get_fg_backend_status` returns them as `optiscaler_dir` and `optiscaler_detection`, and `gfg-diagnostics` prints them.
- 14 regression tests added (`tests/test_optiscaler_discovery.py`). Against gfg.2 code 11 of them fail.

## Still your responsibility / not verified

- OptiScaler itself must be installed and configured (Frame Generation enabled in `OptiScaler.ini`, a supported DX12 game, matching GPU generation). This plugin only routes the Wine override.
- The wrapper was verified with synthetic game folders and the Proton-style command line; it was not run against a live Steam/Proton session or a real OptiScaler build.
- Auto Detect treats a missing `OptiScaler.ini` as a weaker signal: it then falls back to the first proxy-named DLL it finds, which can be a game's own DLL. Select the proxy explicitly in that case.
