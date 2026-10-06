// GFG Extreme UI. No npm deps: Decky provides SP_REACT and DFL as globals; `callable` comes from the shim.
import { css } from "./theme.js";
import { LOGO } from "./logo.js";
const R = window.SP_REACT;
const { useState, useEffect, useRef, useCallback } = R;
const h = (t, p, ...c) => R.createElement(t, p, ...c);

const rpc = {
  governor: callable("get_governor_status"),
  setGovernor: callable("set_governor_enabled"),
  setHud: callable("set_governor_hud"),
  setScaleReady: callable("set_governor_scale_ready"),
  profiles: callable("get_profiles"),
  setProfile: callable("set_current_profile"),
  profileConfig: callable("get_profile_config"),
  patch: callable("update_profile_config_fields"),
  inspector: callable("get_pipeline_inspector"),
  runtime: callable("get_runtime_status"),
  launch: callable("get_launch_option"),
};

// ---------- helpers
const num = (v, d = 1) => (v == null || isNaN(v) ? "–" : Number(v).toFixed(d).replace(/\.0$/, ""));
const MODE_NAME = { oled: "Steam Deck OLED", lcd: "Steam Deck LCD", dock: "Dock", external: "Dock", unknown: "Display" };
const POINT_LABEL = (p) => (p ? (p.multiplier > 1 ? "×" + p.multiplier : "Native") + (p.render_scale_pct < 100 ? " · " + p.render_scale_pct + "%" : "") : "–");

// Plain-language state for the hero card. Returns {head, body, tone}
function describe(s) {
  const cap = (s.capability && s.capability.reason) || "";
  if (!s.enabled) return { head: "Ready", body: "Press Run — GFG will pick the target for this screen and manage the engine.", tone: "idle" };
  if (s.state === "PAUSED") return { head: "Paused", body: s.reason === "overlay-restore-failed" ? "Could not restore settings — retrying." : "Waiting. Your saved profile is untouched.", tone: "warn" };
  if (cap === "relaunch-required-for-governor-overlay") return { head: "Restart the game", body: "GFG is on. Relaunch the game once so the engine can attach.", tone: "warn" };
  if (s.state === "OBSERVE_ONLY") return { head: "Observing", body: "Another backend owns the pipeline. GFG only watches.", tone: "idle" };
  if (s.state === "PROBE" || s.state === "PLAN") return { head: "Measuring", body: "Learning how the game runs. Nothing is changed yet.", tone: "busy" };
  if (s.state === "APPLY") return { head: "Testing " + POINT_LABEL(s.request && s.request.point), body: "Checking the result before keeping it.", tone: "busy" };
  if (s.state === "OPTIMIZE_POWER") return { head: "Saving power", body: "Lowering TDP while holding the target.", tone: "ok" };
  if (s.state === "LOCKED") return { head: "Locked in", body: "Stable at target. GFG stays out of the way.", tone: "ok" };
  if (s.state === "GUARD") return { head: "Protecting", body: "Quality dipped — restoring a safe setting.", tone: "warn" };
  return { head: "Running", body: "", tone: "ok" };
}

