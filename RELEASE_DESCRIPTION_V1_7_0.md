# GFG Extreme 1.7.0 pre-alpha

Release status: pre-release

This is a test build for log collection and a first Autopilot power trial. It is not the official release. The official version after this test remains 2.0.0. Do not install it for regular play.

## What the selector does
- Battery, Balanced and Quality stay.
- **Extreme is replaced by Autopilot** in this test build. A profile that was on Extreme opens as Autopilot.
- Autopilot runs one power trial under the current limit. It does not change flow scale.
- Leaving Autopilot puts an applied trial watt back before the selected mode continues.

## Logs
Stop a log recording to export `autopilot-trace.jsonl` with the usual ZIP. The trace is written even while the button is off. It is not a measurement of smoothness or latency.

## Not claimed
No Deck result is claimed for this build. No FPS, latency or ghosting number is claimed. Saved profiles and the generator model are unchanged.
