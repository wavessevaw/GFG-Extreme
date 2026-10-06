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
  schema: callable("get_config_schema"),
  createProfile: callable("create_profile"),
  deleteProfile: callable("delete_profile"),
  renameProfile: callable("rename_profile"),
  journal: callable("get_config_journal"),
  restoreJournal: callable("restore_config_journal_entry"),
  checkInstalled: callable("check_mako_installed"),
  install: callable("install_mako"),
  uninstall: callable("uninstall_mako"),
  fpStatus: callable("check_flatpak_extension_status"),
  fpInstall: callable("install_flatpak_extension"),
  fpUninstall: callable("uninstall_flatpak_extension"),
  fpApps: callable("get_flatpak_apps"),
  fpSet: callable("set_flatpak_app_override"),
  fpRemove: callable("remove_flatpak_app_override"),
  logStart: callable("start_log_recording"),
  logStop: callable("stop_log_recording"),
  logStatus: callable("get_log_recording_status"),
};

// ---------- helpers
const num = (v, d = 1) => (v == null || isNaN(v) ? "–" : Number(v).toFixed(d).replace(/\.0$/, ""));
const MODE_NAME = { oled: "Steam Deck OLED", lcd: "Steam Deck LCD", dock: "Dock", external: "Dock", unknown: "Display" };
const fmtMult = (m) => { const q = Math.round(Number(m) * 4) / 4; return "×" + (Number.isInteger(q) ? q : String(q)); };
const POINT_LABEL = (p) => (p ? (p.multiplier > 1 ? fmtMult(p.multiplier) : "Native") + (p.render_scale_pct < 100 ? " · " + p.render_scale_pct + "%" : "") : "–");

const PAUSED_TEXT = {
  "overlay-restore-failed": "Could not restore settings — retrying.",
  "game-not-running": "Start the game with the GFG launch command.",
  "diagnostics-active-no-events": "No FPS from the engine yet. If the game was started before GFG was turned on, relaunch it.",
  "diagnostics-events-no-fps-samples": "The engine reports no FPS yet. Is frame generation on?",
  "telemetry-stale": "FPS from the engine stopped arriving.",
  "external-tdp-change": "TDP was changed outside GFG — not fighting it.",
  "tdp-write-failed": "Could not write TDP.",
};

