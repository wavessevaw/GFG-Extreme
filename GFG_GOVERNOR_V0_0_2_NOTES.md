# GFG Governor v0.0.2 - Functional and architectural release

Branch: `main`. Baseline: Governor v0.0.1 Beta.2 (97 tests). This release: 207 tests, none removed.
Renderer, Flatpak extensions, helper binaries: byte-identical to Beta.2 (see `bin/SHA256SUMS.txt`).

## What changed

### Governor engine
- **Runtime overlay.** Operating points are applied through a temporary per-profile overlay config selected by the launch wrapper only while the plugin's owner-PID lease is alive. The Saved profile is never written by the Governor. Overlay writes are atomic (tmp + fsync + replace + read-back verify). `owner=0` means released.
- **Confirmed actuation.** Each request is confirmed on fresh renderer samples (own request correlation, event/sample sequence bridge). `runtime-transition-failed` rolls back at once; confirm/trial timeouts are bounded.
- **Bounded trial ladder.** Highest quality first, native, then fractional x1.25 .. x2.75 in 0.25 steps (target 90 -> real 72, 60, 51, 45, 40, 36, 33; target 60 -> 48, 40, 34, 30, 27, 24, 22), then x2 with render scale 90/80 before x2.75 and x3, at most 12 attempts, rejected points never retried in a session. Scaled points are skipped (not rejected) when the engine was not provisioned at launch.
- **Release invariant.** Overlay is restored to Saved (verified) before power ownership is released; on failure ownership is kept and restoration retried.
- **Telemetry fix.** Real FPS is derived from `fixed-plan` (`real = output / (generated_per_real + 1)`); replay corpus rewritten to the real diagnostic shape.
- **Device-aware targets.** DMI `Galileo` = OLED 90, `Jupiter` = LCD 60, docked/external = 60, unknown = internal panel maximum.
- **Capability gate.** `relaunch-required-for-governor-overlay` when the game was not launched with an overlay.
- **GFG Effort.** Easy / Medium / Hard / Nightmare, hysteretic, withheld until stable (45 s initial dwell; up 20 s, down 60 s one step at a time; min 30 s between changes; unreachable target reported at once).
- **Fractional multipliers (x1.25 .. x2.75, 0.25 steps; x1.7 maps to the nearest, x1.75).** Expressed as a pinned adaptive-mode overlay (adaptive on, target and real-frame cap fixed, auto-cap and stable-cadence off, max multiplier 2) and confirmed on the real ratio from `adaptive-plan` interval telemetry (tolerance 0.12 for fractions, 0.22 for integers, so neighbouring rungs are not confused). Anything above x3 is never produced. Cost model: penalty is piecewise linear in the multiplier, so the planner spends render scale and TDP headroom before generation depth.
- **Idle loop.** With nothing enabled the loop sleeps 5 s and wakes instantly on enable/HUD changes.

### In-game overlay
- Compact MangoHud bar (top right by default): FPS, frame time, multiplier, real>output, render scale, TDP (read from sysfs even when not Governor-owned), battery time-to-empty (smoothed), effort. No CPU load. Presets Minimal / Standard / Detailed.
- Active only when no other external Vulkan layer is selected; published/removed via `<config_dir>/hud/active.conf`.

### Launcher and wrapper
- Launch command is now `gfg` (`/home/deck/.local/bin/gfg %command%`); `mako-run` remains a managed alias.
- Wrapper format 77; launch manifest records `governor_launch`.

### Interface (rebuilt from scratch)
- Home: target ring, state in plain language, Real -> GFG -> Output, TDP and time left, GFG Effort, one **RUN/STOP** button (or **INSTALL ENGINE** when missing).
- Sub-pages: Governor, Frame Generation, Scaling (scale-ready launch), In-game overlay, Profile (create/duplicate/rename/delete), Advanced (Inspector, Journal, All settings, System with engine and Flatpak management).
- **All settings** is a schema-driven editor so no profile option is lost; values validated server-side. `get_config_schema` now also returns field descriptions.
- Palette: near-black, graphite, white/grey text, single red taken from the logo (#FB0D00). New wolf logo.
- Source in `frontend/` (no runtime npm deps); `dist/index.js` built by `npm run build`.

### Packaging and project
- Restored a real `scripts/check_generated_config.py` (checks `config_schema_generated.py` against `shared_config.py`; covered by tests). Removed `package.json` scripts that pointed at files not in the tree; added `build`, `test`, `test:backend`, `test:frontend`, `screenshots`.
- README rewritten as the GitHub landing page.
- GitHub milestone and issues #2-#10 created for the v0.0.2 - v0.0.10 cycle.

## Not done / needs hardware (see docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md)
Nothing in this release was run on a Steam Deck. Hardware validation is scheduled for v0.0.10.

## Package contents
- `GFG-Extreme-Governor-v0_0_2.zip` - full plugin tree (includes the unchanged binaries and Flatpak extensions).
- `GFG-Extreme-Governor-v0_0_2-from-Beta_2.patch` - unified diff of text files against Beta.2 (`patch -p1`). Binary assets (logo and documentation PNGs) are only in the zip.
- Notes, test report, known limitations and `SHA256SUMS.txt`.
