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
        self.series = self.last_stamp = None
        self.blocked = 0
        self.misses = 0
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
        records = self.settings.data.get("sr_profiles", {})
        record = records.get(key, {})
        if not record and key.endswith(":0"):
            # Before the FG scheduler starts its refresh period may be unknown.
            # Reuse prior evidence only when the known outputs agree on a size.
            prefix = key.rsplit(":", 1)[0] + ":"
            heights = {v.get("next") for k, v in records.items() if isinstance(k, str)
                       and k.startswith(prefix) and isinstance(v, dict) and v.get("next") in HEIGHTS}
            if len(heights) == 1:
                record = {"next": heights.pop()}
        size = record.get("next") if isinstance(record, dict) else None
        height = size if size in HEIGHTS else 500
        token = time.monotonic_ns() % 4294967294 + 1 if launch else 0
        self.ctl.set_var("kfg_sr", f"{app}:{height}:{token}")
        self.app, self.height, self.token, self.key = app, height, token, key
        self.sent = self.clock()
        self.pending_until = self.sent + 30 if launch else 0
        self.samples.clear()
        self.series = self.last_stamp = None
        self.misses = self.blocked = 0
        self.done = False
        self.message = "Launch requested" if launch else "Observing current surface"

    def launch(self, app):
        if not self.enabled() or type(app) is not int or not 1 < app <= 0xffffffff or app == 769:
            return False
        st = self.ctl.status() or {}
        if not st.get("fresh") or not st.get("sr_capable") or not st.get("sr_output_height"):
            return False
        if self.blocked == app:
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
            self.blocked = 0
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
        if self.blocked and game == self.blocked:
            return
        self.blocked = 0
        if not game:
            self.stop()
        elif self.app != game:
            self.start(game, st, False)
        elif now - self.sent >= 6:
            self.ctl.set_var("kfg_sr", f"{self.app}:{self.height}:{self.token}")
            self.sent = now

    def observe(self, st, live, sensors, target, budget=None, external=None):
        if (not self.app or st.get("app_id") != self.app or st.get("steam_ui")
                or not st.get("fresh")):
            return
        key = self.context(self.app, st)
        if self.key != key:
            self.key, self.done, self.misses = key, False, 0
            self.samples.clear()
        managed = st.get("sr_managed_app") == self.app
        if not managed and self.height != 800:
            self.message = "Reconstructing existing surface" if st.get("sr_selected") else "Game controls its surface"
            return
        stamp = st.get("time_ns")
        if stamp is not None and self.last_stamp == stamp:
            return
        self.last_stamp = stamp
        # A game can ignore the virtual size, or submit unsupported HDR/video.
        # Allow startup to settle, then give the original virtual mode back.
        if managed and not st.get("sr_selected") and st.get("sr_width") and st.get("sr_height"):
            self.misses += 1
            if self.misses >= 12:
                next_size = HEIGHTS[min(HEIGHTS.index(self.height) + 1, len(HEIGHTS)-1)]
                if st.get("transfer") in ("hdr10_pq", "scrgb", "pq"):
                    next_size = 800
                self.settings.data.setdefault("sr_profiles", {})[self.key] = {
                    "next": next_size, "tested": self.height, "reason": "bypass"}
                self.settings.save()
                blocked = self.app
                self.stop()
                self.blocked = blocked
                self.message = "Unsupported surface; original display restored or lease expiring"
            return
        self.misses = 0
        if self.done:
            return
        context = (target, budget, external, st.get("multiplier"))
        if context != self.series:
            self.samples.clear()
            self.series = context
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
        # If a lower first trial failed to relieve a GPU limit under the same
        # cap, budget and power source, keep the larger measured size.
        records = self.settings.data.setdefault("sr_profiles", {})
        previous = records.get(self.key, {})
        median_fps = statistics.median(r[4] for r in self.samples)
        median_gpu = statistics.median(r[2] for r in self.samples)
        floor = 480
        if isinstance(previous, dict) and previous.get("conditions") == list(context):
            floor = previous.get("floor") if previous.get("floor") in HEIGHTS else 480
            if (previous.get("tested") in HEIGHTS and previous["tested"] > self.height
                    and previous.get("matched") == 60 and all(r[0] for r in self.samples)
                    and median_fps <= previous["real_fps"] * 1.03
                    and median_gpu >= previous["gpu_pct"] - 3):
                floor = previous["tested"]
                self.message = "Smaller output produced no measured relief; prefer prior size"
        idx = max(idx, HEIGHTS.index(floor))
        records[self.key] = {
            "conditions": list(context), "floor": floor, "next": HEIGHTS[min(len(HEIGHTS)-1, max(0, idx))], "tested": self.height, "surface": actual,
            "matched": sum(r[0] for r in self.samples), "real_fps": round(statistics.median(r[4] for r in self.samples), 1),
            "gpu_pct": round(statistics.median(r[2] for r in self.samples), 1)}
        self.settings.save()
        self.done = True
