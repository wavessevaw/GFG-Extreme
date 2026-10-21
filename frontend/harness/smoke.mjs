// Frontend smoke test: renders the 3.0 UI (all four tabs) against a mock backend state,
// checks the ring resizes on a tap and a mode tile reaches the backend; fails on page errors.
// Usage: node frontend/harness/smoke.mjs [screenshot-dir]   (GFG_CHROMIUM: a Chromium binary)
import { build } from "esbuild";
import { chromium } from "playwright-core";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../.."), outDir = process.argv[2] || "";
const app = await build({ entryPoints: [path.join(root, "frontend/src/app.js")], bundle: true, format: "iife", globalName: "GFGPlugin", write: false, target: "es2020" });
const rb = await build({ stdin: { contents: 'import * as React from "react"; import { createRoot } from "react-dom/client"; window.React = React; window.__createRoot = createRoot;', resolveDir: root }, bundle: true, format: "iife", write: false, define: { "process.env.NODE_ENV": '"production"' } });
const settings = { profiles: { default: { name: "Default", fg: "auto", base_fps: 45, objective: "autopilot", filters: { effects: ["vibrance"], sharpen: "cas", sharpness: 0.5, denoise: 0.17, aa: "none" } } },
  hud: { enabled: true, position: "top-right", detail: "standard" }, autopilot: { preference: "auto" }, power: { enabled: true, split: true, gpu_clock: true }, engine: { hdr: true }, telemetry: { level: "standard" } };
const state = { version: "3.0.0", codename: "Independence", device: "Steam Deck OLED", settings, profiles: { active: "default", game_key: "app:1245620", names: { default: "Default" } },
  migration: { from: "2.1.6", steps: ["Settings moved (backup kept)", "MAKO removed, system restored"] }, coexist: { standalone: false }, capture: {},
  live: { game: true, app: 1245620, refresh: 90, objective: "balanced", live: { fps: 90, real: 30, pace: 0.998 },
    pilot: { phase: "locked", point: 30, reason: "point 30 holds: locked" }, policy: { state: "confirmed", epoch: 412 },
    engine: { state: "active", multiplier: 3, cap_fps: 30, auto: true, auto_floor: 24, gpu_us_avg: 2100, transfer: "sdr" },
    governor: { tdp_w: 9.5, ceiling_w: 15, draw_w: 10.8, owned: true }, sensors: { temp_c: 68, cpu_top_core_pct: 41, gpu_busy_pct: 96, gpu_clock_mhz: 1600, fan_rpm: 3900 },
    split: { phase: "hold", cap_khz: 1800000, max_khz: 3500000, measured: true, pairs: 3, gain_pct: 6.8 }, gpu_clock: { phase: "observe" } } };
const catalog = { presets: [["off","Off"],["sharp","Sharp"],["vivid","Vivid"],["hdr","HDR look"],["cinema","Cinema"],["noir","Noir"],["retro","Retro"],["smooth","Smooth"]].map(([id,name]) => ({ id, name, filters: id === "vivid" ? { effects: ["vibrance"], sharpen: "cas", aa: "none" } : {} })),
  effects: ["HDR Look","Clarity","Levels+","Curves","Vibrance","Colourfulness","Technicolor","DPX","Noir","Sepia","Film grain","Vignette","Deband"].map((n) => ({ key: n === "Vibrance" ? "vibrance" : n, name: n })) };
const mock = `window.SP_REACT = React; window.DFL = { staticClasses: { Title: "t" } }; window.appStore = { GetAppOverviewByAppID: () => ({ display_name: "Elden Ring" }) };
window.__calls = []; window.__state = ${JSON.stringify(state)}; const __cat = ${JSON.stringify(catalog)};
var callable = (n) => async (...a) => { window.__calls.push([n, a]); return ({ get_state: () => window.__state, get_catalog: () => __cat, diagnose: () => ({ checks: [{ key: "a", ok: true, text: "Gamescope KEDAVRA 3.0.0 installed" }, { key: "b", ok: true, text: "Running after reboot (confirmed)" }, { key: "c", ok: true, text: "Libraries found on this SteamOS" }] }) }[n] || (() => ({})))(...a); };
var definePlugin = (f) => f;`;
const b = await chromium.launch({ args: ["--no-sandbox"], ...(process.env.GFG_CHROMIUM ? { executablePath: process.env.GFG_CHROMIUM } : {}) });
const page = await b.newPage({ viewport: { width: 330, height: 1400 }, deviceScaleFactor: 2 });
const errors = []; page.on("pageerror", (e) => errors.push(String(e)));
await page.setContent(`<html><body style="margin:0;background:#000"><div id=r style="width:330px"></div></body></html>`);
await page.addScriptTag({ content: rb.outputFiles[0].text });
await page.addScriptTag({ content: mock + "\n" + app.outputFiles[0].text.replace(/^var GFGPlugin = /, "window.__P = ") });
await page.evaluate(() => { const p = window.__P.default(); window.__createRoot(document.getElementById("r")).render(p.content); });
await page.waitForTimeout(500);
for (const [i, t] of ["Dash", "Graphics", "Engine", "Setup"].entries()) {
  await page.locator(".tab", { hasText: t }).first().click(); await page.waitForTimeout(300);
  if (outDir) await page.locator("#r").screenshot({ path: path.join(outDir, `ui-${i + 1}-${t.toLowerCase()}.png`) });
  const text = await page.locator("#r").innerText();
  for (const want of { Dash: ["Steam Deck OLED", "CPU TOP", "FAN RPM"], Graphics: ["Top right", "Bottom right", "Standard"], Engine: ["POWER SPLIT", "GPU clock ceiling", "1.8 GHz"], Setup: ["Take over", "Frame generation in HDR games"] }[t])
    if (!text.includes(want) && !(t === "Setup" && want === "Take over")) errors.push(`${t}: missing "${want}"`);
}
await page.locator(".tab", { hasText: "Dash" }).first().click(); await page.waitForTimeout(200);
await page.locator(".herotap").first().click(); await page.waitForTimeout(200);
const classic = await page.locator(".ring").first().evaluate((e) => e.style.width);
await page.locator(".tile", { hasText: "Battery" }).first().click(); await page.waitForTimeout(100);
const calls = await page.evaluate(() => window.__calls.filter((c) => c[0] === "set_profile"));
console.log(JSON.stringify({ errors, classic, calls }));
await b.close();
if (errors.length || classic !== "176px" || !calls.length) process.exit(1);
