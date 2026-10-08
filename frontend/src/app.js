// GFG Extreme UI. No npm deps: Decky provides SP_REACT and DFL as globals; `callable` comes from the shim.
import { css } from "./theme.js";
import { LOGO } from "./logo.js";
const R = window.SP_REACT;
const { useState, useEffect, useRef, useCallback } = R;
const h = (t, p, ...c) => R.createElement(t, p, ...c);

// Every backend call goes through here: a failure is remembered and shown, never silently swallowed.
const rpcErrors = { last: null, listeners: new Set() };
const reportRpcError = (name, e) => { rpcErrors.last = { name, message: String((e && e.message) || e) }; rpcErrors.listeners.forEach((f) => f()); };
const safeCallable = (name) => { const f = callable(name); return async (...a) => { try { const r = await f(...a); if (rpcErrors.last && rpcErrors.last.name === name) { rpcErrors.last = null; rpcErrors.listeners.forEach((g) => g()); } return r; } catch (e) { if (name !== "log_ui_event") reportRpcError(name, e); throw e; } }; };
const rpc = {
  governor: safeCallable("get_governor_status"),
  setGovernor: safeCallable("set_governor_enabled"),
  setHud: safeCallable("set_governor_hud"),
  setScaleReady: safeCallable("set_governor_scale_ready"),
  setFrameOs: safeCallable("set_governor_frame_os"),
  setFrameOsActUnlock: safeCallable("set_governor_frame_os_act_unlock"),
  setMode: safeCallable("set_governor_mode"),
  forgetModel: safeCallable("forget_governor_game_model"),
  modelTarget: safeCallable("get_governor_game_model_target"),
  profiles: safeCallable("get_profiles"),
  setProfile: safeCallable("set_current_profile"),
  profileConfig: safeCallable("get_profile_config"),
  patch: safeCallable("update_profile_config_fields"),
  inspector: safeCallable("get_pipeline_inspector"),
  runtime: safeCallable("get_runtime_status"),
  launch: safeCallable("get_launch_option"),
  schema: safeCallable("get_config_schema"),
  createProfile: safeCallable("create_profile"),
  deleteProfile: safeCallable("delete_profile"),
  renameProfile: safeCallable("rename_profile"),
  journal: safeCallable("get_config_journal"),
  restoreJournal: safeCallable("restore_config_journal_entry"),
  checkInstalled: safeCallable("check_mako_installed"),
  install: safeCallable("install_mako"),
  uninstall: safeCallable("uninstall_mako"),
  fpStatus: safeCallable("check_flatpak_extension_status"),
  fpInstall: safeCallable("install_flatpak_extension"),
  fpUninstall: safeCallable("uninstall_flatpak_extension"),
  fpApps: safeCallable("get_flatpak_apps"),
  fpSet: safeCallable("set_flatpak_app_override"),
  fpRemove: safeCallable("remove_flatpak_app_override"),
  logStart: safeCallable("start_log_recording"),
  logStop: safeCallable("stop_log_recording"),
  logStatus: safeCallable("get_log_recording_status"),
  setupCheck: safeCallable("run_setup_check"),
  logUi: safeCallable("log_ui_event"),
};

// ---------- helpers
const num = (v, d = 1) => (v == null || isNaN(v) ? "–" : Number(v).toFixed(d).replace(/\.0$/, ""));
const MODE_NAME = { oled: "Steam Deck OLED", lcd: "Steam Deck LCD", dock: "Dock", external: "Dock", unknown: "Display" };
const fmtMult = (m) => { const q = Math.round(Number(m) * 4) / 4; return "×" + (Number.isInteger(q) ? q : String(q)); };
const MODE_LABEL = { budget: "Battery", balanced: "Balanced", quality: "Quality" };
// review 1.1.x: a session switched between modes reads "Battery 18m · Balanced 13m", not just its last mode.
const frameOsMinutes = (m) => Object.entries(m || {}).map(([k, v]) => k + " " + num(v, 0) + "m").join(" · ");
const sessionModes = (x) => (x && x.mode === "mixed" && x.modes ? Object.entries(x.modes).map(([m, v]) => (MODE_LABEL[m] || m) + " " + num(v, 0) + "m").join(" · ") : (MODE_LABEL[x && x.mode] || "–"));
const POINT_LABEL = (p) => (p ? (p.multiplier > 1 ? fmtMult(p.multiplier) : "Native") + (p.render_scale_pct < 100 ? " · " + p.render_scale_pct + "%" : "") : "–");

const PAUSED_TEXT = {
  "steam-menu-open": "Steam menu is open: frame generation is paused there. Measuring resumes when you return to the game.",
  "overlay-restore-failed": "Could not restore settings — retrying.",
  "game-not-running": "Start the game with the GFG launch command.",
  "diagnostics-active-no-events": "Waiting for the game to draw frames (loading, intro or menu). If it stays like this in gameplay, relaunch the game once.",
  "diagnostics-events-no-fps-samples": "Waiting for the game to draw frames (loading screen or menu). GFG starts on its own as soon as frames arrive.",
  "telemetry-stale": "FPS from the engine stopped arriving.",
  "external-tdp-change": "TDP was changed outside GFG. In Battery and Balanced modes GFG takes it back after 30 s (at most 3 times).",
  "tdp-write-failed": "Could not write TDP.",
};

