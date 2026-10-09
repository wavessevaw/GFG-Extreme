// README cards: screens of the real interface (mock Decky globals, sample data) laid out on one
// canvas per topic. Writes docs/img/card-*.png. The Quick Access panel is 330 px wide; everything is
// rendered at 2x. No real game names in the pictures.
import fs from "node:fs";
import { launch, openPage, STATES } from "./lib.mjs";

const out = process.env.GFG_SHOT_DIR || new URL("../../docs/img/", import.meta.url).pathname;
fs.mkdirSync(out, { recursive: true });
const VERSION = JSON.parse(fs.readFileSync(new URL("../../package.json", import.meta.url), "utf8")).version;
const browser = await launch();
const st = (name, more = {}) => ({ ...STATES[name], version: VERSION, ...more });

// ---------- raw panels
async function settle(page) {
  await page.evaluate(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
  await page.waitForTimeout(150);
}
async function bottomOf(page) {
  // The content's own bottom (the page itself is at least one viewport tall).
  return page.evaluate(() => {
    const root = document.querySelector(".gfg") || document.body;
    let bottom = 0;
    for (const e of root.querySelectorAll("*")) bottom = Math.max(bottom, e.getBoundingClientRect().bottom);
    return Math.ceil(bottom + window.scrollY) + 16;
  });
}
// A whole screen, cut after `until` (text of the first element not to show) or at `maxH` px.
async function screen(state, { nav = [], until = null, maxH = 1400, taps = 0, extra = {} } = {}) {
  const page = await openPage(browser, state, nav, extra);
  for (let i = 0; i < taps; i++) { await page.locator(".herotap").first().click(); await page.waitForTimeout(80); }
  await settle(page);
  let h = Math.min(maxH, await bottomOf(page));
  if (until) {
    const y = await page.getByText(until, { exact: true }).first().evaluate((e) => e.getBoundingClientRect().top + window.scrollY);
    h = Math.min(h, Math.floor(y) - 6);
  }
  const png = await page.screenshot({ fullPage: true, clip: { x: 0, y: 0, width: 330, height: h } });
  if (page.__errors.length) console.error("page errors", page.__errors);
  await page.close();
  return png;
}
// From one element's top to another's bottom (CSS selectors or section headings by text).
async function region(state, { nav = [], from, to, extra = {} } = {}) {
  const page = await openPage(browser, state, nav, extra);
  await settle(page);
  // ".sel": CSS selector; "~text": text contained in an element; otherwise the exact text.
  // A leading "^" takes the card (or list) around that element instead.
  const box = async (q) => {
    const up = q.startsWith("^");
    if (up) q = q.slice(1);
    const loc = q.startsWith(".") ? page.locator(q).first()
      : q.startsWith("~") ? page.getByText(q.slice(1)).first() : page.getByText(q, { exact: true }).first();
    return loc.evaluate((e, up) => { const t = up ? e.closest(".card, .list") || e : e; const r = t.getBoundingClientRect(); return { top: r.top + window.scrollY, bottom: r.bottom + window.scrollY }; }, up);
  };
  // to "<text": stop just above that element (the next section's heading).
  const before = to && to.startsWith("<");
  const a = await box(from), b = !to ? { bottom: await bottomOf(page) }
    : before ? await box(to.slice(1)).then((r) => ({ bottom: r.top - 14 })) : await box(to);
  const top = Math.max(0, Math.ceil(a.top)), bottom = Math.floor(b.bottom);
  const png = await page.screenshot({ fullPage: true, clip: { x: 10, y: top, width: 310, height: bottom - top } });
  png.bare = true;  // the element brings its own card frame
  if (page.__errors.length) console.error("page errors", page.__errors);
  await page.close();
  return png;
}

// ---------- cards
const CSS = `
*{box-sizing:border-box}body{margin:0;background:#0a0a0c;font-family:"Motiva Sans","Inter","Segoe UI",system-ui,sans-serif}
.canvas{display:inline-flex;align-items:flex-start;gap:28px;padding:36px 40px 30px;background:#0a0a0c}
.col{display:flex;flex-direction:column;gap:12px;align-items:center}
.shot{width:330px;border-radius:22px;border:1px solid #2e2e36;overflow:hidden;box-shadow:0 18px 50px rgba(0,0,0,.55);background:#0a0a0c}
.shot img{display:block;width:330px}
.shot.bare{width:310px;border:0;border-radius:0;box-shadow:none;overflow:visible}.shot.bare img{width:310px}
.cap{font-size:11px;font-weight:700;letter-spacing:.18em;color:#8a8a94;text-transform:uppercase}
.cap b{color:#fb0d00;font-weight:800}`;
async function card(name, cols) {
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 }, deviceScaleFactor: 2 });
  const html = cols.map((c) => `<div class="col"><div class="shot${c.png.bare ? " bare" : ""}"><img src="data:image/png;base64,${c.png.toString("base64")}"></div>`
    + (c.label ? `<div class="cap">${c.label}</div>` : "") + `</div>`).join("");
  await page.setContent(`<html><head><meta charset=utf-8><style>${CSS}</style></head><body><div class="canvas">${html}</div></body></html>`);
  await page.waitForTimeout(150);
  await page.locator(".canvas").screenshot({ path: out + name + ".png" });
  await page.close();
  console.log(out + name + ".png");
}

