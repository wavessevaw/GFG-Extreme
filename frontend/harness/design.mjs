// Design review shots (not part of CI): hero layouts and the Filters UI. GFG_SHOT_DIR sets the folder.
import fs from "node:fs";
import { launch, openPage, STATES } from "./lib.mjs";
const out = process.env.GFG_SHOT_DIR || "/tmp/gfg-design/";
fs.mkdirSync(out, { recursive: true });
const browser = await launch();
const live = { ...STATES["home-locked-oled"], version: "1.5.0" };
async function crop(name, state, nav, extra, sel) {
  const page = await openPage(browser, state, nav, extra);
  await page.waitForTimeout(300);
  const box = await page.locator(sel).first().boundingBox();
  await page.screenshot({ path: out + name + ".png", clip: { x: 0, y: Math.max(0, box.y - 52), width: 330, height: box.height + 64 }, fullPage: true });
  if (page.__errors.length) console.error(name, page.__errors);
  await page.close();
  console.log(out + name + ".png");
}
async function full(name, state, nav, extra) {
  const page = await openPage(browser, state, nav, extra);
  await page.waitForTimeout(300);
  await page.screenshot({ path: out + name + ".png", fullPage: true });
  if (page.__errors.length) console.error(name, page.__errors);
  await page.close();
  console.log(out + name + ".png");
}
for (const v of ["classic", "compact", "side", "arc", "flow"]) await crop("hero-" + v, live, [], { hero: v }, ".hero");
const base = { fg_backend: "gfg", multiplier: 2, vkbasalt_sharpness: 0.5, vkbasalt_dls_denoise: 0.2 };
const running = { ...live, __actual: { state: "running", vkbasalt_loaded: true } };
await crop("filters-home-off", live, [], { cfg: { ...base, external_vulkan_layer: "", vkbasalt_shader: "none", vkbasalt_sharpening: "none", vkbasalt_antialiasing: "none" } }, ".filters");
await crop("filters-home-live", running, [], { cfg: { ...base, external_vulkan_layer: "vkbasalt", vkbasalt_shader: "vibrance", vkbasalt_sharpening: "cas", vkbasalt_sharpness: 0.35, vkbasalt_antialiasing: "none" } }, ".filters");
await crop("filters-home-custom", { ...live, __actual: { state: "running", vkbasalt_loaded: false } }, [], { cfg: { ...base, external_vulkan_layer: "vkbasalt", vkbasalt_shader: "clarity:vibrance", vkbasalt_sharpening: "dls", vkbasalt_sharpness: 0.45, vkbasalt_antialiasing: "fxaa" } }, ".filters");
await full("filters-page", running, ["Settings", "Filters"], { cfg: { ...base, external_vulkan_layer: "vkbasalt", vkbasalt_shader: "clarity:vibrance:film_grain", vkbasalt_sharpening: "cas", vkbasalt_sharpness: 0.45, vkbasalt_antialiasing: "smaa" } });
await full("settings-with-filters", live, ["Settings"], {});
await browser.close();
