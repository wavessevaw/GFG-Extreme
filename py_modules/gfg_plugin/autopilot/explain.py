"""User-facing reasons. Missing measurements stay unavailable; nothing is invented."""


def explain(decision):
    return {
        "action": decision.action.value,
        "strategy": decision.strategy.value,
        "reason": decision.reason,
        "knob": None if decision.knob is None else decision.knob.value,
        "confirmed_gain": None,
        "input_latency": "unavailable",
        "visual_quality": "unavailable",
        "rejected": [{"knob": knob, "value": value, "reason": reason}
                     for knob, value, reason in decision.rejected],
    }
