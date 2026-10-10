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
  ["home-power-split", ["Details"], ["CPU / GPU POWER SPLIT", "CPU capped at 2.4 GHz · the GPU gets the watts", "+7.4% GPU clock/W · 6 A/B", "+7.9% GPU clock, −0.4% draw", "Smart power split"]],
  ["home-power-split-short", ["Details"], ["Full CPU speed · real frames came first", "Not measured yet"]],
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
  ["home-frame-os-act", [], ["FRAME OS", "BOOST", "−47%", "+50%", "0%", "Response", "Frames", "Energy"]],
  ["home-frame-os-act", [], ["Measured in game: Response ×5 · Frames ×3"]],
  ["home-frame-os-learned", [], ["Boost off here: no real-frame gain measured"]],
  ["home-frame-os-learned", ["Settings", "Diagnostics"], ["THIS GAME", "no gain · off (5 A/B)", "helps (12 A/B)"]],
  ["home-frame-os-act", ["Settings", "Diagnostics"], ["A/B check in Act", "Response (A/B)", "+47% (39…55) · 5 pairs", "Energy (A/B)", "+12% · 1 pair", "THIS GAME", "Sessions with Act", "helps (5 A/B)", "helps (9 A/B)", "learning (1 A/B)"]],
  ["home-frame-os-rest", [], ["FRAME OS", "REST", "—"]],
  ["home-frame-os-observe", [], ["FRAME OS", "ESTIMATE", "−44%", "+50%", "—"]],
  ["home-frame-os-early", [], ["FRAME OS", "Response", "—"]],
  ["frame-os-no-layer", ["Settings", "Diagnostics"], ["FRAME OS (EXPERIMENTAL)", "Frame OS layer not installed: this build does not include the Frame OS layer."]],
  ["home-last-session-mixed", [], ["LAST SESSION", "Modes", "Battery 18m · Balanced 13m", "Energy saved", "~2.3 Wh measured · ~14 min more battery", "Frame OS", "calm 20m · boost 6m · rest 4m", "Response", "−41%", "+12%", "—"]],
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
  ["home-locked-oled", [], ["FILTERS", "Vivid", "HDR look", "Fine-tune ›"]],
  ["home-locked-oled", ["Settings", "Filters"], ["Shader filters", "LOOKS", "SHARPENING", "ANTI-ALIASING", "EFFECTS · NONE", "Film Grain"]],
  ["home-extreme", [], ["BETA / EXPERIMENTAL", "not recommended for regular play", "BETA", "Extreme · 15 W", "▲ ON", "Limit 15 W · render 80% · sharpen 0.30", "Gain vs Balanced: not measured yet", "EXTREME BOOSTERS", "3 / 9 ACTIVE", "Upscale + sharpen", "80% · sharpen 0.30", "CPU capped at 2.4 GHz", "No safe Steam API yet", "Stock fan control stays", "Not applied: untested risk", "Sharpening", "EXTREME"]],
  ["home-extreme", ["Details"], ["EXTREME", "Power limit", "15 W · stock limit", "1024×640 → 1280×800", "0.30 (engine confirmed)", "not measured (needs an A-B-A check)", "the whole limit: 15 W or your lower one, never above"]],
  ["home-extreme-verify", [], ["Extreme · checking", "Render 90% counts only once the engine shows", "Checking render 90%", "Limit 15 W"]],
  ["home-extreme-restart", [], ["Extreme · 12 W", "your own 12 W limit (never raised)", "Restart the game once to enable"]],
  ["home-extreme-offer", [], ["Want more real frames?", "4 W of your 15 W limit unused", "not promised", "Try Extreme", "Not now"]],
  ["home-scale-ignored", ["Details"], ["Lower resolution", "Off · this game always renders at full size"]],
  ["home-scale-ignored", ["Settings", "Scaling"], ["This game sets its own render size", "has no effect here"]],
  ["home-extreme", [], ["80% · sharpen 0.30"]],
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
// Tapping the ring cycles the hero layout: side (default) -> half-ring -> big ring -> smaller ring -> side.
{
  const page = await openPage(browser, STATES["home-locked-oled"]);
  const layout = () => page.evaluate(() => {
    const e = document.querySelector(".hero");
    return e.querySelector(".hero-side") ? "side" : e.querySelector(".arc") ? "arc" : e.querySelector(".ring.compact") ? "compact" : "classic";
  });
  const seen = [await layout()];
  for (let i = 0; i < 4; i++) { await page.locator(".herotap").first().click(); await page.waitForTimeout(80); seen.push(await layout()); }
  if (seen.join(",") !== "side,arc,classic,compact,side") { failed++; console.error(`FAIL hero tap cycle: ${seen.join(",")}`); }
  for (const e of page.__errors) { failed++; console.error(`FAIL hero cycle: page error ${e}`); }
  await page.close();
  cases.push(["hero-cycle"]);
}
// One tap on a look writes the filter fields (and turns the vkBasalt layer on).
{
  const page = await openPage(browser, STATES["home-locked-oled"]);
  await page.getByText("Vivid", { exact: true }).first().click();
  await page.waitForTimeout(150);
  const p = await page.evaluate(() => window.__patches);
  if (!p.length || p[0].external_vulkan_layer !== "vkbasalt" || p[0].vkbasalt_shader !== "vibrance") { failed++; console.error(`FAIL filter preset patch: ${JSON.stringify(p)}`); }
  await page.close();
  cases.push(["filter-preset"]);
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
// Extreme: the wolf sits inside the main ring in every hero layout, and only in Extreme.
{
  const page = await openPage(browser, STATES["home-extreme"]);
  for (let i = 0; i < 4; i++) {
    const wolf = await page.evaluate(() => !!document.querySelector(".hero .num.wolf img.wolfimg"));
    if (!wolf) { failed++; console.error(`FAIL extreme wolf missing in hero layout ${i}`); }
    await page.locator(".herotap").first().click(); await page.waitForTimeout(80);
  }
  for (const e of page.__errors) { failed++; console.error(`FAIL extreme wolf: page error ${e}`); }
  await page.close();
  const other = await openPage(browser, STATES["home-balanced"]);
  if (await other.evaluate(() => !!document.querySelector(".hero .wolfimg"))) { failed++; console.error("FAIL wolf shown outside Extreme"); }
  await other.close();
  cases.push(["extreme-wolf"]);
}
// First switch to Extreme asks about Frame OS Act once, then switches with the answer.
{
  const page = await openPage(browser, STATES["home-extreme-consent"]);
  await page.getByText("EXTREME", { exact: true }).first().click();
  await page.waitForTimeout(120);
  const before = await page.evaluate(() => window.__modes || []);
  if (before.length) { failed++; console.error(`FAIL extreme switched before the Act question: ${JSON.stringify(before)}`); }
  if (!(await page.getByText("Let Frame OS Act join Extreme?", { exact: true }).count())) { failed++; console.error("FAIL no Act question"); }
  await page.getByText("Without Act", { exact: true }).first().click();
  await page.waitForTimeout(150);
  const r = await page.evaluate(() => ({ modes: window.__modes || [], consents: window.__consents || [] }));
  if (JSON.stringify(r) !== JSON.stringify({ modes: ["extreme"], consents: [false] })) { failed++; console.error(`FAIL extreme consent flow: ${JSON.stringify(r)}`); }
  await page.close();
  cases.push(["extreme-consent"]);
}
// The sharpening correction goes to the backend in 0.05 steps.
{
  const page = await openPage(browser, STATES["home-extreme"]);
  await page.locator(".xsharp .stepb").nth(1).click();
  await page.waitForTimeout(120);
  const v = await page.evaluate(() => window.__sharp || []);
  if (JSON.stringify(v) !== "[0.05]") { failed++; console.error(`FAIL extreme sharpening step: ${JSON.stringify(v)}`); }
  await page.close();
  cases.push(["extreme-sharpening"]);
}
// Extreme native preferences are available, saved independently and rolled back on RPC failure.
{
  const page = await openPage(browser, STATES["home-extreme"]);
  await page.getByText("Stall shield", { exact: true }).first().click();
  await page.waitForTimeout(120);
  await page.getByText("Frame timing", { exact: true }).first().click();
  await page.waitForTimeout(120);
  const sets = await page.evaluate(() => (window.__featureSets || []).map(x => x.slice(1)));
  if (JSON.stringify(sets) !== '[["shield",true],["latency",false]]') {
    failed++; console.error("FAIL frame timing preference calls: " + JSON.stringify(sets));
  }
  await page.close();
  cases.push(["extreme-frame-preferences"]);
}
{
  const state = { ...STATES["home-extreme"], __featureFail: true };
  const page = await openPage(browser, state);
  const row = page.locator(".row").filter({ has: page.getByText("Stall shield", { exact: true }) });
  await row.click();
  await page.waitForTimeout(120);
  if (!(await page.getByText("Could not save frame timing", { exact: true }).count())
      || await row.locator(".tog.on").count()) {
    failed++; console.error("FAIL frame timing save error kept a successful toggle");
  }
  await page.close();
  cases.push(["extreme-frame-preferences-error"]);
}
// Energy text is cap savings; its independent arc is the current battery charge.
{
  for (const [slow, fast, expected] of [[15,15,"25%"],[12,12,"40%"],[12.75,12.75,"36%"],[12,20,"0%"],[null,null,"—"]]) {
    const state = { ...STATES["home-frame-os-act"], battery: { percent: 72 }, power: { observed_tdp_w: slow, observed_fast_w: fast, maximum_tdp_w: 30, gamescope_max_tdp_w: 20 } };
    const page = await openPage(browser, state);
    const data = await page.evaluate(() => {
      const ring = [...document.querySelectorAll(".fos .mini")].find(e => e.querySelector(".mlab").textContent === "Energy");
      return { text: ring.querySelector(".mnum").textContent, offset: Number(ring.querySelector("circle:last-child").getAttribute("stroke-dashoffset")) };
    });
    if (data.text !== expected || Math.abs(data.offset - 2 * Math.PI * 26 * .28) > .0001) {
      failed++; console.error("FAIL Energy text/arc: " + JSON.stringify(data));
    }
    await page.close();
  }
  cases.push(["energy-cap-number-battery-arc"]);
}
{
  const page = await openPage(browser, STATES["home-extreme"], ["Settings", "Frame generation backend"]);
  if (await page.getByText("GFG Open generator", { exact: true }).count()) {
    failed++; console.error("FAIL retired generator still selectable");
  }
  for (const e of page.__errors) { failed++; console.error("FAIL ordinary generator: " + e); }
  await page.close();
  cases.push(["ordinary-generator-only"]);
}
// Battery charge drives arc and colour independently of cap savings.
{
  for (const [charge, maximum, expectedText] of [[100,20,"25%"],[50,20,"25%"],[25,20,"25%"],[0,20,"25%"],[null,20,"25%"],[72,null,"—"]]) {
    const state = { ...STATES["home-frame-os-act"], battery: { percent: charge },
      power: { observed_tdp_w: 15, observed_fast_w: 15, gamescope_max_tdp_w: maximum } };
    const page = await openPage(browser, state);
    const data = await page.evaluate(() => {
      const ring = [...document.querySelectorAll(".fos .mini")].find(e => e.querySelector(".mlab").textContent === "Energy");
      const circles = ring.querySelectorAll("circle");
      return { text: ring.querySelector(".mnum").textContent, count: circles.length,
        offset: Number(circles[circles.length - 1].getAttribute("stroke-dashoffset")),
        color: circles[circles.length - 1].getAttribute("stroke") };
    });
    const expectedColor = charge == null ? "#26262d" : "hsl(" + (120 * Math.min(1, charge / 50)) + " 80% 52%)";
    const badArc = charge == null ? data.count !== 1 : Math.abs(data.offset - 2 * Math.PI * 26 * (1 - charge / 100)) > .0001;
    if (data.text !== expectedText || badArc || data.color !== expectedColor) {
      failed++; console.error("FAIL battery ENERGY " + JSON.stringify({charge, data}));
    }
    await page.close();
  }
  cases.push(["energy-battery-colour-and-unknown-limits"]);
}
// Installation succeeds or fails visibly; copying is distinct from enabling CSS Loader.
for (const fail of [false, true]) {
  const page = await openPage(browser, { ...STATES["home-extreme"], __themeFail: fail }, ["Settings", "GFG theme"]);
  await page.getByText("Install theme", { exact: true }).click();
  await page.waitForTimeout(150);
  const text = fail ? "Theme folder is read-only" : "Installed and up to date";
  if (!(await page.getByText(text, { exact: true }).count()) ||
      await page.evaluate(() => window.__themeCalls) !== 1) {
    failed++; console.error("FAIL theme installer " + text);
  }
  for (const error of page.__errors) { failed++; console.error("FAIL theme: " + error); }
  await page.close();
  cases.push(["theme-installer-" + (fail ? "error" : "success")]);
}
for (const fail of [false, true]) {
  const page = await openPage(browser, { ...STATES["home-extreme"], __flowFail: fail, flow_control: { enabled: true } }, ["Settings"]);
  const row = page.locator(".row").filter({ has: page.getByText("Automatic flow scale", { exact: true }) });
  await row.click();
  await page.waitForTimeout(150);
  const calls = await page.evaluate(() => window.__flowSets);
  const on = await row.locator(".tog.on").count();
  if (JSON.stringify(calls) !== "[false]" || on !== (fail ? 1 : 0) ||
      (fail && !(await page.getByText("Error: Could not save flow policy", { exact: true }).count()))) {
    failed++; console.error("FAIL automatic flow toggle: " + JSON.stringify({ fail, calls, on }));
  }
  await page.close();
  cases.push(["automatic-flow-" + (fail ? "error" : "success")]);
}
// C1 observation shares the existing status RPC; zero/missing never use targets.
for (const output of [0, null, 90]) {
  const page = await openPage(browser, { ...STATES["home-locked-oled"], autopilot_observation: {
    perception: { primary: "UNKNOWN", reason: "measured-fps-unavailable", confidence: 0 },
    real_fps: null, output_fps: output, sample_count: 5,
    measurement_clock: "log-receipt; producer age unavailable",
    limitation: "Correlated hypotheses; no physical latency measurement."
  } }, ["Details"]);
  const card = page.getByTestId("autopilot-observation");
  const text = await card.textContent();
  const expected = output == null ? "Output: unavailable" : "Output: " + output + " FPS";
  if (!text.includes(expected) || !text.includes("Real: unavailable") ||
      !text.includes("no Autopilot control or learning") || !text.includes("UNKNOWN")) {
    failed++; console.error("FAIL Autopilot observation: " + text);
  }
  if (page.__errors.length) { failed++; console.error("FAIL Autopilot errors: " + page.__errors); }
  await page.close();
  cases.push(["autopilot-observation-" + output]);
}
await browser.close();
console.log(failed ? `${failed} failure(s)` : `frontend smoke OK (${cases.length} screens)`);
process.exit(failed ? 1 : 0);