const TIER_TEXT = {
  ideal: "Ideal: 11 W or less. GFG keeps watching and reacts if a scene gets heavier.",
  heavy: "Heavy game: needs 12–15 W. GFG keeps watching.",
  emergency: "Last resort: the deepest ratio or above 15 W, because the game keeps missing its frame budget.",
};
const PHASE_TEXT = { settle: "Starting at 10 W", search_down: "Lowering TDP", upgrade: "Fewer generated frames", probe: "Re-checking", locked: "Watching", guard: "Protecting" };
const MODE_TEXT = {
  balanced: "Balanced: starts at about 45 real FPS and 12 W, never goes below 30 real FPS and never above your Deck's normal power range. A bit more battery for a steadier picture.",
  budget: "Battery: lowest TDP first, 9–11 W ideal. Real FPS stays at 24 or more; a deeper ratio (down to 20 real) and the highest watts your Deck allows only as a last resort.",
  quality: "Quality: fewest generated frames first, then lowers TDP. Uses more battery.",
};
// The ceilings come from the device (a stock Deck stops at 15 W).
const budgetRule = (b) => {
  const lim = (b && b.limits_w) || {};
  if (lim.normal == null) return "9–11 W ideal, then what your Deck allows";
  const last = lim.emergency > lim.normal ? ", " + num(lim.emergency, 0) + " W last resort" : " (this Deck's maximum)";
  return "9–11 W ideal, " + num(lim.normal, 0) + " W max" + last;
};

// Plain-language state for the hero card. Returns {head, body, tone}
function describe(s) {
  const cap = (s.capability && s.capability.reason) || "";
  if (!s.enabled) return { head: "Ready", body: "Press Run — GFG will pick the target for this screen and manage the engine.", tone: "idle" };
  if (cap === "relaunch-required-for-governor-overlay" || s.reason === "relaunch-required-for-governor-overlay") return { head: "Restart the game once", body: "This game was started without the GFG launch command, or before this GFG version. Relaunch it once; after that GFG can be turned on while the game runs.", tone: "warn" };
  if (s.state === "PAUSED" && s.reason === "steam-menu-open") return { head: "Steam menu open", body: PAUSED_TEXT[s.reason], tone: "idle" };
  if (s.state === "PAUSED") return { head: "Paused", body: PAUSED_TEXT[s.reason] || "Waiting (" + (s.reason || "unknown") + "). Your saved profile is untouched.", tone: "warn" };
  if (s.state === "OBSERVE_ONLY" && s.reason === "tdp-control-not-writable") return { head: "No TDP access", body: "GFG manages frame generation, but cannot change TDP: the plugin has no write access to the power caps.", tone: "warn" };
  if (s.state === "OBSERVE_ONLY") return { head: "Observing", body: "Another backend owns the pipeline. GFG only watches.", tone: "idle" };
  if (s.state === "PROBE" || s.state === "PLAN") return { head: "Measuring", body: "Learning how the game runs. Nothing is changed yet.", tone: "busy" };
  if (s.state === "APPLY") return { head: "Testing " + (s.request && s.request.point ? fmtMult(String(s.request.point).split("x")[1] || 1) : ""), body: "Checking the result on the engine's own data before keeping it (a few seconds).", tone: "busy" };
  const b = s.budget;
  const fb = s.power_feedback || {};
  if (b && b.cap_ignored) return { head: "TDP limit overridden", body: "The APU draws " + num(fb.draw_w, 1) + " W while GFG's limit is " + num(fb.cap_w, 0) + " W: another tool (ryzenadj, PowerTools…) sets the real limit. GFG keeps a deep ratio instead of spending power.", tone: "warn" };
  if (b && s.state === "OPTIMIZE_POWER") return { head: "Saving battery", body: b.probe === "up" ? "Trying fewer generated frames at " + num(b.tdp_w, 0) + " W." : "Looking for the lowest TDP that holds the target (now " + num(b.tdp_w, 0) + " W).", tone: "ok" };
  if (b && s.state === "LOCKED" && b.thermal_deferred && b.heat_limited) return { head: "Cooling · " + num(b.tdp_w, 0) + " W", body: "The Deck is " + (b.thermal === "hot" ? "hot" : b.thermal === "heating" ? "heating up" : "cooling down") + ": GFG keeps the current ratio and only tries lower watts. Fewer generated frames are tried again once it cools.", tone: "warn" };
  if (b && s.state === "LOCKED") return { head: "Adapting · " + num(b.tdp_w, 0) + " W", body: (b.warm_started ? "Started from what worked last time. " : "") + (TIER_TEXT[b.tier] || "Checks FPS every second: adds watts at once when the game falls short, tries lower watts every 45 s."), tone: b.tier === "emergency" ? "warn" : "ok" };
  if (b && s.state === "GUARD") return { head: "Protecting", body: "A scene got heavier: more generated frames first, then more watts.", tone: "warn" };
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
  const copy = async () => { const ok = await copyText(cmd); rpc.logUi("copy-launch-command", { ok, cmd }).catch(() => {}); setState(ok ? "Copied" : "Select and type it manually"); setTimeout(() => setState(""), 2500); };
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
    !st.recording && (st.findings || []).length ? h("div", { className: "card" }, h("div", { className: "sec" }, "WHAT THE LOG SHOWS"), ...(st.findings || []).map((f, i) => h("div", { key: i, className: "hint", style: { textAlign: "left" } }, "• " + f))) : null,
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
  const busy = useRef(false);
  // One status call at a time: a slow backend must not pile up requests every 1.5 s.
  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try { const r = await Promise.race([rpc.governor(profile || ""), new Promise((_, rej) => setTimeout(() => rej(new Error("status call timed out")), 10000))]); if (alive.current) setS(r); } catch (e) {}
    busy.current = false;
  }, [profile]);
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

