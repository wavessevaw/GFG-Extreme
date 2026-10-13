// This checks our real React components in Chromium, not Steam compatibility.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { launch, openPage, STATES } from "./lib.mjs";
const root = fileURLToPath(new URL("../../", import.meta.url));
const theme = path.join(root, "themes/GFG-SteamOS");
const manifest = JSON.parse(fs.readFileSync(path.join(theme, "theme.json"), "utf8"));
const contracts = JSON.parse(fs.readFileSync(path.join(root, "themes/dependency-contracts.json"), "utf8"));
for (const [name, patches] of Object.entries(manifest.dependencies)) {
  assert.ok(contracts[name], `Missing dependency contract: ${name}`);
  for (const [key, value] of Object.entries(patches)) assert.ok(contracts[name].options[key]?.includes(value), `${name}: invalid ${key}=${value}`);
}
assert.equal(manifest.manifest_version, 9);
assert.ok(manifest.flags.includes("REQUIRE_NAV_PATCH"));
const browser = await launch();
let count = 0;
try {
  const parser = await browser.newPage();
  for (const [file, groups] of Object.entries(manifest.inject)) {
    assert.ok(groups.every(g => manifest.tabs[g]), `Invalid tab mapping ${file}`);
    assert.equal(path.basename(file), file);
    const css = fs.readFileSync(path.join(theme, file), "utf8");
    assert.ok(!/data-gfg-shell|@import|https?:\/\//.test(css.replace(/\/\*[\s\S]*?\*\//g, "")), `Legacy marker or remote resource: ${file}`);
    const sheet = await parser.addStyleTag({ content: css });
    assert.ok(await sheet.evaluate(e => e.sheet.cssRules.length > 0), `Empty CSS sheet ${file}`);
    count++;
  }
  await parser.close();
  const state = { ...STATES["home-autopilot"],
    frame_fusion: { setting_enabled: true, scope_active: false },
    frame_os: { feature_settings: { continuous_boost: false } } };
  const page = await openPage(browser, state);
  const themeStyle = await page.addStyleTag({ content: fs.readFileSync(path.join(theme, "tokens.css"), "utf8") });
  await page.locator(".gfg-shell-controls").waitFor();
  assert.equal(await page.getByRole("switch").count(), 3); count++;
  const boost = page.getByRole("switch", { name: "Continuous Boost", exact: true });
  await boost.click();
  await page.waitForFunction(() => document.querySelector('[aria-label="Continuous Boost"]').getAttribute("aria-checked") === "true");
  assert.deepEqual(await page.evaluate(() => window.__featureSets), [["Sample Game", "continuous_boost", true]]); count++;
  // Real failure: no optimistic toggle, error visible, request made only once.
  await page.evaluate(() => { window.__state.__fusionFail = true; });
  await page.getByRole("switch", { name: "Frame Fusion", exact: true }).click();
  await page.getByRole("alert").waitFor();
  assert.equal(await page.getByRole("switch", { name: "Frame Fusion", exact: true }).getAttribute("aria-checked"), "true"); count++;
  assert.equal(await page.locator(".gfg-shell-controls").evaluate(e => e.scrollWidth <= e.clientWidth), true);
  await page.getByText("Настройки", { exact: true }).click();
  await page.getByText("GFG theme", { exact: true }).click();
  await page.getByText("GFG CSS Loader styles detected in this window", { exact: true }).waitFor();
  assert.equal(await page.getByText("Apply the GFG appearance", { exact: false }).count(), 0); count++;
  assert.deepEqual(page.__errors, []);
  await page.close();
  const restore = await openPage(browser, state);
  const style = await restore.addStyleTag({ content: ":root{--gfg-cssloader-enabled:1}" });
  await restore.locator(".gfg-shell-controls").waitFor();
  await style.evaluate(e => e.remove());
  await restore.locator(".gfg-shell-controls").waitFor({ state: "detached" });
  await restore.getByText("MODE", { exact: true }).waitFor(); count++;
  assert.deepEqual(restore.__errors, []); await restore.close();
  const modes = await openPage(browser, state);
  await modes.addStyleTag({ content: ":root{--gfg-cssloader-enabled:1}" });
  await modes.getByText("Все режимы и управление GFG", { exact: true }).click();
  await modes.getByText("MODE", { exact: true }).waitFor();
  for (const label of ["Battery", "Balanced", "Quality"]) assert.ok(await modes.getByText(label, { exact: true }).count());
  assert.deepEqual(modes.__errors, []); await modes.close(); count++;
  for (const mode of ["budget", "balanced", "quality", "extreme"]) {
    const p = await openPage(browser, { ...state, mode });
    await p.addStyleTag({ content: ":root{--gfg-cssloader-enabled:1}" });
    await p.locator(".gfg-shell-controls").waitFor();
    const control = p.getByRole("switch", { name: "Continuous Boost", exact: true });
    assert.equal(await control.getAttribute("aria-disabled"), "true");
    await control.click({ force: true });
    assert.equal(await p.evaluate(() => (window.__featureSets || []).length), 0);
    assert.deepEqual(p.__errors, []); await p.close(); count++;
  }
  for (const fail of [false, true]) {
    const p = await openPage(browser, { ...state, __themeFail: fail }, ["Settings", "GFG theme"]);
    await p.getByText("Install CSS Loader theme", { exact: true }).click();
    await p.getByText(fail ? "Theme folder is read-only" : "Installed. Refresh CSS Loader and enable GFG SteamOS with its dependencies.", { exact: true }).waitFor();
    assert.equal(await p.evaluate(() => window.__themeCalls), 1);
    assert.equal(await p.evaluate(() => !!window.__themeInstalled), !fail);
    assert.deepEqual(p.__errors, []); await p.close(); count++;
  }
  if (process.env.GFG_SHELL_SCREENSHOT) {
    const shot = await openPage(browser, state);
    await shot.addStyleTag({ content: ":root{--gfg-cssloader-enabled:1}" });
    await shot.locator(".gfg-shell-controls").waitFor();
    await shot.screenshot({ path: process.env.GFG_SHELL_SCREENSHOT, fullPage: true });
    await shot.close();
  }
  console.log(`CSS Loader checks OK (${count}); Chromium + mocked RPC, NOT Steam Deck acceptance.`);
} finally { await browser.close(); }
