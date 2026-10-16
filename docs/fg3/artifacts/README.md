# internal.6 experimental packages

Source: f7d007998f137697d1a186af1afc79c3255a6ef8, PR #133.

- `GFG-Extreme-GSF-0.0.0-fg3-internal.6.zip`: integrated Decky GFG with an opt-in
  native component. Settings → Diagnostics → GFG Native Generator → ×2/×3.
  The selection installs the checksum-verified bundled component; restart game.
- `GFG-Native-FG-v0_0_0-fg3-internal_6.zip`: standalone component, corresponding
  engine source, installer/rollback and diagnostic capture. No Decky required.

Verify SHA256SUMS.txt before installation. The included README.ru.md explains
configuration and limits. Both artifacts were installed/tested in isolated cloud
homes. The component ELF rebuilds byte-identically from its included source.
Its ABI was loaded with glibc2.31; its WSI path passed software validation.

**Steam Deck / Gamescope / physical90FPS: NOT TESTED. Not a stable release.**
The current cloud has no DRM device or connected Deck. These packages preserve
and transfer the implementation for the hardware stage; they do not close #132.