// Frame OS benefit rings: colour by effectiveness, red when Frame OS made it worse.
const ringHue = (v, max) => (v < 0 ? 0 : 25 + 115 * Math.min(1, Math.abs(v) / max));
function MiniRing({ value, max, text, label, live, estimate, fixed }) {
  const r = 26, w = 4, size = 2 * (r + w), c = 2 * Math.PI * r;
  const has = value != null;
  const f = has ? Math.min(1, Math.abs(value) / max) : 0;
  const color = fixed || (estimate ? "#5c5c66" : "hsl(" + ringHue(value || 0, max) + " 80% 52% / " + (live ? 1 : 0.38) + ")");
  const glow = live && has && !estimate && !fixed;
  return h("div", { className: "mini" + (glow ? " live" : "") },
    h("div", { className: "mring", style: { width: size, height: size } },
      h("svg", { viewBox: "0 0 " + size + " " + size, width: size, height: size },
        h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#26262d", strokeWidth: w }),
        // Halo as a wider faint arc inside the SVG: a CSS drop-shadow is clipped to a square in Steam's browser.
        glow ? h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: color, strokeOpacity: 0.22, strokeWidth: w + 4, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: c * (1 - f), style: { transition: "stroke-dashoffset .6s" } }) : null,
        has ? h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: color, strokeWidth: w, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: c * (1 - f), style: { transition: "stroke-dashoffset .6s" } }) : null),
      h("div", { className: "mnum" + (estimate || !has ? " dim" : "") }, has ? text : "—")),
    h("div", { className: "mlab" }, label));
}

function FrameOsCard({ fo }) {
  const b = fo.benefit;
  if (!fo.enabled || !b) return null;
  const est = !!b.estimate;
  const level = (fo.decision || {}).level;
  const pct = (v, sign) => (v == null ? "" : (sign && v > 0 ? sign : v < 0 && !sign ? "−" : "") + Math.abs(Math.round(v)) + "%");
  const resp = b.response_pct, frames = b.frames_pct, energy = b.energy_pct;
  return h("div", { className: "card fos" },
    h("div", { className: "fos-head" }, h("span", null, "FRAME OS"),
      h("span", { className: "pill " + (est ? "would" : level || "") }, est ? "ESTIMATE" : (level || "").toUpperCase())),
    h("div", { className: "rings" },
      h(MiniRing, { value: resp, max: 50, text: resp == null ? "" : (resp >= 0 ? "−" : "+") + Math.abs(Math.round(resp)) + "%", label: "Response", live: level !== "rest", estimate: est }),
      h(MiniRing, { value: frames, max: 50, text: frames == null ? "" : (frames >= 0 ? "+" : "−") + Math.abs(Math.round(frames)) + "%", label: "Frames", live: level === "boost", estimate: est }),
      h(MiniRing, { value: energy, max: 30, text: energy == null ? "" : pct(energy), label: "Energy", live: level === "rest", estimate: est })));
}