// ---------- primitives
const Icon = ({ d, size = 16 }) => h("svg", { viewBox: "0 0 24 24", width: size, height: size, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, h("path", { d }));
const ICONS = {
  bolt: "M13 2L4 14h7l-1 8 9-12h-7z", layers: "M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5", scale: "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0", hud: "M3 5h18v10H3zM8 19h8", cog: "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12h2M3 12h2M12 3v2M12 19v2",
  play: "M6 4l14 8-14 8z", stop: "M6 6h12v12H6z",
};
const Focusable = ({ onClick, className, children }) => {
  const F = window.DFL && window.DFL.Focusable;
  const props = { className: (className || ""), onClick, "flow-children": "horizontal" };
  return F ? h(F, props, children) : h("div", { ...props, tabIndex: 0 }, children);
};
const Row = ({ icon, title, sub, value, onClick }) =>
  h(Focusable, { className: "row", onClick },
    icon ? h("div", { className: "ic" }, h(Icon, { d: ICONS[icon] })) : null,
    h("div", { className: "t" }, h("b", null, title), sub ? h("span", null, sub) : null),
    value ? h("div", { className: "val" }, value) : null, h("div", { className: "chev" }, "›"));
const Toggle = ({ on, onChange, title, sub }) =>
  h(Focusable, { className: "row", onClick: () => onChange(!on) },
    h("div", { className: "t" }, h("b", null, title), sub ? h("span", { style: { whiteSpace: "normal" } }, sub) : null),
    h("div", { className: "tog" + (on ? " on" : "") }));
const Seg = ({ value, options, onChange }) =>
  h("div", { className: "seg" }, options.map(([v, l]) => h("button", { key: v, className: v === value ? "on" : "", onClick: () => onChange(v) }, l)));
const Page = ({ title, onBack, children }) =>
  h("div", null, h("div", { className: "bar-top" }, h(Focusable, { className: "back", onClick: onBack }, "‹"), h("div", { className: "title" }, title)), children);
const Note = ({ quiet, children }) => h("div", { className: "note" + (quiet ? " quiet" : "") }, children);

// ---------- data
function useGovernor(profile) {
  const [s, setS] = useState(null);
  const alive = useRef(true);
  const refresh = useCallback(async () => { try { const r = await rpc.governor(profile || ""); if (alive.current) setS(r); } catch (e) {} }, [profile]);
  useEffect(() => { alive.current = true; refresh(); const t = setInterval(refresh, 1500); return () => { alive.current = false; clearInterval(t); }; }, [refresh]);
  return [s, refresh];
}

// ---------- Home
function Ring({ value, max, label, sub }) {
  const r = 78, c = 2 * Math.PI * r, f = Math.max(0, Math.min(1, max ? value / max : 0));
  return h("div", { className: "ring" },
    h("svg", { viewBox: "0 0 176 176", width: 176, height: 176 },
      h("circle", { cx: 88, cy: 88, r, fill: "none", stroke: "#26262d", strokeWidth: 9 }),
      h("circle", { cx: 88, cy: 88, r, fill: "none", stroke: "#ff3b30", strokeWidth: 9, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: c * (1 - f), style: { transition: "stroke-dashoffset .6s" } })),
    h("div", { className: "num" }, h("div", { className: "big" }, label), h("div", { className: "sub" }, sub)));
}

function Home({ s, profile, go, refresh }) {
  const [busy, setBusy] = useState(false);
  const d = describe(s);
  const dev = s.device || {};
  const tel = s.telemetry || {};
  const latest = tel.latest || {};
  const target = s.target_output_fps || dev.target || 60;
  const real = tel.real && tel.real.median, out = tel.output && tel.output.median;
  const mult = latest.effective_multiplier;
  const pw = s.power || {};
  const toggle = async () => { setBusy(true); try { await rpc.setGovernor(profile, !s.enabled); } catch (e) {} await refresh(); setBusy(false); };
  const showLive = s.enabled && out != null;
  const tdp = pw.observed_tdp_w != null ? pw.observed_tdp_w : pw.current_w;
  const eff = s.effort && s.effort.level;
  const mins = s.battery && s.battery.minutes_left;
  const left = mins != null ? (mins >= 60 ? Math.floor(mins / 60) + "h" + String(mins % 60).padStart(2, "0") : mins + "m") : "";
  return h("div", null,
    h("div", { className: "top" }, h("div", { className: "brand" }, h("img", { src: LOGO, width: 30, height: 30, style: { marginRight: 8, verticalAlign: "middle" } }), "GFG", h("b", null, "·"), "EXTREME"),
      h("div", { className: "chip" + (s.enabled ? " on" : "") }, h("i"), MODE_NAME[dev.mode] || "Display")),
    h("div", { className: "card hero" },
      h(Ring, { value: showLive ? out : 0, max: target, label: showLive ? num(out, 0) : String(target), sub: showLive ? "FPS OUTPUT" : "TARGET FPS" }),
      h("div", { className: "status" }, h("div", { className: "h" }, d.head), d.body ? h("div", { className: "p" }, d.body) : null),
      showLive ? h("div", { className: "flow" },
        h("div", { className: "stat" }, h("div", { className: "v" }, num(real, 0)), h("div", { className: "l" }, "REAL")), h("div", { className: "a" }, "→"),
        h("div", { className: "stat hot" }, h("div", { className: "v" }, mult ? "×" + num(mult, 0) : POINT_LABEL(s.active_point)), h("div", { className: "l" }, "GFG")), h("div", { className: "a" }, "→"),
        h("div", { className: "stat" }, h("div", { className: "v" }, num(out, 0)), h("div", { className: "l" }, "OUTPUT"))) : null,
      s.enabled ? h("div", { className: "effort" }, h("span", null, "GFG EFFORT"),
        h("b", { className: eff ? "lv " + eff : "lv" }, eff ? eff.toUpperCase() : "ASSESSING…")) : null,
      tdp != null ? h("div", { className: "power" }, h("div", { className: "r" }, h("span", null, "TDP NOW"), h("span", null, num(tdp, 0) + " W" + (left ? "  ·  " + left + " left" : ""))),
        h("div", { className: "bar" }, h("div", { style: { width: Math.min(100, (tdp / (pw.saved_w || 15)) * 100) + "%" } }))) : null),
    h(Focusable, { className: "run" + (s.enabled ? " stop" : ""), onClick: busy ? undefined : toggle },
      h(Icon, { d: s.enabled ? ICONS.stop : ICONS.play, size: 18 }), s.enabled ? "STOP" : "RUN"),
    h("div", { className: "hint" }, s.enabled ? "Stop returns everything to your saved profile." : "Target " + target + " FPS · " + (dev.reason || "picked automatically for this screen")),
    h("div", { className: "list" },
      h(Row, { icon: "bolt", title: "Governor", sub: "What it decided and why", onClick: () => go("governor") }),
      h(Row, { icon: "layers", title: "Frame Generation", sub: "Backend and quality", onClick: () => go("fg") }),
      h(Row, { icon: "scale", title: "Scaling", sub: "Render scale for extra headroom", onClick: () => go("scaling") }),
      h(Row, { icon: "hud", title: "In-game overlay", sub: "FPS, ×N, TDP while playing", onClick: () => go("hud") }),
      h(Row, { icon: "user", title: "Profile", value: profile || "Default", onClick: () => go("profiles") }),
      h(Row, { icon: "cog", title: "Advanced", sub: "Inspector, journal, install", onClick: () => go("advanced") })));
}

// ---------- Sub screens
function GovernorPage({ s, back }) {
  const dev = s.device || {}, req = s.request, pt = s.active_point, lad = s.ladder || {};
  return h(Page, { title: "Governor", onBack: back },
    h("div", { className: "sec" }, "DECISION"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "State"), h("b", null, describe(s).head),
      h("span", null, "Device"), h("b", null, MODE_NAME[dev.mode] || "–"),
      h("span", null, "Target"), h("b", null, (s.target_output_fps || dev.target || "–") + " FPS"),
      h("span", null, "Active point"), h("b", null, POINT_LABEL(pt) + (s.active_point_mode ? " (" + s.active_point_mode + ")" : "")),
      h("span", null, "Testing"), h("b", null, req ? POINT_LABEL(req.point) : "–"),
      h("span", null, "Attempts"), h("b", null, lad.attempts != null ? lad.attempts + " / " + (lad.max_attempts || 6) : "–"))),
    dev.reason ? h(Note, { quiet: true }, dev.reason) : null,
    h("div", { className: "sec" }, "RULES"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Multipliers"), h("b", null, "×1 ×2 ×3 only"),
      h("span", null, "Saved profile"), h("b", null, "never modified"),
      h("span", null, "TDP"), h("b", null, "never above your own"))),
    (s.limitations || []).length ? h("div", { className: "sec" }, "LIMITS") : null,
    ...(s.limitations || []).map((t, i) => h(Note, { key: i, quiet: true }, t)));
}

