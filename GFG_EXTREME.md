# GFG Extreme 4.0.0-gfg.4 + Governor 0.0.1 Beta.1


## GFG Governor 0.0.1 Beta.1

Adds an opt-in Governor that observes renderer evidence, recommends a bounded 90/60 FPS Operating Point, and performs ownership-safe coarse-to-fine TDP optimization when the live point is already confirmed. Stable points transition to LOCKED instead of being continuously retuned. Saved FG/scale profile fields are not automatically rewritten in this first Beta.


## Pipeline Inspector and Configuration Journal

GFG Extreme gfg.4 adds a read-mostly **Pipeline Inspector** that compares three layers for the selected profile: **Saved** configuration, **Effective** launch configuration, and **Actual** process mappings. The wrapper writes an atomic per-profile launch manifest immediately before `exec`, including the launch PID and `/proc/<pid>/stat` start time. The Inspector rejects PID reuse, follows launch descendants and matching Steam AppID processes, and checks `/proc/<pid>/maps` for the GFG renderer, managed vkBasalt, and supported OptiScaler proxy DLLs.

The Inspector reports why Saved and Effective differ, for example when an external Frame Generation backend suppresses GFG Frame Generation or Automatic Dock. It also warns only on observed double-FG evidence: GFG Frame Generation must be effective **and** an OptiScaler proxy must actually be mapped. Merely finding a DLL in the game directory is not treated as proof that it loaded.

The new **Configuration Journal** records bounded per-profile diffs with the actor (`ui`, `dock`, `backend`, `recovery`), reason, timestamp, and before/after values. A schema-compatible previous change can be restored from Decky; recovery itself is journaled. The journal is capped to avoid unbounded growth.

Runtime inspection is intentionally observational. `/proc/<pid>/maps` can be unavailable under restrictive ptrace policies; that condition is reported rather than misrepresented as “not loaded”. Native in-game FG remains opaque in gfg.4.

## Frame Generation backend ownership

GFG Extreme gfg.4 separates the saved profile from the effective runtime owner of Frame Generation. Each profile can select **GFG Engine**, **OptiScaler**, **Game Native**, or **Off**. Changing ownership does not rewrite the saved GFG multiplier, Adaptive, Target FPS, or Automatic Dock choices. When ownership returns to GFG Engine, those saved settings become effective again.

OptiScaler integration is launcher-only: GFG Extreme never downloads or copies OptiScaler. **Auto Detect** finds the proxy where OptiScaler is actually installed — beside the game executable, located from the launch arguments, `STEAM_COMPAT_INSTALL_PATH`, or the working directory, and anchored on `OptiScaler.ini` — matches names case-insensitively, and merges the Wine override without replacing an existing override for the same DLL. The supported proxy choices are `dxgi`, `winmm`, `d3d12`, `version`, `wininet`, `winhttp`, and `dbghelp`; this list was checked against OptiScaler's official Manual Installation documentation for this release.

For external/native/off ownership, the bundled Renderer v4 receives runtime overrides that disable only its Frame Generation path. Scaling and managed shaders can still require and use the Renderer independently. Automatic Dock remains saved but is effective only while **GFG Engine** owns Frame Generation.

## Automatic Dock / 60 FPS Display Lock

Predictive Frame Generation from extreme.1/extreme.2 remains retired completely.
GFG Extreme now keeps LSFG inside its normal interpolation range.

When **Automatic Dock 60 FPS** is enabled and Gamescope reports an external display:

- target output is 60 FPS, or the highest display rate when the display cannot reach 60;
- on a verified exact-60-Hz output, real game frames are not deliberately capped;
- VRR is disabled for the Dock profile;
- Frame Generation is provisioned/enabled;
- on a confirmed exact-60-Hz output, GFG Engine uses **FixedRefreshBudget** with Fixed 3x only as a hard capacity ceiling;
- FixedRefreshBudget spends generated frames only when a 60-Hz output slot would otherwise be missing;
- e.g. 25 real FPS requires an average 2.4x cadence (25 real + about 35 generated = 60 displayed), while 58 real FPS needs only sparse generated frames;
- if exact 60 Hz cannot be verified, GFG Extreme uses Fractional Adaptive with Target 60 and temporarily caps the real stream at 56 FPS, preventing the upstream-compatible engine's near-target native preference from settling at 57–59 FPS; this fallback exists only because the physical display is not actually running at 60 Hz;
- the original handheld profile is snapshotted to disk and restored on undock, plugin unload, or profile transition.

The renderer payload uses the upstream-compatible interpolation timestamps (`0 < t < 1`). No PFG preload, predictive Vulkan layer, or extrapolation patch is shipped. Legacy PFG files from extreme.1/extreme.2 are deleted during installation.

### Physical floor

Automatic Dock deliberately caps generation at 3x. Therefore a 60 FPS contract is mathematically reachable down to roughly 20 real FPS. Below that, the renderer holds the 3x ceiling and output necessarily falls below 60 rather than escalating to 4x/5x.

## Legacy extreme.4 audit fixes

- Automatic Dock no longer trusts a Wayland modeset request as proof of refresh. It reads `GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK` from Gamescope Xwayland server zero before selecting Fixed refresh-budget mode.
- The monitor no longer reissues the same modeset every 1.5 seconds. Stable fallback/fixed contracts are retained and only revalidated.
- Enabling Automatic Dock synchronously pre-provisions Frame Generation for the next game launch. A game already running when the option is first enabled may still need one restart because engine provisioning is process-start state.
- PFG remains absent and normal interpolation validation remains `0 < t < 1`.
- 25 real FPS reaches 60 at about 2.4x, while 24 FPS reaches it at 2.5x. 3x is reserved for roughly 20 FPS; 4x/5x Dock operation is intentionally disabled.


## Legacy extreme.5 Dock policy carried into GFG Extreme

Automatic Dock now has a hard 3x ceiling. The 60 Hz display budget remains the clock:
- ~30 real FPS -> ~2.0x output ratio
- ~24-25 real FPS -> ~2.4-2.5x output ratio
- ~20 real FPS -> up to 3.0x
- below ~20 real FPS, 60 displayed FPS cannot be guaranteed with the 3x ceiling

3x is a last rung, not the preferred operating point. The scheduler keeps every available real frame and requests only the synthetic frames needed to fill the confirmed 60 Hz budget.