// Last session as rings: averages for the whole game session, benefit rings when Frame OS ran.
function SessionRings({ ls, target }) {
  const b = ls.frame_os_benefit;
  const signed = (v, good) => (v == null ? "" : (v >= 0 ? good : good === "+" ? "−" : "+") + Math.abs(Math.round(v)) + "%");
  const limit = ls.reference_w || 15;
  return h("div", null,
    h("div", { className: "rings" },
      h(MiniRing, { value: ls.avg_output_fps, max: target, text: num(ls.avg_output_fps, 0), label: "FPS avg", fixed: "#fb0d00" }),
      h(MiniRing, { value: ls.avg_real_fps, max: ls.avg_output_fps || target, text: num(ls.avg_real_fps, 0), label: "Real avg", fixed: "#f5f5f7" }),
      h(MiniRing, { value: ls.avg_tdp_w, max: limit, text: ls.avg_tdp_w != null ? num(ls.avg_tdp_w, 0) + "W" : "", label: "TDP avg", fixed: "#f5f5f7" })),
    b ? h("div", { className: "rings", style: { marginTop: 10 } },
      h(MiniRing, { value: b.response, max: 50, text: signed(b.response, "−"), label: "Response", live: true, estimate: b.estimate }),
      h(MiniRing, { value: b.frames, max: 50, text: signed(b.frames, "+"), label: "Frames", live: true, estimate: b.estimate }),
      h(MiniRing, { value: b.energy, max: 30, text: b.energy == null ? "" : (b.energy < 0 ? "−" : "") + Math.abs(Math.round(b.energy)) + "%", label: "Energy", live: true, estimate: b.estimate })) : null);
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
  const tdp = pw.observed_tdp_w != null ? pw.observed_tdp_w : pw.current_tdp_w;
  const eff = s.effort && s.effort.level;
  const effWhy = eff && s.effort.reason;
  const mins = s.battery && s.battery.minutes_left;
  const cap0 = (s.capability && s.capability.reason) || "";
  const needsLaunch = s.enabled && (cap0 === "relaunch-required-for-governor-overlay" || s.reason === "relaunch-required-for-governor-overlay" || s.reason === "game-not-running" || s.reason === "diagnostics-active-no-events");
  const [problems, setProblems] = useState([]);
  const troubledNow = s.state === "PAUSED" || (s.enabled && s.reason === "target-not-proven-viable");
  const troubled = troubledNow;
  // Trouble: look for a concrete cause once (not on every poll) and say what to do about it.
  useEffect(() => {
    if (!troubledNow) { setProblems([]); return; }
    let alive = true;
    rpc.setupCheck(profile || "").then((r) => { if (alive && r && r.checks) setProblems(r.checks.filter((c) => !c.ok && c.advice).slice(0, 2)); }).catch(() => {});
    return () => { alive = false; };
  }, [troubledNow, s.reason]);
  const dg = s.diagnosis || {}, sn = s.sensors || {};
  const health = s.enabled ? [dg.bottleneck && dg.bottleneck !== "unknown" && dg.bottleneck !== "none" ? { gpu: "GPU-bound", cpu: "CPU-bound", power: "Power-limited" }[dg.bottleneck] : null,
    sn.temp_c != null ? Math.round(sn.temp_c) + " °C" + (dg.thermal === "hot" ? " · hot" : dg.thermal === "heating" ? " · heating up" : "") : null,
    dg.smoothness === "stuttering" ? "stutter detected" : dg.smoothness === "smooth" ? "smooth" : null].filter(Boolean).join(" · ") : "";
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
        h("b", { className: eff ? "lv " + eff : "lv" }, eff ? eff.toUpperCase() : "ASSESSING…", effWhy ? h("span", { className: "why" }, " · " + effWhy) : null)) : null,
      tdp != null ? h("div", { className: "power" }, h("div", { className: "r" }, h("span", null, "TDP NOW"), h("span", null, num(tdp, 0) + " W" + (left ? "  ·  " + left + " left" : ""))),
        pw.owned && pw.initial_tdp_w && pw.initial_tdp_w - tdp >= 1 ? h("div", { className: "r" }, h("span", null, "SAVING"), h("span", null, num(pw.initial_tdp_w - tdp, 0) + " W under your " + num(pw.initial_tdp_w, 0) + " W limit")) : null,
        h("div", { className: "bar" }, h("div", { style: { width: Math.min(100, (tdp / (pw.initial_tdp_w || pw.maximum_tdp_w || 15)) * 100) + "%" } }))) : null),
    s.enabled && s.frame_os && s.frame_os.mode && s.frame_os.mode !== "off" ? h(FrameOsCard, { fo: s.frame_os }) : null,
    h(Focusable, { className: "run" + (s.enabled ? " stop" : ""), onClick: busy ? undefined : toggle },
      h(Icon, { d: s.enabled ? ICONS.stop : ICONS.play, size: 18 }), busy ? "WORKING…" : missing ? "INSTALL ENGINE" : s.enabled ? "STOP" : "RUN"),
    h("div", { className: "hint" }, s.enabled ? "Stop returns everything to your saved profile." : missing ? "The GFG engine is not installed yet. One tap installs it." : "Target " + target + " FPS · " + (dev.reason || "picked automatically for this screen")),
    h("div", { className: "sec" }, "MODE"),
    h(Seg, { value: s.mode || "budget", options: [["budget", "Battery"], ["balanced", "Balanced"], ["quality", "Quality"]], onChange: async (v) => { try { await rpc.setMode(profile, v); } catch (e) {} refresh(); } }),
    h(Note, { quiet: true }, MODE_TEXT[s.mode || "budget"]),
    health ? h("div", { className: "hint" }, health) : null,
    !s.session && s.last_session ? h("div", { className: "card" }, h("div", { className: "sec" }, "LAST SESSION"),
      h(SessionRings, { ls: s.last_session, target }),
      h("div", { className: "kv", style: { marginTop: 12 } },
        h("span", null, "Played"), h("b", null, num(s.last_session.minutes, 0) + " min"),
        s.last_session.mode === "mixed" ? h("span", null, "Modes") : null, s.last_session.mode === "mixed" ? h("b", null, sessionModes(s.last_session)) : null,
        s.last_session.frame_os ? h("span", null, "Frame OS") : null, s.last_session.frame_os ? h("b", null, frameOsMinutes(s.last_session.frame_os)) : null,
        s.last_session.reference_w ? h("span", null, "Your limit") : null, s.last_session.reference_w ? h("b", null, num(s.last_session.reference_w, 0) + " W") : null,
        s.last_session.saved_w > 0 ? h("span", null, "Saved") : null, s.last_session.saved_w > 0 ? h("b", null, "~" + num(s.last_session.saved_w, 1) + " W under your limit on average") : null,
        s.last_session.saved_wh > 0 ? h("span", null, "Energy saved") : null, s.last_session.saved_wh > 0 ? h("b", null, "~" + num(s.last_session.saved_wh, 1) + " Wh measured" + (s.last_session.battery_minutes_gained > 0 ? " · ~" + s.last_session.battery_minutes_gained + " min more battery" : "")) : null,
        s.last_session.max_temp_c ? h("span", null, "Hottest") : null, s.last_session.max_temp_c ? h("b", null, num(s.last_session.max_temp_c, 0) + " °C" + (s.last_session.hot_pct ? " · warm " + s.last_session.hot_pct + "% of the time" : "")) : null,
        s.last_session.stutter_pct ? h("span", null, "Stutter") : null, s.last_session.stutter_pct ? h("b", null, s.last_session.stutter_pct + "% of the time") : null)) : null,
    needsLaunch ? h("div", null, h("div", { className: "sec" }, "START THE GAME WITH THIS LAUNCH OPTION"), h(LaunchCopy, { launch })) : null,
    troubled && problems.length ? h("div", { className: "card" }, h("div", { className: "sec" }, "LIKELY CAUSE"), ...problems.map((c, i) => h("div", { key: i, className: "hint", style: { textAlign: "left" } }, "• " + c.advice))) : null,
    troubled ? h("div", { className: "list" }, h(Row, { icon: "play", title: problems.length ? "Check setup" : "Something wrong? Record a log", sub: "Settings → Diagnostics", onClick: () => go(problems.length ? "setup" : "advanced") })) : null,
    h("div", { className: "list" },
      h(Row, { icon: "bolt", title: "Details", sub: "What GFG does and why", onClick: () => go("governor") }),
      h(Row, { icon: "cog", title: "Settings", sub: "Overlay, profile, diagnostics", onClick: () => go("settings") })));
}

