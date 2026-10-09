# GFG Open: colour-flow interpolation

Independent GPL-3.0-or-later compute shaders. The Vulkan transport is pinned MAKO source; frame synthesis does not extract shaders or weights from Lossless.dll. This is an experimental implementation, not the AMD SDK port. AMD Optical Flow is a reference for hierarchical matching and confidence, not a claimed dependency or validation.

## Pipeline

For each pair of real frames: classify static 8x8 tiles, 4× box-filtered colour pyramids and bidirectional coarse matching at 4-pixel steps, selectively refine ambiguous/high-residual tiles at full resolution, with a bounded wide fine search only when the coarse pair is plausible but local refinement fails, then compose each requested intermediate timestamp. Difficult wide-search candidates are screened with two colour samples before the nine-sample comparison. A confident tile skips expensive refinement. Previously confident motion that matches the current pair also skips the coarse search; history is never accepted without revalidation. Generated images are never used as source history; only real-frame colour and validated motion are retained. Previous flow is only a search candidate and must pass current-pair colour matching again. Initial history is invalid; context recreation resets it. Opposing-vector consistency and warped colour agreement decide whether to blend, use a single visible source, or display the nearest real frame. Original resolution is preserved. Descriptor sets and two source-phase command chains are cached per context; unchanged uniforms are not uploaded every frame.

## Integration

Frame Generation → GFG Open generator. Opt-in per profile, applies on the next game launch. Native x86_64 SDR8 only in this version. The native library, manifest, checksums, GPL notices and exact upstream source archive are included in the release ZIP. Flatpak uses the existing renderer and logs the fallback. Legacy mode remains available. Both backends retain the application's GPU choice, imported-FD ownership, external timeline semaphore ordering, bounded per-context fences and retirement. No BIOS, clock or TDP changes.

## Limits

Search is bounded to ±16 pixels coarse plus ±3 refinement, not arbitrary motion. Colour-only matching cannot recover hidden geometry, game motion vectors, TAA history, transparency or semantic HUD separation. Conservative fallbacks trade local interpolation smoothness for avoiding mismatched contour blending. GPU savings depend on the proportion of easy tiles; a busy scene may spend more on matching. No Deck power/FPS/ghosting improvement is claimed before controlled device tests. This first open backend has fixed motion-quality parameters; the legacy neural model, flow_scale and FP16 controls apply to the legacy backend, not to these independent shaders.

## Verification

`bash engine/gfg-open/build.sh` compiles GLSL, validates SPIR-V and links the real Vulkan layer. `g++ -std=c++20 -O2 engine/gfg-open/tests/gpu.cpp -lvulkan -o gpu-test` executes those same shaders on Vulkan. CI uses Mesa lavapipe. Test scenes include identity, small and large translation, fractional timestamps, occlusion, static overlay strokes, discontinuity, history warm-up and odd dimensions. This establishes functional behaviour, not Deck timing or end-to-end game compatibility.

## Field-regression protection (1.6.7)

Wide search scans a bounded two-pixel lattice and limits expensive full-colour comparisons to 32 plus four nearly exact candidates, followed by a 3×3 polish. Native timestamps measure prepass and each output separately. Three repeated samples above 4 ms after three warm-up samples latch real-frame passthrough for the context; unsupported GPU timing also selects passthrough. The log states this explicitly. Select legacy FG and restart to restore legacy interpolation. This is a safety fallback, not proof of a field-performance fix.
