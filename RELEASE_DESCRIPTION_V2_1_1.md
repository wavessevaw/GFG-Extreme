# GFG Extreme 2.1.1 — stable

Bug-fix update for 2.1.0. Every Governor mode now offers normal multipliers from ×1 to ×3.75 in quarter steps, including Battery, Balanced, Quality, Autopilot and the legacy Extreme mode.

- Quality includes ×3.25, ×3.5 and ×3.75. Balanced can use these steps when higher real-frame targets cannot hold. At 60 output FPS, ×3.75 means 16 real FPS; at 90 it means 24. Mode priorities and power limits still apply.
- Governor launch overlays reserve up to three generated-frame slots. Fractional point changes retain this capacity, so a low initial ratio does not strand the session below the newly available steps. Restart the game after updating. Drivers that cannot provide the required resources retain their measured capacity limit.
- When output is short and measured APU draw is below the power cap, a feasible fractional ratio can restore output without futile extra watts. Healthy output and transient stalls keep their guards.
- Emergency points remain separate from the normal ×3.75 range. The legacy Extreme fallback now targets 90 output instead of requesting fixed 23×4 = 92.
- Updated mode descriptions, English/Russian README and UI cards. Corrected damaged punctuation in the English README.

**Continuous Boost** is a separate Autopilot-only switch, off by default. It holds the higher real-frame cadence without the 1.5-second pulse limit, including without stick input. It may use extra power within the normal power ceiling; menu, heat, delivery and power-search guards still pause it. Turning it off restores the short-pulse policy.

Fusion and both Boost policies remain Autopilot-only. Existing saved feature choices are preserved. No measured performance or battery-life gain is claimed by this release.

Install **GFG-Extreme-v2_1_1.zip** through Decky, update the bundled engine if prompted, and restart the game through `/home/deck/.local/bin/gfg %command%` so the new launch capacity is provisioned.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
