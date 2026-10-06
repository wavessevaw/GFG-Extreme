// Frontend smoke test: renders each key screen against mock Decky globals and asserts visible text.
import { launch, openPage, STATES } from "./lib.mjs";
const cases = [
  ["home-idle-oled", [], ["RUN", "90", "TARGET FPS", "Ready", "Steam Deck OLED"]],
  ["home-measuring", [], ["STOP", "Measuring", "ASSESSING"]],
  ["home-locked-oled", [], ["STOP", "Locked in", "45", "x2".replace("x", "×"), "MEDIUM", "TDP NOW", "2h05 left"]],
  ["home-locked-lcd", [], ["Steam Deck LCD", "Saving power", "ASSESSING"]],
  ["home-relaunch-dock", [], ["Restart the game", "Dock"]],
  ["home-paused-relaunch", [], ["Restart the game"]],
  ["home-no-tdp", [], ["No TDP access"]],
  ["home-locked-oled", ["Details"], ["Details", "HEALTH", "Frametime p95 / p99", "24.5 / 31.2 ms", "×1 to ×3.75, deeper only as a last resort", "never modified"]],
  ["home-budget-oled", [], ["Adapting · 9 W", "Ideal: 11 W or less", "EASY"]],
  ["home-budget-oled", ["Details"], ["BATTERY", "TDP target", "9 W", "Ideal (≤ 11 W)", "9–11 W ideal, 15 W max, 20 W last resort"]],
  ["home-warm-start", [], ["Adapting · 8 W", "Started from what worked last time."]],
  ["home-warm-start", ["Details"], ["Remembered from last session"]],
  ["home-budget-oled", ["Details"], ["Searched from scratch"]],
  ["home-balanced", [], ["Balanced", "never goes below 30 real FPS"]],
  ["home-balanced", ["Details"], ["×1 to ×3, never below 30 real FPS", "12–13 W start"]],
  ["log-saved", ["Settings", "Diagnostics"], ["Saved: /home/deck/Desktop/GFG-Extreme-log-1.zip", "WHAT THE LOG SHOWS", "No renderer diagnostics were written"]],
  ["home-idle-oled", ["Settings", "Diagnostics", "Check setup"], ["Everything GFG needs is in place (3 checks)", "✓ launch wrapper installed"]],
  ["setup-bad", ["Settings", "Diagnostics", "Check setup"], ["2 of 3 checks failed", "NEEDS ATTENTION", "✗ host MangoHud Vulkan layer present", "cannot appear", "Turn the overlay on in Settings"]],
  ["home-paused-setup", [], ["LIKELY CAUSE", "Start the game with the GFG launch command", "Check setup"]],
  ["home-cap-ignored", [], ["TDP limit overridden", "17.4 W", "another tool"]],
  ["home-quality-oled", ["Details"], ["×1 to ×3, steps of 0.25", "never above your own"]],
  ["home-quality-oled", [], ["fewest generated frames first"]],
  ["home-locked-oled", ["Settings", "Frame generation backend"], ["BACKEND", "GFG", "OptiScaler"]],
  ["home-locked-oled", ["Settings", "Scaling"], ["Scale-ready launch"]],
  ["home-locked-oled", ["Settings", "In-game overlay"], ["Show overlay in game", "Minimal", "Detailed", "Top right"]],
  ["home-locked-oled", ["Settings", "Profile"], ["Elden Ring", "NEW PROFILE"]],
  ["home-locked-oled", ["Settings", "System"], ["ENGINE", "Installed", "Runtime 24.08", "Heroic"]],
  ["home-locked-oled", ["Settings", "All settings"], ["scaling_factor", "allow_fp16"]],
  ["home-locked-oled", ["Settings", "Diagnostics", "Journal"], ["Journal"]],
  ["home-idle-oled", [], ["MODE", "Battery", "Quality", "Details", "Settings"]],
  ["home-relaunch-dock", [], ["START THE GAME WITH THIS LAUNCH OPTION", "Copy launch command"]],
  ["home-paused-relaunch", [], ["Something wrong? Record a log"]],
  ["home-idle-oled", ["Settings", "Launch command"], ["Copy launch command", "Launch Options"]],
  ["home-idle-oled", ["Settings", "Diagnostics"], ["RECORD A LOG", "Record log"]],
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
