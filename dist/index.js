// Decky Loader will pass this api in, it's versioned to allow for backwards compatibility.
// @ts-ignore

// Prevents it from being duplicated in output.
const manifest = {"name": "GFG Extreme", "author": "Eugenio Segala", "flags": ["root"], "api_version": 1, "publish": {"tags": ["frame-generation", "framegen", "gamescope", "kedavra", "tdp", "steam-deck", "gfg-extreme"], "description": "GFG Extreme 3.0: frame generation x2–x3.75 on its own engine (GSF Kedavra in Gamescope), Autopilot, TDP Governor, Power Split and GPU clock ceiling. No Lossless Scaling."}};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
// Initialize
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
// Version 1 throws on version mismatch so we have to account for that here.
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => {
    return (...args) => {
        // TODO: Maybe wrap this
        return fn(...args);
    };
};


// frontend/src/theme.js
var css = `
.gfg{--bg:#0a0a0c;--s1:#141417;--s2:#1c1c21;--s3:#26262d;--line:#2e2e36;--tx:#f5f5f7;--tx2:#a1a1ab;--tx3:#6b6b76;--red:#fb0d00;--redbg:rgba(251,13,0,.13);--ok:#3ecf6e;--warn:#e3c04a;
 font-family:"Motiva Sans","Inter","Segoe UI",system-ui,sans-serif;color:var(--tx);box-sizing:border-box;-webkit-font-smoothing:antialiased;
 padding:10px 10px 18px;min-height:100%;background:linear-gradient(180deg,#120c0d 0%,var(--bg) 22%,var(--bg) 100%)}
.gfg *{box-sizing:border-box}
.gfg .top{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 10px;margin:4px 2px 12px;line-height:1.2}
.gfg .brand{display:flex;align-items:center;font-weight:800;letter-spacing:.14em;font-size:12px;white-space:nowrap}
.gfg .brand img{width:20px;height:20px;margin-right:6px;filter:drop-shadow(0 0 6px rgba(251,13,0,.6))}
.gfg .brand b{color:var(--red);text-shadow:0 0 12px rgba(251,13,0,.65);margin-left:5px}
.gfg .chip{display:inline-flex;align-items:center;gap:5px;font-size:9.5px;font-weight:600;color:var(--tx2);background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:3px 8px;white-space:nowrap;margin-left:auto}
.gfg .chip i{width:5px;height:5px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red)}
.gfg .tabs{display:flex;align-items:center;gap:3px;background:var(--s1);border:1px solid var(--line);border-radius:14px;padding:4px;margin-bottom:10px}
.gfg .bump{font-size:10px;font-weight:800;color:var(--tx3);background:var(--s3);border-radius:6px;padding:3px 5px}
.gfg .tab{flex:1;text-align:center;font-size:11.5px;font-weight:700;color:var(--tx2);padding:7px 0;border-radius:10px}
.gfg .tab.on{color:var(--tx);background:linear-gradient(180deg,rgba(251,13,0,.24),rgba(251,13,0,.08));box-shadow:inset 0 -2px 0 var(--red),0 0 14px rgba(251,13,0,.28)}
.gfg .card{background:linear-gradient(160deg,#18161a 0%,var(--s1) 55%,#121214 100%);border:1px solid var(--line);border-radius:16px;padding:12px;margin-bottom:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
.gfg .sec{font-size:10.5px;font-weight:800;letter-spacing:.14em;color:var(--tx3);margin:0 0 9px}
.gfg .sec2{margin-top:12px}
.gfg .hero{display:flex;gap:12px;align-items:center;background:radial-gradient(120% 110% at 22% 20%,rgba(251,13,0,.16) 0%,#1a1214 38%,var(--s1) 72%)}
.gfg .hero.col{flex-direction:column;text-align:center}
.gfg .herotap{flex:none;border-radius:50%}
.gfg .ring{position:relative;flex:none}.gfg .ring svg{position:absolute;inset:0;transform:rotate(-90deg);overflow:visible}
.gfg .ring .arcg{filter:drop-shadow(0 0 6px rgba(251,13,0,.75));transition:stroke-dashoffset .6s}
.gfg .ring .n,.gfg .arc .n{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gfg .arc{position:relative;width:190px;height:104px}.gfg .arc svg{overflow:visible}.gfg .arc .n{top:auto;justify-content:flex-end}
.gfg .wolfimg{display:block;filter:drop-shadow(0 0 6px rgba(251,13,0,.6))}
.gfg .big{font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.gfg .sm{font-weight:700;letter-spacing:.14em;color:var(--tx2);margin-top:2px}
.gfg .st h3{margin:0 0 3px;font-size:19px;font-weight:800}.gfg .st h3 b{color:var(--red)}
.gfg .st p{margin:0;font-size:11.5px;color:var(--tx2);line-height:1.35}
.gfg .phase{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}.gfg .hero.col .phase{justify-content:center}
.gfg .phase span{font-size:8px;font-weight:800;letter-spacing:.06em;padding:3px 5px;border-radius:6px;background:var(--s3);color:var(--tx3)}
.gfg .phase span.on{background:linear-gradient(135deg,#ff2d1a,#b30800);color:#fff;box-shadow:0 0 10px rgba(251,13,0,.55)}
.gfg .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:6px}
.gfg .stat{background:linear-gradient(180deg,#222228,var(--s2));border-radius:10px;padding:6px 2px;text-align:center}
.gfg .stat b{display:block;font-size:14px;font-variant-numeric:tabular-nums}.gfg .stat span{font-size:9px;color:var(--tx3);font-weight:700;letter-spacing:.08em}
.gfg .minis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 4px;background:linear-gradient(160deg,#18161a 0%,var(--s1) 55%,#121214 100%);border:1px solid var(--line);border-radius:16px;padding:10px 4px 8px;margin-bottom:10px}
.gfg .mini{display:flex;flex-direction:column;align-items:center}
.gfg .mring{position:relative;width:62px;height:62px}.gfg .mring svg{position:absolute;inset:0;transform:rotate(-90deg);overflow:visible}
.gfg .mring .mg{transition:stroke-dashoffset .6s,stroke .6s}
.gfg .mn{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1}
.gfg .mn b{font-weight:800;font-variant-numeric:tabular-nums;line-height:1}.gfg .mn i{font-style:normal;line-height:1;font-size:8px;font-weight:700;color:var(--tx3);margin-top:2px;letter-spacing:.04em}
.gfg .mini>span{font-size:8.5px;font-weight:800;letter-spacing:.08em;color:var(--tx3);margin-top:4px}
.gfg .fgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.gfg .ftile{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 2px 7px;border-radius:12px;border:1px solid transparent;background:var(--s2)}
.gfg .ftile .sw{position:relative;width:38px;height:38px;border-radius:11px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);overflow:hidden}
.gfg .ftile .slash{position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;background:var(--tx3);transform:rotate(45deg)}
.gfg .ftile .fl{font-size:10.5px;font-weight:700;color:var(--tx2);white-space:nowrap}
.gfg .ftile.on{border-color:var(--red);background:var(--redbg);box-shadow:0 0 14px rgba(251,13,0,.22)}.gfg .ftile.on .fl{color:var(--tx)}
.gfg .fmore{margin-top:10px;padding:9px 10px;border-radius:11px;background:var(--s2);font-size:11.5px;color:var(--tx2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gfg .egrid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
.gfg .echip{display:flex;align-items:center;gap:8px;padding:8px 9px;border-radius:11px;background:var(--s2);border:1px solid var(--line);min-width:0}
.gfg .echip .en{font-size:12px;font-weight:600;color:var(--tx2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .echip.on{border-color:rgba(251,13,0,.6);background:var(--redbg)}.gfg .echip.on .en{color:var(--tx)}
.gfg .eord{width:20px;height:20px;border-radius:6px;background:var(--s3);color:var(--tx3);font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}
.gfg .eord.on{background:var(--red);color:#fff}
.gfg .t2 b{display:block;font-size:12.5px;font-weight:600}.gfg .t2 span{font-size:10px;color:var(--tx3)}
.gfg .tile.mode{display:flex;align-items:center;gap:8px;position:relative;overflow:hidden;padding:7px 8px;line-height:1.2}
.gfg .tile.mode>div:last-child{min-width:0}
.gfg .tile.mode b{font-size:12.5px;line-height:1.2}.gfg .tile.mode span{display:block;font-size:10px;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .mico{width:26px;height:26px;flex:none;border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--tx2);
 background:linear-gradient(160deg,#33333b,#1c1c21);box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 0 0 1px var(--line)}
.gfg .tile.mode{background:linear-gradient(160deg,#222228 0%,var(--s2) 60%,#18181c 100%)}
.gfg .tile.mode.on .mico{color:#fff;background:linear-gradient(160deg,#ff2d1a,#b30800);box-shadow:0 0 12px rgba(251,13,0,.5)}
.gfg .grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.gfg .tile{background:var(--s2);border:1px solid var(--line);border-radius:12px;padding:9px 10px;height:100%}
.gfg .tile b{display:block;font-size:13px}.gfg .tile span{font-size:10.5px;color:var(--tx2)}
.gfg .tile.on,.gfg .pre.on,.gfg .ec.on{border-color:var(--red);background:linear-gradient(160deg,rgba(251,13,0,.22),rgba(251,13,0,.06));box-shadow:0 0 16px rgba(251,13,0,.25);color:var(--tx)}
.gfg .seg{display:flex;background:var(--s2);border-radius:11px;padding:3px;gap:2px}
.gfg .seg>div{flex:1}
.gfg .seg .o{text-align:center;font-size:11.5px;font-weight:700;color:var(--tx2);padding:7px 0;border-radius:9px;white-space:nowrap}
.gfg .seg .o.on{background:linear-gradient(180deg,#ff2d1a,#d10a00);color:#fff;box-shadow:0 0 14px rgba(251,13,0,.45)}
.gfg .lrow{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 2px;border-top:1px solid var(--line);font-size:12.5px}
.gfg .lrow.first{border-top:0}
.gfg .lrow .v{color:var(--tx);font-weight:700;font-size:11.5px;text-align:right}
.gfg .tog{width:34px;height:20px;border-radius:999px;background:var(--s3);position:relative;flex:none}
.gfg .tog::after{content:"";position:absolute;top:3px;left:3px;width:14px;height:14px;border-radius:50%;background:var(--tx3)}
.gfg .tog.on{background:linear-gradient(180deg,#ff2d1a,#c40900);box-shadow:0 0 10px rgba(251,13,0,.55)}.gfg .tog.on::after{left:17px;background:#fff}
.gfg .step{display:flex;align-items:center;gap:6px}
.gfg .step .b{width:26px;height:26px;border-radius:8px;background:var(--s3);display:flex;align-items:center;justify-content:center;font-weight:800}
.gfg .step .val{min-width:44px;text-align:center;font-weight:800;font-variant-numeric:tabular-nums}
.gfg .chips{display:flex;flex-wrap:wrap;gap:5px}
.gfg .ec{font-size:10.5px;font-weight:700;padding:5px 8px;border-radius:999px;background:var(--s2);border:1px solid var(--line);color:var(--tx2)}
.gfg .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.gfg .pre{background:var(--s2);border:1px solid var(--line);border-radius:10px;text-align:center;padding:8px 0;font-size:10.5px;font-weight:700;color:var(--tx2)}
.gfg .note{font-size:10.5px;color:var(--tx2);background:var(--s2);border-radius:10px;padding:8px 9px;line-height:1.4;margin-top:8px}
.gfg .note.bad{color:#ffb4a8;background:#2a1010}
.gfg .btns{display:flex;gap:6px;margin-top:9px}.gfg .btns>div{flex:1}
.gfg .btn{text-align:center;font-size:11.5px;font-weight:800;padding:9px 0;border-radius:10px;background:var(--s3)}
.gfg .btn.red{background:linear-gradient(180deg,#ff2d1a,#d10a00);box-shadow:0 0 14px rgba(251,13,0,.45)}
.gfg .check{display:flex;gap:7px;font-size:11.5px;padding:3px 0;color:var(--tx2)}.gfg .check b{color:var(--ok)}.gfg .check b.x{color:var(--red)}
.gfg .warn{border-color:#5a2a10;background:linear-gradient(180deg,#22140d,var(--s1))}
.gfg .sub{font-size:10.5px;color:var(--tx3);line-height:1.4}
.gfg .err{font-size:11px;color:#ffb4a8;background:#2a1010;border:1px solid #5a1a10;border-radius:10px;padding:7px 9px;margin-bottom:8px}
.gfg .row{display:block}
/* Gamepad focus: Steam marks the element under the stick / D-pad with .gpfocus, but our own
   backgrounds hide its ring. As in 2.x, the focused control turns white; a selected one gets a white ring. */
.gfg .gpfocus,.gfg :focus-visible{outline:none}
.gfg .tab.gpfocus,.gfg .seg .o.gpfocus,.gfg .pre.gpfocus,.gfg .ec.gpfocus,.gfg .ftile.gpfocus,.gfg .echip.gpfocus,.gfg .btn.gpfocus,.gfg .step .b.gpfocus,.gfg .bump.gpfocus,.gfg .gpfocus>.tile,
.gfg .tab:focus-visible,.gfg .seg .o:focus-visible,.gfg .pre:focus-visible,.gfg .ec:focus-visible,.gfg .btn:focus-visible,.gfg .step .b:focus-visible,.gfg :focus-visible>.tile{background:linear-gradient(180deg,#fff 0%,#dcdce2 100%)!important;color:#0a0a0c!important;border-color:#fff!important;box-shadow:0 0 16px rgba(255,255,255,.35)!important}
.gfg .gpfocus>.tile span,.gfg :focus-visible>.tile span{color:#3a3a44!important}
.gfg .tab.on.gpfocus,.gfg .seg .o.on.gpfocus,.gfg .pre.on.gpfocus,.gfg .ec.on.gpfocus,.gfg .ftile.on.gpfocus,.gfg .echip.on.gpfocus,.gfg .btn.red.gpfocus,.gfg .gpfocus>.tile.on,
.gfg .tab.on:focus-visible,.gfg .seg .o.on:focus-visible,.gfg .pre.on:focus-visible,.gfg .ec.on:focus-visible,.gfg .btn.red:focus-visible,.gfg :focus-visible>.tile.on{background:linear-gradient(180deg,#ff2d1a,#d10a00)!important;color:#fff!important;box-shadow:0 0 0 2px #fff,0 0 18px rgba(251,13,0,.6)!important}
.gfg .gpfocus>.tile.on span,.gfg :focus-visible>.tile.on span{color:#ffd9d4!important}
.gfg .tog.gpfocus,.gfg .tog:focus-visible,.gfg .herotap.gpfocus,.gfg .herotap:focus-visible{box-shadow:0 0 0 2px #fff,0 0 14px rgba(255,255,255,.4)!important}
.gfg .gpfocus>.lrow,.gfg :focus-visible>.lrow{background:var(--s3);border-radius:10px;box-shadow:0 0 0 2px #fff}
.gfg .gate{text-align:center;padding:18px 12px 16px}
.gfg .gate .wolf{display:block;width:60px;height:60px;margin:2px auto 10px;filter:drop-shadow(0 0 16px rgba(251,13,0,.7))}
.gfg .gate .gh{font-size:14px;font-weight:800;margin:0 0 6px;line-height:1.25}
.gfg .gate .gp{font-size:10.5px;color:var(--tx2);line-height:1.45;margin:0 0 12px}
.gfg .steps{display:flex;gap:5px;margin:0 0 12px}
.gfg .steps .st{flex:1;min-width:0;border-radius:10px;padding:7px 2px;background:var(--s2);border:1px solid var(--line);font-size:9.5px;font-weight:700;color:var(--tx3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .steps .st b{display:block;font-size:12.5px;margin-bottom:1px}
.gfg .steps .st.on{color:var(--tx);border-color:rgba(251,13,0,.6);background:linear-gradient(180deg,rgba(251,13,0,.22),rgba(251,13,0,.06));box-shadow:0 0 14px rgba(251,13,0,.25)}
.gfg .steps .st.done{color:var(--ok)}
.gfg .gate>.steps,.gfg .gate>.btn,.gfg .gate>.btns,.gfg .gate>.note{align-self:stretch;width:100%}
.gfg .gate .btn{white-space:nowrap}
.gfg .gate .small{font-size:9.5px;color:var(--tx3);margin-top:9px;line-height:1.4}
.gfg .gate .note{text-align:left}
`;

