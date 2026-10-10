# C2 plan slice: one unarmed decision, then one power step

The coordinator may name at most one of two tools, the power cap or flow scale.
Flow is not connected. Power is connected only behind `_autopilot_power_enabled`,
which defaults off and is not a user mode. While it is on, the Governor loop does
not also run Battery, Balanced, Quality or Extreme writers.

A power trial claims nothing itself. It steps one watt toward the owned ceiling,
requires readback, then restores. It does not write the trial winner back.
Pending restore, a missing ACK, or a second tool clears the slot. A1/A2 drift is
INCONCLUSIVE and is not learned.

Hardware: NOT_TESTED. Checks are SIMULATED.
