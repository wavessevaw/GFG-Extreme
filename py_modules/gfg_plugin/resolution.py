"""Compositor-owned game display lease. Recommendations apply on the next launch."""

HEIGHTS = (480, 500, 540, 600, 640, 720, 800)


class ResolutionController:
    def __init__(self, settings, ctl, clock):
        self.settings, self.ctl, self.clock = settings, ctl, clock
        self.app = self.token = self.sent = self.pending_until = 0
        self.height = 640
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
        return f"sr2:{app}:{mode}:{st.get('sr_output_width',0)}x{st.get('sr_output_height',0)}:{hz}"

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
        height = 640  # fixed for SR.2; no learned or adaptive resolution changes
        token = 0  # Steam Properties owns the virtual mode; never request a Gamescope resize.
        self.ctl.set_var("kfg_sr", f"{app}:{height}:{token}")
        self.app, self.height, self.token, self.key = app, height, token, key
        self.sent = self.clock()
        self.pending_until = self.sent + 30 if launch else 0
        self.samples.clear()
        self.series = self.last_stamp = None
        self.misses = self.blocked = 0
        self.done = False
        self.message = "Waiting for Steam 640p surface" if launch else "Observing current surface"

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
        if not self.app or st.get("app_id") != self.app or st.get("steam_ui") or not st.get("fresh"):
            return
        actual = (st.get("sr_width"), st.get("sr_height"))
        if st.get("sr_selected") and actual == (1024, 640):
            self.message = "640p confirmed; Native SR active"
        elif st.get("sr_selected"):
            self.message = "Reconstructing existing surface; Steam 640p not confirmed"
        else:
            self.message = "Steam 640p not confirmed or surface unsupported"
