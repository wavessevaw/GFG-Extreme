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
  ["home-last-session", [], ["LAST SESSION", "42 min", "FPS avg", "Real avg", "TDP avg", "11W", "Your limit", "15 W", "~4.4 W under your limit on average", "83 °C · warm 12% of the time", "Stutter", "3% of the time"]],
  ["home-cooling", [], ["Cooling · 8 W", "only tries lower watts"]],
  ["home-cooling", ["Details"], ["Heat", "on hold until the APU cools", "Lower resolution", "Scale-ready launch"]],
  ["home-history", ["Details"], ["RECENT SESSIONS", "29 min · Battery", "90 FPS · 10.7 W · 77 °C", "12 min · Quality", "88 FPS · 19.4 W"]],
  ["home-saving", [], ["SAVING", "6 W under your 15 W limit"]],
  ["home-effort-reason", [], ["GFG EFFORT", "HARD", "x3 required"]],
  ["home-frame-os-act", [], ["FRAME OS", "BOOST", "−47%", "+50%", "9%", "Response", "Frames", "Energy"]],
  ["home-frame-os-act", [], ["Measured in game: Response ×5 · Frames ×3"]],
  ["home-frame-os-learned", [], ["Boost off here: no real-frame gain measured"]],
  ["home-idle-oled", [], ["SAVINGS EFFORT", "Off", "Light", "Medium", "Hard"]],
  ["home-savings-hard", [], ["SAVINGS EFFORT", "OLED 60 Hz · LCD 45 Hz"]],
  ["home-savings-medium", [], ["Stronger savings", "standard screen refresh"]],
  ["home-savings-limited", [], ["FPS protection raised the power floor"]],
  ["home-frame-os-learned", ["Settings", "Diagnostics"], ["THIS GAME", "no gain · off (5 A/B)", "helps (12 A/B)"]],
  ["home-frame-os-act", ["Settings", "Diagnostics"], ["A/B check in Act", "Response (A/B)", "+47% (39…55) · 5 pairs", "Energy (A/B)", "+12% · 1 pair", "THIS GAME", "Sessions with Act", "helps (5 A/B)", "helps (9 A/B)", "learning (1 A/B)"]],
  ["home-frame-os-rest", [], ["FRAME OS", "REST", "−6%"]],
  ["home-frame-os-observe", [], ["FRAME OS", "ESTIMATE", "−44%", "+50%", "11%"]],
  ["home-frame-os-early", [], ["FRAME OS", "Response", "—"]],
  ["frame-os-no-layer", ["Settings", "Diagnostics"], ["FRAME OS (EXPERIMENTAL)", "Frame OS layer not installed: this build does not include the Frame OS layer."]],
  ["home-last-session-mixed", [], ["LAST SESSION", "Modes", "Battery 18m · Balanced 13m", "Energy saved", "~2.3 Wh measured · ~14 min more battery", "Frame OS", "calm 20m · boost 6m · rest 4m", "Response", "−41%", "+12%", "9%"]],
  ["home-last-session-mixed", ["Details"], ["RECENT SESSIONS", "31 min · Battery 18m · Balanced 13m"]],
  ["home-idle-oled", ["Settings", "Diagnostics"], ["Reset what GFG learned for Sample Game", "Starts the next search from scratch"]],
  ["home-idle-oled", ["Settings", "Diagnostics", "Reset what GFG learned for Sample Game"], ["Tap again to forget", "remembered for Sample Game", "This cannot be undone"]],
  ["home-paused-external-tdp", [], ["changed outside GFG", "In Battery and Balanced modes GFG takes it back"]],
  ["home-no-model-game", ["Settings", "Diagnostics"], ["Reset what GFG learned for this game", "No game identified yet"]],
  ["home-cap-ignored", [], ["TDP limit overridden", "17.4 W", "another tool"]],
  ["home-quality-oled", ["Details"], ["×1 to ×3, steps of 0.25", "never above your own"]],
  ["home-quality-oled", [], ["fewest generated frames first"]],
  ["home-locked-oled", ["Settings", "Frame generation backend"], ["BACKEND", "GFG", "OptiScaler"]],
  ["home-locked-oled", ["Settings", "Scaling"], ["Scale-ready launch"]],
  ["home-locked-oled", ["Settings", "In-game overlay"], ["Show overlay in game", "STYLE", "Rings", "Text", "Rings refresh once a second", "Minimal", "Detailed", "Bottom left"]],
  ["home-locked-oled", ["Settings", "Profile"], ["Sample Game", "NEW PROFILE"]],
  ["home-locked-oled", ["Settings", "System"], ["ENGINE", "Installed", "Runtime 24.08", "Heroic"]],
  ["home-locked-oled", ["Settings", "All settings"], ["scaling_factor", "allow_fp16"]],
  ["home-locked-oled", ["Settings", "Diagnostics", "Journal"], ["Journal"]],
  ["home-idle-oled", [], ["MODE", "Battery", "Quality", "Details", "Settings"]],
  ["home-relaunch-dock", [], ["START THE GAME WITH THIS LAUNCH OPTION", "Copy launch command"]],
  ["home-paused-relaunch", [], ["Something wrong? Record a log"]],
  ["home-idle-oled", ["Settings"], ["GFG Extreme 1.0.0"]],
  ["home-idle-oled", ["Settings", "Launch command"], ["Copy launch command", "Launch Options"]],
  ["home-idle-oled", ["Settings", "Diagnostics"], ["RECORD A LOG", "Record log", "FRAME OS (EXPERIMENTAL)", "Observe"]],
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
// Savings effort must only be visible on Battery mode, never Balanced / Quality.
for (const mode of ["home-balanced", "home-quality-oled"]) {
  const page = await openPage(browser, STATES[mode]);
  const shown = await page.evaluate(() => document.body.innerText);
  if (shown.includes("SAVINGS EFFORT")) { failed++; console.error("FAIL savings selector visible in " + mode); }
  await page.close();
}
{
  const page = await openPage(browser, STATES["home-savings-hard"]);
  const chosen = await page.evaluate(() => document.body.innerText);
  if (!chosen.includes("OLED 60 Hz · LCD 45 Hz")) { failed++; console.error("FAIL missing Hard rate policy"); }
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
// A session above the user's limit (or from an older plugin) never shows a negative saving.
{
  const page = await openPage(browser, STATES["home-last-session-above-limit"]);
  const text = await page.evaluate(() => document.body.innerText);
  if (!text.includes("LAST SESSION")) { failed++; console.error(`FAIL above-limit session not shown`); }
  for (const bad of ["-2.1", "Energy saved", "under your limit on average"]) if (text.includes(bad)) { failed++; console.error(`FAIL above-limit session shows "${bad}"`); }
  await page.close();
  cases.push(["last-session-above-limit"]);
}
// Frame OS safety: Act is absent unless the backend explicitly unlocks it;
// refused Observe/Shadow changes must still roll back to Off.
{
  const page = await openPage(browser, STATES["frame-os-refused"], ["Settings", "Diagnostics"]);
  if (await page.getByText("Act", { exact: true }).count()) {
    failed++; console.error("FAIL Frame OS Act visible without developer unlock");
  }
  await page.getByText("Shadow", { exact: true }).first().click();
  await page.waitForTimeout(150);
  const on = await page.evaluate(() => [...document.querySelectorAll(".segb.on")].map((e) => e.textContent));
  if (!on.includes("Off") || on.includes("Shadow")) { failed++; console.error(`FAIL frame os mode not rolled back: ${JSON.stringify(on)}`); }
  await page.close();
  cases.push(["frame-os-safety-rollback"]);
}
// Act unlock: the first tap only asks, the second unlocks and shows Act.
{
  const page = await openPage(browser, STATES["frame-os-refused"], ["Settings", "Diagnostics", "Unlock Act (experimental)"]);
  const asked = await page.evaluate(() => (window.__actUnlocks || []).length);
  await page.getByText("Tap again to unlock Act", { exact: true }).first().click();
  await page.waitForTimeout(150);
  const calls = await page.evaluate(() => window.__actUnlocks || []);
  if (asked !== 0) { failed++; console.error("FAIL act unlocked without confirmation"); }
  if (JSON.stringify(calls) !== "[true]") { failed++; console.error(`FAIL act unlock calls: ${JSON.stringify(calls)}`); }
  if (!(await page.getByText("Act", { exact: true }).count())) { failed++; console.error("FAIL Act not offered after unlock"); }
  if (!(await page.getByText("Lock Act", { exact: true }).count())) { failed++; console.error("FAIL no Lock Act after unlock"); }
  await page.close();
  cases.push(["frame-os-act-unlock"]);
}
// Reset what GFG learned: the first tap only asks, the second one forgets.
{
  const page = await openPage(browser, STATES["home-idle-oled"], ["Settings", "Diagnostics", "Reset what GFG learned for Sample Game"]);
  const asked = await page.evaluate(() => (window.__forgets || []).length);
  await page.getByText("Tap again to forget", { exact: true }).first().click();
  await page.waitForTimeout(150);
  const forgets = await page.evaluate(() => window.__forgets || []);
  const text = await page.evaluate(() => document.body.innerText);
  if (asked !== 0) { failed++; console.error(`FAIL forget model ran without confirmation`); }
  if (forgets.length !== 1) { failed++; console.error(`FAIL forget model calls: ${JSON.stringify(forgets)}`); }
  if (!text.includes("Forgotten. The next start searches from scratch.")) { failed++; console.error(`FAIL forget model result not shown`); }
  await page.close();
  cases.push(["forget-model-confirm"]);
}
await browser.close();
console.log(failed ? `${failed} failure(s)` : `frontend smoke OK (${cases.length} screens)`);
process.exit(failed ? 1 : 0);
