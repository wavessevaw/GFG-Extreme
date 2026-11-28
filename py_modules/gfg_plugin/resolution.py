"""Compositor-owned game display lease. Recommendations apply on the next launch."""
import statistics
import time

HEIGHTS = (480, 500, 540, 600, 720, 800)


class ResolutionController:
    def __init__(self, settings, ctl, clock):
        self.settings, self.ctl, self.clock = settings, ctl, clock
        self.app = self.token = self.sent = self.pending_until = 0
        self.height = 500
        self.key = ""
        self.samples = []
        self.done = False
        self.message = "Off"

    def enabled(self):
        return self.settings.data["engine"].get("super_resolution", False)

    def context(self, app, st):
        mode = self.settings.profile_for(app)[1]["objective"]
        hz = round(1e9 / st["refresh_ns"]) if st.get("refresh_ns", 0) > 0 else 0
        return f"{app}:{mode}:{st.get('sr_output_width',0)}x{st.get('sr_output_height',0)}:{hz}"

    def start(self, app, st, launch):
        key = self.context(app, st)
        record = self.settings.data.get("sr_profiles", {}).get(key, {})
        size = record.get("next") if isinstance(record, dict) else None
        height = size if size in HEIGHTS else 500
        token = time.monotonic_ns() % 4294967294 + 1 if launch else 0
        self.ctl.set_var("kfg_sr", f"{app}:{height}:{token}")
        self.app, self.height, self.token, self.key = app, height, token, key
        self.sent = self.clock()
        self.pending_until = self.sent + 30 if launch else 0
        self.samples.clear()
        self.done = False
        self.message = "Launch requested" if launch else "Observing current surface"

    def launch(self, app):
        if not self.enabled() or type(app) is not int or not 1 < app <= 0xffffffff or app == 769:
            return False
        st = self.ctl.status() or {}
        if not st.get("fresh") or not st.get("sr_capable") or not st.get("sr_output_height"):
            return False
        if self.app == app and (self.pending_until > self.clock() or app == st.get("app_id")):
            return False
        self.start(app, st, True)
        return True

    def stop(self):
        if self.app:
            self.ctl.set_var("kfg_sr", "0")
        self.app = self.token = self.pending_until = 0
        self.samples.clear()
        self.message = "Waiting for launch" if self.enabled() else "Off"

    def tick(self, game, st):
        if not self.enabled():
            self.stop()
            return
        if not st.get("fresh") or not st.get("sr_capable"):
            self.message = "Waiting for compatible Gamescope"
            return
        now = self.clock()
        if st.get("app_id") == self.app:
            self.pending_until = 0
        if self.pending_until > now:
            game = self.app
        if not game:
            self.stop()
        elif self.app != game:
            self.start(game, st, False)
        elif now - self.sent >= 6:
            self.ctl.set_var("kfg_sr", f"{self.app}:{self.height}:{self.token}")
            self.sent = now

    def observe(self, st, live, sensors, target):
        if (not self.app or self.done or st.get("app_id") != self.app or st.get("steam_ui")
                or not st.get("fresh") or self.key != self.context(self.app, st)):
            return
        managed = st.get("sr_managed_app") == self.app
        if not managed and self.height != 800:
            self.message = "Reconstructing existing surface" if st.get("sr_selected") else "Game controls its surface"
            return
        fps, gpu = live.get("real"), sensors.get("gpu_busy_pct")
        if not fps or gpu is None or not target or not st.get("sr_width"):
            return
        actual = (st.get("sr_width"), st.get("sr_height"))
        expected = (st.get("sr_virtual_width"), st.get("sr_virtual_height")) if managed else (
            st.get("sr_output_width"), st.get("sr_output_height"))
        self.samples.append((actual == expected, fps / target, gpu, sensors.get("cpu_top_core_pct") or 0,
                             float(fps), sensors.get("temp_c") or 0))
        if len(self.samples) < 60:
            return
        idx = HEIGHTS.index(self.height)
        windows = (self.samples[:30], self.samples[30:])
        if any(sum(r[0] for r in w) < 28 for w in windows):
            idx += 1
            self.message = "Surface mismatch; try a larger mode next launch"
        elif all(statistics.median(r[1] for r in w) < .94 and statistics.median(r[2] for r in w) >= 91 for w in windows):
            idx -= 1
            self.message = "GPU limited; try a smaller mode next launch"
        elif all(statistics.median(r[2] for r in w) < 76 and
                 (statistics.median(r[1] for r in w) >= .98 or statistics.median(r[3] for r in w) >= 90)
                 and max(r[5] for r in w) < 84 for w in windows):
            idx += 1
            self.message = "GPU headroom; try a larger mode next launch"
        else:
            self.message = "Retain measured size"
        self.settings.data.setdefault("sr_profiles", {})[self.key] = {
            "next": HEIGHTS[min(len(HEIGHTS)-1, max(0, idx))], "tested": self.height, "surface": actual,
            "matched": sum(r[0] for r in self.samples), "real_fps": round(statistics.median(r[4] for r in self.samples), 1),
            "gpu_pct": round(statistics.median(r[2] for r in self.samples), 1)}
        self.settings.save()
        self.done = True