// Plain-language state for the hero card. Returns {head, body, tone}
function describe(s) {
  const cap = (s.capability && s.capability.reason) || "";
  if (!s.enabled) return { head: "Ready", body: "Press Run — GFG will pick the target for this screen and manage the engine.", tone: "idle" };
  if (cap === "relaunch-required-for-governor-overlay" || s.reason === "relaunch-required-for-governor-overlay") return { head: "Restart the game", body: "GFG is on. Relaunch the game once so the engine can attach.", tone: "warn" };
  if (s.state === "PAUSED") return { head: "Paused", body: PAUSED_TEXT[s.reason] || "Waiting (" + (s.reason || "unknown") + "). Your saved profile is untouched.", tone: "warn" };
  if (s.state === "OBSERVE_ONLY" && s.reason === "tdp-control-not-writable") return { head: "No TDP access", body: "GFG manages frame generation, but cannot change TDP: the plugin has no write access to the power caps.", tone: "warn" };
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
// Gamepad / Steam Deck buttons only reach `onActivate` (A button) and `onOKButton`; `onClick` is touch/mouse only.
const Focusable = ({ onClick, className, children, style }) => {
  const F = window.DFL && window.DFL.Focusable;
  const fire = onClick ? (e) => onClick(e || {}) : undefined;
  const props = { className: (className || ""), onClick, style, "flow-children": "horizontal" };
  if (F) return h(F, { ...props, onActivate: fire, onOKButton: fire }, children);
  return h("div", { ...props, tabIndex: 0, onKeyDown: onClick ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(e); } : undefined }, children);
};
// Clipboard inside the Steam/CEF page: the async API needs focus + secure context, so fall back to execCommand.
async function copyText(text) {
  try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); return true; } } catch (e) {}
  try {
    const ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta); ta.focus(); ta.select();
    const ok = document.execCommand("copy"); document.body.removeChild(ta); return !!ok;
  } catch (e) { return false; }
}
const LAUNCH_DEFAULT = "/home/deck/.local/bin/gfg %command%";
function LaunchCopy({ launch }) {
  const cmd = launch || LAUNCH_DEFAULT;
  const [state, setState] = useState("");
  const copy = async () => { const ok = await copyText(cmd); setState(ok ? "Copied" : "Select and type it manually"); setTimeout(() => setState(""), 2500); };
  return h("div", null,
    h("div", { className: "card" }, h("div", { style: { fontFamily: "monospace", fontSize: 12, wordBreak: "break-all", userSelect: "all" } }, cmd)),
    h("div", { className: "list" }, h(Row, { icon: "play", title: state || "Copy launch command", sub: "Paste into the game's Steam Properties → Launch Options", value: state ? "" : "Copy", onClick: copy })));
}
function LogRecorder({ profile }) {
  const [st, setSt] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const load = useCallback(async () => { try { setSt((await rpc.logStatus()) || {}); } catch (e) {} }, []);
  useEffect(() => { load(); const t = setInterval(load, 2000); return () => clearInterval(t); }, []);
  const toggle = async () => {
    setBusy(true); setErr("");
    try {
      const r = st.recording ? await rpc.logStop() : await rpc.logStart(profile || "");
      if (r && r.success === false) setErr(r.error || "failed");
      setSt(r || {});
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  };
  const mm = (n) => Math.floor(n / 60) + ":" + String(Math.floor(n % 60)).padStart(2, "0");
  return h("div", null,
    h("div", { className: "list" }, h(Row, {
      icon: st.recording ? "stop" : "play",
      title: st.recording ? "Stop and save log to Desktop" : "Record log",
      sub: st.recording ? "Recording " + mm(st.elapsed_s || 0) + " · play the game, then stop" : "Start, play for a minute or two, stop. A zip lands on the Steam Deck desktop.",
      value: busy ? "…" : "", onClick: busy ? undefined : toggle })),
    st.last_file && !st.recording ? h(Note, { quiet: true }, "Saved: " + st.last_file) : null,
    err ? h(Note, null, "Log error: " + err) : null);
}
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
  h("div", { className: "seg" }, options.map(([v, l]) => h(Focusable, { key: v, className: "segb" + (v === value ? " on" : ""), onClick: () => onChange(v) }, l)));
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
      h("circle", { cx: 88, cy: 88, r, fill: "none", stroke: "#fb0d00", strokeWidth: 9, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: c * (1 - f), style: { transition: "stroke-dashoffset .6s" } })),
    h("div", { className: "num" }, h("div", { className: "big" }, label), h("div", { className: "sub" }, sub)));
}

