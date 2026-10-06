import { build } from "/opt/npm-tools/node_modules/esbuild/lib/main.js";
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire("/opt/npm-tools/node_modules/");
const { chromium } = require("playwright");
const out = await build({ entryPoints: ["src/app.js"], bundle: true, format: "iife", globalName: "GFGPlugin", write: false, target: "es2020" });
const rb = await build({ entryPoints: ["harness/reactbundle.js"], bundle: true, format: "iife", write: false, nodePaths: ["/opt/npm-tools/node_modules"], define: {"process.env.NODE_ENV":"\"development\""} });
const reactJs = rb.outputFiles[0].text; const domJs = "";
const dev = (mode, target) => ({ mode, target, reason: { oled: "Steam Deck OLED panel runs 90 Hz", lcd: "Steam Deck LCD panel tops out at 60 Hz", dock: "External display: 60 FPS" }[mode] });
const base = { hud: { enabled: true, preset: "standard", position: "top-left" }, success: true, enabled: false, state: "DISABLED", telemetry: {}, power: {}, limitations: ["a game must be (re)launched after Governor is enabled to use the overlay and diagnostics"], ladder: { attempts: 2, max_attempts: 6 } };
const tel = (real, out, m) => ({ real: { median: real }, output: { median: out }, latest: { effective_multiplier: m } });
const STATES = {
  "home-idle-oled": { ...base, device: dev("oled", 90), target_output_fps: 90 },
  "home-measuring": { ...base, enabled: true, state: "PROBE", device: dev("oled", 90), target_output_fps: 90, capability: {} },
  "home-locked-oled": { ...base, enabled: true, state: "LOCKED", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(45, 90, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, active_point_mode: "applied", power: { owned: true, observed_tdp_w: 9, saved_w: 15 }, effort: { level: "medium" }, battery: { minutes_left: 125 } },
  "home-locked-lcd": { ...base, enabled: true, state: "OPTIMIZE_POWER", device: dev("lcd", 60), target_output_fps: 60, telemetry: tel(30, 60, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 8, saved_w: 15 }, effort: { level: null, assessing: true } },
  "home-relaunch-dock": { ...base, enabled: true, state: "PLAN", device: dev("dock", 60), target_output_fps: 60, capability: { reason: "relaunch-required-for-governor-overlay" } },
};
const mockSrc = (state, extra) => `
window.SP_REACT = React; window.DFL = { staticClasses: { Title: "t" }, Focusable: null };
window.__state = ${JSON.stringify(state)};
window.__cfg = ${JSON.stringify(extra.cfg || { fg_backend: "gfg", multiplier: 2, })};
var callable = (n) => async (...a) => ({ get_governor_status: () => window.__state, get_profiles: () => ({ profiles: ["Default", "Elden Ring", "Cyberpunk 2077"], current_profile: "Elden Ring" }),
  get_profile_config: () => ({ config: window.__cfg }), get_pipeline_inspector: () => ({ saved: { fg_backend: "gfg", multiplier: 2, scaling: "off" }, effective: { fg_backend: "gfg", multiplier: 2, scaling: "off" }, actual: { renderer: "loaded", multiplier: 2 } }),
  get_launch_option: () => ({ launch_option: "/home/deck/.local/bin/gfg %command%" }) }[n] || (() => ({ success: true })))();
var definePlugin = (f) => f;`;
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined, args: ["--no-sandbox"] });
const shots = [];
async function shot(name, state, nav, extra = {}) {
  const page = await browser.newPage({ viewport: { width: 330, height: 760 }, deviceScaleFactor: 2 });
  const code = out.outputFiles[0].text.replace(/^var GFGPlugin = /, "window.__P = ");
  await page.setContent(`<html><body style="margin:0;background:#0a0a0c"><div id=r></div></body></html>`);
  await page.addScriptTag({ content: reactJs });
  await page.addScriptTag({ content: mockSrc(state, extra) + "\n" + code + "\nwindow.__P=GFGPlugin;" });
  await page.evaluate(() => { const p = window.__P.default(); window.__createRoot(document.getElementById("r")).render(p.content); });
  await page.waitForTimeout(400);
  for (const t of nav) { await page.getByText(t, { exact: true }).first().click(); await page.waitForTimeout(250); }
  const f = `/tmp/claude-0/shots/${name}.png`; fs.mkdirSync("/tmp/claude-0/shots", { recursive: true });
  await page.screenshot({ path: f, fullPage: true }); shots.push(f); await page.close();
}
for (const [k, v] of Object.entries(STATES)) await shot(k, v, []);
await shot("page-governor", STATES["home-locked-oled"], ["Governor"]);
await shot("page-fg", STATES["home-locked-oled"], ["Frame Generation"]);
await shot("page-hud", STATES["home-locked-oled"], ["In-game overlay"]);
await shot("page-advanced", STATES["home-locked-oled"], ["Advanced"]);
await browser.close(); console.log(shots.join("\n"));
