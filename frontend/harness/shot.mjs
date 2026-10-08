// README screenshots of the current interface (mock Decky globals, sample data). Writes docs/img/*.png.
// Viewport is the Deck quick-access panel (330 px wide, 2x). No real game names in the pictures.
import fs from "node:fs";
import { launch, openPage, STATES } from "./lib.mjs";
const out = process.env.GFG_SHOT_DIR || new URL("../../docs/img/", import.meta.url).pathname;
fs.mkdirSync(out, { recursive: true });
const VERSION = JSON.parse(fs.readFileSync(new URL("../../package.json", import.meta.url), "utf8")).version;
const browser = await launch();
// Frame OS acting in a fight: 45 real frames at 90 Hz, just-in-time pacing.
const frameOs = { mode: "act", enabled: true, acting: true, act_unlocked: true, layer_installed: true, acknowledged: true,
  decision: { level: "boost", real_hz: 45 },
  telemetry: { live: true, frames: 48210, freshness_ms: 13.1, present_interval_p50_ms: 22.2, present_interval_p95_ms: 23.6 } };
const st = (name, more = {}) => ({ ...STATES[name], version: VERSION, ...more });
async function shot(name, state, nav = [], from = null, to = null) {
  const page = await openPage(browser, state, nav);
  const file = out + name + ".png";
  if (from) {
    // Crop from a section heading to the next one (or the end of the page).
    const top_ = (t) => page.getByText(t, { exact: true }).first().evaluate((e) => e.getBoundingClientRect().top + window.scrollY);
    const y = await top_(from);
    const h = to ? Math.ceil(await top_(to)) - 8 : await page.evaluate(() => document.documentElement.scrollHeight);
    const top = Math.max(0, Math.floor(y) - 16);
    await page.screenshot({ path: file, fullPage: true, clip: { x: 0, y: top, width: 330, height: h - top } });
  } else {
    await page.screenshot({ path: file, fullPage: true });
  }
  if (page.__errors.length) console.error(name, page.__errors);
  await page.close();
  console.log(file);
}
await shot("home-idle-oled", st("home-idle-oled"));
await shot("home-adapting-oled", st("readme-home"));
await shot("home-balanced-oled", st("home-balanced"));
const oled = { device: STATES["home-idle-oled"].device, target_output_fps: 90 };
await shot("home-last-session", st("home-last-session-mixed", oled));
await shot("page-details", st("readme-home"), ["Details"]);
await shot("details-power-split", st("home-power-split"), ["Details"], "CPU / GPU POWER SPLIT", "DECISION");
await shot("page-settings", st("readme-home"), ["Settings"]);
await shot("page-setup", st("setup-bad"), ["Settings", "Diagnostics", "Check setup"]);
await shot("page-hud", st("readme-home"), ["Settings", "In-game overlay"]);
// Diagnostics panel: the Home state plus the layer's full telemetry.
const fosBase = STATES["home-frame-os-act"] ? st("home-frame-os-act") : st("readme-home");
const fo = fosBase.frame_os || {};
await shot("page-frame-os", { ...fosBase, frame_os: { ...frameOs, ...fo, acknowledged: true, telemetry: { ...frameOs.telemetry, ...(fo.telemetry || {}), frames: frameOs.telemetry.frames } } },
  ["Settings", "Diagnostics"], "FRAME OS (EXPERIMENTAL)", "INSPECTOR");
if (STATES["home-frame-os-act"]) await shot("home-frame-os", st("home-frame-os-act"));
else console.error("home-frame-os-act not in lib.mjs yet: home-frame-os.png not rendered");
await browser.close();
