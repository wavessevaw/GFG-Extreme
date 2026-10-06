# GFG Extreme + Governor v0.0.1 Beta.1 Test Report

Baseline: exact `GFG-Extreme-v4.0.0-gfg.4.zip` release tree.

## Automated validation

- Python unit/regression/replay/service tests: **93/93 PASS**.
- Python syntax: `python3 -m compileall -q .` PASS.
- Decky compiled UI syntax: `node --check dist/index.js` PASS.
- Frontend/backend RPC parity: **37 frontend RPC methods, 0 missing backend methods**.
- Governor RPCs: `get_governor_status`, `set_governor_enabled`.
- Existing gfg.4 regressions remain in the test run, including Wayland/Xwayland hardening, configuration locking, backend ownership, OptiScaler, Inspector, Journal and gfg.3.2 fixes.

## New Governor coverage

- Native90 / 45x2 / 30x3 planner choices.
- Dock 30x2 target policy.
- x4/x5 excluded from automatic candidates.
- Coarse-to-fine PowerSearch and restore-to-last-good behavior.
- User/session TDP ceiling never exceeded.
- fastPPT/slowPPT discovery, proportional writes, clean restore.
- External TDP change releases ownership and is not overwritten.
- Incremental telemetry parsing and measured-output priority.
- Scheduler interval cadence derivation.
- pressure/miss/bypass accounting.
- first attach skips historical diagnostics backlog.
- cached samples do not count as new fresh evidence.
- service disabled-by-default behavior.
- external FG backend remains observe-only.
- enabled proven 45x2 begins power optimization without profile mutation.
- Dock runtime target is 60.
- offline replay: Native90, 45x2 and Dock30x2.

## Binary identity

- `bin/MAKO-Renderer-v4.0.0-linux.tar.xz`  
  `72ae1202f2a649f65cb75a7d1082f7aeacb7e87c8a2d6f29888343d5271c2b7c`
- `bin/org.freedesktop.Platform.VulkanLayer.makorender-23.08.flatpak`  
  `d74a2e53ff8f80a7f662a9ef1052557cba5fbf1a63a2fef700de75aa83c11cf5`
- `bin/org.freedesktop.Platform.VulkanLayer.makorender-24.08.flatpak`  
  `ae2c78242e6edd0f8c148243c4559aef78f3748f0bd50702c5257c9138f64cee`
- `bin/org.freedesktop.Platform.VulkanLayer.makorender-25.08.flatpak`  
  `05f30339935979e94be0d346908e7d0d4b47927a4613ef67758152250705adc0`
- `py_modules/gfg_plugin/gamescope_display.py`  
  `1238a3bc30c6f96ee61b9e6ae3572d88372c733d9d74bccb70e8481bb4370be6`

All five match gfg.4.

## Release-source limitation inherited from gfg.4

The gfg.4 release ZIP contains a `package.json` that references `scripts/check_generated_config.py`, but that script directory is not present in the release tree. Therefore that specific source-generation check cannot be run from this release artifact. This Beta does not remove or modify generated configuration files; existing unit/regression tests and Python compilation pass.

## Live integration

**NOT RUN:** real Steam Deck OLED Game Mode / Gamescope / writable amdgpu PPT / actual games. Hardware validation is required before considering TDP automation production-ready.