// Overview: Battery at work, Extreme, Details.
await card("card-overview", [
  { png: await screen(st("readme-home"), { until: "MODE" }), label: "Battery · at work" },
  { png: await screen(st("home-extreme"), { taps: 2, until: "STOP" }), label: "<b>Extreme</b> · whole stock limit" },
  { png: await screen(st("readme-home"), { nav: ["Details"], until: "HEALTH" }), label: "Details · every decision" },
]);

// The four modes: the Home hero of each.
await card("card-modes", [
  { png: await region(st("readme-home"), { from: ".hero", to: ".hero" }), label: "Battery" },
  { png: await region(st("home-balanced"), { from: ".hero", to: ".hero" }), label: "Balanced" },
  { png: await region(st("home-quality-oled"), { from: ".hero", to: ".hero" }), label: "Quality" },
  { png: await region(st("home-extreme"), { from: ".hero", to: ".hero" }), label: "<b>Extreme</b>" },
]);

// Extreme: what it does now, what it checks, what it asks.
await card("card-extreme", [
  { png: await region(st("home-extreme"), { from: ".xcard", to: ".xcard" }), label: "Nine directions, each with its state" },
  { png: await region(st("home-extreme-verify"), { from: ".hero", to: ".hero" }), label: "A new render scale is checked first" },
  { png: await region(st("home-extreme"), { nav: ["Details"], from: "EXTREME", to: "^Gain vs Balanced" }), label: "Details · confirmed values only" },
]);

// Smart power split.
await card("card-power-split", [
  { png: await region(st("home-power-split"), { nav: ["Details"], from: "CPU / GPU POWER SPLIT", to: "^Smart power split" }), label: "CPU cap measured in game" },
]);

// Frame OS.
{
  const fo = st("home-frame-os-act");
  await card("card-frame-os", [
    { png: await region(fo, { from: ".fos", to: ".fos" }), label: "Home · measured in game" },
    { png: await region(fo, { nav: ["Settings", "Diagnostics"], from: "FRAME OS (EXPERIMENTAL)", to: "<INSPECTOR" }), label: "Diagnostics · A/B and per-game memory" },
  ]);
}

// Filters: the Home card while a game runs with vkBasalt loaded, and the full page.
{
  const fcfg = { fg_backend: "gfg", multiplier: 2, external_vulkan_layer: "vkbasalt", vkbasalt_shader: "vibrance",
    vkbasalt_sharpening: "cas", vkbasalt_sharpness: 0.35, vkbasalt_antialiasing: "none", vkbasalt_dls_denoise: 0.2 };
  const fstate = { ...st("readme-home"), __actual: { state: "running", vkbasalt_loaded: true } };
  await card("card-filters", [
    { png: await region(fstate, { from: ".filters", to: ".filters", extra: { cfg: fcfg } }), label: "Home · one tap, live" },
    { png: await screen(fstate, { nav: ["Settings", "Filters"], until: "EFFECTS · 3 ON, IN THIS ORDER", extra: { cfg: { ...fcfg,
      vkbasalt_shader: "clarity:vibrance:film_grain", vkbasalt_sharpness: 0.45, vkbasalt_antialiasing: "smaa" } } }), label: "Settings · Filters" },
  ]);
}

// After the game, and the overlay settings.
await card("card-session", [
  { png: await region(st("home-last-session-mixed", { device: STATES["home-idle-oled"].device, target_output_fps: 90 }), { from: "^LAST SESSION", to: "^LAST SESSION" }), label: "Last session" },
  { png: await screen(st("readme-home"), { nav: ["Settings", "In-game overlay"], maxH: 900 }), label: "In-game overlay" },
]);

// Help: Check setup and a recorded log.
await card("card-help", [
  { png: await screen(st("setup-bad"), { nav: ["Settings", "Diagnostics", "Check setup"], maxH: 900 }), label: "Check setup" },
  { png: await region(st("log-saved"), { nav: ["Settings", "Diagnostics"], from: "RECORD A LOG", to: "^~Median output FPS" }), label: "Record a log" },
]);

await browser.close();
