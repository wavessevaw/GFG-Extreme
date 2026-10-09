# GFG Extreme 1.6.6 — Open frame generation and Energy

This release introduces **GFG Open**, an independent frame generator with open compute shaders. Frame generation does not require Lossless.dll. The Vulkan transport uses pinned MAKO source; the frame synthesis algorithm is implemented separately.

- Static regions and confidently matched motion use a low-cost path.
- Difficult regions receive selective refinement, with motion checked in both directions.
- Occlusions and inconsistent contours use a single reliable source or the nearest real frame instead of blending mismatched trails.
- Motion history is revalidated against the current frame pair and reset when a new context is created. The game's source resolution is preserved.
- **Energy:** only the number changes. A 12 W cap out of a 15 W maximum displays **20%**. The arc, colour, opacity and position remain unchanged. This represents TDP-cap savings, not measured battery-energy savings.
- Frame timing and Stall shield controls from the 1.6.6 development branch are included. They operate through Frame OS Act with native-policy acknowledgement.

**Enable:** Settings → Frame Generation → GFG Engine → **GFG Open generator**, then restart the game. The choice is saved per profile and is available in Extreme. This first version supports native 64-bit SDR games. Flatpak continues to use the existing generator and logs the fallback reason. LS1 scaling shaders may still require the DLL separately.

**Status:** experimental. Validation covers the native Vulkan-layer build, SPIR-V compilation and execution on synthetic image sequences, Python tests, native layers and the interface. Improvements in FPS, GPU load and ghosting on Steam Deck have not yet been established by a controlled in-game comparison. Motion search is bounded; transparency, game-side TAA trails and fast motion may require falling back to a real frame. Extreme retains its 15 W ceiling, without overclocking or BIOS changes.

The native payload was rebuilt against an older system-library baseline for Steam Runtime compatibility: required symbol versions are at most GLIBC 2.34 and GLIBCXX 3.4.29.

**Install:** download **GFG-Extreme-v1_6_6.zip** and use Decky Loader → Install from zip. Restart the game to load the new native components.

SHA-256: `abe362824c52a07a7e75a47007c17a0058e2500bfa3ba3eaed9afa3bb44e7c59` (also provided in SHA256SUMS.txt).
