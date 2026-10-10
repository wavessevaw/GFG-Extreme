"""Bounded raw-event tap; never calls an actuator or reconstructs FPS from plans."""
from collections import deque
from .contracts import Sample, number

PRESSURE = frozenset(("generated-delivery-miss", "render-fence-budget-missed",
                      "ordered-acquire-budget-exhausted", "pipeline-busy-bypass",
                      "ordered-acquire-guard-bypass"))


def first(fields, names):
    for name in names:
        if name in fields:
            return number(fields[name])
    return None


class ObservationStream:
    MAX_SAMPLES = 64
    MAX_PRESSURE = 64

    def __init__(self):
        self.samples = deque(maxlen=self.MAX_SAMPLES)
        self.pressure = deque(maxlen=self.MAX_PRESSURE)
        self.context = ""
        self.seq = 0

    def reset(self):
        self.samples.clear()
        self.pressure.clear()
        self.context = ""

    def consume(self, fields, timestamp_mono, event_seq):
        if number(timestamp_mono) is None:
            return
        # A spatial layer's FPS/capacity must never enter generator evidence.
        if fields.get("role") not in (None, "frame-generation"):
            return
        context = str(fields.get("context") or "")
        if not context or len(context) > 128:
            return
        if context != self.context:
            self.reset()
            self.context = context
        self.seq = event_seq
        operation = fields.get("operation")
        if operation in PRESSURE:
            self.pressure.append((event_seq, timestamp_mono, context))
        if operation not in ("fixed-plan", "adaptive-plan"):
            return
        real = first(fields, ("current_base_fps", "measured_base_fps", "instantaneous_base_fps"))
        output = first(fields, ("current_output_fps", "observed_output_fps"))
        # base_fps, generated_per_real, previous_output_fps and scheduler intervals
        # have ambiguous/derived provenance and are deliberately not promoted.
        self.samples.append(Sample(event_seq, timestamp_mono, context, real, output))
