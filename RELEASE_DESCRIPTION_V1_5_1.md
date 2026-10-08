## GFG Extreme 1.5.1: Frame OS Act no longer stops the battery search

A field log on 1.5.0 showed that with **Frame OS Act** on, the Governor stopped looking for lower watts as soon as Act took over. One session stayed at the 10 W start for 11 minutes, another at 13 W left over from a short boost during a mode test. The Smart power split never got a turn either.

### Fixed
- Act now waits until the Governor has **found and settled** the watts for the current mode (about a minute after the last successful step down), then takes over.
- Every 10 minutes Act **steps aside for 2 minutes**. The Governor checks whether a lower level still holds, and the Smart power split measures in that time. These pauses are never counted as Act failing.
- With Act off nothing changes.

### Also in this build
- **GFG Extreme theme for CSS Loader** (`themes/css-loader/GFG Extreme` in the repository): near-black panels, GFG red accents, a red focus frame, the last game as a vertical card on Home, and accent status icons. To install, copy the folder to `~/homebrew/themes/`.

### Install
Download `GFG-Extreme-v1_5_1.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