// ---------- Sub screens
function GovernorPage({ s, back, profile, refresh }) {
  const dev = s.device || {}, req = s.request, pt = s.active_point, lad = s.ladder || {}, b = s.budget;
  const mode = s.mode || "budget";
  return h(Page, { title: "Details", onBack: back },
    b ? h("div", { className: "sec" }, "BATTERY") : null,
    b ? h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "TDP target"), h("b", null, b.tdp_w != null ? num(b.tdp_w, 0) + " W" : "no TDP access"),
      h("span", null, "Budget"), h("b", null, { ideal: "Ideal (≤ 11 W)", heavy: "Heavy (12–15 W)", emergency: "Last resort", unknown: "–" }[b.tier] || "–"),
      h("span", null, "Point"), h("b", null, POINT_LABEL(pt)),
      h("span", null, "Step"), h("b", null, PHASE_TEXT[b.phase] || b.phase),
      h("span", null, "Start"), h("b", null, b.warm_started ? "Remembered from last session" : "Searched from scratch"),
      b.verifying ? h("span", null, "Verifying") : null, b.verifying ? h("b", null, fmtMult(String(b.verifying).split("x")[1] || 1) + " — the engine chose it, checking it holds") : null,
      h("span", null, "Lower resolution"), h("b", null, b.scale_capable ? "On · 90% / 80% before more watts" : "Off · Settings → Scaling → Scale-ready launch, then restart the game"),
      b.thermal_deferred ? h("span", null, "Heat") : null, b.thermal_deferred ? h("b", null, b.heat_limited ? "Quality step on hold until the APU cools" : "Cooled — quality step will be retried") : null,
      b.current_max_multiplier ? h("span", null, "Engine allows") : null, b.current_max_multiplier ? h("b", null, "up to " + fmtMult(b.current_max_multiplier)) : null,
      Object.keys(b.known_failures || {}).length ? h("span", null, "Recently failed") : null,
      Object.keys(b.known_failures || {}).length ? h("b", null, Object.entries(b.known_failures).slice(0, 3).map(([k, w]) => fmtMult(k.split("x")[1] || 1) + " at ≤" + num(w, 0) + " W").join(", ")) : null)) : null,
    h("div", { className: "sec" }, "DECISION"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "State"), h("b", null, describe(s).head),
      h("span", null, "Device"), h("b", null, MODE_NAME[dev.mode] || "–"),
      h("span", null, "Target"), h("b", null, (s.target_output_fps || dev.target || "–") + " FPS"),
      h("span", null, "Active point"), h("b", null, POINT_LABEL(pt) + (s.active_point_mode ? " (" + s.active_point_mode + ")" : "")),
      h("span", null, "Testing"), h("b", null, req ? POINT_LABEL(req.point) : "–"),
      ...(b ? [] : [h("span", null, "Attempts"), h("b", null, lad.attempts != null ? lad.attempts + " / " + (lad.max_attempts || 12) : "–")]))),
    dev.reason ? h(Note, { quiet: true }, dev.reason) : null,
    h("div", { className: "sec" }, "HEALTH"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Limits the game"), h("b", null, { gpu: "GPU", cpu: "CPU", power: "TDP cap", none: "Nothing", unknown: "–" }[(s.diagnosis || {}).bottleneck || "unknown"]),
      h("span", null, "Temperature"), h("b", null, (s.sensors || {}).temp_c != null ? Math.round(s.sensors.temp_c) + " °C" + (s.sensors.temp_slope_c_per_min != null ? " (" + (s.sensors.temp_slope_c_per_min > 0 ? "+" : "") + num(s.sensors.temp_slope_c_per_min, 1) + "/min)" : "") : "–"),
      h("span", null, "GPU / CPU load"), h("b", null, ((s.sensors || {}).gpu_busy_pct != null ? num(s.sensors.gpu_busy_pct, 0) + "%" : "–") + " / " + ((s.sensors || {}).cpu_top_core_pct != null ? num(s.sensors.cpu_top_core_pct, 0) + "% top core" : "–")),
      h("span", null, "Frametime p95 / p99"), h("b", null, (((s.telemetry || {}).summary || {}).frametime || {}).p95_ms != null ? num(s.telemetry.summary.frametime.p95_ms, 1) + " / " + num(s.telemetry.summary.frametime.p99_ms, 1) + " ms" : "–"),
      h("span", null, "Battery draw"), h("b", null, (s.sensors || {}).battery_discharge_w != null ? num(s.sensors.battery_discharge_w, 1) + " W" : "–"),
      h("span", null, "Fan"), h("b", null, (s.sensors || {}).fan_rpm != null ? num(s.sensors.fan_rpm, 0) + " rpm" : "–"))),
    h("div", { className: "sec" }, "RULES"),
    h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Multipliers"), h("b", null, mode === "balanced" ? "×1 to ×3, never below 30 real FPS" : mode === "budget" ? "×1 to ×3.75, deeper only as a last resort" : "×1 to ×3, steps of 0.25"),
      h("span", null, "Saved profile"), h("b", null, "never modified"),
      h("span", null, "TDP"), h("b", null, mode === "balanced" ? "12–13 W start, never above the normal range" : mode === "budget" ? budgetRule(b) : "never above your own"),
      mode !== "quality" ? h("span", null, "Reacts") : null,
      mode !== "quality" ? h("b", null, "up within ~2 s, down in 1 W steps") : null)),
    (s.session_history || []).length ? h("div", { className: "sec" }, "RECENT SESSIONS") : null,
    (s.session_history || []).length ? h("div", { className: "card" }, h("div", { className: "kv" },
      ...(s.session_history || []).slice(0, 5).flatMap((x, i) => [
        h("span", { key: "k" + i }, num(x.minutes, 0) + " min · " + sessionModes(x)),
        h("b", { key: "v" + i }, num(x.avg_output_fps, 0) + " FPS · " + (x.avg_tdp_w != null ? num(x.avg_tdp_w, 1) + " W" : "–") + (x.max_temp_c ? " · " + num(x.max_temp_c, 0) + " °C" : ""))]))) : null,
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
      h(Note, { quiet: true }, "Used when the Governor is off. With the Governor on, it picks ×1 to ×3.75 itself (×4 only as a last resort) and never changes this value.")) :
      h(Note, { quiet: true }, "External backend: GFG observes only and does not change it."));
}