function Home({ s, profile, go, refresh, inst, reloadInst, launch }) {
  const [busy, setBusy] = useState(false);
  const missing = inst && inst.installed === false;
  const d = describe(s);
  const dev = s.device || {};
  const tel0 = s.telemetry || {};
  const tel = tel0.summary || tel0; // backend sends {snapshot, summary}
  const latest = tel.latest || {};
  const target = s.target_output_fps || dev.target || 60;
  const real = tel.real && tel.real.median, out = tel.output && tel.output.median;
  const mult = latest.effective_multiplier;
  const pw = s.power || {};
  const toggle = async () => {
    if (!missing && !profile) return;
    setBusy(true);
    try { if (missing) { await rpc.install(); await reloadInst(); } else { await rpc.setGovernor(profile, !s.enabled); } } catch (e) {}
    await refresh(); setBusy(false);
  };
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
        h("div", { className: "stat hot" }, h("div", { className: "v" }, mult ? fmtMult(mult) : POINT_LABEL(s.active_point)), h("div", { className: "l" }, "GFG")), h("div", { className: "a" }, "→"),
        h("div", { className: "stat" }, h("div", { className: "v" }, num(out, 0)), h("div", { className: "l" }, "OUTPUT"))) : null,
      s.enabled ? h("div", { className: "effort" }, h("span", null, "GFG EFFORT"),
        h("b", { className: eff ? "lv " + eff : "lv" }, eff ? eff.toUpperCase() : "ASSESSING…")) : null,
      tdp != null ? h("div", { className: "power" }, h("div", { className: "r" }, h("span", null, "TDP NOW"), h("span", null, num(tdp, 0) + " W" + (left ? "  ·  " + left + " left" : ""))),
        h("div", { className: "bar" }, h("div", { style: { width: Math.min(100, (tdp / (pw.saved_w || 15)) * 100) + "%" } }))) : null),
    h(Focusable, { className: "run" + (s.enabled ? " stop" : ""), onClick: busy ? undefined : toggle },
      h(Icon, { d: s.enabled ? ICONS.stop : ICONS.play, size: 18 }), busy ? "WORKING…" : missing ? "INSTALL ENGINE" : s.enabled ? "STOP" : "RUN"),
    h("div", { className: "hint" }, s.enabled ? "Stop returns everything to your saved profile." : missing ? "The GFG engine is not installed yet. One tap installs it." : "Target " + target + " FPS · " + (dev.reason || "picked automatically for this screen")),
    h("div", { className: "list" },
      h(Row, { icon: "bolt", title: "Governor", sub: "What it decided and why", onClick: () => go("governor") }),
      h(Row, { icon: "layers", title: "Frame Generation", sub: "Backend and quality", onClick: () => go("fg") }),
      h(Row, { icon: "scale", title: "Scaling", sub: "Render scale for extra headroom", onClick: () => go("scaling") }),
      h(Row, { icon: "hud", title: "In-game overlay", sub: "FPS, ×N, TDP while playing", onClick: () => go("hud") }),
      h(Row, { icon: "user", title: "Profile", value: profile || "Default", onClick: () => go("profiles") }),
      h(Row, { icon: "cog", title: "Advanced", sub: "Inspector, journal, install", onClick: () => go("advanced") })),
    h("div", { className: "sec" }, "STEP 1 · LAUNCH OPTION"),
    h(LaunchCopy, { launch }),
    h("div", { className: "sec" }, "SOMETHING WRONG? SEND ME A LOG"),
    h(LogRecorder, { profile }));
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
      h("span", null, "Attempts"), h("b", null, lad.attempts != null ? lad.attempts + " / " + (lad.max_attempts || 12) : "–"))),
    dev.reason ? h(Note, { quiet: true }, dev.reason) : null,
    h("div", { className: "sec" }, "RULES"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Multipliers"), h("b", null, "×1 to ×3, steps of 0.25"),
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
    h(Seg, { value: be, options: [["gfg", "GFG Engine"], ["optiscaler", "OptiScaler"], ["native", "In-game"], ["off", "Off"]], onChange: (v) => patch({ fg_backend: v }) }),
    h(Note, { quiet: true }, { gfg: "GFG Engine makes the extra frames. This is the only mode the Governor controls.", optiscaler: "The game's OptiScaler makes the frames. GFG only watches.", native: "The game's own frame generation (DLSS/FSR) is used. GFG only watches.", off: "No frame generation from GFG." }[be]),
    be === "gfg" ? h("div", null,
      h("div", { className: "sec" }, "SAVED MULTIPLIER"),
      h(Seg, { value: String(mult), options: [["2", "×2"], ["3", "×3"]], onChange: (v) => patch({ multiplier: Number(v) }) }),
      h(Note, { quiet: true }, "Used when the Governor is off. With the Governor on, it picks ×1 to ×3 itself and never changes this value.")) :
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
    h(Seg, { value: hud.position, options: [["top-right", "Top right"], ["top-left", "Top left"], ["bottom-left", "Bottom left"]], onChange: (v) => set({ position: v }) }),
    h(Note, { quiet: true }, "Takes effect on next game launch. Not used when another overlay layer (MangoHud/vkBasalt) is chosen for the profile."));
}

