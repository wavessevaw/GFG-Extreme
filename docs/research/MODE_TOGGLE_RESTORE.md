# Restore Stable 3.2.2 Mode interaction

The Dash Mode tiles again control generation: tapping the active mode disables FG; selecting any mode while off enables Auto. Selecting a different mode also enables Auto, as in 3.2.2. No mode tile is highlighted while FG is off.

The mistakenly restored separate FRAME GENERATION card is removed. Its full selector and custom cap remain available as MULTIPLIER inside Mode: Off, Auto, x2, x3, permitted x3.75 and Custom. Selecting a mode after using a fixed multiplier returns to Auto; this follows the protected historical Mode behavior. Fixed settings remain explicitly selectable and are not removed from backend profiles.

Cause: main replaced the Mode RPC payload with an objective-only update and removed FG state from tile highlighting. The former smoke test merely checked that a profile RPC occurred; its mock did not apply profile changes, so it could not exercise click/state transitions.

The expanded smoke test applies scoped profile RPCs and returns fresh state objects. It verifies disable/re-enable, switching modes while off, disabling from x3, Custom cap changes, permission-gated x3.75, game-profile operations and preservation of the default profile. Running this test against the unmodified parent frontend failed at the first expected Mode payload. The corrected frontend passed with no page errors. Existing tab, ring-size and Setup toast checks remain.

Local validation: npm 10.9.2 `ci`, Node 24.22.1 build, browser smoke on installed Edge, and visual inspection of the 330 CSS-pixel Dash screenshot. The compiled `dist/index.js` is rebuilt from the changed source. Local before/after logs and screenshots are retained in `baseline-evidence/mode-toggle-*` outside the checkout. Linux Chromium CI is required before integration. Decky gamepad focus/activation on real hardware remains UNVERIFIED.

Candidate notes: include this as a restored interaction, not an FPS/energy improvement. On the Deck, check each of four modes with FG on/off, a fixed multiplier, a game-specific profile and the narrow Quick Access panel. This branch does not contain the pending Governor, migration or installer fixes and is not a consolidated installable candidate. No Stable merge or release is approved.
