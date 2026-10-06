// README screenshots of the current interface (mock Decky globals, sample data). Writes docs/img/*.png.
import fs from "node:fs";
import { launch, openPage, STATES } from "./lib.mjs";
const out = new URL("../../docs/img/", import.meta.url).pathname;
fs.mkdirSync(out, { recursive: true });
const browser = await launch();
async function shot(name, state, nav = []) {
  const page = await openPage(browser, STATES[state], nav);
  await page.screenshot({ path: out + name + ".png", fullPage: true });
  await page.close();
  console.log(out + name + ".png");
}
await shot("home-idle-oled", "home-idle-oled");
await shot("home-adapting-oled", "readme-home");
await shot("home-balanced-oled", "home-balanced");
await shot("page-details", "readme-home", ["Details"]);
await shot("page-settings", "readme-home", ["Settings"]);
await shot("page-setup", "setup-bad", ["Settings", "Diagnostics", "Check setup"]);
await shot("page-hud", "readme-home", ["Settings", "In-game overlay"]);
await browser.close();
