# GFG Extreme 1.7.1 pre-alpha

Release status: pre-release

Test build. Not the official release. The official version after this test remains 2.0.0.

## Fix from the first Deck log
- Choosing Autopilot no longer leaves the Governor in DISABLED. A stopped state was blocking every renderer receipt, so the first capture could not observe frames.
- Autopilot still replaces Extreme in the selector. It still runs one power trial only after there is a real measurement. Flow scale is unchanged.
- No FPS, latency or ghosting number is claimed. The first Deck capture had no measured frames.

## Logs
Stop a log recording to export `autopilot-trace.jsonl` with the usual ZIP.
