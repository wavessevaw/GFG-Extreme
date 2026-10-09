# HUD readings

ENERGY is present in Standard and Detailed regardless of whether Frame OS is enabled.

- Number: max(0, min(100, (device maximum TDP - confirmed cap) / device maximum TDP * 100)).
- Device maximum: Gamescope/QAM slider maximum from SteamOSManager first, hardware maximum second. An initial/current cap is not a device maximum. Unknown maximum or cap displays an em dash.
- Cap: higher of confirmed fast/slow caps, preserving precision before formatting. At 20 W maximum and 15 W cap the number is 25%. This is saved TDP allowance, not measured battery-energy savings.
- Arc: battery charge / 100, independent of the numeric savings, Frame OS state, benefit estimates and Extreme's 15 W ceiling.
- Colour: green at/above 50% charge; continuously towards red as charge drops below 50%. Unknown charge gives an empty grey track. Arc opacity is always 1.

FPS and REAL use fresh renderer interval samples. Ring HUD holds the last valid sample for at most five seconds from its sample time; game/profile/renderer-session changes reset that hold. Text fallback uses fresh interval samples as well, including HUD-only sessions with the Governor disabled. Zero FPS/TDP is valid; booleans, NaN and infinity are unavailable.

RESP/FRAMES keep their existing response/gain conventions. Values without controlled measurement are grey. BOOST requires a fresh renderer sample, active executor and acknowledgement; held FPS cannot confirm it, and missing Frame OS telemetry clears the active badge while preserving the group briefly to avoid resizing flicker.

Detailed BATTERY shows remaining time while available, or the charge percentage while charging. Ring layout, typography, presets, four corners and scale selection follow the committed HUD reference pictures; the updated ENERGY semantics supersede the historical pictures' energy reading.
