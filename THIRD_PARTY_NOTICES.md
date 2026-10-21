# GFG Extreme 3.0 third-party notices

This document supplements [LICENSE.md](LICENSE.md). GFG Extreme is distributed under the GNU
General Public License, version 3 or any later version; each third-party copyright, license
and trademark remains with its owner.

## What the 3.0 Decky zip contains

| Component | Where | License |
| --- | --- | --- |
| GFG Extreme plugin (Python backend, UI) | `py_modules/`, `main.py`, `dist/` | GPL-3.0-or-later; historic MAKO-lineage copyrights in the covered files are retained (see LICENSE.md) |
| KEDAVRA runtime: Gamescope with the KEDAVRA patch, gamescopectl, bundled libraries | `runtime/` | Gamescope: BSD-2-Clause (Valve); KEDAVRA (GSF Kedavra, <https://github.com/wavessevaw/GSF_Kedavra>): GPL-3.0-or-later; bundled libraries keep their own licenses. Notices in `runtime/share/licenses/` |
| KEDAVRA post filters (SweetFX, Colourfulness, AMD CAS, NVIDIA DLS, haasn deband, SMAA) | compiled into the runtime | MIT / BSD; full notices in `runtime/share/licenses/KEDAVRA-filters-THIRD_PARTY.md` |
| Decky API shim (@decky/api) | `dist/index.js` | LGPL-2.1, Steam Deck Homebrew; license in `third_party_licenses/` |

React and React DOM are provided by Steam at runtime and are not bundled.

## What 3.0 no longer contains

GFG Extreme 3.0 removed MAKO Renderer, lsfg-vk, vkBasalt and their shaders, the Frame OS and
HUD Vulkan layers, and every Flatpak payload of 2.x. It does not contain, download or use
Lossless Scaling, `Lossless.dll` or any LSFG model or shader. Lossless Scaling and LSFG are
trademarks of their owner and are named here only to say they are not used.

The notices of 2.x (MAKO, lsfg-vk lineage, vkBasalt, SweetFX shaders as shipped by MAKO) are
kept with the 2.x history in `docs/history/` and in LICENSE.md, conservatively.

## Project artwork

The GFG wolf and the project artwork: see [ASSET_PROVENANCE.md](ASSET_PROVENANCE.md).
