# GFG Extreme 4.0.0-sr.2 · Native Super Resolution test candidate

Install the inner ZIP through Decky Loader, reinstall Gamescope Kedavra in Setup and reboot.
Enable Graphics → Super Resolution → Auto. The frontend requests per-app Steam Properties
resolution 1024x640 and the internal-display override before RunGame on a 1280x800 display.
The API is verified by reading the values back; launch surfaces bypassing the hook may only
apply on a subsequent launch. No temporary virtual display resize is requested by GFG;
Gamescope receives an app-scoped passive SR lease with launch token zero. Actual game surface
size is reported, and a game may ignore its advertised display mode. Focus and frame generation
remain unchanged. Turning Auto off attempts to restore recorded Steam settings; if the Steam
API is unavailable, restore Properties manually. User changes to a different resolution are
not overwritten by rollback. Previous setting receipts are stored per Steam account when the
account is available; otherwise they survive only for the frontend session.

The experimental phase-dependent 12-tap reconstruction is enabled only at 5:4. Other ratios
retain the original SR. Hardware performance and live launch ordering are unverified.
Do not install the older candidate from the engine build run: it lacks this Steam Properties fix.