function FgPage({ back, cfg, patch }) {
  const be = (cfg && cfg.fg_backend) || "gfg";
  const mult = (cfg && cfg.multiplier) || 2;
  return h(Page, { title: "Frame Generation", onBack: back },
    h("div", { className: "sec" }, "BACKEND"),
    h(Seg, { value: be, options: [["gfg", "GFG"], ["optiscaler", "OptiScaler"], ["native", "Native"], ["off", "Off"]], onChange: (v) => patch({ fg_backend: v }) }),
    be === "gfg" ? h("div", null,
      h("div", { className: "sec" }, "SAVED MULTIPLIER"),
      h(Seg, { value: String(mult), options: [["2", "×2"], ["3", "×3"]], onChange: (v) => patch({ multiplier: Number(v) }) }),
      h(Note, { quiet: true }, "Governor may pick ×1, ×2 or ×3 on its own. This is only your saved preference.")) :
      h(Note, { quiet: true }, "External backend: GFG observes only and does not change it."));
}

function ScalingPage({ s, back, profile, refresh }) {
  const ready = !!s.scale_ready;
  return h(Page, { title: "Scaling", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } },
      h(Toggle, { on: ready, title: "Scale-ready launch", sub: "Provision the Scaling Engine at launch so Governor can lower render scale live without relaunching. Applies from the next game start.", onChange: async (v) => { await rpc.setScaleReady(profile, v); refresh(); } })),
    h(Note, { quiet: true }, "Governor only uses 90% or 80% render scale, and only after FG alone is not enough."));
}

