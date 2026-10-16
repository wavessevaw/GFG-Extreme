# 2.1.5-gsf.8 — latest experimental package, hardware NOT TESTED

Source: 43658e884d67326183d3fce749840053a0c1cebe, PR #133.
Use **GFG-Extreme-2.1.5-gsf.8.zip** for Decky or
**GFG-Native-FG-v0_0_0-fg3-internal_8.zip** for the standalone component.
Both retain the launch repairs below and add linear-light GPU HDR10 PQ
reconstruction with retained swapchain color-space metadata. Numerical x2/x3,
1024-level duplicate precision, unchanged legacy shaders, the full GSF pipeline,
actual extracted-package WSI/recovery and exact-source rebuild checks pass.
See ../HDR_PQ_RECONSTRUCTION.md and ../evidence/hdr-pq-internal_8.json.

HDR game quality, physical output and GPU cost on Deck remain NOT TESTED.
The extra linear cache is15.625MiB at1280x800, only for PQ. G1/G2 queue ordering
and the renderer-cut issue are not claimed fixed by this color correction.
No stable release or physical30→90 acceptance is asserted. Verify SHA256SUMS.txt.

---

## Previous launch-recovery package (superseded by internal.8)

# 2.1.5-gsf.7 experimental packages — hardware NOT TESTED

Source: **9ddb5802e3cac33df0f5c50df6b67ff55d2d892a**, PR #133.
Includes upstream main **25ca625** (2.1.5, PR #140/#141 fixes).

- **GFG-Extreme-2.1.5-gsf.7.zip**: integrated Decky package. Its backend verifies
  and installs the native component and executable launcher at plugin startup.
  Initial mode is Off. Settings → Diagnostics → GFG Native Generator shows
  Off / ×2 / ×3, installation errors, build identity and the Steam command
  only after the executable/component are present. Restart the game for mode changes.
- **GFG-Native-FG-v0_0_0-fg3-internal_7.zip**: standalone independent component,
  full corresponding engine source, installer, rollback and optional diagnostics.
  Follow its README.ru.md; the standalone CLI explicitly opts in when no Decky
  mode marker exists. No proprietary DLL, model or other FG backend is needed.

Verify **SHA256SUMS.txt**. Full backend 1409 tests (1 root-only skip), frontend 123
screens, native contracts and 17 GSF pipeline checks passed in cloud. The actual
extracted ZIP passed 13 installation/WSI/recovery checks, including read-only
Vulkan features and Proton present metadata. The ELF rebuilds byte-identically
from its included source and loads with actual glibc2.31. Evidence:
../evidence/launch-recovery-2_1_5-gsf_7.json and the matching evidence ZIP.

**Steam Deck / Gamescope / physical 30→90FPS: NOT TESTED. Not a stable release.**
The cloud has no DRM device or authenticated Deck endpoint. The owner's all-game
exit cause remains unconfirmed on-device; the discovered launch defects have
independent reproductions and fixes. See ../LAUNCH_RECOVERY_2_1_5_GSF_7.md.

**internal.6 is WITHDRAWN.** Its old archives remain only as reproducible history.
They used the stale 2.1.2-te.8 plugin base and had launcher-installation/off/recovery
defects. If a Steam prefix itself fails, remove the entire GFG prefix from launch
options (empty field or `%command%`); `--off` requires a working executable first.
