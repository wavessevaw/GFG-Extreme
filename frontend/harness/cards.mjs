// README cards: renders the real 3.0 UI (same mock backend as smoke.mjs) and lays the shots out
// on 2.x-style cards in docs/img.
// Usage: node frontend/harness/cards.mjs [hud-png-dir]   (GFG_CHROMIUM: a Chromium binary)
import { build } from "esbuild";
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../.."), hudDir = process.argv[2] || "";
const img = path.join(root, "docs/img");
const app = await build({ entryPoints: [path.join(root, "frontend/src/app.js")], bundle: true, format: "iife", globalName: "GFGPlugin", write: false, target: "es2020" });
const rb = await build({ stdin: { contents: 'import * as React from "react"; import { createRoot } from "react-dom/client"; window.React = React; window.__createRoot = createRoot;', resolveDir: root }, bundle: true, format: "iife", write: false, define: { "process.env.NODE_ENV": '"production"' } });
const settings = (objective) => ({ profiles: { default: { name: "Default", fg: "auto", base_fps: 45, objective, filters: { effects: ["vibrance"], sharpen: "cas", sharpness: 0.5, denoise: 0.17, aa: "none" } } },
  hud: { enabled: true, position: "top-right", detail: "standard" }, autopilot: { preference: "auto" }, power: { enabled: true, split: true, gpu_clock: true }, engine: { hdr: true }, telemetry: { level: "standard" } });
const state = ({ objective = "autopilot", live = "balanced", real = 30, mult = 3, tdp = 9.5 } = {}) => ({ version: "3.0.0", codename: "Independence", device: "Steam Deck OLED", settings: settings(objective),
  profiles: { active: "default", game_key: "app:1245620", names: { default: "Default" } }, migration: {}, coexist: { standalone: false }, capture: {},
  live: { game: true, app: 1245620, refresh: 90, objective: live, live: { fps: 90, real, pace: 0.998 },
    pilot: { phase: "locked", point: real, reason: `point ${real} holds: locked` }, policy: { state: "confirmed", epoch: 412 },
    engine: { state: "active", multiplier: mult, cap_fps: real, auto: true, auto_floor: 24, gpu_us_avg: 2100, transfer: "sdr" },
    governor: { tdp_w: tdp, ceiling_w: 15, draw_w: tdp + 1.3, owned: true }, sensors: { temp_c: 68, cpu_top_core_pct: 41, gpu_busy_pct: 96, gpu_clock_mhz: 1600, fan_rpm: 3900 },
    split: { phase: "hold", cap_khz: 1800000, max_khz: 3500000, measured: true, pairs: 3, gain_pct: 6.8 }, gpu_clock: { phase: "observe" } } });
const catalog = { presets: [["off","Off"],["sharp","Sharp"],["vivid","Vivid"],["hdr","HDR look"],["cinema","Cinema"],["noir","Noir"],["retro","Retro"],["smooth","Smooth"]].map(([id,name]) => ({ id, name, filters: id === "vivid" ? { effects: ["vibrance"], sharpen: "cas", aa: "none" } : {} })),
  effects: ["HDR Look","Clarity","Levels+","Curves","Vibrance","Colourfulness","Technicolor","DPX","Noir","Sepia","Film grain","Vignette","Deband"].map((n) => ({ key: n === "Vibrance" ? "vibrance" : n, name: n })) };
const mock = `try { localStorage.length; } catch (e) { const m = {}; Object.defineProperty(window, "localStorage", { value: { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } } }); }
window.SP_REACT = React; window.DFL = { staticClasses: { Title: "t" } }; window.appStore = { GetAppOverviewByAppID: () => ({ display_name: "Elden Ring" }) };
window.__state = null; const __cat = ${JSON.stringify(catalog)};
var callable = (n) => async (...a) => ({ get_state: () => window.__state, get_catalog: () => __cat, diagnose: () => ({ checks: [{ key: "a", ok: true, text: "Gamescope KEDAVRA 3.0.0 installed" }, { key: "b", ok: true, text: "Running after reboot (confirmed)" }, { key: "c", ok: true, text: "Libraries found on this SteamOS" }] }) }[n] || (() => ({})))(...a);
var definePlugin = (f) => f;`;
const b = await chromium.launch({ args: ["--no-sandbox"], ...(process.env.GFG_CHROMIUM ? { executablePath: process.env.GFG_CHROMIUM } : {}) });
const page = await b.newPage({ viewport: { width: 330, height: 300 }, deviceScaleFactor: 2 });
const errors = []; page.on("pageerror", (e) => errors.push(String(e)));
await page.setContent(`<html><body style="margin:0;background:#000"><div id=r style="width:330px"></div></body></html>`);
await page.addScriptTag({ content: rb.outputFiles[0].text });
await page.addScriptTag({ content: mock + "\n" + app.outputFiles[0].text.replace(/^var GFGPlugin = /, "window.__P = ") });

