# C2 against the specification

`coordinator.plan` is the decision entry from section 5. It is pure.

Step A drops candidates that exceed the verified power ceiling, go under the
user render-scale floor, need an unconfirmed renderer capacity, boost CPU for a
GPU limit, cut scale for a CPU limit, or start Frame OS Act without consent.
Step B keeps the non-dominated point. A tie, or a gain that does not pay for
its watts, is HOLD. A drop below the last verified delivery is RECOVER, not a
new trial. Strategy changes wait out the dwell unless delivery is starving or
the limit is thermal.

`explain` reports the reason and leaves confirmed gain, input latency and
visual quality unavailable. Nothing is invented.

The power and flow flags in the Governor remain off and are not this decision.
They are not a user mode. Hardware: NOT_TESTED. These checks are SIMULATED.
