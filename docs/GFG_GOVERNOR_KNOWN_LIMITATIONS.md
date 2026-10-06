# GFG Governor v0.0.2 Known Limitations

1. **No hardware validation yet.** All behaviour is verified with unit, replay, service and real-bash wrapper tests. Replay lines are modelled on the Renderer's diagnostic format strings, not captured from a Deck. First on-device testing is the v0.0.10 release.
2. **`fixed-plan` cadence is unverified.** Real FPS is derived from `fixed-plan` events; their emission rate while FG is active has to be confirmed on a Deck.
3. **Native (x1) points may have no evidence.** With Frame Generation off the Renderer may emit no periodic FPS event, so a native trial could time out and be rejected.
4. **Restart-bound toggles.** Scaling Engine and Frame Generation provisioning are process-static. The game must be (re)launched once after enabling the Governor; scaled points need the opt-in *Scale-ready launch* and a relaunch.
5. **Saved snapshot while running.** After the Governor is disabled, a running game keeps the Saved snapshot taken at launch; later Saved edits apply on the next launch.
6. **Guard is minimal.** Full Runtime Guard is planned for v0.0.4.
7. **Dock interplay not yet audited.** Interaction with the plugin's Automatic Dock state machine is the first v0.0.3 audit item.
8. **Overlay directory in Flatpak.** The overlay lives next to the Saved config and is assumed readable from Flatpak sandboxes; unverified.
9. **In-game overlay.** MangoHud horizontal layout and the refresh rate of the `exec` status line are unverified on device. The overlay is skipped when another external layer (MangoHud/vkBasalt) is chosen for the profile.
10. **TDP control** needs writable amdgpu `fastPPT`/`slowPPT` caps; otherwise the Governor stays observe-only. TDP display needs readable hwmon values (otherwise `TDPn/a`).
11. **GFG Effort thresholds** (nightmare below 18 real FPS, dwell times) are design choices not yet tuned on real games.
12. **UI.** Frontend is verified in a mock Decky environment (Chromium) with sample data; focus/controller navigation on a real Deck is untested. Shader-effect and per-field presets from the old UI are reachable only through *All settings*.
13. **External backends** (OptiScaler, Game Native) are observe-only; the Governor never changes them.
