# GFG Extreme 4.0.0-sr.4 · Native Super Resolution test candidate

Install the inner ZIP through Decky Loader, reinstall Gamescope Kedavra in Setup and reboot.
Enable Graphics → Super Resolution → Auto. The frontend requests per-app Steam Properties
resolution 1024x640 and the internal-display override before RunGame on a 1280x800 display.
The API is verified by reading the values back; launch surfaces bypassing the hook may only
apply on a subsequent launch. No temporary virtual display resize is requested by GFG;
Gamescope receives an app-scoped passive SR lease with launch token zero. Actual game surface
size is reported, and a game may ignore its advertised display mode. Focus is automatically forced while SR is enabled without modifying the saved profile; frame generation remains unchanged. Turning Auto off attempts to restore recorded Steam settings; if the Steam
API is unavailable, restore Properties manually. User changes to a different resolution are
not overwritten by rollback. Previous setting receipts are stored per Steam account when the
account is available; otherwise they survive only for the frontend session.

The experimental 16-tap, 25-phase learned residual reconstruction is enabled only at 5:4. Other input/output resolutions bypass Kedavra SR. Hardware performance and live launch ordering are unverified.
The previous SR.2 package remains a rollback option. Coefficients were fitted using synthetic photographic downsampling and an approximate CPU Focus implementation; actual game fidelity and GPU performance are unverified.

SR.4 inverse candidate: reconstructs a Focus-based spatial prior, projects raw pre-Focus SDR luma through a regularized 5:4 area + mild low-pass inverse and corrects the prior. One additional compute dispatch at 1280x800, no temporal history. The inverse path is limited to fullscreen, exact-size opaque SDR game content with Focus only; other active post effects use spatial SR.3. GPU performance and real-game quality remain unverified. Disable other look/AA effects to test the inverse candidate.