function ProfilesPage({ back, profiles, current, pick, reload }) {
  const [sel, setSel] = useState(null);
  const [msg, setMsg] = useState("");
  const [name, setName] = useState("");
  const TF = window.DFL && window.DFL.TextField;
  const act = async (fn) => { setMsg(""); try { const r = await fn(); if (r && r.success === false) setMsg(r.error || "Failed"); } catch (e) { setMsg(String(e)); } await reload(); };
  if (sel) {
    const isDefault = sel === "Default";
    return h(Page, { title: sel, onBack: () => { setSel(null); setName(""); } },
      h("div", { className: "list", style: { marginTop: 0 } },
        h(Row, { title: sel === current ? "Active profile" : "Make active", onClick: () => act(async () => { await pick(sel); }) }),
        h(Row, { title: "Duplicate", sub: "Copy into a new profile", onClick: () => act(() => rpc.createProfile(sel + " copy", sel)) })),
      !isDefault ? h("div", null,
        h("div", { className: "sec" }, "RENAME"),
        TF ? h(TF, { value: name, placeholder: "New name", onChange: (e) => setName(e.target.value) }) : null,
        h("div", { className: "list" },
          h(Row, { title: "Rename", onClick: () => name.trim() && act(async () => { const r = await rpc.renameProfile(sel, name.trim()); if (r && r.success) { setSel(null); setName(""); } return r; }) }),
          h(Row, { title: "Delete profile", sub: "Cannot be undone", onClick: () => act(async () => { const r = await rpc.deleteProfile(sel); if (r && r.success) setSel(null); return r; }) }))) : null,
      msg ? h(Note, null, msg) : null);
  }
  return h(Page, { title: "Profile", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, (profiles || []).map((p) => h(Row, { key: p, title: p, value: p === current ? "Active" : "", onClick: () => setSel(p) }))),
    h("div", { className: "sec" }, "NEW PROFILE"),
    TF ? h(TF, { value: name, placeholder: "Profile name", onChange: (e) => setName(e.target.value) }) : null,
    h("div", { className: "list" }, h(Row, { title: "Create from current", onClick: () => name.trim() && act(async () => { const r = await rpc.createProfile(name.trim(), current); if (r && r.success) setName(""); return r; }) })),
    msg ? h(Note, null, msg) : null);
}

function JournalPage({ back, profile, reloadCfg }) {
  const [entries, setEntries] = useState(null);
  const [msg, setMsg] = useState("");
  const load = useCallback(async () => { try { const r = await rpc.journal(profile || "", 15); setEntries(r && r.success ? r.entries || [] : []); } catch (e) { setEntries([]); } }, [profile]);
  useEffect(() => { load(); }, [load]);
  const restore = async (id) => { setMsg(""); try { const r = await rpc.restoreJournal(id); if (!r || r.success === false) setMsg((r && r.error) || "Restore failed"); else await reloadCfg(); } catch (e) { setMsg(String(e)); } load(); };
  const when = (t) => { try { return new Date((t > 1e12 ? t : t * 1000)).toLocaleString(); } catch (e) { return ""; } };
  return h(Page, { title: "Journal", onBack: back },
    entries == null ? h("div", { className: "hint" }, "Loading…") :
    entries.length === 0 ? h(Note, { quiet: true }, "No changes recorded yet.") :
    h("div", { className: "list", style: { marginTop: 0 } }, entries.map((e) =>
      h(Row, { key: e.id, title: Object.keys(e.changes || {}).slice(0, 3).join(", ") || "change", sub: (e.source ? e.source + " · " : "") + when(e.timestamp || e.time || e.ts), value: "Restore", onClick: () => restore(e.id) }))),
    msg ? h(Note, null, msg) : null);
}