// One shot of the panel (or one element of it) for a backend state, ring layout and tab.
async function shot(st, { layout = "side", tab = "Dash", sel = "#r" } = {}) {
  await page.evaluate(([s, l]) => { window.__state = s; localStorage.setItem("gfg3.ring", l); if (window.__root) window.__root.unmount();
    window.__root = window.__createRoot(document.getElementById("r")); window.__root.render(window.__P.default().content); }, [st, layout]);
  await page.waitForTimeout(400);
  if (tab !== "Dash") { await page.locator(".tab", { hasText: tab }).first().click(); await page.waitForTimeout(300); }
  return (await page.locator(sel).first().screenshot()).toString("base64");
}
const css = `body{margin:0;background:#0a0a0c;font-family:Inter,"Segoe UI",system-ui,sans-serif}
.w{display:inline-flex;gap:40px;padding:44px 48px 36px;align-items:flex-start;background:radial-gradient(90% 60% at 50% 0%,#170b0c 0%,#0a0a0c 70%)}
.c{display:flex;flex-direction:column;align-items:center}
.f{border:1px solid #2e2e36;border-radius:22px;overflow:hidden;box-shadow:0 0 40px rgba(251,13,0,.08),inset 0 1px 0 rgba(255,255,255,.04)}
.f img{display:block}
.l{margin-top:18px;font-size:13px;font-weight:700;letter-spacing:.24em;color:#a1a1ab}.l b{color:#fb0d00}`;
async function card(name, panels, width) {
  const cp = await b.newPage({ viewport: { width: 400, height: 400 }, deviceScaleFactor: 2 });
  await cp.setContent(`<html><head><style>${css}</style></head><body><div class=w>${panels.map(([png, label, w]) =>
    `<div class=c><div class=f><img src="data:image/png;base64,${png}" style="width:${w || width}px"></div><div class=l>${label}</div></div>`).join("")}</div></body></html>`);
  await cp.waitForTimeout(200);
  await cp.locator(".w").screenshot({ path: path.join(img, name) });
  await cp.close();
}

const base = state();
await card("card-overview.png", [
  [await shot(base), "<b>DASH</b> · LIVE POINT"],
  [await shot(base, { tab: "Graphics" }), "GRAPHICS · FILTERS & HUD"],
  [await shot(base, { tab: "Engine" }), "ENGINE · POWER"],
  [await shot(base, { tab: "Setup" }), "SETUP · INSTALL & LOGS"]], 330);
await card("card-modes.png", [
  [await shot(state({ objective: "battery", live: "battery", real: 30, mult: 3, tdp: 8 }), { sel: ".hero" }), "BATTERY"],
  [await shot(state({ objective: "balanced", live: "balanced", real: 45, mult: 2, tdp: 10 }), { sel: ".hero" }), "BALANCED"],
  [await shot(state({ objective: "quality", live: "quality", real: 45, mult: 2, tdp: 12 }), { sel: ".hero" }), "QUALITY"],
  [await shot(state({ objective: "autopilot", live: "battery", real: 24, mult: 3.75, tdp: 7 }), { sel: ".hero" }), "<b>AUTOPILOT</b> · X3.75"]], 310);
await card("card-ring-sizes.png", [
  [await shot(base, { layout: "side", sel: ".hero" }), "SIDE"],
  [await shot(base, { layout: "classic", sel: ".hero" }), "CLASSIC"],
  [await shot(base, { layout: "compact", sel: ".hero" }), "COMPACT"],
  [await shot(base, { layout: "arc", sel: ".hero" }), "ARC"]], 310);
if (hudDir) {
  const hud = (f) => fs.readFileSync(path.join(hudDir, f)).toString("base64");
  await card("hud-rings-gfg3.png", [[hud("hud-minimal.png"), "HUD · MINIMAL", 152], [hud("hud-standard.png"), "HUD · STANDARD", 368]]);
}
console.log(JSON.stringify({ errors }));
await b.close();
if (errors.length) process.exit(1);