function ScalingPage({ s, back, profile, refresh }) {
  const ready = !!s.scale_ready;
  return h(Page, { title: "Scaling", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } },
      h(Toggle, { on: ready, title: "Scale-ready launch", sub: "Provision the Scaling Engine at launch so Governor can lower render scale live without relaunching. Applies from the next game start.", onChange: async (v) => { try { await rpc.setScaleReady(profile, v); } catch (e) {} refresh(); } })),
    h(Note, { quiet: true }, "Governor only uses 90% or 80% render scale, and only after FG alone is not enough."));
}

function HudPage({ back, s, profile, refresh }) {
  const hud = s.hud || { enabled: false, preset: "standard", position: "top-right" };
  const set = async (c) => { try { await rpc.setHud(profile, c.enabled, c.preset, c.position, c.style); } catch (e) {} refresh(); };
  const style = hud.style || "rings";
  return h(Page, { title: "In-game overlay", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, h(Toggle, { on: hud.enabled, title: "Show overlay in game", sub: "FPS, TDP and Frame OS payoff — as rings or a text line.", onChange: (v) => set({ enabled: v }) })),
    h("div", { className: "sec" }, "STYLE"),
    h(Seg, { value: style, options: [["rings", "Rings"], ["text", "Text"]], onChange: (v) => set({ style: v }) }),
    style === "rings" ? h(Note, { quiet: true }, "Rings show 20-second averages and refresh every 20 s. They need one game restart after you first pick them; until then the text line is shown.") : null,
    h("div", { className: "sec" }, "DETAIL"),
    h(Seg, { value: hud.preset, options: [["minimal", "Minimal"], ["standard", "Standard"], ["detailed", "Detailed"]], onChange: (v) => set({ preset: v }) }),
    h("div", { className: "sec" }, "POSITION"),
    h(Seg, { value: hud.position, options: [["top-right", "Top right"], ["top-left", "Top left"], ["bottom-left", "Bottom left"], ["bottom-right", "Bottom right"]], onChange: (v) => set({ position: v }) }),
    hud.layer_available === false ? h(Note, null, "MangoHud layer not found on this system, so the overlay cannot appear. Record a log and send it.") : null,
    h(Note, { quiet: true }, "Turns on and off while the game runs. Several quick changes are applied together, at most every 5 s. Works for games started with the GFG launch command (a game started before this version needs one relaunch). Works together with shader effects (vkBasalt); not used when the profile already loads its own MangoHud."));
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

function SettingsPage({ back, go, profile, s }) {
  return h(Page, { title: "Settings", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } },
      h(Row, { icon: "hud", title: "In-game overlay", sub: "FPS, ×N, TDP while playing", onClick: () => go("hud") }),
      h(Row, { icon: "user", title: "Profile", value: profile || "Default", onClick: () => go("profiles") }),
      h(Row, { icon: "play", title: "Launch command", sub: "Copy it into the game's Steam launch options", onClick: () => go("launch") }),
      h(Row, { icon: "layers", title: "Frame generation backend", sub: "GFG Engine, OptiScaler, in-game", onClick: () => go("fg") }),
      h(Row, { icon: "scale", title: "Scaling", sub: "Render scale for extra headroom", onClick: () => go("scaling") })),
    h("div", { className: "sec" }, "SUPPORT"),
    h("div", { className: "list" },
      h(Row, { icon: "cog", title: "Diagnostics", sub: "Record a log, inspector, journal", onClick: () => go("advanced") }),
      h(Row, { icon: "cog", title: "System", sub: "Engine install, Flatpak access", onClick: () => go("system") }),
      h(Row, { icon: "cog", title: "All settings", sub: "Every profile option", onClick: () => go("all") })),
    h("div", { className: "hint" }, "GFG Extreme " + ((s && s.version) || "")));
}

function SetupCheckPage({ back, profile }) {
  const [r, setR] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(async () => { setBusy(true); try { setR(await rpc.setupCheck(profile || "")); } catch (e) { setR({ success: false, checks: [], failed: 0, total: 0 }); } setBusy(false); }, [profile]);
  useEffect(() => { run(); }, [run]);
  const bad = r ? (r.checks || []).filter((c) => !c.ok) : [];
  const good = r ? (r.checks || []).filter((c) => c.ok) : [];
  return h(Page, { title: "Check setup", onBack: back },
    !r ? h("div", { className: "hint" }, "Checking…") :
    r.success === false ? h(Note, null, "The check could not run. Record a log instead.") :
    h("div", null,
      h(Note, { quiet: bad.length === 0 }, bad.length === 0 ? "Everything GFG needs is in place (" + r.total + " checks)." : bad.length + " of " + r.total + " checks failed."),
      bad.length ? h("div", { className: "sec" }, "NEEDS ATTENTION") : null,
      ...bad.map((c, i) => h("div", { key: "b" + i, className: "card" }, h("b", null, "✗ " + c.check), c.advice ? h("div", { className: "hint", style: { textAlign: "left" } }, c.advice) : null, c.detail ? h("div", { className: "hint", style: { textAlign: "left", fontFamily: "monospace", wordBreak: "break-all" } }, c.detail) : null)),
      good.length ? h("div", { className: "sec" }, "OK") : null,
      good.length ? h("div", { className: "card" }, ...good.map((c, i) => h("div", { key: "g" + i, className: "hint", style: { textAlign: "left" } }, "✓ " + c.check))) : null),
    h("div", { className: "list" }, h(Row, { icon: "play", title: busy ? "Checking…" : "Check again", onClick: busy ? undefined : run })));
}

function LaunchPage({ back, launch }) {
  return h(Page, { title: "Launch command", onBack: back }, h(LaunchCopy, { launch }),
    h(Note, { quiet: true }, "Steam → the game → Properties → Launch Options. Games started this way are the ones GFG can manage."));
}

