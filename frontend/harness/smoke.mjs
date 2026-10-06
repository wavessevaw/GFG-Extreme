// Frontend smoke test: renders each key screen against mock Decky globals and asserts visible text.
import { launch, openPage, STATES } from "./lib.mjs";
const cases = [
  ["home-idle-oled", [], ["RUN", "90", "TARGET FPS", "Ready", "Steam Deck OLED"]],
  ["home-measuring", [], ["STOP", "Measuring", "ASSESSING"]],
  ["home-locked-oled", [], ["STOP", "Locked in", "45", "x2".replace("x", "×"), "MEDIUM", "TDP NOW", "2h05 left"]],
  ["home-locked-lcd", [], ["Steam Deck LCD", "Saving power", "ASSESSING"]],
  ["home-relaunch-dock", [], ["Restart the game", "Dock"]],
  ["home-locked-oled", ["Governor"], ["Governor", "×1 to ×3, steps of 0.25", "never modified"]],
  ["home-locked-oled", ["Frame Generation"], ["BACKEND", "GFG", "OptiScaler"]],
  ["home-locked-oled", ["Scaling"], ["Scale-ready launch"]],
  ["home-locked-oled", ["In-game overlay"], ["Show overlay in game", "Minimal", "Detailed", "Top right"]],
  ["home-locked-oled", ["Profile"], ["Elden Ring", "NEW PROFILE"]],
  ["home-locked-oled", ["Advanced", "System"], ["ENGINE", "Installed", "Runtime 24.08", "Heroic"]],
  ["home-locked-oled", ["Advanced", "All settings"], ["scaling_factor", "allow_fp16"]],
  ["home-locked-oled", ["Advanced", "Journal"], ["Journal"]],
];
const browser = await launch();
let failed = 0;
for (const [state, nav, expected] of cases) {
  const page = await openPage(browser, STATES[state], nav);
  const text = await page.evaluate(() => document.body.innerText);
  for (const needle of expected) if (!text.includes(needle)) { failed++; console.error(`FAIL ${state} ${JSON.stringify(nav)}: missing "${needle}"`); }
  for (const e of page.__errors) { failed++; console.error(`FAIL ${state}: page error ${e}`); }
  await page.close();
}
await browser.close();
console.log(failed ? `${failed} failure(s)` : `frontend smoke OK (${cases.length} screens)`);
process.exit(failed ? 1 : 0);
