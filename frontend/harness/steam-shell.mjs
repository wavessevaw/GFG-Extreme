// Native-shape DOM fixtures, not a claim of hardware validation. Exercises the
// actual bundled runtime + stylesheet against CEF-compatible Chromium.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { chromium } from "playwright";

const root = fileURLToPath(new URL("../../", import.meta.url));
const runtime = fs.readFileSync(path.join(root, "themes/gfg-shell/runtime.js"), "utf8");
const css = fs.readFileSync(path.join(root, "themes/gfg-shell/shell.css"), "utf8");
const browser = await chromium.launch({ headless: true, ...(process.env.GFG_CHROMIUM ? { executablePath: process.env.GFG_CHROMIUM } : {}) });
const cards = ["Control", "Hades II", "Stray", "Doom", "Forza", "Elden Ring", "Portal 2", "Hollow Knight"]
  .map((name, i) => `<button class="appportrait_LibraryItemBox_hash${i} ${i === 0 ? "gpfocus" : ""}" onclick="window.actions=(window.actions||0)+1">${name}</button>`).join("");
const menu = `<aside class="mainmenu_Menu_x"><h2>Никита</h2>${["Главная", "Библиотека", "Магазин", "Друзья", "Загрузки", "Настройки"].map((n, i) => `<button class="mainmenu_MenuItem_x ${i === 1 ? "gpfocus" : ""}">${n}</button>`).join("")}</aside>`;
const fields = `<div class="gamepaddialog_Field_x"><label>Яркость</label><div class="gamepadslider_SliderTrack_x"><div class="gamepadslider_SliderTrackFilled_x" style="width:70%"></div><i class="gamepadslider_SliderThumb_x"></i></div></div><div class="gamepaddialog_Field_x">Ночной режим <button class="DialogButton">Выкл.</button></div>`;
const screens = {
  home: `<main class="gamepadhome_TabbedContent_x"><h1>Продолжить игру</h1><div class="appportrait_FeaturedCapsule_x"><h1>CONTROL</h1><button class="appdetailsplaysection_PlayButton_x" onclick="window.actions=(window.actions||0)+1">Играть</button></div><h2>Недавно играли</h2><section class="covers">${cards.slice(0, cards.indexOf('<button class="appportrait_LibraryItemBox_hash4'))}</section></main>`,
  library: `<main class="gamepadlibrary_GamepadLibrary_x"><h1>Библиотека</h1><section class="covers">${cards}</section></main>`,
  game: `<main class="basicappdetailssectionstyler_AppDetailsRoot_x"><h1>CONTROL</h1><button class="appdetailsplaysection_PlayButton_x">Играть</button><section class="appdetailssection_AppDetailsSection_x"><h2>Достижения</h2>18 / 46</section></main>`,
  quickaccess: `<aside class="quickaccessmenu_QuickAccessMenu_x"><h1>Быстрые настройки</h1>${fields}<div class="gamepaddialog_Field_x">Autopilot <button class="gamepadtoggle_ToggleSwitch_x On">Вкл.</button></div><div class="gamepaddialog_Field_x">Continuous Boost <button>Выкл.</button></div></aside>`,
  settings: `<section class="settings"><aside class="gamepadpagedsettings_PagedSettingsDialog_PageListColumn_x"><button class="gamepadpagedsettings_PageListItem_x">Система</button><button class="gamepadpagedsettings_PageListItem_x Selected">Экран</button><button class="gamepadpagedsettings_PageListItem_x">Звук</button></aside><main class="gamepadpagedsettings_PagedSettingDialog_ContentColumn_x"><h1>Экран</h1>${fields}<div class="gamepaddialog_Field_x">Частота обновления <button class="DialogButton">90 Гц</button></div></main></section>`,
  downloads: `<main class="downloads_DownloadsPage_x"><h1>Загрузки</h1><section class="downloads_Section_x"><h2>Control</h2><progress class="downloads_ProgressBar_x" value="43" max="100"></progress><p>12,4 / 28,6 ГБ</p><button class="DialogButton" onclick="window.actions=(window.actions||0)+1">Пауза</button></section><div class="downloads_DownloadItem_x">Stray — в очереди</div></main>`,
  menu,
  keyboard: `<h1>Поиск</h1><input value="Control"><section class="virtualkeyboard_Keyboard_x">${["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"].map(row => `<div>${[...row].map(key => `<button class="virtualkeyboard_KeyboardKey_x ${key === "C" ? "gpfocus" : ""}" onclick="window.actions=(window.actions||0)+1">${key}</button>`).join("")}</div>`).join("")}<button class="virtualkeyboard_KeyboardKey_x" data-key="Enter">Найти</button></section>`
};
const fixture = (body) => `<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#23384b;color:#ddd;font:24px Arial}header,footer{padding:24px;display:flex;justify-content:space-between}main{padding:30px}h1{font-size:42px}button{font:inherit;padding:18px;border:1px solid #526a80;background:#35597a;color:white}section{padding:20px;margin:20px 0}.covers{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;padding:0}.covers button{height:175px}.appportrait_FeaturedCapsule_x{background:#382121;height:230px;padding:22px;box-sizing:border-box}.appportrait_FeaturedCapsule_x h1{margin:0 0 30px}.quickaccessmenu_QuickAccessMenu_x{margin-left:auto;width:450px;padding:25px;min-height:610px}.mainmenu_Menu_x{width:300px;padding:25px}.mainmenu_Menu_x button{display:block;width:100%;margin:6px 0}.settings{display:flex;padding:0}.settings aside{padding:25px;width:230px}.settings aside button{width:100%;margin:8px 0}.settings main{flex:1}.gamepaddialog_Field_x{padding:25px;margin:15px 0;background:#203044;display:flex;justify-content:space-between;align-items:center;gap:25px}.gamepadslider_SliderTrack_x{width:230px;height:10px;position:relative;background:#778899}.gamepadslider_SliderTrackFilled_x{height:10px;background:cyan}.gamepadslider_SliderThumb_x{position:absolute;left:70%;top:-7px;width:24px;height:24px;background:white}.virtualkeyboard_Keyboard_x{margin-top:230px;padding:24px;text-align:center}.virtualkeyboard_KeyboardKey_x{width:100px;margin:4px;padding:20px}progress{width:90%;height:12px}input{font:inherit;margin:20px;padding:15px}footer{font-size:18px}
</style></head><body><header class="header_Header_x"><b>STEAM</b><span>Главная　Библиотека　Магазин</span><span>82%　21:08</span></header>${body}<footer class="footer_BasicFooter_x"><span>STEAM　Меню</span><span>A Выбрать　 B Назад</span></footer></body></html>`;
let count = 0;
try {
  for (const [surface, body] of Object.entries(screens)) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page.route("https://steamloopback.host/**", route => route.fulfill({ contentType: "text/html", body: fixture(body) }));
    await page.goto("https://steamloopback.host/Valve%20Steam%20Gamepad/default");
    const apply = enabled => page.evaluate(`(${runtime})(${JSON.stringify({ enabled, css, leaseMs: 15000, revision: "test" })})`);
    const before = await page.locator("button").count();
    assert.ok((await apply(true)).surfaces.includes(surface), surface);
    assert.equal(await page.locator("button").count(), before, "native controls preserved");
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--gfg-shell-red").trim()), "#ff1608");
    await apply(true);
    assert.equal(await page.locator("#gfg-steamos-shell-v1").count(), 1, "idempotent heartbeat");
    if (await page.locator(".gpfocus").count()) assert.equal(await page.locator(".gpfocus").first().evaluate(e => getComputedStyle(e).outlineColor), "rgb(255, 22, 8)");
    if (process.env.GFG_SHELL_SHOTS) { fs.mkdirSync(process.env.GFG_SHELL_SHOTS, { recursive: true }); await page.screenshot({ path: path.join(process.env.GFG_SHELL_SHOTS, surface + ".png"), fullPage: true }); }
    const button = page.locator("button[onclick]").first();
    if (await button.count()) { await button.click(); assert.equal(await page.evaluate(() => window.actions), 1); }
    await apply(false);
    assert.equal(await page.locator("#gfg-steamos-shell-v1").count(), 0);
    assert.equal(await page.evaluate(() => document.documentElement.hasAttribute("data-gfg-shell")), false);
    assert.equal(await page.locator("button").count(), before);
    // A reload destroys the old lease; reapplying reattaches to the new document.
    await page.reload(); await apply(true);
    assert.equal(await page.locator("#gfg-steamos-shell-v1").count(), 1);
    await page.evaluate(`(${runtime})(${JSON.stringify({ enabled: true, css, leaseMs: 1000, revision: "expiry" })})`);
    await page.waitForTimeout(1200);
    assert.equal(await page.locator("#gfg-steamos-shell-v1").count(), 0, "crash lease restores Steam");
    await page.close(); count++;
  }
  const page = await browser.newPage();
  await page.route("**/*", route => route.fulfill({ contentType: "text/html", body: fixture(screens.home) }));
  await page.goto("https://example.com/");
  assert.equal((await page.evaluate(`(${runtime})(${JSON.stringify({ enabled: true, css })})`)).applied, false);
  await page.goto("https://steamloopback.host/");
  await page.setContent("<html><head></head><body>Unrecognized client</body></html>");
  assert.equal((await page.evaluate(`(${runtime})(${JSON.stringify({ enabled: true, css })})`)).applied, false);
  console.log(`GFG Shell OK (${count} native-shape screen fixtures; enable, disable, reload, expiry, focus, native actions; unknown/external documents rejected)`);
} finally { await browser.close(); }