function AdvancedPage({ back, s, insp, launch, go, profile }) {
  const sv = insp && insp.saved, ef = insp && insp.effective, ac = insp && insp.actual;
  const col = (t, o, hot) => h("div", { className: "col" + (hot ? " hot" : "") }, h("h4", null, t),
    ...Object.entries(o || {}).slice(0, 5).map(([k, v]) => h("div", { key: k }, h("span", null, k), String(v))));
  return h(Page, { title: "Diagnostics", onBack: () => go("settings") },
    h("div", { className: "list" }, h(Row, { icon: "cog", title: "Check setup", sub: "Is the engine, launcher, overlay and TDP access in place?", onClick: () => go("setup") })),
    h("div", { className: "sec" }, "RECORD A LOG"),
    h(LogRecorder, { profile }),
    h("div", { className: "list" }, h(Row, { icon: "cog", title: "Journal", sub: "Undo recent changes", onClick: () => go("journal") })),
    h(ForgetModel, { profile }),
    h(FrameOsPanel, { s, profile }),
    h("div", { className: "sec" }, "INSPECTOR"),
    h("div", { className: "cols" }, col("SAVED", sv), col("EFFECTIVE", ef), col("GOVERNOR", s && s.active_point ? { point: POINT_LABEL(s.active_point) } : {}, true), col("ACTUAL", ac)));
}


// review 1.1.x: a stale memory (new driver, game patch) could only be outlived, never reset.  Two taps,
// and the game is named before the reset (a shared profile used to reset its last game silently).
const steamName = (id) => { try { const o = id && window.appStore && window.appStore.GetAppOverviewByAppID(Number(id)); return (o && o.display_name) || ""; } catch (e) { return ""; } };
const gameLabel = (g) => (g.name || steamName(g.app_id) || (g.app_id ? "Steam app " + g.app_id : "games on profile " + g.profile));
function ForgetModel({ profile }) {
  const [step, setStep] = useState("idle"); // idle -> confirm -> done
  const [msg, setMsg] = useState("");
  const [target, setTarget] = useState(undefined); // undefined: loading, null: no game identified
  useEffect(() => { let on = true; setTarget(undefined); rpc.modelTarget(profile || "").then((r) => { if (on) setTarget((r && r.target) || null); }).catch(() => { if (on) setTarget(null); }); return () => { on = false; }; }, [profile, step === "done"]);
  const forget = async () => {
    setStep("busy");
    try { const r = await rpc.forgetModel(profile || ""); setMsg(r && r.success ? (r.forgotten ? "Forgotten. The next start searches from scratch." : "Nothing was learned for this game yet.") : r && r.error === "no-game-identified" ? "GFG cannot tell which game to reset. Play the game under this profile once, then try again." : "Could not reset: " + ((r && r.error) || "unknown error")); } catch (e) { setMsg("Could not reset."); }
    setStep("done");
  };
  const name = target ? gameLabel(target) : "";
  return h("div", null,
    h("div", { className: "list" }, step === "confirm" && target
      ? h(Row, { icon: "stop", title: "Tap again to forget", sub: "Watts, points and failures it remembered for " + name, onClick: forget })
      : h(Row, { icon: "cog", title: "Reset what GFG learned for " + (target ? name : "this game"),
        sub: step === "busy" ? "Working…" : target === undefined ? "Checking…" : target ? "Starts the next search from scratch" : "No game identified yet: play one under this profile first",
        onClick: step === "busy" || !target ? undefined : () => { setMsg(""); setStep("confirm"); } })),
    step === "confirm" && target ? h(Note, { quiet: true }, "This cannot be undone. Your saved profile is not touched.") : null,
    step === "done" && msg ? h(Note, { quiet: true }, msg) : null);
}

// GFG Frame OS (development): observe/shadow only measure; act changes frame timing and watts.
function FrameOsPanel({ s, profile }) {
  const fo = (s && s.frame_os) || {};
  const [mode, setMode] = useState(fo.mode || "off");
  useEffect(() => { if (fo.mode) setMode(fo.mode); }, [fo.mode]);
  const t = fo.telemetry || {};
  const d = fo.decision || {};
  const [unlock, setUnlock] = useState("idle"); // idle -> confirm -> busy
  const [unlocked, setUnlocked] = useState(!!fo.act_unlocked);
  useEffect(() => { setUnlocked(!!fo.act_unlocked); }, [fo.act_unlocked]);
  const toggleAct = async (enabled) => {
    setUnlock("busy");
    try { const r = await rpc.setFrameOsActUnlock(enabled); if (r && r.success) setUnlocked(!!r.act_unlocked); } catch (e) {}
    if (!enabled && mode === "act") setMode("observe");
    setUnlock("idle");
  };
  return h("div", null,
    h("div", { className: "sec" }, "FRAME OS (EXPERIMENTAL)"),
    h(Seg, { value: mode, options: [["off", "Off"], ["observe", "Observe"], ["shadow", "Shadow"]].concat(unlocked ? [["act", "Act"]] : []),
             onChange: async (v) => { const prev = mode; setMode(v); let ok = false; try { const r = await rpc.setFrameOs(profile, v); ok = !!(r && r.success); } catch (e) {} if (!ok) setMode(prev); } }),
    h("div", { className: "list" }, unlocked
      ? h(Row, { icon: "stop", title: "Lock Act", sub: "Back to measuring only", onClick: unlock === "busy" ? undefined : () => toggleAct(false) })
      : unlock === "confirm"
        ? h(Row, { icon: "stop", title: "Tap again to unlock Act", sub: "Act changes frame timing and power in the game", onClick: () => toggleAct(true) })
        : h(Row, { icon: "cog", title: "Unlock Act (experimental)", sub: "More real frames in action, savings in pauses", onClick: unlock === "busy" ? undefined : () => setUnlock("confirm") })),
    h(Note, { quiet: true }, unlocked
      ? "Observe and Shadow only measure. Act changes frame timing and power. Applies from the next game start."
      : "Frame OS is diagnostic only until Deck validation. Applies from the next game start."),
    mode !== "off" && fo.enabled && fo.telemetry && !fo.telemetry.live && fo.layer_installed !== false
      ? h(Note, null, "Frame OS is not active in this game yet: it loads at game start. Restart the game.")
      : null,
    mode !== "off" && fo.layer_installed === false
      ? h(Note, null, fo.layer_error ? "Frame OS layer not installed: " + fo.layer_error + "." : "Frame OS layer not installed yet.")
      : null,
    fo.enabled ? h("div", { className: "card" }, h("div", { className: "kv" },
      h("span", null, "Decision"), h("b", null, (d.level || "–") + (fo.acting ? "" : " (would)") + " · " + num(d.real_hz, 0) + " real"),
      h("span", null, "Freshness"), h("b", null, t.freshness_ms != null ? num(t.freshness_ms, 1) + " ms" : "–"),
      h("span", null, "Present interval"), h("b", null, t.present_interval_p50_ms != null ? num(t.present_interval_p50_ms, 1) + " / " + num(t.present_interval_p95_ms, 1) + " ms" : "–"),
      h("span", null, "Layer"), h("b", null, t.frames ? (fo.acknowledged ? "in sync" : "updating") + " · " + t.frames + " frames" : "not loaded"))) : null);
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
    return h(DraftText, { value: v, onCommit: (text) => patch({ [n]: text }) });
  };
  return h(Page, { title: "All settings", onBack: back },
    h("div", { className: "list", style: { marginTop: 0 } }, names.map((n) =>
      h(Focusable, { key: n, className: "row", onClick: types[n] === "boolean" ? () => patch({ [n]: !val(n) }) : undefined },
        h("div", { className: "t" }, h("b", { style: { fontSize: 13 } }, n), h("span", { style: { whiteSpace: "normal" } }, desc[n] || "")),
        control(n)))),
    h(Note, { quiet: true }, "Values are validated by the engine. Saved profile only; Governor never writes here."));
}

