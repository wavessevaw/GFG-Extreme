import { build } from "esbuild";
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
export const launch = () => chromium.launch({ args: ["--no-sandbox"], ...(process.env.GFG_CHROMIUM ? { executablePath: process.env.GFG_CHROMIUM } : {}) });
const out = await build({ entryPoints: [new URL("../src/app.js", import.meta.url).pathname], bundle: true, format: "iife", globalName: "GFGPlugin", write: false, target: "es2020" });
const rb = await build({ entryPoints: [new URL("./reactbundle.js", import.meta.url).pathname], bundle: true, format: "iife", write: false, define: {"process.env.NODE_ENV":"\"development\""} });
const reactJs = rb.outputFiles[0].text; const domJs = "";
const dev = (mode, target) => ({ mode, target, reason: { oled: "Steam Deck OLED panel runs 90 Hz", lcd: "Steam Deck LCD panel tops out at 60 Hz", dock: "External display: 60 FPS" }[mode] });
const base = { version: "1.0.0", hud: { enabled: true, preset: "standard", position: "top-left" }, success: true, enabled: false, state: "DISABLED", telemetry: {}, power: {}, limitations: ["a game must be (re)launched after Governor is enabled to use the overlay and diagnostics"], ladder: { attempts: 2, max_attempts: 6 } };
// Real backend shape: {snapshot, summary}.
const tel = (real, out, m) => ({ snapshot: { available: true }, summary: { real: { median: real }, output: { median: out }, latest: { effective_multiplier: m }, frametime: { p95_ms: 24.5, p99_ms: 31.2, stutter_ratio: 0.01 } } });
export const STATES = {
  "home-idle-oled": { ...base, device: dev("oled", 90), target_output_fps: 90 },
  "home-measuring": { ...base, enabled: true, state: "PROBE", device: dev("oled", 90), target_output_fps: 90, capability: {} },
  "home-locked-oled": { ...base, enabled: true, state: "LOCKED", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(45, 90, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, active_point_mode: "applied", power: { owned: true, observed_tdp_w: 9, saved_w: 15 }, effort: { level: "medium" }, battery: { minutes_left: 125 } },
  "home-budget-oled": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, active_point_mode: "applied", power: { owned: true, observed_tdp_w: 9, saved_w: 15 }, effort: { level: "easy" }, budget: { phase: "locked", point: "30x3", tdp_w: 9, tdp_control: true, tier: "ideal", probe: null, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-warm-start": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 8, saved_w: 15 }, effort: { level: "easy" }, budget: { phase: "locked", point: "30x3", tdp_w: 8, tdp_control: true, tier: "ideal", probe: null, warm_started: true, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-balanced": { ...base, enabled: true, state: "LOCKED", mode: "balanced", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(45, 90, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 12, saved_w: 15 }, effort: { level: "medium" }, budget: { phase: "locked", point: "45x2", tdp_w: 12, tdp_control: true, tier: "heavy", probe: null, flavor: "balanced", limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "log-saved": { ...base, __log: { recording: false, last_file: "/home/deck/Desktop/GFG-Extreme-log-1.zip", findings: ["No renderer diagnostics were written during the recording: the game was not started with the GFG launch command.", "Median output FPS 90 against a 90 FPS target."] } },
  "setup-bad": { ...base, __setup: { success: true, total: 3, failed: 2, checks: [{ check: "launch wrapper installed", ok: true }, { check: "host MangoHud Vulkan layer present", ok: false, detail: "/usr/share/vulkan/implicit_layer.d/MangoHud.json", advice: "MangoHud's Vulkan layer is not installed on this system, so the in-game overlay cannot appear." }, { check: "overlay config published (active.conf)", ok: false, detail: "/x/hud/active.conf", advice: "Turn the overlay on in Settings → In-game overlay." }] } },
  "home-paused-setup": { ...base, enabled: true, state: "PAUSED", reason: "diagnostics-active-no-events", device: dev("oled", 90), __setup: { success: true, total: 2, failed: 1, checks: [{ check: "renderer diagnostics log: present-diagnostics.log", ok: false, detail: "missing", advice: "Start the game with the GFG launch command (Settings → Launch command), then press RUN." }, { check: "launch wrapper installed", ok: true }] } },
  "readme-home": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, active_point_mode: "applied", power: { owned: true, observed_tdp_w: 9, saved_w: 15 }, effort: { level: "easy" }, battery: { minutes_left: 152 }, sensors: { temp_c: 68, temp_slope_c_per_min: 0.4, gpu_busy_pct: 94, cpu_top_core_pct: 61, battery_discharge_w: 12.8, fan_rpm: 3100 }, diagnosis: { bottleneck: "gpu", thermal: "ok", smoothness: "smooth" }, budget: { phase: "locked", point: "30x3", tdp_w: 9, tdp_control: true, tier: "ideal", probe: null, warm_started: true, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "budget-memory": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 10, saved_w: 15 }, effort: { level: "easy" }, budget: { phase: "locked", point: "30x3", tdp_w: 10, tdp_control: true, tier: "ideal", probe: null, verifying: "30x3", current_max_multiplier: 3, known_failures: { "33x2.75": 10 }, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-loading": { ...base, enabled: true, state: "PAUSED", reason: "diagnostics-events-no-fps-samples", device: dev("oled", 90) },
  "home-testing": { ...base, enabled: true, state: "APPLY", reason: "awaiting-fresh-evidence", device: dev("oled", 90), request: { point: "33x2.75" } },
  "home-last-session": { ...base, last_session: { minutes: 42.3, avg_output_fps: 89.6, avg_real_fps: 30.2, avg_tdp_w: 10.6, avg_draw_w: 10.1, reference_w: 15, saved_w: 4.4, max_temp_c: 83, hot_pct: 12, stutter_pct: 3, profile: "mako" } },
  "home-cooling": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, diagnosis: { thermal: "hot" }, sensors: { temp_c: 84 }, budget: { phase: "locked", point: "30x3", tdp_w: 8, tdp_control: true, tier: "ideal", thermal: "hot", thermal_deferred: true, heat_limited: true, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-history": { ...base, session_history: [{ minutes: 29, mode: "budget", avg_output_fps: 89.6, avg_tdp_w: 10.7, max_temp_c: 77 }, { minutes: 12, mode: "quality", avg_output_fps: 88.1, avg_tdp_w: 19.4 }] },
  "home-saving": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 9, ceiling_tdp_w: 15, initial_tdp_w: 15 }, session: { minutes: 3 }, budget: { phase: "locked", point: "30x3", tdp_w: 9, tdp_control: true, tier: "ideal", limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-cap-ignored": { ...base, enabled: true, state: "LOCKED", mode: "budget", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(30, 90, 3), active_point: { multiplier: 3, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 8 }, power_feedback: { draw_w: 17.4, cap_w: 8, cap_ignored: true }, budget: { phase: "locked", point: "30x3", tdp_w: 8, tdp_control: true, tier: "ideal", cap_ignored: true, limits_w: { min: 6, normal: 15, emergency: 15 } } },
  "home-quality-oled": { ...base, enabled: true, state: "LOCKED", mode: "quality", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(45, 90, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, active_point_mode: "applied", power: { owned: true, observed_tdp_w: 12, saved_w: 15 }, effort: { level: "medium" } },
  "home-locked-lcd": { ...base, enabled: true, state: "OPTIMIZE_POWER", device: dev("lcd", 60), target_output_fps: 60, telemetry: tel(30, 60, 2), active_point: { multiplier: 2, render_scale_pct: 100 }, power: { owned: true, observed_tdp_w: 8, saved_w: 15 }, effort: { level: null, assessing: true } },
  "home-paused-relaunch": { ...base, enabled: true, state: "PAUSED", reason: "relaunch-required-for-governor-overlay", device: dev("oled", 90), target_output_fps: 90, capability: { reason: "relaunch-required-for-governor-overlay" } },
  "home-no-tdp": { ...base, enabled: true, state: "OBSERVE_ONLY", reason: "tdp-control-not-writable", device: dev("oled", 90), target_output_fps: 90, telemetry: tel(45, 90, 2), active_point: { multiplier: 2, render_scale_pct: 100 } },
  "home-relaunch-dock": { ...base, enabled: true, state: "PLAN", device: dev("dock", 60), target_output_fps: 60, capability: { reason: "relaunch-required-for-governor-overlay" } },
};
const mockSrc = (state, extra) => `
window.SP_REACT = React; window.DFL = { staticClasses: { Title: "t" }, Focusable: null, TextField: (p) => React.createElement("input", { ...p, "data-tf": "1" }) };
window.__patches = [];
window.__state = ${JSON.stringify(state)};
window.__cfg = ${JSON.stringify(extra.cfg || { fg_backend: "gfg", multiplier: 2, })};
var callable = (n) => async (...a) => ({ get_governor_status: () => window.__state, get_profiles: () => ({ profiles: ["Default", "Elden Ring", "Cyberpunk 2077"], current_profile: "Elden Ring" }),
  get_profile_config: () => ({ config: window.__cfg }), get_pipeline_inspector: () => ({ saved: { fg_backend: "gfg", multiplier: 2, scaling: "off" }, effective: { fg_backend: "gfg", multiplier: 2, scaling: "off" }, actual: { renderer: "loaded", multiplier: 2 } }),
  check_mako_installed: () => ({ installed: true, installed_engine_version: '4.0.1', expected_engine_version: '4.0.1', engine_update_required: false, host_architecture_supported: true }), check_flatpak_extension_status: () => ({ success: true, installed_23_08: false, installed_24_08: true, installed_25_08: true }), get_flatpak_apps: () => ({ success: true, total_apps: 2, apps: [{ app_id: 'org.example.A', app_name: 'Heroic', has_filesystem_override: true, has_wrapper_override: true, has_required_env_override: true }, { app_id: 'org.example.B', app_name: 'Lutris', has_filesystem_override: false, has_wrapper_override: false }] }),
  get_config_schema: () => ({ field_names: ['scaling_enabled','scaling_factor','multiplier','dll','allow_fp16'], field_types: { scaling_enabled: 'boolean', scaling_factor: 'float', multiplier: 'integer', dll: 'string', allow_fp16: 'boolean' }, defaults: { scaling_enabled: false, scaling_factor: 1.5, multiplier: 2, dll: '', allow_fp16: true }, descriptions: { scaling_enabled: 'restart-bound scaling engine switch', scaling_factor: 'output scaling factor from 1.0x to 2.0x', multiplier: 'fixed multiplier', dll: 'optional full path to Lossless.dll', allow_fp16: 'allow FP16 acceleration' } }),
  run_setup_check: () => window.__state.__setup || ({ success: true, total: 3, failed: 0, checks: [{ check: 'launch wrapper installed', ok: true }, { check: 'overlay config published (active.conf)', ok: true }, { check: 'TDP control: fastPPT/slowPPT cap writable', ok: true }] }),
  get_log_recording_status: () => window.__state.__log || {},
  get_launch_option: () => ({ launch_option: "/home/deck/.local/bin/gfg %command%" }),
  update_profile_config_fields: (p, c) => { window.__patches.push(c); return { success: true }; } }[n] || (() => ({ success: true })))(...a);
var definePlugin = (f) => f;`;

export async function openPage(browser, state, nav = [], extra = {}) {
  const page = await browser.newPage({ viewport: { width: 330, height: 760 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const code = out.outputFiles[0].text.replace(/^var GFGPlugin = /, "window.__P = ");
  await page.setContent(`<html><body style="margin:0;background:#0a0a0c"><div id=r></div></body></html>`);
  await page.addScriptTag({ content: reactJs });
  await page.addScriptTag({ content: mockSrc(state, extra) + "\n" + code });
  await page.evaluate(() => { const p = window.__P.default(); window.__createRoot(document.getElementById("r")).render(p.content); });
  await page.waitForTimeout(400);
  for (const t of nav) { await page.getByText(t, { exact: true }).first().click(); await page.waitForTimeout(250); }
  page.__errors = errors;
  return page;
}