// frontend/src/logo.js
var LOGO = "data:image/png;base64,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";

// frontend/src/app.js
var R = window.SP_REACT;
var { useState, useEffect, useCallback } = R;
var h = (t, p, ...c) => R.createElement(t, p, ...c);
var errs = { last: null, subs: /* @__PURE__ */ new Set() };
var call = (name) => {
  const f = callable(name);
  return async (...a) => {
    try {
      const r = await f(...a);
      if (errs.last && errs.last.name === name) {
        errs.last = null;
        errs.subs.forEach((g) => g());
      }
      return r;
    } catch (e) {
      errs.last = { name, message: String(e && e.message || e) };
      errs.subs.forEach((g) => g());
      throw e;
    }
  };
};
var rpc = {
  state: call("get_state"),
  catalog: call("get_catalog"),
  setProfile: call("set_profile"),
  dropGame: call("drop_game_profile"),
  setSection: call("set_section"),
  install: call("engine_install"),
  uninstall: call("engine_uninstall"),
  reboot: call("reboot"),
  diagnose: call("diagnose"),
  bench: call("run_bench"),
  report: call("save_report"),
  startCapture: call("start_capture"),
  stopCapture: call("stop_capture"),
  captures: call("list_captures"),
  logs: call("get_logs"),
  takeOver: call("take_over"),
  benchStart: call("bench_start"),
  benchAnswer: call("bench_answer")
};
var TABS = ["Dash", "Graphics", "Engine", "Setup"];
var num = (v) => typeof v === "number" && isFinite(v) ? v : null;
var fmt = (v, d = 0, unit = "") => num(v) === null ? "\u2014" : v.toFixed(d) + unit;
var Focusable = ({ onClick, className, children, style, onButtonDown }) => {
  const F = window.DFL && window.DFL.Focusable;
  if (F) return h(F, { className, style, onActivate: onClick, onClick, onButtonDown }, children);
  return h("div", { className, style, onClick }, children);
};
var Seg = ({ value, options, onChange }) => h(
  "div",
  { className: "seg" },
  options.map(([v, label]) => h(Focusable, { key: v, className: "o" + (value === v ? " on" : ""), onClick: () => onChange(v) }, label))
);
var Tog = ({ on, onChange }) => h(Focusable, { className: "tog" + (on ? " on" : ""), onClick: () => onChange(!on) });
var Row = ({ k, v, first, children }) => h("div", { className: "lrow" + (first ? " first" : "") }, k, children || h("span", { className: "v" }, v));
var Card = ({ title, children, cls }) => h("div", { className: "card" + (cls ? " " + cls : "") }, title ? h("div", { className: "sec" }, title) : null, children);
var LAYOUTS = ["side", "classic", "compact", "arc"];
var LAYOUT_KEY = "gfg3.ring";
function useLayout() {
  const [v, setV] = useState(() => {
    try {
      const s = window.localStorage.getItem(LAYOUT_KEY);
      if (LAYOUTS.includes(s)) return s;
    } catch (e) {
    }
    return "side";
  });
  const next = () => setV((cur) => {
    const n = LAYOUTS[(LAYOUTS.indexOf(cur) + 1) % LAYOUTS.length];
    try {
      window.localStorage.setItem(LAYOUT_KEY, n);
    } catch (e) {
    }
    return n;
  });
  return [v, next];
}
function Ring({ size, stroke, frac: frac2, label, sub }) {
  const r = (size - stroke) / 2 - 1, c = 2 * Math.PI * r, off2 = c * (1 - Math.max(0, Math.min(1, frac2)));
  const big = size >= 170 ? 34 : size >= 120 ? 24 : size >= 100 ? 22 : 15;
  return h(
    "div",
    { className: "ring", style: { width: size, height: size } },
    h(
      "svg",
      { viewBox: `0 0 ${size} ${size}`, width: size, height: size },
      h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#26262d", strokeWidth: stroke }),
      h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#fb0d00", strokeOpacity: 0.25, strokeWidth: stroke + 5, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: off2 }),
      h("circle", { className: "arcg", cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#fb0d00", strokeWidth: stroke, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: off2 })
    ),
    h(
      "div",
      { className: "n" },
      h("img", { className: "wolfimg", src: LOGO, width: Math.round(size * 0.34), height: Math.round(size * 0.34) }),
      h("div", { className: "big", style: { fontSize: big } }, label),
      sub && size >= 100 ? h("div", { className: "sm", style: { fontSize: size >= 170 ? 9.5 : 8 } }, sub) : null
    )
  );
}
function Arc({ frac: frac2, label, sub }) {
  const len = Math.PI * 83, off2 = len * (1 - Math.max(0, Math.min(1, frac2)));
  return h(
    "div",
    { className: "arc" },
    h(
      "svg",
      { viewBox: "0 0 190 104", width: 190, height: 104 },
      h("path", { d: "M12 98 A83 83 0 0 1 178 98", fill: "none", stroke: "#26262d", strokeWidth: 9, strokeLinecap: "round" }),
      h("path", { className: "arcg", d: "M12 98 A83 83 0 0 1 178 98", fill: "none", stroke: "#fb0d00", strokeWidth: 9, strokeLinecap: "round", strokeDasharray: len, strokeDashoffset: off2, style: { filter: "drop-shadow(0 0 6px rgba(251,13,0,.75))" } })
    ),
    h(
      "div",
      { className: "n" },
      h("img", { className: "wolfimg", src: LOGO, width: 34, height: 34 }),
      h("div", { className: "big", style: { fontSize: 28 } }, label),
      sub ? h("div", { className: "sm", style: { fontSize: 9 } }, sub) : null
    )
  );
}
var FAN_MAX = 7e3;
var frac = (v, max) => num(v) === null || !max ? 0 : v / max;
var off = (v, ideal, offAt) => num(v) === null ? null : Math.max(0, Math.min(1, (v - ideal) / (offAt - ideal)));
var tone = (t) => t === null || t === void 0 ? null : `hsl(${Math.round(130 - 126 * t)},85%,${Math.round(50 + 4 * Math.sin(Math.PI * t))}%)`;
function Mini({ frac: f, v, u, k, t }) {
  const size = 62, stroke = 5, r = (size - stroke) / 2 - 1, c = 2 * Math.PI * r, dash = c * (1 - Math.max(0, Math.min(1, f || 0)));
  const col = tone(t);
  return h(
    "div",
    { className: "mini" },
    h(
      "div",
      { className: "mring" },
      h(
        "svg",
        { viewBox: `0 0 ${size} ${size}`, width: size, height: size },
        h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#26262d", strokeWidth: stroke }),
        h("circle", { className: "mg", cx: size / 2, cy: size / 2, r, fill: "none", stroke: col || "#4a4a55", strokeWidth: stroke, strokeLinecap: "round", strokeDasharray: c, strokeDashoffset: dash })
      ),
      h("div", { className: "mn" }, h("b", { style: { fontSize: String(v).length > 4 ? 12 : 14 } }, v), u ? h("i", null, u) : null)
    ),
    h("span", null, k)
  );
}
var PHASES = ["MEASURE", "LOCK", "GUARD", "ADAPT"];
var phaseOf = (p) => ({ measure: "MEASURE", trial: "ADAPT", demote: "ADAPT", locked: "GUARD", fixed: "LOCK" })[p] || null;
var multText = (refresh, point, eng) => {
  if (eng && eng.state !== "active") return "OFF";
  if (!point) return eng && eng.multiplier > 1 ? "\xD7" + eng.multiplier : "OFF";
  const m = refresh / point;
  return "\xD7" + (Math.abs(m - Math.round(m)) < 0.01 ? Math.round(m) : m.toFixed(2).replace(/0$/, ""));
};
var heroLine = (live) => {
  const p = live.pilot || {};
  if (!live.game) return ["Waiting for a game", "GFG Extreme starts when a game draws frames."];
  if (live.policy && live.policy.state === "conflict") return ["Another tool owns the engine", "See Setup: take over or let it be."];
  return [{ measure: "Measuring the game", trial: "Trying the next point up", demote: "Stepping down", locked: "Point locked and guarded.", fixed: "Fixed multiplier" }[p.phase] || "Starting", p.reason || ""];
};
var gameName = (app) => {
  try {
    const o = window.appStore && window.appStore.GetAppOverviewByAppID(app);
    return o && o.display_name || (app ? "App " + app : "");
  } catch (e) {
    return "";
  }
};
var OBJ = { autopilot: ["Autopilot", "adapts \xB7 12 W"], battery: ["Battery", "\xD73 \xB7 low watts"], balanced: ["Balanced", "best point"], quality: ["Quality", "real frames"] };
var objSub = (k, sub, above) => k === "battery" && above ? "\xD73.75 \xB7 low watts" : sub;
var svg = (...c) => h("svg", { viewBox: "0 0 24 24", width: 16, height: 16, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, ...c);
var ICON = {
  autopilot: svg(h("path", { d: "M12 2.5l2.2 5.3 5.3 2.2-5.3 2.2L12 17.5l-2.2-5.3L4.5 10l5.3-2.2z", fill: "currentColor", stroke: "none" }), h("path", { d: "M18.5 15.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z", fill: "currentColor", stroke: "none" })),
  battery: svg(h("rect", { x: 2.5, y: 7, width: 17, height: 10, rx: 2.5 }), h("path", { d: "M21.5 10.5v3" }), h("rect", { x: 5, y: 9.5, width: 7, height: 5, rx: 1, fill: "currentColor", stroke: "none" })),
  balanced: svg(h("path", { d: "M12 4v16M7 20h10M5 7h14" }), h("path", { d: "M5 7l-2.5 6a2.5 2.5 0 0 0 5 0z M19 7l-2.5 6a2.5 2.5 0 0 0 5 0z" })),
  quality: svg(h("path", { d: "M6 3h12l3 6-9 12L3 9z" }), h("path", { d: "M3 9h18M9.5 3L12 21M14.5 3L12 21" }))
};
function Bench({ live, set }) {
  const b = live.bench || {}, last = (live.game_profile || {}).bench, refresh = live.refresh || 90;
  const busy = b.state === "waiting" || b.state === "running";
  const start = () => set(async () => {
    const r = await rpc.benchStart();
    notify("GFG Extreme \xB7 Benchmark", r && r.ok === false ? r.error : "Close Quick Access: the 20 s start in game. Do not touch anything.");
  });
  if (b.state === "done") {
    const r = b.result || {}, m = r.medians || {};
    return h(
      Card,
      { title: "BENCHMARK DONE" },
      h(Row, { k: "Base FPS", v: `${r.point || "\u2014"} \xB7 ${multText(refresh, r.point)}`, first: true }),
      h(Row, { k: "Expected power", v: r.watts ? `~${r.watts} W` : "\u2014" }),
      h(Row, { k: "Medians at 15 W", v: `${fmt(m.real)} FPS \xB7 GPU ${fmt(m.gpu, 0, "%")} \xB7 ${fmt(m.temp_c, 0, " \xB0C")}` }),
      h("div", { className: "sub" }, "Autopilot starts here and still adapts to heavier and lighter scenes."),
      h(
        "div",
        { className: "btns" },
        h(Focusable, { className: "btn red", onClick: () => set(() => rpc.benchAnswer(true)) }, "Accept"),
        h(Focusable, { className: "btn", onClick: () => set(() => rpc.benchAnswer(false)) }, "No, keep searching")
      )
    );
  }
  return h(
    Card,
    { title: "BENCHMARK" },
    h(
      Focusable,
      { className: "btn" + (busy ? "" : " red"), onClick: busy ? () => set(() => rpc.benchAnswer(false)) : start },
      busy ? b.state === "running" ? `Measuring \xB7 ${b.seconds_left} s \xB7 tap to cancel` : "Close Quick Access to start \xB7 tap to cancel" : "Run benchmark"
    ),
    b.state === "cancelled" ? h("div", { className: "note bad" }, "Benchmark cancelled: " + b.reason + ".") : null,
    h("div", { className: "sub", style: { marginTop: 6 } }, !live.game ? "Start a game first: 20 s in game at 15 W, generation off." : last ? `Last for this game: base ${last.point} ${multText(refresh, last.point)} \xB7 accepted` : "20 s in game at 15 W, generation off: a starting point for Autopilot.")
  );
}
function Dash({ s, set }) {
  const [layout, next] = useLayout();
  const live = s.live || {}, eng = live.engine || {}, gov = live.governor || {}, sen = live.sensors || {}, split = live.split || {};
  const prof = s.settings.profiles[s.profiles.active] || s.settings.profiles.default;
  const refresh = live.refresh || 90, fps = num((live.live || {}).fps), real = num((live.live || {}).real);
  const point = (live.pilot || {}).point || 0;
  const [head, body] = heroLine(live);
  const ph = phaseOf((live.pilot || {}).phase);
  const ring = layout === "arc" ? h(Arc, { frac: (fps || 0) / refresh, label: fmt(fps), sub: real !== null ? Math.round(real) + " REAL" : "" }) : h(Ring, { ...{ side: { size: 112, stroke: 7 }, classic: { size: 176, stroke: 9 }, compact: { size: 128, stroke: 7 } }[layout], frac: (fps || 0) / refresh, label: fmt(fps), sub: real !== null ? Math.round(real) + " REAL" : "" });
  const status = h(
    "div",
    { className: "st" },
    h("h3", null, h("b", null, multText(refresh, point, eng)), point ? ` \xB7 ${point} FPS` : ""),
    h("p", null, head, h("br"), live.game ? `${gameName(live.app)} \xB7 ${(OBJ[live.objective] || [live.objective])[0]}` : body),
    h("div", { className: "phase" }, PHASES.map((p) => h("span", { key: p, className: p === ph ? "on" : "" }, p)))
  );
  const scope = (s.profiles.active || "").startsWith("app:") ? "game" : "default";
  const setProf = (changes) => set(() => rpc.setProfile(scope, changes));
  const above = !!s.settings.engine.above_x3, minCap = above ? 20 : Math.ceil(refresh / 3);
  const fgOpts = [["off", "Off"], ["auto", "Auto"], ["x2", "\xD72"], ["x3", "\xD73"], ...above ? [["x3.75", "\xD73.75"]] : [], ["custom", "Custom"]];
  const cpuGhz = split.cap_khz ? (split.cap_khz / 1e6).toFixed(1) : null;
  const pace = num((live.live || {}).pace), hdr = !!(eng.transfer && eng.transfer !== "sdr");
  const short = !!(point && real !== null && real < 0.9 * point);
  return h(
    "div",
    null,
    h("div", { className: "card hero" + (layout === "side" ? "" : " col") }, h(Focusable, { className: "herotap", onClick: next }, ring), status),
    h(
      "div",
      { className: "minis" },
      // TDP: 12 W good, 9-10 W ideal (user, 3.0.3); 20 W is way off.
      h(Mini, { frac: frac(gov.tdp_w, gov.ceiling_w || 15), v: fmt(gov.tdp_w, 1), u: "W", k: "TDP", t: off(gov.tdp_w, 10, 20) }),
      // APU: the Governor steps down from 90 C, 97 C is critical.
      h(Mini, { frac: frac(sen.temp_c, 100), v: fmt(sen.temp_c, 0), u: "\xB0C", k: "APU", t: off(sen.temp_c, 70, 95) }),
      h(Mini, { frac: frac(pace, 1), v: pace === null ? "\u2014" : (100 * pace).toFixed(1), u: "%", k: "PACE", t: off(pace === null ? null : 100 * pace, 99.5, 95) }),
      h(Mini, { frac: 1, v: hdr ? "HDR" : "SDR", k: "COLOR" }),
      h(Mini, { frac: frac(sen.cpu_top_core_pct, 100), v: fmt(sen.cpu_top_core_pct, 0), u: "%", k: "CPU TOP", t: off(sen.cpu_top_core_pct, 70, 100) }),
      // GPU: a busy GPU is the point of a low TDP; it is off only when the game misses its cap too.
      h(Mini, {
        frac: frac(sen.gpu_busy_pct, 100),
        v: fmt(sen.gpu_busy_pct, 0),
        u: "%",
        k: "GPU",
        t: num(sen.gpu_busy_pct) === null ? null : short ? off(sen.gpu_busy_pct, 80, 98) : 0.25 * off(sen.gpu_busy_pct, 90, 100)
      }),
      // CPU clock: a cap Power Split kept saves watts; MAX is fine, not ideal.
      h(Mini, { frac: split.cap_khz && split.max_khz ? split.cap_khz / split.max_khz : 1, v: cpuGhz || "MAX", u: cpuGhz ? "GHz" : "", k: "CPU CLOCK", t: cpuGhz ? 0 : 0.3 }),
      h(Mini, { frac: frac(sen.fan_rpm, FAN_MAX), v: num(sen.fan_rpm) === null ? "\u2014" : (sen.fan_rpm / 1e3).toFixed(1), u: "k rpm", k: "FAN", t: off(sen.fan_rpm, 3500, 7e3) })
    ),
    h(Card, { title: "MODE" }, h("div", { className: "grid2" }, Object.entries(OBJ).map(([k, [name, sub]]) => h(Focusable, { key: k, onClick: () => setProf({ objective: k }) }, h(
      "div",
      { className: "tile mode m-" + k + (prof.objective === k ? " on" : "") },
      h("div", { className: "mico" }, ICON[k]),
      h(
        "div",
        null,
        h("b", null, name),
        h("span", null, k === "autopilot" && prof.objective === "autopilot" && live.objective && live.objective !== "autopilot" ? "now " + (OBJ[live.objective] || [live.objective])[0] : objSub(k, sub, above))
      )
    ))))),
    h(
      Card,
      { title: "FRAME GENERATION" },
      h(Seg, { value: prof.fg === "x3.75" && !above ? "x3" : prof.fg, options: fgOpts, onChange: (v) => setProf({ fg: v }) }),
      prof.fg === "custom" ? h(
        "div",
        { className: "lrow first", style: { marginTop: 6 } },
        "Base FPS cap",
        h(
          "div",
          { className: "step" },
          h(Focusable, { className: "b", onClick: () => setProf({ base_fps: Math.max(minCap, Math.max(minCap, prof.base_fps) - 1) }) }, "\u2212"),
          h("span", { className: "val" }, Math.max(minCap, prof.base_fps)),
          h(Focusable, { className: "b", onClick: () => setProf({ base_fps: Math.min(90, prof.base_fps + 1) }) }, "+")
        )
      ) : null,
      h("div", { className: "note" }, prof.fg === "custom" ? `The game is capped at ${Math.max(minCap, prof.base_fps)} FPS, generation fills ${refresh} Hz.` : `Custom: the game is capped at your base FPS (${minCap}\u201390), generation fills the display.`)
    ),
    h(Card, { title: "SETTINGS APPLY TO" }, h(Seg, {
      value: scope,
      options: [["game", "This game"], ["default", "All games"]],
      onChange: (v) => set(() => v === "game" ? rpc.setProfile("game", {}) : rpc.dropGame())
    })),
    h(Bench, { live, set })
  );
}
var SWATCH = {
  off: "linear-gradient(135deg,#2a2a31,#151519)",
  sharp: "linear-gradient(135deg,#6f7682,#f2f5fa)",
  vivid: "linear-gradient(135deg,#ff2d55,#ffcc00 55%,#34c759)",
  hdr: "linear-gradient(135deg,#ff9500,#ffe7b0 50%,#2f7cf6)",
  cinema: "linear-gradient(135deg,#0f6a6a,#e09a3e)",
  noir: "linear-gradient(135deg,#050505,#d9d9d9)",
  retro: "linear-gradient(135deg,#6b3f17,#e6c27a)",
  smooth: "linear-gradient(135deg,#3a4a66,#9fb4d9)"
};
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
  const presets = cat && cat.presets || [], effects = cat && cat.effects || [];
  const names = Object.fromEntries(effects.map((e) => [e.key, e.name]));
  const same = (a, b) => JSON.stringify([...a.effects || []].sort()) === JSON.stringify([...b.effects || []].sort()) && (a.sharpen || "none") === (b.sharpen || "none") && (a.aa || "none") === (b.aa || "none");
  const active = (presets.find((p) => same(f, p.filters)) || {}).id || "custom";
  const hud = s.settings.hud;
  const hdr = ((s.live || {}).engine || {}).transfer && s.live.engine.transfer !== "sdr";
  const chain = f.effects || [];
  const step = (k, dv) => put({ [k]: Math.max(0, Math.min(1, Math.round(((f[k] || 0) + dv) * 20) / 20)) });
  const stepper = (k) => h(
    "div",
    { className: "step" },
    h(Focusable, { className: "b", onClick: () => step(k, -0.05) }, "\u2212"),
    h("span", { className: "val" }, Math.round((f[k] || 0) * 100) + "%"),
    h(Focusable, { className: "b", onClick: () => step(k, 0.05) }, "+")
  );
  return h(
    "div",
    null,
    h(
      Card,
      { title: "LOOK" },
      h("div", { className: "fgrid" }, presets.map((p) => h(
        Focusable,
        { key: p.id, className: "ftile" + (active === p.id ? " on" : ""), onClick: () => set(() => rpc.setProfile(scope, { filters: p.id })) },
        h("div", { className: "sw", style: { background: SWATCH[p.id] || SWATCH.off } }, p.id === "off" ? h("i", { className: "slash" }) : null),
        h("div", { className: "fl" }, p.name)
      ))),
      h("div", { className: "fmore" }, h("span", null, active === "custom" ? "Custom \xB7 " + lookSummary(f, names) : lookSummary(f, names)))
    ),
    h(
      Card,
      { title: "SHARPENING" },
      h(Seg, { value: f.sharpen, options: [["none", "Off"], ["cas", "CAS"], ["dls", "DLS"]], onChange: (v) => put({ sharpen: v }) }),
      f.sharpen !== "none" ? h("div", { className: "lrow first", style: { marginTop: 6 } }, h("div", { className: "t2" }, h("b", null, "Strength"), h("span", null, "May show grain")), stepper("sharpness")) : null,
      f.sharpen === "dls" ? h("div", { className: "lrow" }, h("div", { className: "t2" }, h("b", null, "Denoise"), h("span", null, "Keeps DLS off film grain")), stepper("denoise")) : null,
      h("div", { className: "sec sec2" }, "ANTI-ALIASING"),
      h(Seg, { value: f.aa, options: [["none", "Off"], ["fxaa", "FXAA"], ["smaa", "SMAA"]], onChange: (v) => put({ aa: v }) })
    ),
    h(
      Card,
      { title: "EFFECTS \xB7 " + (chain.length ? chain.length + " ON" : "NONE") },
      h("div", { className: "egrid" }, effects.map((e) => {
        const on = chain.includes(e.key);
        return h(
          Focusable,
          { key: e.key, className: "echip" + (on ? " on" : ""), onClick: () => put({ effects: on ? chain.filter((x) => x !== e.key) : [...chain, e.key] }) },
          h("span", { className: "eord" + (on ? " on" : "") }, on ? "\u2713" : "+"),
          h("span", { className: "en" }, e.name)
        );
      })),
      chain.length ? h(Focusable, { className: "btn", style: { marginTop: 8 }, onClick: () => put({ effects: [] }) }, "Clear effects") : null,
      h("div", { className: "note" }, "Each effect costs some GPU time, the heavy ones (HDR Look, Clarity, SMAA) the most: with the Governor on, that can mean a little more power or a deeper ratio. " + (hdr ? "This game runs in HDR: colour effects are skipped, sharpening and anti-aliasing still apply." : "HDR games: colour effects are skipped, sharpening and anti-aliasing still apply."))
    ),
    h(
      Card,
      { title: "HDR" },
      h(Row, { k: "HDR output", first: true }, h(Tog, { on: s.settings.engine.hdr_output !== false, onChange: (v) => set(() => rpc.setSection("engine", { hdr_output: v })) })),
      h("div", { className: "sub" }, s.settings.engine.hdr_output !== false ? "On: HDR as set in Steam. Off: the screen and games get SDR." : "Off: the screen and games get SDR. A game started in HDR may need a restart.")
    ),
    h(
      Card,
      { title: "HUD" },
      h(Row, { k: "Show HUD in game", first: true }, h(Tog, { on: hud.enabled, onChange: (v) => set(() => rpc.setSection("hud", { enabled: v })) })),
      h("div", { className: "sec sec2" }, "POSITION"),
      h(Seg, { value: hud.position, options: [["top-right", "Top right"], ["top-left", "Top left"], ["bottom-left", "Bottom left"], ["bottom-right", "Bottom right"]], onChange: (v) => set(() => rpc.setSection("hud", { position: v })) }),
      h("div", { className: "sec sec2" }, "DETAIL"),
      h(Seg, { value: hud.detail, options: [["minimal", "Minimal"], ["standard", "Standard"]], onChange: (v) => set(() => rpc.setSection("hud", { detail: v })) })
    )
  );
}
function Engine({ s, set }) {
  const live = s.live || {}, eng = live.engine || {}, p = live.pilot || {}, gov = live.governor || {}, sen = live.sensors || {};
  const split = live.split || {}, gc = live.gpu_clock || {}, pol = live.policy || {}, cfg = s.settings;
  const [cap, setCap] = useState(null);
  const refresh = live.refresh || 90;
  const stateText = eng.state === "active" ? "Generating \xB7 " + multText(refresh, p.point, eng) : eng.state ? eng.state[0].toUpperCase() + eng.state.slice(1) : "Not running";
  const splitText = split.cap_khz ? `${(split.cap_khz / 1e6).toFixed(1)} GHz (${Math.round(100 * split.cap_khz / (split.max_khz || split.cap_khz))}%)${split.measured ? " \xB7 proven" : ""}` : split.phase === "off" ? "Full clock" : "Full clock \xB7 " + (split.reason || split.phase || "");
  const ab = split.pairs ? `${split.gain_pct >= 0 ? "+" : ""}${fmt(split.gain_pct, 1, "%")} GPU clock/W \xB7 ${split.pairs} A/B` : "Not measured yet";
  return h(
    "div",
    null,
    h(
      Card,
      { title: "KEDAVRA" },
      h(Row, { k: "State", v: stateText, first: true }),
      h(Row, { k: "Base cap", v: eng.cap_fps ? `${eng.cap_fps} FPS${eng.auto ? ` (Auto, floor ${eng.auto_floor || "\u2014"})` : ""}` : "\u2014" }),
      h(Row, { k: "GPU per frame", v: num(eng.gpu_us_avg) === null ? "\u2014" : (eng.gpu_us_avg / 1e3).toFixed(1) + " ms" }),
      h(Row, { k: "Color", v: eng.transfer === "pq" ? "HDR10 (PQ)" : eng.transfer === "scrgb" ? "HDR (scRGB)" : "SDR" }),
      h(Row, { k: "Policy", v: (pol.state || "\u2014")[0].toUpperCase() + (pol.state || "\u2014").slice(1) + (pol.epoch ? " \xB7 rev " + pol.epoch : "") })
    ),
    h(
      Card,
      { title: "AUTOPILOT" },
      h(Row, { k: "Point", v: p.point ? `${p.point} FPS \xB7 ${multText(refresh, p.point, eng)}` : "\u2014", first: true }),
      h(Row, { k: "Phase", v: phaseOf(p.phase) || "\u2014" }),
      h("div", { className: "sub", style: { padding: "0 2px 6px" } }, p.reason || ""),
      h("div", { className: "sec sec2" }, "PREFERENCE"),
      h(Seg, { value: cfg.autopilot.preference, options: [["auto", "Auto"], ["battery", "Battery"], ["smoothness", "Smoothness"]], onChange: (v) => set(() => rpc.setSection("autopilot", { preference: v })) })
    ),
    h(
      Card,
      { title: "POWER (GOVERNOR)" },
      h(Row, { k: "TDP control", first: true }, h(Tog, { on: cfg.power.enabled, onChange: (v) => set(() => rpc.setSection("power", { enabled: v })) })),
      h(Row, { k: "TDP now", v: num(gov.tdp_w) === null ? "\u2014" : `${fmt(gov.tdp_w, 1)} W of ${fmt(gov.ceiling_w, 0)} W` }),
      h(Row, { k: "APU draw", v: fmt(gov.draw_w, 1, " W") }),
      h(Row, { k: "CPU top core \xB7 GPU busy", v: `${fmt(sen.cpu_top_core_pct, 0, "%")} \xB7 ${fmt(sen.gpu_busy_pct, 0, "%")}` }),
      h("div", { className: "sec sec2" }, "POWER SPLIT"),
      h(Row, { k: "CPU \u2192 GPU watts", first: true }, h(Tog, { on: cfg.power.split, onChange: (v) => set(() => rpc.setSection("power", { split: v })) })),
      h(Row, { k: "CPU clock cap", v: splitText }),
      h(Row, { k: "A/B result", v: ab }),
      h("div", { className: "sec sec2" }, "GPU CLOCK \xB7 FAN"),
      h(Row, { k: "GPU clock ceiling", first: true }, h(Tog, { on: cfg.power.gpu_clock, onChange: (v) => set(() => rpc.setSection("power", { gpu_clock: v })) })),
      h(Row, { k: "GPU clock", v: gc.limit_mhz ? `${gc.limit_mhz} MHz cap \xB7 now ${fmt(sen.gpu_clock_mhz)} MHz` : `Auto \xB7 ${fmt(sen.gpu_clock_mhz)} MHz` }),
      h(Row, { k: "Fan", v: `SteamOS \xB7 ${fmt(sen.fan_rpm)} rpm` }),
      h("div", { className: "sub" }, "Power Split and the GPU ceiling act only on a locked point, when the TDP has settled. Every change restarts measurement.")
    ),
    h(
      Card,
      { title: "PACE CAPTURE" },
      h("div", { className: "sub" }, "Records every display flip, then checks pacing (P95, P99, missed)."),
      h(
        "div",
        { className: "btns" },
        h(Focusable, { className: "btn red", onClick: () => set(async () => setCap(await ((s.capture || {}).active ? rpc.stopCapture() : rpc.startCapture("run")))) }, (s.capture || {}).active ? "Stop capture" : "Start capture"),
        h(Focusable, { className: "btn", onClick: async () => setCap(await rpc.captures()) }, "Results")
      ),
      cap ? h("div", { className: "note" }, typeof cap === "string" ? cap : JSON.stringify(cap).slice(0, 400)) : null
    )
  );
}
var notify = (title, body) => {
  try {
    if (typeof toaster !== "undefined" && toaster) toaster.toast({ title, body, duration: 6e3 });
  } catch (e) {
  }
};
var resultText = (r, label) => r && (r.message || r.error || (r.path ? "Saved to " + r.path : null) || (r.rebooting ? "Rebooting now" : null)) || label + ": done";
function Setup({ s, set }) {
  const [diag, setDiag] = useState(null);
  const [msg, setMsg] = useState({ where: "", text: "", bad: false });
  const co = s.coexist || {}, mig = s.migration || {}, cfg = s.settings;
  const run = (where, label, f, busy) => set(async () => {
    setMsg({ where, text: busy + "\u2026", bad: false });
    notify("GFG Extreme", busy + "\u2026");
    try {
      const r = await f();
      const text = r && r.ok === false ? String(r.log || r.error || label + " failed") : resultText(r, label);
      const bad = !!(r && r.ok === false);
      setMsg({ where, text, bad });
      notify(bad ? "GFG Extreme \xB7 " + label + " failed" : "GFG Extreme \xB7 " + label, text.slice(0, 160));
      return r;
    } catch (e) {
      const text = String(e && e.message || e);
      setMsg({ where, text, bad: true });
      notify("GFG Extreme \xB7 " + label + " failed", text.slice(0, 160));
      throw e;
    }
  });
  const note = (where) => msg.where === where && msg.text ? h("div", { className: "note" + (msg.bad ? " bad" : "") }, msg.text) : null;
  const check = () => run("diag", "Checks", async () => {
    const d = await rpc.diagnose();
    setDiag(d);
    const bad = (d.checks || []).filter((c) => !c.ok).length;
    return { message: bad ? bad + " check" + (bad > 1 ? "s" : "") + " failed: see the list above" : "All checks passed" };
  }, "Running checks");
  const checks = diag && diag.checks || [];
  return h(
    "div",
    null,
    h(
      Card,
      { title: "ENGINE INSTALL" },
      checks.length ? checks.slice(0, 6).map((c) => h("div", { key: c.key, className: "check" }, h("b", { className: c.ok ? "" : "x" }, c.ok ? "\u2713" : "\u2717"), c.text)) : h("div", { className: "sub" }, diag ? "No checks returned." : "Checking\u2026"),
      h(
        "div",
        { className: "btns" },
        h(Focusable, { className: "btn", onClick: () => run("install", "Reinstall", rpc.install, "Installing the engine") }, "Reinstall"),
        h(Focusable, { className: "btn", onClick: () => run("install", "Remove", rpc.uninstall, "Removing the engine") }, "Remove"),
        h(Focusable, { className: "btn", onClick: () => run("install", "Reboot", rpc.reboot, "Rebooting the Deck") }, "Reboot")
      ),
      note("install")
    ),
    co.standalone && !co.taken_over ? h(
      Card,
      { title: "STANDALONE GSF KEDAVRA FOUND", cls: "warn" },
      h("div", { className: "sub" }, "Both plugins can drive the engine. GFG backs off instead of fighting."),
      h("div", { className: "btns" }, h(Focusable, { className: "btn red", onClick: () => run("coexist", "Take over", rpc.takeOver, "Taking over the engine") }, "Take over")),
      note("coexist")
    ) : null,
    h(
      Card,
      { title: "GENERATION" },
      h(Row, { k: "Frame generation in HDR games", first: true }, h(Tog, { on: cfg.engine.hdr, onChange: (v) => set(() => rpc.setSection("engine", { hdr: v })) })),
      h(Row, { k: "Allow above \xD73" }, h(Tog, { on: !!cfg.engine.above_x3, onChange: (v) => set(() => rpc.setSection("engine", { above_x3: v })) })),
      h("div", { className: "sub" }, cfg.engine.above_x3 ? "On: \xD73.75 in Battery, on a low battery and as a choice on Dash. More artefacts and latency." : "Off: no mode goes above \xD73. \xD73.75 shows more artefacts and latency.")
    ),
    // Boost 2.0 (user, 3.1.1): hidden down here, off by default.
    h(
      Card,
      { title: "EXPERIMENTAL" },
      h(Row, { k: "Boost 2.0", first: true }, h(Tog, { on: !!cfg.engine.boost, onChange: (v) => set(() => rpc.setSection("engine", { boost: v })) })),
      cfg.engine.boost ? h(Seg, { value: cfg.engine.boost_mult || 1.5, options: [[1.25, "\xD71.25"], [1.5, "\xD71.5"], [1.75, "\xD71.75"]], onChange: (v) => set(() => rpc.setSection("engine", { boost_mult: v })) }) : null,
      h("div", { className: "sub" }, "A camera turn of about a second with the right stick gets real frames: the multiplier drops for up to 1.5 s and comes back when the stick rests. Watts are not raised.")
    ),
    h(
      Card,
      { title: "DIAGNOSTICS" },
      h(Focusable, { onClick: check }, h(Row, { k: "Run checks", v: "\u203A", first: true })),
      h(Focusable, { onClick: () => run("diag", "Report", rpc.report, "Saving the report") }, h(Row, { k: "Save report to Desktop", v: "\u203A" })),
      h(Focusable, { onClick: () => run("diag", "Engine log", async () => ({ message: String(await rpc.logs()).slice(-600) }), "Reading the engine log") }, h(Row, { k: "Engine log", v: "\u203A" })),
      h(Focusable, { onClick: () => run("diag", "GPU benchmark", async () => {
        const r = await rpc.bench();
        return r && r.ok !== false ? { ...r, message: "Benchmark done. " + String(r.log || "").trim().slice(-240) } : r;
      }, "Running the GPU benchmark") }, h(Row, { k: "GPU benchmark", v: "\u203A" })),
      note("diag"),
      h("div", { className: "sec sec2" }, "TELEMETRY"),
      h(Seg, { value: cfg.telemetry.level, options: [["minimal", "Minimal"], ["standard", "Standard"], ["debug", "Debug"]], onChange: (v) => set(() => rpc.setSection("telemetry", { level: v })) })
    ),
    mig && mig.from ? h(Card, { title: "FROM GFG EXTREME 2.X" }, (mig.steps || []).slice(0, 4).map((t, i) => h("div", { key: i, className: "check" }, h("b", null, "\u2713"), String(t)))) : null,
    h("div", { className: "sub", style: { textAlign: "center", marginTop: 4 } }, `GFG Extreme ${s.version}${s.codename ? " " + s.codename : ""}`)
  );
}
function Gate({ g, set, version }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({ text: "", bad: false });
  const st = g.state;
  const go = (label, f, doing) => set(async () => {
    setBusy(true);
    setMsg({ text: doing + "\u2026", bad: false });
    notify("GFG Extreme", doing + "\u2026");
    try {
      const r = await f();
      const bad = !!(r && r.ok === false);
      const text2 = bad ? String(r.log || r.error || label + " failed") : resultText(r, label);
      setMsg({ text: text2, bad });
      notify("GFG Extreme \xB7 " + label + (bad ? " failed" : ""), text2.slice(0, 160));
    } catch (e) {
      const text2 = String(e && e.message || e);
      setMsg({ text: text2, bad: true });
      notify("GFG Extreme \xB7 " + label + " failed", text2.slice(0, 160));
    }
    setBusy(false);
  });
  const tiles = (a, b) => h(
    "div",
    { className: "steps" },
    h("div", { className: "st " + a }, h("b", null, "1"), "Install"),
    h("div", { className: "st " + b }, h("b", null, "2"), "Reboot"),
    h("div", { className: "st" }, h("b", null, "3"), "Play")
  );
  const install = h(Focusable, { className: "btn red", onClick: () => !busy && go("Install", rpc.install, "Installing the engine") }, busy ? "Installing\u2026" : st === "failed" ? "Try again" : g.update ? "Update engine" : "Install engine");
  let head, text, body;
  if (st === "reboot") {
    head = "Reboot to start the engine";
    text = "Installed. Gamescope KEDAVRA starts with the next boot; until then the Deck runs stock Gamescope.";
    body = [
      tiles("done", "on"),
      h(Focusable, { key: "r", className: "btn red", onClick: () => go("Reboot", rpc.reboot, "Rebooting the Deck") }, "Reboot now"),
      h("div", { key: "s", className: "small" }, "After the reboot open GFG Extreme again: all tabs unlock.")
    ];
  } else if (st === "failed") {
    head = "The engine could not be installed";
    text = "The panel stays locked so nothing runs half installed.";
    body = [
      tiles("on", ""),
      h(
        "div",
        { key: "b", className: "btns", style: { marginTop: 0 } },
        install,
        h(Focusable, { className: "btn", onClick: () => go("Report", rpc.report, "Saving the report") }, "Save report")
      ),
      h("div", { key: "e", className: "note bad" }, g.error || "Install failed.")
    ];
  } else {
    head = g.update ? "Update the KEDAVRA engine" : "Install the KEDAVRA engine";
    text = g.update ? "This GFG Extreme carries a newer engine. Install it, then reboot." : "GFG Extreme generates frames inside its own Gamescope. Install it first: nothing in SteamOS is overwritten, and Remove in Setup brings stock Gamescope back.";
    body = [tiles("on", ""), install, h("div", { key: "s", className: "small" }, "The panel opens after the engine is installed and the Deck has rebooted.")];
  }
  return h(
    "div",
    { className: "card hero col gate" },
    h("img", { className: "wolf", src: LOGO }),
    h("div", { className: "gh" }, head),
    h("div", { className: "gp" }, text),
    body,
    msg.text && st !== "failed" ? h("div", { className: "note" + (msg.bad ? " bad" : "") }, msg.text) : null,
    h("div", { className: "small" }, "GFG Extreme " + version)
  );
}
function Content() {
  const [s, setS] = useState(null);
  const [cat, setCat] = useState(null);
  const [tab, setTab] = useState(0);
  const [, bump] = useState(0);
  const load = useCallback(() => rpc.state().then(setS).catch(() => {
  }), []);
  useEffect(() => {
    load();
    rpc.catalog().then(setCat).catch(() => {
    });
    const t = setInterval(load, 1e3);
    const f = () => bump((x) => x + 1);
    errs.subs.add(f);
    return () => {
      clearInterval(t);
      errs.subs.delete(f);
    };
  }, []);
  const set = async (f) => {
    try {
      await f();
    } catch (e) {
    }
    load();
  };
  const step = (d) => setTab((t) => (t + d + TABS.length) % TABS.length);
  const GB = window.DFL && window.DFL.GamepadButton || {};
  const onButtonDown = (e) => {
    if (s && s.gate && s.gate.state && s.gate.state !== "ready") return;
    const b = e && e.detail && e.detail.button;
    if (b === (GB.BUMPER_LEFT ?? 5)) step(-1);
    else if (b === (GB.BUMPER_RIGHT ?? 6)) step(1);
  };
  const gated = !!(s && s.gate && s.gate.state && s.gate.state !== "ready");
  const body = !s ? h("div", { className: "sub" }, "Loading\u2026") : gated ? h(Gate, { g: s.gate, set, version: s.version }) : h([Dash, Graphics, Engine, Setup][tab], { s, set, cat });
  return h(
    Focusable,
    { className: "gfg", onButtonDown },
    h("style", null, css),
    h(
      "div",
      { className: "top" },
      h("div", { className: "brand" }, h("img", { src: LOGO }), "GFG \xB7", h("b", null, "EXTREME")),
      h("div", { className: "chip" }, h("i"), s && s.device || "Steam Deck")
    ),
    gated ? null : h(
      "div",
      { className: "tabs" },
      h(Focusable, { className: "bump", onClick: () => step(-1) }, "L1"),
      TABS.map((t, i) => h(Focusable, { key: t, className: "tab" + (i === tab ? " on" : ""), onClick: () => setTab(i) }, t)),
      h(Focusable, { className: "bump", onClick: () => step(1) }, "R1")
    ),
    errs.last ? h("div", { className: "err" }, `${errs.last.name}: ${errs.last.message}`) : null,
    body
  );
}
var Icon = () => h("img", { src: LOGO, width: 20, height: 20 });
var app_default = definePlugin(() => ({
  name: "GFG Extreme",
  titleView: h("div", { className: window.DFL.staticClasses.Title }, "GFG \xB7 EXTREME"),
  alwaysRender: true,
  content: h(Content, null),
  icon: h(Icon, null),
  onDismount() {
  }
}));
export {
  app_default as default
};
