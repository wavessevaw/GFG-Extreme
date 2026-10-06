# GFG Extreme


## GFG Governor v0.0.1 Beta.1

This build adds the first GFG Governor runtime: a centralized incremental telemetry observer, deterministic 90 FPS OLED / 60 FPS Dock planner, offline replay framework, and an ownership-aware Steam Deck TDP optimizer. Governor is disabled per profile by default. Beta.1 never rewrites saved multiplier or render scale automatically; it optimizes TDP only after live telemetry proves the currently running point. The Decky home surface is also reorganized around Governor, with the previous detailed controls behind **Advanced Controls**.

> **Compatibility note:** GFG Extreme keeps upstream `mako-*` filenames, Vulkan layer identifiers, configuration paths, and RPC names where changing them would break renderer compatibility. Those are implementation identifiers, not the product name. Upstream MAKO attribution remains in licensing and provenance files.


<!-- prettier-ignore -->
> [!NOTE]
> **GFG Extreme succeeds <a href="https://github.com/eugeniosegala/decky-lsfg-vk-experimental" target="_blank" rel="noopener noreferrer">Decky LSFG-VK Experimental</a> under a separate product and package identity.** The <a href="https://github.com/eugeniosegala/MAKO" target="_blank" rel="noopener noreferrer">MAKO repository</a> continues its development lineage, but GFG Extreme imports state only from public MAKO 2.0.0 or newer; install it separately from the differently named predecessor.

GFG Extreme is a Decky Loader interface built on the MAKO renderer lineage. It provides per-game controls, installation, updates, Flatpak preparation, and game launch integration for GFG Engine on Steam Deck, Steam Machine, SteamOS, and Linux more broadly.

The bundled engine is derived from the MAKO community project bringing LSFG frame generation, spatial scaling, and bundled shader effects to Linux. GFG Extreme does not contain or distribute Lossless Scaling, `Lossless.dll`, or extracted proprietary model payloads. LSFG and LS1 read selected resources at runtime from a lawful, user-supplied <a href="https://store.steampowered.com/app/993090/Lossless_Scaling/" target="_blank" rel="noopener noreferrer">Lossless Scaling</a> installation; the open GFG Scaler and bundled shaders do not require it. GFG Extreme does not alter the user's DLL file, and translated resources remain process-local. Users are responsible for complying with the terms applicable to their copy. See <a href="../THIRD_PARTY_NOTICES.md" target="_blank" rel="noopener noreferrer">Third-party notices</a>.

## Download

For frame generation or LS1 scaling, first install the **default public version** of <a href="https://store.steampowered.com/app/993090/Lossless_Scaling/" target="_blank" rel="noopener noreferrer">Lossless Scaling</a> through Steam. The upstream-compatible engine can use beta branches, but they are not validated; the default public branch is recommended. The open GFG Scaler works without `Lossless.dll`.

This archive is the GFG Extreme plugin package. The upstream MAKO repository remains the renderer lineage and licensing reference; GFG Extreme release packaging should use its own release location.

The bundled engine payload keeps the upstream MAKO v4.0.0 file identity for binary compatibility. Do not rename the renderer archive or Vulkan layer identifiers inside the package.

Published GFG Engine packages target x86_64 Linux hosts, with 64-bit and 32-bit x86 game-process layers. GFG Extreme safely refuses incompatible native AArch64/Armada installation; see <a href="docs/ARMADA.md" target="_blank" rel="noopener noreferrer">Armada and native AArch64 support</a> for that boundary.

## What it manages

- Installs and updates the per-user GFG Engine Vulkan layer and common `mako-run` wrapper.
- Saves per-game and per-process profiles, then selects them automatically by Steam application ID or process name.
- Orchestrates Frame Generation per profile through **GFG Engine**, **OptiScaler**, **Game Native**, or **Off** while keeping Spatial Scaling and Shaders independent. Switching ownership preserves the saved GFG Engine settings instead of rewriting them. **Live Status** reports the active mode, scaler, resolutions, limits, fallbacks, and pending changes for the running game.
- Adds a **Pipeline Inspector** that compares Saved, Effective, and Actual launch state using an atomic launch manifest plus live `/proc/<pid>/maps` verification, including PID-reuse protection and observed double-FG warnings.
- Keeps a bounded **Configuration Journal** with actor/reason/diff history and schema-safe restore of the previous change.
- Provides a per-profile Gamescope WSI compatibility option, host-installed MangoHud, and MAKO's private pinned 64-bit/32-bit vkBasalt build, including live per-game sharpening, anti-aliasing, and lightweight shader presets. Scaling uses the combined Renderer by default; the independent WSI option selects the managed compatibility path inside a supported Gamescope session.
- Prepares matching Vulkan runtime extensions and application access for supported Flatpak workflows.
- Shares one active native Renderer version with the standalone archive installer. Installing either version selects it for both launch workflows; a later GFG Extreme installation adopts a valid standalone Renderer and offers its bundled update when the versions differ.
- Removes files supplied by either managed native Renderer installer when you select **Uninstall GFG Engine**, while preserving GFG Extreme and its profiles. Uninstalling GFG Extreme also removes the managed native Renderer; shared Flatpak runtime extensions remain installed.

Close games using GFG Extreme before installing or updating GFG Engine. Installation preserves valid profiles. If the saved configuration cannot be read or validated, installation resets it and its profiles to defaults. Read-only configurations stop installation. If installation fails, GFG Extreme attempts to restore the previous installation and configuration and reports any recovery problems.

## Install and use

Follow the [installation guide](../README.md#install-and-use) to install Decky Loader and the GFG Extreme ZIP. Then open GFG Extreme and select **Install GFG Engine**; installing the ZIP alone does not install its bundled Renderer. For a native Steam or Proton game, add this under **Steam Properties > Launch Options**:

```text
/home/deck/.local/bin/mako-run %command%
```

Start the game normally. GFG Extreme automatically selects a matching saved profile, or uses the Default profile when no match exists.

For Heroic, Lutris, EmuDeck, and other Flatpak applications, follow the [launcher setup guide](docs/LAUNCHERS.md).

When updating, follow the [update guide](../README.md#updating-gfg-extreme) to replace GFG Extreme, its bundled Renderer, and any prepared Flatpak extensions.

## Panel display

Press **R1** or select **Hide info** to hide explanations and optional information while keeping settings and actions available. The Lossless Scaling and GFG Engine installation status card stays visible, as does **Live Status** while a game runs, along with any Lossless Scaling model warning and its update action. The version number and release codename also stay visible. Press **R1** again or select **Show info** to restore the information. GFG Extreme remembers your display preference without changing game profiles or which settings sections you have collapsed.

See the [configuration guide](docs/CONFIGURATION.md) for settings and profiles, [troubleshooting](docs/TROUBLESHOOTING.md) for common problems, and [Collect GFG Extreme Diagnostics](docs/COLLECT_DIAGNOSTICS.md) to create a report when you need help.

## Development

To build GFG Extreme from source or create a local test ZIP, follow the [packaging guide](docs/PACKAGING.md). Contributors should also follow the [testing guide](../TESTING.md).

The [frontend code map](docs/FRONTEND-ARCHITECTURE.md) identifies the owners of profile state, configuration writes, settings views, and the shader effect selector. The [backend code map](docs/BACKEND-ARCHITECTURE.md) identifies the RPC, profile, wrapper, installation, Flatpak, and runtime-status boundaries.
