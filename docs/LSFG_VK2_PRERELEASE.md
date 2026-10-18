# GFG Extreme 2.1.7-lsfg2.rc1 — LSFG-VK 2.0 backend preview

This is a **pre-release** Decky plugin based on the verified native payload of stable GFG Extreme 2.1.6.
The preview contains GFG's integration only; it does **not** redistribute the
proprietary Lossless Scaling model or third-party LSFG-VK Vulkan library.

## New generator selection
Settings → Frame Generation → Generator Backend → **LSFG-VK 2.0**.
The selected game profile remains owner of its settings. The game must restart
to apply a new Vulkan layer configuration. GFG's power/Governor interface may
observe external FG; it does not autonomously adjust LSFG-VK's multiplier.

## Supported LSFG-VK 2.0 options
- Multiplier ×2, ×3, ×4, ×5
- Motion flow scale: 0.25–1.0
- Performance model
- FP16 permission
- FIFO / presentation override
- Preserve swapchain image minimum
- Optional absolute path to **lsfg-vk.dll**; without one, search installed Steam libraries
- LSFG-VK's documented synchronous/vsync presentation mode

## Required local dependencies
Install an independently obtained compatible LSFG-VK 2.x Vulkan layer and its
licensed **lsfg-vk.dll** in the Steam library. GFG checks both components and
displays missing-resource status instead of silently claiming FG is active.

## Vulkan launch isolation
When this backend is selected for the game, GFG disables its own GPU frame
generation, Temporal Engine, Frame OS pacing and ring HUD, and never enables the
MAKO renderer in parallel. Inherited managed layer names are removed; LSFG-VK
is enabled only when its manifest and model file are present. Existing unrelated
Steam/Gamescope layers remain available. Backend changes apply after relaunch.

The default backend remains **GFG Engine** for all other profiles. No changes
are made to SteamOS's system files, other games, or stable GFG release.

## Evidence and scope
CI verifies source/config schema, backend setting persistence, layer selection
contracts and game-launch environment assembly. No physical Steam Deck OLED
scanout or game compatibility is claimed until separately tested. Native Vulkan
components shipped unchanged from stable 2.1.6, with the latter release ZIP's
published SHA256 checked before repackaging.
