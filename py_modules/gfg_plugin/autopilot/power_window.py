"""Keep real power readings aligned to the renderer window used by an experiment."""
import math
import statistics


class PowerWindow:
    def __init__(self):
        self.session = None
        self.rows = []

    def add(self, now, session, seq, watts):
        if session != self.session:
            self.session, self.rows = session, []
        self.rows = [r for r in self.rows if 0 <= now-r[0] <= 20]
        if (type(watts) not in (int,float) or not math.isfinite(watts) or watts <= 0
                or type(seq) is not int or seq <= 0 or self.rows and seq <= self.rows[-1][1]):
            return
        self.rows.append((now,seq,float(watts)))
        self.rows = self.rows[-40:]

    def summary(self, first, last):
        rows = [r for r in self.rows if isinstance(first,int) and isinstance(last,int) and first <= r[1] <= last]
        span = rows[-1][0]-rows[0][0] if rows else 0
        return {"draw_w": statistics.median([r[2] for r in rows]) if len(rows)>=5 and span>=2 else None,
                "draw_samples":len(rows),"draw_span_s":round(span,3),"draw_basis":"renderer-window-median"}