// Text settings are saved on Enter or when the field loses focus, not per keystroke: a partial value
// ("ls1-") is rejected by the engine, and every save rewrites the Saved config and live overlays.
function DraftText({ value, onCommit }) {
  const shown = String(value == null ? "" : value);
  const [draft, setDraft] = useState(shown);
  const [editing, setEditing] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { if (!editing) setDraft(shown); }, [shown, editing]);
  // React fires no blur when a focused input unmounts (Back, closing the menu): save it then.
  const pending = useRef({ editing: false, draft: shown, shown, onCommit });
  pending.current = { editing, draft, shown, onCommit };
  useEffect(() => () => { const p = pending.current; if (p.editing && p.draft !== p.shown) p.onCommit(p.draft); }, []);
  const commit = async () => {
    setEditing(false);
    if (draft === shown) return;
    const r = await onCommit(draft);
    if (r && r.success === false) { setErr(r.error || "Not accepted"); setDraft(shown); } else setErr("");
  };
  const TF = window.DFL && window.DFL.TextField;
  if (!TF) return h("div", { className: "val" }, shown || "–");
  return h("div", null,
    h(TF, { value: draft, onChange: (e) => { setEditing(true); setDraft(e.target.value); }, onBlur: commit,
            onKeyDown: (e) => { if (e.key === "Enter") commit(); } }),
    err ? h("div", { className: "hint", style: { color: "#ff6b6b", textAlign: "left" } }, err) : null);
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

  const patch = async (c) => {
    setCfg({ ...(cfg || {}), ...c });
    let r = null;
    try { r = await rpc.patch(profile, c); } catch (e) { r = { success: false, error: String((e && e.message) || e) }; }
    loadCfg(profile);
    return r;
  };
  const pick = async (p) => { await rpc.setProfile(p); await loadProfiles(); setScreen("settings"); };
  const back = () => setScreen("home");
  const go = setScreen;

  const [, force] = useState(0);
  useEffect(() => { const f = () => force((n) => n + 1); rpcErrors.listeners.add(f); return () => rpcErrors.listeners.delete(f); }, []);
  const errBanner = rpcErrors.last ? h("div", { className: "note" }, "Backend call failed: " + rpcErrors.last.name + " — " + rpcErrors.last.message + ". Settings → Diagnostics → Record a log.") : null;
  let body;
  if (!s) body = h("div", { className: "hint" }, "Loading…");
  else if (screen === "governor") body = h(GovernorPage, { s, back, profile, refresh });
  else if (screen === "fg") body = h(FgPage, { back: () => setScreen("settings"), cfg, patch });
  else if (screen === "scaling") body = h(ScalingPage, { s, back: () => setScreen("settings"), profile, refresh });
  else if (screen === "hud") body = h(HudPage, { back: () => setScreen("settings"), s, profile, refresh });
  else if (screen === "profiles") body = h(ProfilesPage, { back: () => setScreen("settings"), profiles, current: profile, pick, reload: loadProfiles });
  else if (screen === "settings") body = h(SettingsPage, { back, go, profile, s });
  else if (screen === "setup") body = h(SetupCheckPage, { back: () => setScreen("advanced"), profile });
  else if (screen === "launch") body = h(LaunchPage, { back: () => setScreen("settings"), launch });
  else if (screen === "journal") body = h(JournalPage, { back: () => setScreen("advanced"), profile, reloadCfg: () => loadCfg(profile) });
  else if (screen === "all") body = h(AllSettingsPage, { back: () => setScreen("settings"), cfg, patch });
  else if (screen === "system") body = h(SystemPage, { back: () => setScreen("settings"), inst, reloadInst });
  else if (screen === "advanced") body = h(AdvancedPage, { back, s, insp, launch, go, profile });
  else body = h(Home, { s, profile, go, refresh, inst, reloadInst, launch });
  return h("div", { className: "gfg" }, h("style", null, css), errBanner, body);
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
