# GFG Extreme 3.0.2 Independence

HDR fix: Gamescope KEDAVRA now reads SteamOS's display scripts, so the Steam Deck OLED is
recognised again and HDR is available in games, switched on automatically like in the stock
Gaming Mode, together with frame generation.

> Tested in CI and in the sandbox. **Not yet checked on a Steam Deck.**
> After updating: **Setup → Reinstall engine, then reboot**, so the new Gamescope is used.

## What was wrong

Gamescope looks for its display scripts in `<install prefix>/share/gamescope/scripts`. Our build
used the default prefix `/usr/local`, so it never found `/usr/share/gamescope/scripts`, where
SteamOS keeps the Steam Deck OLED script. Without that script the panel looked like an unknown
display without HDR metadata, and Gamescope reported HDR as unsupported. With the plugin's
Gamescope removed, the stock one read the script and HDR worked.

## Changes

- Gamescope KEDAVRA built with prefix `/usr`; CI checks the script path in the binary.
- The runtime version now carries the GFG build, so Setup asks for a reinstall whenever the
  engine changes.
- Setup → Diagnostics shows whether the installed Gamescope reads SteamOS's display scripts.

Everything from 3.0.1 (faster Governor, Auto that follows the real frame rate, smaller aligned HUD,
gamepad focus) is included.