function AdvancedPage({ back, s, insp, launch, go }) {
  const sv = insp && insp.saved, ef = insp && insp.effective, ac = insp && insp.actual;
  const col = (t, o, hot) => h("div", { className: "col" + (hot ? " hot" : "") }, h("h4", null, t),
    ...Object.entries(o || {}).slice(0, 5).map(([k, v]) => h("div", { key: k }, h("span", null, k), String(v))));
  return h(Page, { title: "Advanced", onBack: back },
    h("div", { className: "sec" }, "LAUNCH OPTION"),
    h(LaunchCopy, { launch }),
    h("div", { className: "list" }, h(Row, { icon: "cog", title: "All settings", sub: "Every profile option", onClick: () => go("all") }),
      h(Row, { icon: "cog", title: "Journal", sub: "Undo recent changes", onClick: () => go("journal") }),
      h(Row, { icon: "cog", title: "System", sub: "Engine install, Flatpak access", onClick: () => go("system") })),
    h("div", { className: "sec" }, "INSPECTOR"),
    h("div", { className: "cols" }, col("SAVED", sv), col("EFFECTIVE", ef), col("GOVERNOR", s && s.active_point ? { point: POINT_LABEL(s.active_point) } : {}, true), col("ACTUAL", ac)));
}


// Generic schema-driven editor: every profile setting stays reachable, validated server-side.
function AllSettingsPage({ back, cfg, patch }) {
  const [schema, setSchema] = useState(null);
  const [q, setQ] = useState("");
  useEffect(() => { rpc.schema().then(setSchema).catch(() => {}); }, []);
  if (!schema) return h(Page, { title: "All settings", onBack: back }, h("div", { className: "hint" }, "Loading…"));
  const names = (schema.field_names || []).filter((n) => !q || n.includes(q.toLowerCase())).sort();
  const types = schema.field_types || {}, defs = schema.defaults || {}, desc = schema.descriptions || {};
  const val = (n) => (cfg && cfg[n] != null ? cfg[n] : defs[n]);
  const control = (n) => {
    const t = types[n], v = val(n);
    if (t === "boolean") return h("div", { className: "tog" + (v ? " on" : "") });
    if (t === "integer" || t === "float") {
      const st = t === "integer" ? 1 : 0.1;
      const set = (d) => (e) => { e.stopPropagation && e.stopPropagation(); const nv = Math.round((Number(v) + d) * 1000) / 1000; patch({ [n]: t === "integer" ? Math.round(nv) : nv }); };
      return h("div", { className: "step" }, h(Focusable, { className: "stepb", onClick: set(-st) }, "−"), h("div", { className: "v" }, String(v)), h(Focusable, { className: "stepb", onClick: set(st) }, "+"));
    }
    const TF = window.DFL && window.DFL.TextField;
    return TF ? h(TF, { value: String(v == null ? "" : v), onChange: (e) => patch({ [n]: e.target.value }) }) : h("div", { className: "val" }, String(v == null ? "" : v) || "–");
  };
  return h(Page, { title: "All settings", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, names.map((n) =>
      h(Focusable, { key: n, className: "row", onClick: types[n] === "boolean" ? () => patch({ [n]: !val(n) }) : undefined },
        h("div", { className: "t" }, h("b", { style: { fontSize: 13 } }, n), h("span", { style: { whiteSpace: "normal" } }, desc[n] || "")),
        control(n)))),
    h(Note, { quiet: true }, "Values are validated by the engine. Saved profile only; Governor never writes here."));
}