function HudPage({ back, s, profile, refresh }) {
  const hud = s.hud || { enabled: false, preset: "standard", position: "top-right" };
  const set = async (c) => { await rpc.setHud(profile, c.enabled, c.preset, c.position); refresh(); };
  return h(Page, { title: "In-game overlay", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, h(Toggle, { on: hud.enabled, title: "Show overlay in game", sub: "FPS, frametime, multiplier, scale and TDP.", onChange: (v) => set({ enabled: v }) })),
    h("div", { className: "sec" }, "DETAIL"),
    h(Seg, { value: hud.preset, options: [["minimal", "Minimal"], ["standard", "Standard"], ["detailed", "Detailed"]], onChange: (v) => set({ preset: v }) }),
    h("div", { className: "sec" }, "POSITION"),
    h(Seg, { value: hud.position, options: [["top-right", "Top right"], ["top-left", "Top left"], ["bottom-left", "Bottom"]], onChange: (v) => set({ position: v }) }),
    h(Note, { quiet: true }, "Takes effect on next game launch. Not used when another overlay layer (MangoHud/vkBasalt) is chosen for the profile."));
}

function ProfilesPage({ back, profiles, current, pick }) {
  return h(Page, { title: "Profile", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, (profiles || []).map((p) => h(Row, { key: p, title: p, value: p === current ? "Active" : "", onClick: () => pick(p) }))));
}

function AdvancedPage({ back, s, insp, launch }) {
  const sv = insp && insp.saved, ef = insp && insp.effective, ac = insp && insp.actual;
  const col = (t, o, hot) => h("div", { className: "col" + (hot ? " hot" : "") }, h("h4", null, t),
    ...Object.entries(o || {}).slice(0, 5).map(([k, v]) => h("div", { key: k }, h("span", null, k), String(v))));
  return h(Page, { title: "Advanced", onBack: back },
    h("div", { className: "sec" }, "LAUNCH OPTION"),
    h("div", { className: "card" }, h("div", { style: { fontFamily: "monospace", fontSize: 12, wordBreak: "break-all" } }, launch || "/home/deck/.local/bin/gfg %command%")),
    h("div", { className: "sec" }, "INSPECTOR"),
    h("div", { className: "cols" }, col("SAVED", sv), col("EFFECTIVE", ef), col("GOVERNOR", s && s.active_point ? { point: POINT_LABEL(s.active_point) } : {}, true), col("ACTUAL", ac)));
}

// ---------- Root
function Content() {
  const [screen, setScreen] = useState("home");
  const [profiles, setProfiles] = useState([]);
  const [profile, setProfileName] = useState("");
  const [cfg, setCfg] = useState(null);
  const [insp, setInsp] = useState(null);
  const [launch, setLaunch] = useState("");
  const [s, refresh] = useGovernor(profile);

  const loadProfiles = useCallback(async () => {
    try { const r = await rpc.profiles(); setProfiles(r.profiles || []); setProfileName(r.current_profile || r.current || ""); } catch (e) {}
  }, []);
  const loadCfg = useCallback(async (p) => { try { const r = await rpc.profileConfig(p); setCfg(r.config || r); } catch (e) {} }, []);
  useEffect(() => { loadProfiles(); try { rpc.launch().then((r) => setLaunch((r && (r.launch_option || r.option)) || "")); } catch (e) {} }, []);
  useEffect(() => { if (profile) loadCfg(profile); }, [profile]);
  useEffect(() => { if (screen === "advanced") rpc.inspector(profile).then(setInsp).catch(() => {}); }, [screen]);

  const patch = async (c) => { setCfg({ ...(cfg || {}), ...c }); try { await rpc.patch(profile, c); } catch (e) {} loadCfg(profile); };
  const pick = async (p) => { await rpc.setProfile(p); await loadProfiles(); setScreen("home"); };
  const back = () => setScreen("home");
  const go = setScreen;

  let body;
  if (!s) body = h("div", { className: "hint" }, "Loading…");
  else if (screen === "governor") body = h(GovernorPage, { s, back });
  else if (screen === "fg") body = h(FgPage, { back, cfg, patch });
  else if (screen === "scaling") body = h(ScalingPage, { s, back, profile, refresh });
  else if (screen === "hud") body = h(HudPage, { back, s, profile, refresh });
  else if (screen === "profiles") body = h(ProfilesPage, { back, profiles, current: profile, pick });
  else if (screen === "advanced") body = h(AdvancedPage, { back, s, insp, launch });
  else body = h(Home, { s, profile, go, refresh });
  return h("div", { className: "gfg" }, h("style", null, css), body);
}

const MdBolt = () => h("img", { src: LOGO, width: 20, height: 20 });
export default definePlugin(() => ({
  name: "GFG Extreme",
  titleView: h("div", { className: window.DFL.staticClasses.Title }, "GFG · EXTREME"),
  alwaysRender: true,
  content: h(Content, null),
  icon: h(MdBolt, null),
  onDismount() {},
}));
