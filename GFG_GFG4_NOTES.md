# GFG Extreme 4.0.0-gfg.4

## What changed

- Added Pipeline Inspector with **Saved / Effective / Actual** state.
- Added atomic per-profile launch manifests written immediately before wrapper `exec`.
- Launch manifests record PID plus `/proc/<pid>/stat` start time so stale PID reuse is rejected.
- Runtime inspection follows descendants and matching Steam AppID processes, then reads `/proc/<pid>/maps` for `libmako-render.so`, vkBasalt, and supported OptiScaler proxy DLLs.
- Added observed double-FG warning. A proxy file merely existing on disk is not enough; it must actually be mapped in a running candidate process.
- Added explicit mismatch reasons such as external backend suppression, missing expected renderer, missing OptiScaler mapping, stale launch PID, and unavailable `/proc` access.
- Added bounded Configuration Journal with actor, reason, timestamp, changed fields, and before/after values.
- Added schema-safe “Restore previous change”. Recovery operations are also recorded.

## Baseline provenance

The exact gfg.3.2 ZIP was not mounted in this build environment. The gfg.4 working baseline was reconstructed from the available gfg.3.1 archive plus the three gfg.3.2 fixes supplied in the review: grouped Wine override conflict detection, explicit-proxy readiness, and orphaned Dock snapshot recovery. Those fixes have dedicated regression tests in this release. The source patch is therefore generated against that reconstructed gfg.3.2 baseline rather than claiming byte-for-byte provenance from an unavailable archive.

## gfg.3.2 baseline fixes retained

This build includes the three gfg.3.2 corrections supplied for the baseline:

- grouped `WINEDLLOVERRIDES` such as `D3D11,DXGI=b` are detected as conflicts case-insensitively;
- an explicitly selected proxy that is actually present is treated as ready even without `OptiScaler.ini`;
- switching to a profile with external/native/off FG ownership restores an orphaned GFG Dock snapshot instead of leaving it behind.

All hardening.2 unload, Wayland timeout, Xwayland cache, and configuration-locking behavior remains intact.

## Known limitations

- `Game Native` Frame Generation is not introspected inside the game. Inspector can prove GFG/OptiScaler mappings, not the game engine's internal FG state.
- `/proc/<pid>/maps` visibility depends on Linux ptrace/proc permissions. Permission denial is reported as unavailable inspection, not as a false “not loaded”.
- Proton can create several helper processes. Inspector uses the manifest PID tree and matching Steam AppID processes, but unusual launchers can still require future discovery refinements.
- Frame-pacing telemetry, Benchmark Builder, A/B testing, DRM event monitoring, and runtime Dock overlay are intentionally not part of gfg.4.
- The custom bundled renderer still has the previously documented remote-binary publication mismatch; this release does not change renderer binaries or Flatpak payloads.

## Upgrade

Install gfg.4 over the existing GFG Extreme plugin. Existing profiles remain compatible. The Configuration Journal starts empty and fills only after gfg.4 configuration changes. Pipeline Inspector shows `Not launched yet` until the selected profile has been started through the managed wrapper at least once.
