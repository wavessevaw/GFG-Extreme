## GFG Extreme 1.0.1

**Faster recovery when the GPU cannot feed a requested ratio.**

### Changed
- When the Governor asks for a ratio such as 36×2.5 or 33×2.75 and the GPU cannot render that many real frames, the renderer holds the full frame rate at ×3 on its own. The Governor used to wait the whole 25-second confirmation before following it; in a recorded Witcher 3 session that added up to minutes. Now, once the renderer has applied the request and **8 seconds** of fresh data consistently show the target delivered with fewer real frames, it moves to the delivered point right away (still marked *verifying* until fresh windows confirm it). Output stays at the target the whole time either way.
- Only in Battery and Balanced, and only after the renderer reports that it applied the request.

### Install
Download `GFG-Extreme-v1_0_1.zip` below and install it through Decky Loader (*Install from zip*) over your current version; settings, profiles and game memory are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
