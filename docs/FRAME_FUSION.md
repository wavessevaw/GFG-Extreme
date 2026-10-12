# Frame Fusion Core

Frame Fusion is an experimental native renderer path that shares existing frame images with the open MAKO spatial scaler. It removes one source-sized blit from an eligible reconstruction; the output copy and the original renderer scheduling remain owned by their existing components. This is the first stage of Frame Fusion, not shared LSFG motion analysis or a replacement frame generator.

## Use

Install the experimental GFG build and its updated engine, then enable **Settings → Diagnostics → Frame Fusion** and restart the game. The feature defaults off. Turning it off also applies at the next game launch.

Supported: native Linux x86_64, the open MAKO scaler, validated SDR8 input, and an actual source/presentation split. The normal modes and Autopilot keep their existing goals. Unsupported formats, missing sample access, unregistered images and failed binding setup retain the copy-based path. The initial patch does not add Fusion to Flatpak bundles, 32-bit libraries, LS1 or HDR; it does not force a game to honor a render-scale request.

The status distinguishes requested settings, prepared descriptors and a successfully submitted direct path. An observed path proves that different processing was submitted; it does not prove lower whole-device power, additional real FPS or improved input latency. The copy counter is a snapshot at native publication, not a continuously sampled total.

## Native implementation

At Deck/1080p-class extents, MAKO ordinarily reconstructs the real frame before FG. Fusion negotiates sampled-image usage only at swapchain creation when the actual surface and linear UNORM format support it. A bounded borrowed view samples the logical source rectangle directly from the larger application image. The sampler clamps that rectangle before mapping into physical texture coordinates, preventing neighboring pixels from entering reconstruction. The original image ownership, FG output, return copy, layer order and frame fences remain in place. Nonlinear sRGB and HDR views cannot use this shortcut.

Above the existing pre-FG pixel budget, the original graph generates at source resolution and reconstructs each generated frame. Fusion prebinds matching private FG outputs and samples them directly. No WSI storage usage or effect ordering is changed.

Binding replacement is transactional, capacity is bounded, recording allocates nothing, and source-read layouts are restored. Scaler/backend replacement and retirement drain the existing owners and clear borrowed bindings. The legacy private images remain available for fallback: removing one transfer is not a claim that all intermediate allocations were removed.

## Build and validation

`engine/gfg-fusion/source.json` pins upstream MAKO Renderer v4.0.0 and the reviewed patch checksum. `scripts/build_frame_fusion.py` verifies that identity, regenerates shader payloads with the owning upstream generator, builds the actual production code, runs full CTest and compares the paths on a Vulkan device. The patch does not contain licensed model payloads.

The native harness checks copy commands, alternating private sources, format/extent/usage rejection, descriptor rollback, clearing, unknown sources, RGBA/BGRA cropped inputs, application-image lifetime and FG handoff. Private generated-image comparisons require byte identity; cropped application sampling permits at most one 8-bit code value of difference from normalized-coordinate rounding. The CI device is Lavapipe and validation checks synchronization. Its graph timing is not Steam Deck performance or energy evidence.

The release builder replaces only verified native x86_64 renderer/CLI payloads in a checksum-verified archive, preserves the original 32-bit and Flatpak paths, records source and payload identities, and validates the final Decky ZIP. The package uses the existing local `bundled_renderer` contract; Decky does not fetch a modified payload from an upstream URL.

Steam Deck LCD/OLED, RADV, real LSFG execution, Gamescope WSI presentation, long sessions, suspend/resume and whole-device energy require subsequent device evidence. Fusion should remain experimental until that evidence exists. In particular, a smaller copy count does not by itself establish an overall speedup: negotiated usage and direct reads can change driver costs.

## Further Frame Fusion

Combining compatible post-processing passes is a separate measured candidate. Shared temporal history and motion data require an explicit open executor contract. The current LSFG interface does not export those maps; the first-stage patch makes no such claim.
