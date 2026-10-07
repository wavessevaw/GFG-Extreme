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
  ["home-budget-oled", ["Details"], ["BATTERY", "TDP target", "9 W", "Ideal (≤ 11 W)", "9–11 W ideal, 15 W max (this Deck's maximum)"]],
  ["home-warm-start", [], ["Adapting · 8 W", "Started from what worked last time."]],
  ["home-warm-start", ["Details"], ["Remembered from last session"]],
  ["home-budget-oled", ["Details"], ["Searched from scratch"]],
  ["home-balanced", [], ["Balanced", "never goes below 30 real FPS"]],
  ["home-balanced", ["Details"], ["×1 to ×3, never below 30 real FPS", "12–13 W start"]],
  ["log-saved", ["Settings", "Diagnostics"], ["Saved: /home/deck/Desktop/GFG-Extreme-log-1.zip", "WHAT THE LOG SHOWS", "No renderer diagnostics were written"]],
  ["home-idle-oled", ["Settings", "Diagnostics", "Check setup"], ["Everything GFG needs is in place (3 checks)", "✓ launch wrapper installed"]],
  ["setup-bad", ["Settings", "Diagnostics", "Check setup"], ["2 of 3 checks failed", "NEEDS ATTENTION", "✗ host MangoHud Vulkan layer present", "cannot appear", "Turn the overlay on in Settings"]],
  ["home-paused-setup", [], ["LIKELY CAUSE", "Start the game with the GFG launch command", "Check setup"]],
  ["budget-memory", ["Details"], ["Verifying", "×3 — the engine chose it", "Engine allows", "up to ×3", "Recently failed", "×2.75 at ≤10 W"]],
  ["home-loading", [], ["Waiting for the game to draw frames"]],
  ["home-testing", [], ["Testing ×2.75", "a few seconds"]],
  ["home-last-session", [], ["LAST SESSION", "42 min", "90 FPS avg (30 real)", "10.6 W avg · limit 15 W", "~4.4 W on average", "83 °C · warm 12% of the time", "Stutter", "3% of the time"]],
  ["home-cooling", [], ["Cooling · 8 W", "only tries lower watts"]],
  ["home-cooling", ["Details"], ["Heat", "on hold until the APU cools"]],
  ["home-history", ["Details"], ["RECENT SESSIONS", "29 min · Battery", "90 FPS · 10.7 W · 77 °C", "12 min · Quality", "88 FPS · 19.4 W"]],
  ["home-saving", [], ["SAVING", "6 W under your 15 W limit"]],
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
  ["home-idle-oled", ["Settings"], ["GFG Extreme 1.0.0"]],
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
// Text settings are saved on Enter / blur, never per keystroke.
{
  const page = await openPage(browser, STATES["home-locked-oled"], ["Settings", "All settings"]);
  const field = page.locator("input[data-tf]").first();
  await field.click();
  await field.type("abc");
  const typed = await page.evaluate(() => window.__patches.length);
  await field.press("Enter");
  await page.waitForTimeout(100);
  const saved = await page.evaluate(() => window.__patches);
  if (typed !== 0) { failed++; console.error(`FAIL text field saved ${typed} times while typing`); }
  if (saved.length !== 1 || saved[0].dll !== "abc") { failed++; console.error(`FAIL text field commit: ${JSON.stringify(saved)}`); }
  await page.close();
  cases.push(["text-field-commit"]);
}
// ... and when the page is left with Back before Enter (no blur fires on unmount).
{
  const page = await openPage(browser, STATES["home-locked-oled"], ["Settings", "All settings"]);
  const field = page.locator("input[data-tf]").first();
  await field.click();
  await field.type("xyz");
  await page.locator(".back").first().click();
  await page.waitForTimeout(150);
  const saved = await page.evaluate(() => window.__patches);
  if (saved.length !== 1 || saved[0].dll !== "xyz") { failed++; console.error(`FAIL text field lost on Back: ${JSON.stringify(saved)}`); }
  await page.close();
  cases.push(["text-field-back"]);
}
await browser.close();
console.log(failed ? `${failed} failure(s)` : `frontend smoke OK (${cases.length} screens)`);
process.exit(failed ? 1 : 0);
