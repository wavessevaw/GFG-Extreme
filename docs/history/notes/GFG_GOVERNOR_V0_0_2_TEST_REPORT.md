# GFG Governor v0.0.2 Test Report

Date: 2026-10-06. Environment: Linux container, Python 3.13, Node 22, Chromium (Playwright). **No Steam Deck hardware.**

## Backend (python3 -m unittest discover -s tests)
Result: **207/207 PASS** (Beta.2 baseline: 97). No test removed.

| Module | Tests |
|---|---|
| test_governor_runtime | 44 |
| test_fg_backend | 42 |
| test_governor_overlay | 16 |
| test_optiscaler_discovery | 16 |
| test_governor_core | 12 |
| test_governor_effort | 9 |
| test_governor_telemetry | 8 |
| test_governor_wrapper_overlay | 8 |
| test_governor_hud | 7 |
| test_governor_service | 6 |
| test_pipeline_inspector | 6 |
| test_governor_battery | 5 |
| test_launcher_rename | 5 |
| test_generated_config_check | 4 |
| test_governor_device | 4 |
| test_config_journal | 3 |
| test_gfg32_regressions | 3 |
| test_governor_power | 3 |
| test_governor_replay | 3 |
| test_governor_wrapper_diagnostics | 2 |
| test_config_descriptions | 1 |

Notable coverage: overlay atomicity and lease; wrapper selection run through real bash (overlay lease alive/dead/released, HUD active.conf, format 77); confirmation/rollback/release state machine; trial ladder bounds; device policy; fractional multipliers x1.25..x2.75 (overlay, planner grid, confirmation on the real ratio, neighbouring fraction and integer cadence do not confirm it, cost monotonic, scaled x2 rungs before x2.75/x3); effort hysteresis (flapping input never publishes); battery estimator; HUD status line/config; generated-config drift detection (positive and negative); idle loop wake-up; launcher rename and alias; Saved config hash checked unchanged in every runtime test.

## Generated config check
`python3 scripts/check_generated_config.py` -> generated config OK (43 fields).

## Frontend
`node frontend/harness/smoke.mjs` -> **13 screens OK** (Home states idle/measuring/locked OLED/locked LCD/relaunch Dock, Governor, Frame Generation, Scaling, In-game overlay, Profile, System, All settings, Journal), no page errors. Build: `node frontend/build.mjs` -> `dist/index.js`.

## Binary integrity
Renderer archive, three Flatpak extensions, installer helper and diagnostics helper are byte-identical to Beta.2; SHA-256 values match `bin/SHA256SUMS.txt`.

## Not tested
Anything requiring a Steam Deck: real renderer cadence, sysfs TDP/battery, MangoHud rendering, Flatpak sandbox access, controller navigation. See docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md.