const RUNTIMES = [["23.08", "installed_23_08"], ["24.08", "installed_24_08"], ["25.08", "installed_25_08"]];
function SystemPage({ back, inst, reloadInst }) {
  const [fp, setFp] = useState(null);
  const [apps, setApps] = useState(null);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const load = useCallback(async () => {
    try { setFp(await rpc.fpStatus()); } catch (e) {}
    try { setApps(await rpc.fpApps()); } catch (e) {}
  }, []);
  useEffect(() => { load(); }, []);
  const run = async (key, fn) => {
    setBusy(key); setMsg("");
    try { const r = await fn(); if (r && r.success === false) setMsg(r.error || r.message || "Failed"); } catch (e) { setMsg(String(e)); }
    await load(); await reloadInst(); setBusy("");
  };
  const engine = inst || {};
  return h(Page, { title: "System", onBack: back },
    h("div", { className: "sec" }, "ENGINE"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Status"), h("b", null, engine.installed ? (engine.engine_update_required ? "Update required" : "Installed") : "Not installed"),
      h("span", null, "Version"), h("b", null, engine.installed_engine_version || "–"),
      h("span", null, "Expected"), h("b", null, engine.expected_engine_version || "–"))),
    engine.host_architecture_supported === false ? h(Note, null, "This host architecture is not supported.") : null,
    h("div", { className: "list" },
      h(Row, { title: engine.installed ? (engine.engine_update_required ? "Update engine" : "Reinstall engine") : "Install engine", value: busy === "install" ? "Working…" : "", onClick: () => busy ? null : run("install", rpc.install) }),
      engine.installed ? h(Row, { title: "Uninstall engine", value: busy === "uninstall" ? "Working…" : "", onClick: () => busy ? null : run("uninstall", rpc.uninstall) }) : null),
    msg ? h(Note, null, msg) : null,
    h("div", { className: "sec" }, "FLATPAK RUNTIMES"),
    h("div", { className: "list", style: { marginTop: 0 } }, RUNTIMES.map(([v, field]) => {
      const on = !!(fp && fp[field]);
      return h(Row, { key: v, title: "Runtime " + v, sub: on ? "Extension installed" : "Not installed", value: busy === v ? "Working…" : (on ? "Remove" : "Install"),
        onClick: () => busy ? null : run(v, () => (on ? rpc.fpUninstall(v) : rpc.fpInstall(v))) });
    })),
    h("div", { className: "sec" }, "FLATPAK APPS"),
    apps && apps.apps && apps.apps.length ? h("div", { className: "list", style: { marginTop: 0 } }, apps.apps.map((a) => {
      const on = a.has_filesystem_override && a.has_wrapper_override && a.has_required_env_override !== false;
      return h(Row, { key: a.app_id, title: a.app_name || a.app_id, sub: on ? "GFG enabled" : "GFG off", value: busy === a.app_id ? "Working…" : (on ? "Disable" : "Enable"),
        onClick: () => busy ? null : run(a.app_id, () => (on ? rpc.fpRemove(a.app_id) : rpc.fpSet(a.app_id))) });
    })) : h(Note, { quiet: true }, apps ? "No Flatpak apps found." : "Loading…"));
}

// ---------- Root
function Content() {
  const [screen, setScreen] = useState("home");
  const [profiles, setProfiles] = useState([]);
  const [profile, setProfileName] = useState("");
  const [cfg, setCfg] = useState(null);
  const [insp, setInsp] = useState(null);
  const [launch, setLaunch] = useState("");
  const [inst, setInst] = useState(null);
  const reloadInst = useCallback(async () => { try { setInst(await rpc.checkInstalled()); } catch (e) {} }, []);
  const [s, refresh] = useGovernor(profile);

  const loadProfiles = useCallback(async () => {
    try { const r = await rpc.profiles(); setProfiles(r.profiles || []); setProfileName(r.current_profile || r.current || ""); } catch (e) {}
  }, []);
  const loadCfg = useCallback(async (p) => { try { const r = await rpc.profileConfig(p); setCfg(r.config || r); } catch (e) {} }, []);
  useEffect(() => { reloadInst(); loadProfiles(); try { rpc.launch().then((r) => setLaunch((r && (r.launch_option || r.option)) || "")); } catch (e) {} }, []);
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
  else if (screen === "profiles") body = h(ProfilesPage, { back, profiles, current: profile, pick, reload: loadProfiles });
  else if (screen === "journal") body = h(JournalPage, { back: () => setScreen("advanced"), profile, reloadCfg: () => loadCfg(profile) });
  else if (screen === "all") body = h(AllSettingsPage, { back: () => setScreen("advanced"), cfg, patch });
  else if (screen === "system") body = h(SystemPage, { back: () => setScreen("advanced"), inst, reloadInst });
  else if (screen === "advanced") body = h(AdvancedPage, { back, s, insp, launch, go });
  else body = h(Home, { s, profile, go, refresh, inst, reloadInst, launch });
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
