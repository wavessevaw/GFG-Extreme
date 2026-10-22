// GFG Extreme 3.0 UI: four tabs (Dash / Graphics / Engine / Setup), switched with
// L1/R1 or a tap, as approved in mockup v3. No npm deps: Decky provides SP_REACT and DFL as
// globals; `callable` and `definePlugin` come from the shim.
import { css } from "./theme.js";
import { LOGO } from "./logo.js";
const R = window.SP_REACT;
const { useState, useEffect, useCallback } = R;
const h = (t, p, ...c) => R.createElement(t, p, ...c);

// Every backend call goes through here: a failure is shown, never swallowed.
const errs = { last: null, subs: new Set() };
const call = (name) => { const f = callable(name); return async (...a) => {
  try { const r = await f(...a); if (errs.last && errs.last.name === name) { errs.last = null; errs.subs.forEach((g) => g()); } return r; }
  catch (e) { errs.last = { name, message: String((e && e.message) || e) }; errs.subs.forEach((g) => g()); throw e; } }; };
const rpc = {
  state: call("get_state"), catalog: call("get_catalog"), setProfile: call("set_profile"), dropGame: call("drop_game_profile"),
  setSection: call("set_section"), install: call("engine_install"), uninstall: call("engine_uninstall"), reboot: call("reboot"),
  diagnose: call("diagnose"), bench: call("run_bench"), report: call("save_report"), startCapture: call("start_capture"),
  stopCapture: call("stop_capture"), captures: call("list_captures"), logs: call("get_logs"), takeOver: call("take_over"),
};

const TABS = ["Dash", "Graphics", "Engine", "Setup"];
const num = (v) => (typeof v === "number" && isFinite(v) ? v : null);
const fmt = (v, d = 0, unit = "") => (num(v) === null ? "—" : v.toFixed(d) + unit);
const pressed = (cb) => ({ onClick: cb, onActivate: cb });

const Focusable = ({ onClick, className, children, style, onButtonDown }) => {
  const F = window.DFL && window.DFL.Focusable;
  if (F) return h(F, { className, style, onActivate: onClick, onClick, onButtonDown }, children);
  return h("div", { className, style, onClick }, children);
};
const Seg = ({ value, options, onChange }) => h("div", { className: "seg" },
  options.map(([v, label]) => h(Focusable, { key: v, className: "o" + (value === v ? " on" : ""), onClick: () => onChange(v) }, label)));
const Tog = ({ on, onChange }) => h(Focusable, { className: "tog" + (on ? " on" : ""), onClick: () => onChange(!on) });
const Row = ({ k, v, first, children }) => h("div", { className: "lrow" + (first ? " first" : "") }, k, children || h("span", { className: "v" }, v));
const Card = ({ title, children, cls }) => h("div", { className: "card" + (cls ? " " + cls : "") }, title ? h("div", { className: "sec" }, title) : null, children);

