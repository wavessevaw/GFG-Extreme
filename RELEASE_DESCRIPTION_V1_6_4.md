## GFG Extreme 1.6.4: trustworthy audit summaries

The three user-recorded sessions on 1.5.0–1.6.1 exposed omitted transition samples and inherited A/B results. This release fixes diagnostics so they no longer hide those cases.

### Fixed
- Extreme summaries inspect both fast and slow PPT channels, including APPLY transitions without a confirmed operating point.
- Reports distinguish all observed caps from caps observed while GFG owns control, and count above-ceiling samples against each sample's applicable ceiling. Readback alone is not attributed to a particular writer.
- Frame OS records separate current-session and historical A/B statistics. Reports identify historical-only and mixed old results instead of describing them as fresh measurements.
- Preliminary measurements are labelled when the record provides that confidence flag. The response metric is explicitly internal pacing/freshness telemetry, not independently measured input latency.
- Relay input with an unknown device count is no longer reported as zero controllers. Per-decision sample counts are labelled as samples rather than seconds.

### Scope
This release improves the evidence used to diagnose Extreme. It does not claim to fix Act output starvation, deliver render scaling in Ghost of Tsushima, remove ghosting, or prove that transition overshoots are resolved on a physical Deck. Historical archives cannot yield a current-session A/B mean when only a mixed mean was stored. Runtime control and frame presentation are unchanged; the A/B meter adds small statistics to its existing status snapshots.

### Validation
Regression coverage includes missing-point transition samples, fast-only cap violations, unowned reads, changing ceilings, historical-only/mixed/current A/B provenance and unknown relay device counts. GitHub Actions runs backend, native Frame OS/HUD, frontend smoke/build, HUD benchmark and release archive checks.

### Install
Download GFG-Extreme-v1_6_4.zip and install through Decky Loader (Install from zip).

SHA-256: `<sha256>` (also in SHA256SUMS.txt).
