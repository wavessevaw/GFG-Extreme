# GFG Extreme asset provenance

This release intentionally ships **no legacy MAKO logo, shark mascot, banner, or release artwork** in the Decky package. GFG Extreme uses a code-rendered Redline interface instead of image branding.

## Decky interface

| Material | Origin | Treatment |
| --- | --- | --- |
| GFG Extreme header mark | Material Design bolt icon exposed through `react-icons` | Rendered as an interface glyph; licensing for `react-icons` is included in `third_party_licenses/react-icons-LICENSE.txt` and `THIRD_PARTY_NOTICES.md`. |
| Redline palette | GFG Extreme UI design | Code-defined palette based on black/dark-neutral surfaces, `#ff513d` primary red, `#ff745f` hot red, `#ffc5bc` pale red, and neutral white/gray text. No previous cyan/teal/blue/green accent palette is intentionally retained. |

## Upstream renderer assets

The bundled renderer archive and Flatpak runtime extensions retain their upstream file names and internal resources for binary compatibility. Their third-party and upstream notices remain governed by `LICENSE.md` and `THIRD_PARTY_NOTICES.md`. Those implementation resources are not used as GFG Extreme Decky branding.

## Maintainer rule

Any future visual asset added to GFG Extreme must record its creator/source, modifications, and distribution terms here before release.