// ---------------------------------------------------------------- the ring (tap to resize, as in 2.x)
const LAYOUTS = ["side", "classic", "compact", "arc"];
const LAYOUT_KEY = "gfg3.ring";
function useLayout() {
  const [v, setV] = useState(() => { try { const s = window.localStorage.getItem(LAYOUT_KEY); if (LAYOUTS.includes(s)) return s; } catch (e) {} return "side"; });
  const next = () => setV((cur) => { const n = LAYOUTS[(LAYOUTS.indexOf(cur) + 1) % LAYOUTS.length]; try { window.localStorage.setItem(LAYOUT_KEY, n); } catch (e) {} return n; });
  return [v, next];
}
function Ring({ size, stroke, frac, label, sub }) {
  const r = (size - stroke) / 2 - 1, c = 2 * Math.PI * r, off = c * (1 - Math.max(0, Math.min(1, frac)));
  const big = size >= 170 ? 34 : size >= 120 ? 24 : size >= 100 ? 22 : 15;
  return h("div", { className: "ring", style: { width: size, height: size } },
    h("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size },
      h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#26262d", strokeWidth: stroke }),
      h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#fb0d00", strokeOpacity: 0.25, strokeWidth: stroke + 5, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: off }),
      h("circle", { className: "arcg", cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#fb0d00", strokeWidth: stroke, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: off })),
    h("div", { className: "n" }, h("img", { className: "wolfimg", src: LOGO, width: Math.round(size * 0.34), height: Math.round(size * 0.34) }),
      h("div", { className: "big", style: { fontSize: big } }, label), sub && size >= 100 ? h("div", { className: "sm", style: { fontSize: size >= 170 ? 9.5 : 8 } }, sub) : null));
}
function Arc({ frac, label, sub }) {
  const len = Math.PI * 83, off = len * (1 - Math.max(0, Math.min(1, frac)));
  return h("div", { className: "arc" },
    h("svg", { viewBox: "0 0 190 104", width: 190, height: 104 },
      h("path", { d: "M12 98 A83 83 0 0 1 178 98", fill: "none", stroke: "#26262d", strokeWidth: 9, strokeLinecap: "round" }),
      h("path", { className: "arcg", d: "M12 98 A83 83 0 0 1 178 98", fill: "none", stroke: "#fb0d00", strokeWidth: 9, strokeLinecap: "round", strokeDasharray: len, strokeDashoffset: off, style: { filter: "drop-shadow(0 0 6px rgba(251,13,0,.75))" } })),
    h("div", { className: "n" }, h("img", { className: "wolfimg", src: LOGO, width: 34, height: 34 }),
      h("div", { className: "big", style: { fontSize: 28 } }, label), sub ? h("div", { className: "sm", style: { fontSize: 9 } }, sub) : null));
}

// Dash gauges: a small ring per reading, the number centred in it (the HUD's rule), unit
// under the number, name under the ring. The colour runs smoothly from green at the ideal
// through yellow to red when the reading is way off (user, 3.0.6); grey has no ideal.
const FAN_MAX = 7000;
const frac = (v, max) => (num(v) === null || !max ? 0 : v / max);
// 0 = at the ideal (or better), 1 = way off. `ideal` > `off` means higher is better.
const off = (v, ideal, offAt) => (num(v) === null ? null : Math.max(0, Math.min(1, (v - ideal) / (offAt - ideal))));
const tone = (t) => (t === null || t === undefined ? null : `hsl(${Math.round(130 - 126 * t)},85%,${Math.round(50 + 4 * Math.sin(Math.PI * t))}%)`);
function Mini({ frac: f, v, u, k, t }) {
  const size = 62, stroke = 5, r = (size - stroke) / 2 - 1, c = 2 * Math.PI * r, dash = c * (1 - Math.max(0, Math.min(1, f || 0)));
  const col = tone(t);
  return h("div", { className: "mini" },
    h("div", { className: "mring" },
      h("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size },
        h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#26262d", strokeWidth: stroke }),
        h("circle", { className: "mg", cx: size / 2, cy: size / 2, r, fill: "none", stroke: col || "#4a4a55", strokeWidth: stroke, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: dash })),
      h("div", { className: "mn" }, h("b", { style: { fontSize: String(v).length > 4 ? 12 : 14 } }, v), u ? h("i", null, u) : null)),
    h("span", null, k));
}

// ---------------------------------------------------------------- texts
const PHASES = ["MEASURE", "LOCK", "GUARD", "ADAPT"];
const phaseOf = (p) => ({ measure: "MEASURE", trial: "ADAPT", demote: "ADAPT", locked: "GUARD", fixed: "LOCK" }[p] || null);
const multText = (refresh, point, eng) => {
  if (eng && eng.state !== "active") return "OFF";
  if (!point) return eng && eng.multiplier > 1 ? "×" + eng.multiplier : "OFF";
  const m = refresh / point; return "×" + (Math.abs(m - Math.round(m)) < 0.01 ? Math.round(m) : m.toFixed(2).replace(/0$/, ""));
};
const heroLine = (live) => {
  const p = live.pilot || {};
  if (!live.game) return ["Waiting for a game", "GFG Extreme starts when a game draws frames."];
  if (live.policy && live.policy.state === "conflict") return ["Another tool owns the engine", "See Setup: take over or let it be."];
  return [{ measure: "Measuring the game", trial: "Trying the next point up", demote: "Stepping down", locked: "Point locked and guarded.", fixed: "Fixed multiplier" }[p.phase] || "Starting", p.reason || ""];
};
const gameName = (app) => { try { const o = window.appStore && window.appStore.GetAppOverviewByAppID(app); return (o && o.display_name) || (app ? "App " + app : ""); } catch (e) { return ""; } };
const OBJ = { autopilot: ["Autopilot", "adapts · 12 W"], battery: ["Battery", "×3.75 · low watts"], balanced: ["Balanced", "best point"], quality: ["Quality", "real frames"] };

// Mode icons (user, 3.0.6): drawn, not emoji, so Steam's fonts cannot turn them into boxes.
const svg = (...c) => h("svg", { viewBox: "0 0 24 24", width: 16, height: 16, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, ...c);
const ICON = {
  autopilot: svg(h("path", { d: "M12 2.5l2.2 5.3 5.3 2.2-5.3 2.2L12 17.5l-2.2-5.3L4.5 10l5.3-2.2z", fill: "currentColor", stroke: "none" }), h("path", { d: "M18.5 15.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z", fill: "currentColor", stroke: "none" })),
  battery: svg(h("rect", { x: 2.5, y: 7, width: 17, height: 10, rx: 2.5 }), h("path", { d: "M21.5 10.5v3" }), h("rect", { x: 5, y: 9.5, width: 7, height: 5, rx: 1, fill: "currentColor", stroke: "none" })),
  balanced: svg(h("path", { d: "M12 4v16M7 20h10M5 7h14" }), h("path", { d: "M5 7l-2.5 6a2.5 2.5 0 0 0 5 0z M19 7l-2.5 6a2.5 2.5 0 0 0 5 0z" })),
  quality: svg(h("path", { d: "M6 3h12l3 6-9 12L3 9z" }), h("path", { d: "M3 9h18M9.5 3L12 21M14.5 3L12 21" })),
};

// ---------------------------------------------------------------- tabs
function Dash({ s, set }) {
  const [layout, next] = useLayout();
  const live = s.live || {}, eng = live.engine || {}, gov = live.governor || {}, sen = live.sensors || {}, split = live.split || {};
  const prof = s.settings.profiles[s.profiles.active] || s.settings.profiles.default;
  const refresh = live.refresh || 90, fps = num((live.live || {}).fps), real = num((live.live || {}).real);
  const point = (live.pilot || {}).point || 0;
  const [head, body] = heroLine(live);
  const ph = phaseOf((live.pilot || {}).phase);
  const ring = layout === "arc" ? h(Arc, { frac: (fps || 0) / refresh, label: fmt(fps), sub: real !== null ? Math.round(real) + " REAL" : "" })
    : h(Ring, { ...({ side: { size: 112, stroke: 7 }, classic: { size: 176, stroke: 9 }, compact: { size: 128, stroke: 7 } }[layout]), frac: (fps || 0) / refresh, label: fmt(fps), sub: real !== null ? Math.round(real) + " REAL" : "" });
  const status = h("div", { className: "st" },
    h("h3", null, h("b", null, multText(refresh, point, eng)), point ? ` · ${point} FPS` : ""),
    h("p", null, head, h("br"), live.game ? `${gameName(live.app)} · ${(OBJ[live.objective] || [live.objective])[0]}` : body),
    h("div", { className: "phase" }, PHASES.map((p) => h("span", { key: p, className: p === ph ? "on" : "" }, p))));
  const scope = (s.profiles.active || "").startsWith("app:") ? "game" : "default";
  const setProf = (changes) => set(() => rpc.setProfile(scope, changes));
  const fgOpts = [["off", "Off"], ["auto", "Auto"], ["x2", "×2"], ["x3", "×3"], ["x3.75", "×3.75"], ["custom", "Custom"]];
  const cpuGhz = split.cap_khz ? (split.cap_khz / 1e6).toFixed(1) : null;
  const pace = num((live.live || {}).pace), hdr = !!(eng.transfer && eng.transfer !== "sdr");
  const short = !!(point && real !== null && real < 0.9 * point);
  return h("div", null,
    h("div", { className: "card hero" + (layout === "side" ? "" : " col") }, h(Focusable, { className: "herotap", onClick: next }, ring), status),
    h("div", { className: "minis" },
      // TDP: 12 W good, 9-10 W ideal (user, 3.0.3); 20 W is way off.
      h(Mini, { frac: frac(gov.tdp_w, gov.ceiling_w || 15), v: fmt(gov.tdp_w, 1), u: "W", k: "TDP", t: off(gov.tdp_w, 10, 20) }),
      // APU: the Governor steps down from 90 C, 97 C is critical.
      h(Mini, { frac: frac(sen.temp_c, 100), v: fmt(sen.temp_c, 0), u: "°C", k: "APU", t: off(sen.temp_c, 70, 95) }),
      h(Mini, { frac: frac(pace, 1), v: pace === null ? "—" : (100 * pace).toFixed(1), u: "%", k: "PACE", t: off(pace === null ? null : 100 * pace, 99.5, 95) }),
      h(Mini, { frac: 1, v: hdr ? "HDR" : "SDR", k: "COLOR" }),
      h(Mini, { frac: frac(sen.cpu_top_core_pct, 100), v: fmt(sen.cpu_top_core_pct, 0), u: "%", k: "CPU TOP", t: off(sen.cpu_top_core_pct, 70, 100) }),
      // GPU: a busy GPU is the point of a low TDP; it is off only when the game misses its cap too.
      h(Mini, { frac: frac(sen.gpu_busy_pct, 100), v: fmt(sen.gpu_busy_pct, 0), u: "%", k: "GPU",
        t: num(sen.gpu_busy_pct) === null ? null : short ? off(sen.gpu_busy_pct, 80, 98) : 0.25 * off(sen.gpu_busy_pct, 90, 100) }),
      // CPU clock: a cap Power Split kept saves watts; MAX is fine, not ideal.
      h(Mini, { frac: split.cap_khz && split.max_khz ? split.cap_khz / split.max_khz : 1, v: cpuGhz || "MAX", u: cpuGhz ? "GHz" : "", k: "CPU CLOCK", t: cpuGhz ? 0 : 0.3 }),
      h(Mini, { frac: frac(sen.fan_rpm, FAN_MAX), v: num(sen.fan_rpm) === null ? "—" : (sen.fan_rpm / 1000).toFixed(1), u: "k rpm", k: "FAN", t: off(sen.fan_rpm, 3500, 7000) })),
    h(Card, { title: "MODE" }, h("div", { className: "grid2" }, Object.entries(OBJ).map(([k, [name, sub]]) =>
      h(Focusable, { key: k, onClick: () => setProf({ objective: k }) }, h("div", { className: "tile mode m-" + k + (prof.objective === k ? " on" : "") },
        h("div", { className: "mico" }, ICON[k]), h("div", null, h("b", null, name),
        h("span", null, k === "autopilot" && prof.objective === "autopilot" && live.objective && live.objective !== "autopilot" ? "now " + (OBJ[live.objective] || [live.objective])[0] : sub))))))),
    h(Card, { title: "FRAME GENERATION" }, h(Seg, { value: prof.fg, options: fgOpts, onChange: (v) => setProf({ fg: v }) }),
      prof.fg === "custom" ? h("div", { className: "lrow first", style: { marginTop: 6 } }, "Base FPS cap",
        h("div", { className: "step" }, h(Focusable, { className: "b", onClick: () => setProf({ base_fps: Math.max(20, prof.base_fps - 1) }) }, "−"),
          h("span", { className: "val" }, prof.base_fps), h(Focusable, { className: "b", onClick: () => setProf({ base_fps: Math.min(90, prof.base_fps + 1) }) }, "+"))) : null,
      h("div", { className: "note" }, prof.fg === "custom" ? `The game is capped at ${prof.base_fps} FPS, generation fills ${refresh} Hz.` : "Custom: the game is capped at your base FPS (20–90), generation fills the display.")),
    h(Card, { title: "SETTINGS APPLY TO" }, h(Seg, { value: scope, options: [["game", "This game"], ["default", "All games"]],
      onChange: (v) => set(() => (v === "game" ? rpc.setProfile("game", {}) : rpc.dropGame())) })));
}

// Look as in 2.1.6: colour swatch per preset, a summary line, then sharpening, antialiasing and
// the effects as a two-column list. The engine runs effects in its own fixed order, so a chip
// shows on/off, not a position.
const SWATCH = { off: "linear-gradient(135deg,#2a2a31,#151519)", sharp: "linear-gradient(135deg,#6f7682,#f2f5fa)",
  vivid: "linear-gradient(135deg,#ff2d55,#ffcc00 55%,#34c759)", hdr: "linear-gradient(135deg,#ff9500,#ffe7b0 50%,#2f7cf6)",
  cinema: "linear-gradient(135deg,#0f6a6a,#e09a3e)", noir: "linear-gradient(135deg,#050505,#d9d9d9)",
  retro: "linear-gradient(135deg,#6b3f17,#e6c27a)", smooth: "linear-gradient(135deg,#3a4a66,#9fb4d9)" };
function lookSummary(f, names) {
  const parts = (f.effects || []).map((e) => names[e] || e);
  if (f.aa && f.aa !== "none") parts.push(f.aa.toUpperCase());
  if (f.sharpen && f.sharpen !== "none") parts.push(f.sharpen.toUpperCase() + " " + Math.round((f.sharpness || 0) * 100) + "%");
  return parts.length ? parts.join(" + ") : "No effect";
}
function Graphics({ s, set, cat }) {
  const prof = s.settings.profiles[s.profiles.active] || s.settings.profiles.default;
  const f = prof.filters || { effects: [], sharpen: "none", sharpness: 0.4, denoise: 0.17, aa: "none" };
  const scope = (s.profiles.active || "").startsWith("app:") ? "game" : "default";
  const put = (changes) => set(() => rpc.setProfile(scope, { filters: { ...f, ...changes } }));
  const presets = (cat && cat.presets) || [], effects = (cat && cat.effects) || [];
  const names = Object.fromEntries(effects.map((e) => [e.key, e.name]));
  const same = (a, b) => JSON.stringify([...(a.effects || [])].sort()) === JSON.stringify([...(b.effects || [])].sort()) && (a.sharpen || "none") === (b.sharpen || "none") && (a.aa || "none") === (b.aa || "none");
  const active = (presets.find((p) => same(f, p.filters)) || {}).id || "custom";
  const hud = s.settings.hud;
  const hdr = ((s.live || {}).engine || {}).transfer && s.live.engine.transfer !== "sdr";
  const chain = f.effects || [];
  const step = (k, dv) => put({ [k]: Math.max(0, Math.min(1, Math.round(((f[k] || 0) + dv) * 20) / 20)) });
  const stepper = (k) => h("div", { className: "step" }, h(Focusable, { className: "b", onClick: () => step(k, -0.05) }, "−"),
    h("span", { className: "val" }, Math.round((f[k] || 0) * 100) + "%"), h(Focusable, { className: "b", onClick: () => step(k, 0.05) }, "+"));
  return h("div", null,
    h(Card, { title: "LOOK" },
      h("div", { className: "fgrid" }, presets.map((p) =>
        h(Focusable, { key: p.id, className: "ftile" + (active === p.id ? " on" : ""), onClick: () => set(() => rpc.setProfile(scope, { filters: p.id })) },
          h("div", { className: "sw", style: { background: SWATCH[p.id] || SWATCH.off } }, p.id === "off" ? h("i", { className: "slash" }) : null),
          h("div", { className: "fl" }, p.name)))),
      h("div", { className: "fmore" }, h("span", null, active === "custom" ? "Custom · " + lookSummary(f, names) : lookSummary(f, names)))),
    h(Card, { title: "SHARPENING" }, h(Seg, { value: f.sharpen, options: [["none", "Off"], ["cas", "CAS"], ["dls", "DLS"]], onChange: (v) => put({ sharpen: v }) }),
      f.sharpen !== "none" ? h("div", { className: "lrow first", style: { marginTop: 6 } }, h("div", { className: "t2" }, h("b", null, "Strength"), h("span", null, "May show grain")), stepper("sharpness")) : null,
      f.sharpen === "dls" ? h("div", { className: "lrow" }, h("div", { className: "t2" }, h("b", null, "Denoise"), h("span", null, "Keeps DLS off film grain")), stepper("denoise")) : null,
      h("div", { className: "sec sec2" }, "ANTI-ALIASING"), h(Seg, { value: f.aa, options: [["none", "Off"], ["fxaa", "FXAA"], ["smaa", "SMAA"]], onChange: (v) => put({ aa: v }) })),
    h(Card, { title: "EFFECTS · " + (chain.length ? chain.length + " ON" : "NONE") },
      h("div", { className: "egrid" }, effects.map((e) => {
        const on = chain.includes(e.key);
        return h(Focusable, { key: e.key, className: "echip" + (on ? " on" : ""), onClick: () => put({ effects: on ? chain.filter((x) => x !== e.key) : [...chain, e.key] }) },
          h("span", { className: "eord" + (on ? " on" : "") }, on ? "✓" : "+"), h("span", { className: "en" }, e.name));
      })),
      chain.length ? h(Focusable, { className: "btn", style: { marginTop: 8 }, onClick: () => put({ effects: [] }) }, "Clear effects") : null,
      h("div", { className: "note" }, "Each effect costs some GPU time, the heavy ones (HDR Look, Clarity, SMAA) the most: with the Governor on, that can mean a little more power or a deeper ratio. " +
        (hdr ? "This game runs in HDR: colour effects are skipped, sharpening and anti-aliasing still apply." : "HDR games: colour effects are skipped, sharpening and anti-aliasing still apply."))),
    h(Card, { title: "HDR" },
      h(Row, { k: "HDR output", first: true }, h(Tog, { on: s.settings.engine.hdr_output !== false, onChange: (v) => set(() => rpc.setSection("engine", { hdr_output: v })) })),
      h("div", { className: "sub" }, s.settings.engine.hdr_output !== false ? "On: HDR as set in Steam. Off: the screen and games get SDR." : "Off: the screen and games get SDR. A game started in HDR may need a restart.")),
    h(Card, { title: "HUD" }, h(Row, { k: "Show HUD in game", first: true }, h(Tog, { on: hud.enabled, onChange: (v) => set(() => rpc.setSection("hud", { enabled: v })) })),
      h("div", { className: "sec sec2" }, "POSITION"),
      h(Seg, { value: hud.position, options: [["top-right", "Top right"], ["top-left", "Top left"], ["bottom-left", "Bottom left"], ["bottom-right", "Bottom right"]], onChange: (v) => set(() => rpc.setSection("hud", { position: v })) }),
      h("div", { className: "sec sec2" }, "DETAIL"),
      h(Seg, { value: hud.detail, options: [["minimal", "Minimal"], ["standard", "Standard"]], onChange: (v) => set(() => rpc.setSection("hud", { detail: v })) })));
}

function Engine({ s, set }) {
  const live = s.live || {}, eng = live.engine || {}, p = live.pilot || {}, gov = live.governor || {}, sen = live.sensors || {};
  const split = live.split || {}, gc = live.gpu_clock || {}, pol = live.policy || {}, cfg = s.settings;
  const [cap, setCap] = useState(null);
  const refresh = live.refresh || 90;
  const stateText = eng.state === "active" ? "Generating · " + multText(refresh, p.point, eng) : eng.state ? eng.state[0].toUpperCase() + eng.state.slice(1) : "Not running";
  const splitText = split.cap_khz ? `${(split.cap_khz / 1e6).toFixed(1)} GHz (${Math.round(100 * split.cap_khz / (split.max_khz || split.cap_khz))}%)${split.measured ? " · proven" : ""}`
    : split.phase === "off" ? "Full clock" : "Full clock · " + (split.reason || split.phase || "");
  const ab = split.pairs ? `${split.gain_pct >= 0 ? "+" : ""}${fmt(split.gain_pct, 1, "%")} GPU clock/W · ${split.pairs} A/B` : "Not measured yet";
  return h("div", null,
    h(Card, { title: "KEDAVRA" }, h(Row, { k: "State", v: stateText, first: true }),
      h(Row, { k: "Base cap", v: eng.cap_fps ? `${eng.cap_fps} FPS${eng.auto ? ` (Auto, floor ${eng.auto_floor || "—"})` : ""}` : "—" }),
      h(Row, { k: "GPU per frame", v: num(eng.gpu_us_avg) === null ? "—" : (eng.gpu_us_avg / 1000).toFixed(1) + " ms" }),
      h(Row, { k: "Color", v: eng.transfer === "pq" ? "HDR10 (PQ)" : eng.transfer === "scrgb" ? "HDR (scRGB)" : "SDR" }),
      h(Row, { k: "Policy", v: (pol.state || "—")[0].toUpperCase() + (pol.state || "—").slice(1) + (pol.epoch ? " · rev " + pol.epoch : "") })),
    h(Card, { title: "AUTOPILOT" }, h(Row, { k: "Point", v: p.point ? `${p.point} FPS · ${multText(refresh, p.point, eng)}` : "—", first: true }),
      h(Row, { k: "Phase", v: (phaseOf(p.phase) || "—") }), h("div", { className: "sub", style: { padding: "0 2px 6px" } }, p.reason || ""),
      h("div", { className: "sec sec2" }, "PREFERENCE"),
      h(Seg, { value: cfg.autopilot.preference, options: [["auto", "Auto"], ["battery", "Battery"], ["smoothness", "Smoothness"]], onChange: (v) => set(() => rpc.setSection("autopilot", { preference: v })) })),
    h(Card, { title: "POWER (GOVERNOR)" }, h(Row, { k: "TDP control", first: true }, h(Tog, { on: cfg.power.enabled, onChange: (v) => set(() => rpc.setSection("power", { enabled: v })) })),
      h(Row, { k: "TDP now", v: num(gov.tdp_w) === null ? "—" : `${fmt(gov.tdp_w, 1)} W of ${fmt(gov.ceiling_w, 0)} W` }),
      h(Row, { k: "APU draw", v: fmt(gov.draw_w, 1, " W") }),
      h(Row, { k: "CPU top core · GPU busy", v: `${fmt(sen.cpu_top_core_pct, 0, "%")} · ${fmt(sen.gpu_busy_pct, 0, "%")}` }),
      h("div", { className: "sec sec2" }, "POWER SPLIT"),
      h(Row, { k: "CPU → GPU watts", first: true }, h(Tog, { on: cfg.power.split, onChange: (v) => set(() => rpc.setSection("power", { split: v })) })),
      h(Row, { k: "CPU clock cap", v: splitText }), h(Row, { k: "A/B result", v: ab }),
      h("div", { className: "sec sec2" }, "GPU CLOCK · FAN"),
      h(Row, { k: "GPU clock ceiling", first: true }, h(Tog, { on: cfg.power.gpu_clock, onChange: (v) => set(() => rpc.setSection("power", { gpu_clock: v })) })),
      h(Row, { k: "GPU clock", v: gc.limit_mhz ? `${gc.limit_mhz} MHz cap · now ${fmt(sen.gpu_clock_mhz)} MHz` : `Auto · ${fmt(sen.gpu_clock_mhz)} MHz` }),
      h(Row, { k: "Fan", v: `SteamOS · ${fmt(sen.fan_rpm)} rpm` }),
      h("div", { className: "sub" }, "Power Split and the GPU ceiling act only on a locked point, when the TDP has settled. Every change restarts measurement.")),
    h(Card, { title: "PACE CAPTURE" }, h("div", { className: "sub" }, "Records every display flip, then checks pacing (P95, P99, missed)."),
      h("div", { className: "btns" },
        h(Focusable, { className: "btn red", onClick: () => set(async () => setCap(await ((s.capture || {}).active ? rpc.stopCapture() : rpc.startCapture("run")))) }, (s.capture || {}).active ? "Stop capture" : "Start capture"),
        h(Focusable, { className: "btn", onClick: async () => setCap(await rpc.captures()) }, "Results")),
      cap ? h("div", { className: "note" }, typeof cap === "string" ? cap : JSON.stringify(cap).slice(0, 400)) : null));
}

// Steam toast for actions that take a while or change the system (user, 3.0.7: Setup must
// never be silent). `toaster` comes from the shim; the browser harness has none.
const notify = (title, body) => { try { if (typeof toaster !== "undefined" && toaster) toaster.toast({ title, body, duration: 6000 }); } catch (e) {} };
const resultText = (r, label) => (r && (r.message || r.error || (r.path ? "Saved to " + r.path : null) || (r.rebooting ? "Rebooting now" : null))) || label + ": done";
function Setup({ s, set }) {
  const [diag, setDiag] = useState(null);
  const [msg, setMsg] = useState({ where: "", text: "", bad: false });
  const co = s.coexist || {}, mig = s.migration || {}, cfg = s.settings;
  // Every action says it started, then how it ended, on the card it came from and as a toast.
  const run = (where, label, f, busy) => set(async () => {
    setMsg({ where, text: busy + "…", bad: false });
    notify("GFG Extreme", busy + "…");
    try {
      const r = await f();
      const text = r && r.ok === false ? String(r.log || r.error || label + " failed") : resultText(r, label);
      const bad = !!(r && r.ok === false);
      setMsg({ where, text, bad });
      notify(bad ? "GFG Extreme · " + label + " failed" : "GFG Extreme · " + label, text.slice(0, 160));
      return r;
    } catch (e) {
      const text = String((e && e.message) || e);
      setMsg({ where, text, bad: true });
      notify("GFG Extreme · " + label + " failed", text.slice(0, 160));
      throw e;
    }
  });
  const note = (where) => (msg.where === where && msg.text ? h("div", { className: "note" + (msg.bad ? " bad" : "") }, msg.text) : null);
  const check = () => run("diag", "Checks", async () => { const d = await rpc.diagnose(); setDiag(d);
    const bad = (d.checks || []).filter((c) => !c.ok).length;
    return { message: bad ? bad + " check" + (bad > 1 ? "s" : "") + " failed: see the list above" : "All checks passed" }; }, "Running checks");
  const checks = (diag && diag.checks) || [];
  return h("div", null,
    h(Card, { title: "ENGINE INSTALL" }, checks.length ? checks.slice(0, 6).map((c) => h("div", { key: c.key, className: "check" }, h("b", { className: c.ok ? "" : "x" }, c.ok ? "✓" : "✗"), c.text))
      : h("div", { className: "sub" }, diag ? "No checks returned." : "Checking…"),
      h("div", { className: "btns" }, h(Focusable, { className: "btn", onClick: () => run("install", "Reinstall", rpc.install, "Installing the engine") }, "Reinstall"),
        h(Focusable, { className: "btn", onClick: () => run("install", "Remove", rpc.uninstall, "Removing the engine") }, "Remove"),
        h(Focusable, { className: "btn", onClick: () => run("install", "Reboot", rpc.reboot, "Rebooting the Deck") }, "Reboot")),
      note("install")),
    co.standalone && !co.taken_over ? h(Card, { title: "STANDALONE GSF KEDAVRA FOUND", cls: "warn" },
      h("div", { className: "sub" }, "Both plugins can drive the engine. GFG backs off instead of fighting."),
      h("div", { className: "btns" }, h(Focusable, { className: "btn red", onClick: () => run("coexist", "Take over", rpc.takeOver, "Taking over the engine") }, "Take over")), note("coexist")) : null,
    h(Card, { title: "GENERATION" }, h(Row, { k: "Frame generation in HDR games", first: true }, h(Tog, { on: cfg.engine.hdr, onChange: (v) => set(() => rpc.setSection("engine", { hdr: v })) }))),
    h(Card, { title: "DIAGNOSTICS" },
      h(Focusable, { onClick: check }, h(Row, { k: "Run checks", v: "›", first: true })),
      h(Focusable, { onClick: () => run("diag", "Report", rpc.report, "Saving the report") }, h(Row, { k: "Save report to Desktop", v: "›" })),
      h(Focusable, { onClick: () => run("diag", "Engine log", async () => ({ message: String(await rpc.logs()).slice(-600) }), "Reading the engine log") }, h(Row, { k: "Engine log", v: "›" })),
      h(Focusable, { onClick: () => run("diag", "GPU benchmark", async () => { const r = await rpc.bench(); return r && r.ok !== false ? { ...r, message: "Benchmark done. " + String(r.log || "").trim().slice(-240) } : r; }, "Running the GPU benchmark") }, h(Row, { k: "GPU benchmark", v: "›" })),
      note("diag"),
      h("div", { className: "sec sec2" }, "TELEMETRY"),
      h(Seg, { value: cfg.telemetry.level, options: [["minimal", "Minimal"], ["standard", "Standard"], ["debug", "Debug"]], onChange: (v) => set(() => rpc.setSection("telemetry", { level: v })) })),
    mig && mig.from ? h(Card, { title: "FROM GFG EXTREME 2.X" }, (mig.steps || []).slice(0, 4).map((t, i) => h("div", { key: i, className: "check" }, h("b", null, "✓"), String(t)))) : null,
    h("div", { className: "sub", style: { textAlign: "center", marginTop: 4 } }, `GFG Extreme ${s.version}${s.codename ? " " + s.codename : ""}`));
}

// ---------------------------------------------------------------- first run (user, 3.1.0)
// Until the engine is installed and running in this boot the panel shows only this card:
// install, reboot, then the four tabs (mockup approved 3.1.0, labels must fit their tiles).
function Gate({ g, set, version }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({ text: "", bad: false });
  const st = g.state;
  const go = (label, f, doing) => set(async () => {
    setBusy(true); setMsg({ text: doing + "…", bad: false }); notify("GFG Extreme", doing + "…");
    try { const r = await f(); const bad = !!(r && r.ok === false);
      const text = bad ? String(r.log || r.error || label + " failed") : resultText(r, label);
      setMsg({ text, bad }); notify("GFG Extreme · " + label + (bad ? " failed" : ""), text.slice(0, 160));
    } catch (e) { const text = String((e && e.message) || e); setMsg({ text, bad: true }); notify("GFG Extreme · " + label + " failed", text.slice(0, 160)); }
    setBusy(false);
  });
  const tiles = (a, b) => h("div", { className: "steps" }, h("div", { className: "st " + a }, h("b", null, "1"), "Install"),
    h("div", { className: "st " + b }, h("b", null, "2"), "Reboot"), h("div", { className: "st" }, h("b", null, "3"), "Play"));
  const install = h(Focusable, { className: "btn red", onClick: () => !busy && go("Install", rpc.install, "Installing the engine") }, busy ? "Installing…" : st === "failed" ? "Try again" : g.update ? "Update engine" : "Install engine");
  let head, text, body;
  if (st === "reboot") {
    head = "Reboot to start the engine";
    text = "Installed. Gamescope KEDAVRA starts with the next boot; until then the Deck runs stock Gamescope.";
    body = [tiles("done", "on"), h(Focusable, { key: "r", className: "btn red", onClick: () => go("Reboot", rpc.reboot, "Rebooting the Deck") }, "Reboot now"),
      h("div", { key: "s", className: "small" }, "After the reboot open GFG Extreme again: all tabs unlock.")];
  } else if (st === "failed") {
    head = "The engine could not be installed";
    text = "The panel stays locked so nothing runs half installed.";
    body = [tiles("on", ""), h("div", { key: "b", className: "btns", style: { marginTop: 0 } }, install,
      h(Focusable, { className: "btn", onClick: () => go("Report", rpc.report, "Saving the report") }, "Save report")),
      h("div", { key: "e", className: "note bad" }, g.error || "Install failed.")];
  } else {
    head = g.update ? "Update the KEDAVRA engine" : "Install the KEDAVRA engine";
    text = g.update ? "This GFG Extreme carries a newer engine. Install it, then reboot."
      : "GFG Extreme generates frames inside its own Gamescope. Install it first: nothing in SteamOS is overwritten, and Remove in Setup brings stock Gamescope back.";
    body = [tiles("on", ""), install, h("div", { key: "s", className: "small" }, "The panel opens after the engine is installed and the Deck has rebooted.")];
  }
  return h("div", { className: "card hero col gate" }, h("img", { className: "wolf", src: LOGO }),
    h("div", { className: "gh" }, head), h("div", { className: "gp" }, text), body,
    msg.text && st !== "failed" ? h("div", { className: "note" + (msg.bad ? " bad" : "") }, msg.text) : null,
    h("div", { className: "small" }, "GFG Extreme " + version));
}

// ---------------------------------------------------------------- root
function Content() {
  const [s, setS] = useState(null);
  const [cat, setCat] = useState(null);
  const [tab, setTab] = useState(0);
  const [, bump] = useState(0);
  const load = useCallback(() => rpc.state().then(setS).catch(() => {}), []);
  useEffect(() => { load(); rpc.catalog().then(setCat).catch(() => {}); const t = setInterval(load, 1000); const f = () => bump((x) => x + 1); errs.subs.add(f); return () => { clearInterval(t); errs.subs.delete(f); }; }, []);
  const set = async (f) => { try { await f(); } catch (e) {} load(); };
  const step = (d) => setTab((t) => (t + d + TABS.length) % TABS.length);
  const GB = (window.DFL && window.DFL.GamepadButton) || {};
  const onButtonDown = (e) => { if (s && s.gate && s.gate.state && s.gate.state !== "ready") return; const b = e && e.detail && e.detail.button; if (b === (GB.BUMPER_LEFT ?? 5)) step(-1); else if (b === (GB.BUMPER_RIGHT ?? 6)) step(1); };
  const gated = !!(s && s.gate && s.gate.state && s.gate.state !== "ready");
  const body = !s ? h("div", { className: "sub" }, "Loading…") : gated ? h(Gate, { g: s.gate, set, version: s.version })
    : h([Dash, Graphics, Engine, Setup][tab], { s, set, cat });
  return h(Focusable, { className: "gfg", onButtonDown },
    h("style", null, css),
    h("div", { className: "top" }, h("div", { className: "brand" }, h("img", { src: LOGO }), "GFG ·", h("b", null, "EXTREME")),
      h("div", { className: "chip" }, h("i"), (s && s.device) || "Steam Deck")),
    gated ? null : h("div", { className: "tabs" }, h(Focusable, { className: "bump", onClick: () => step(-1) }, "L1"),
      TABS.map((t, i) => h(Focusable, { key: t, className: "tab" + (i === tab ? " on" : ""), onClick: () => setTab(i) }, t)),
      h(Focusable, { className: "bump", onClick: () => step(1) }, "R1")),
    errs.last ? h("div", { className: "err" }, `${errs.last.name}: ${errs.last.message}`) : null,
    body);
}

const Icon = () => h("img", { src: LOGO, width: 20, height: 20 });
export default definePlugin(() => ({
  name: "GFG Extreme",
  titleView: h("div", { className: window.DFL.staticClasses.Title }, "GFG · EXTREME"),
  alwaysRender: true,
  content: h(Content, null),
  icon: h(Icon, null),
  onDismount() {},
}));
