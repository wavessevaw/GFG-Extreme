import fs from "node:fs";
import { launch, openPage, STATES } from "./lib.mjs";
const browser = await launch();
const shots = [];
async function shot(name, state, nav, extra = {}) {
  const page = await openPage(browser, state, nav, extra);
  const f = `/tmp/claude-0/shots/${name}.png`; fs.mkdirSync("/tmp/claude-0/shots", { recursive: true });
  await page.screenshot({ path: f, fullPage: true }); shots.push(f); await page.close();
}
for (const [k, v] of Object.entries(STATES)) await shot(k, v, []);
await shot("page-governor", STATES["home-locked-oled"], ["Governor"]);
await shot("page-fg", STATES["home-locked-oled"], ["Frame Generation"]);
await shot("page-hud", STATES["home-locked-oled"], ["In-game overlay"]);
await shot("page-advanced", STATES["home-locked-oled"], ["Advanced"]);
await shot("page-all", STATES["home-locked-oled"], ["Advanced", "All settings"]);
await shot("page-system", STATES["home-locked-oled"], ["Advanced", "System"]);
await browser.close(); console.log(shots.join("\n"));
