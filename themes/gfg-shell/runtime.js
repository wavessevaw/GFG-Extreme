function applyGfgShell(config) {
  "use strict";
  const KEY = "__gfgSteamShellV1";
  const ID = "gfg-steamos-shell-v1";
  const root = document.documentElement;
  const previous = window[KEY];
  const remove = () => {
    const current = window[KEY];
    if (current && current.timer) clearTimeout(current.timer);
    document.getElementById(ID)?.remove();
    root?.removeAttribute("data-gfg-shell");
    delete window[KEY];
  };
  if (!config.enabled) { remove(); return { applied: false, restored: true }; }
  if (location.protocol !== "https:" || location.hostname !== "steamloopback.host" || !root || !document.head) {
    remove(); return { applied: false, reason: "unsupported-document" };
  }
  // Semantic module names rather than build-specific hashes. A changed Steam
  // module is reported as unsupported, never hidden or replaced by a fake UI.
  const probes = {
    home: '[class*="gamepadhome_"], [class*="gamepadhomerecentgames_"], [class*="basicgamecarousel_"]',
    library: '[class*="gamepadlibrary_"], [class*="allcollections_"]',
    game: '[class*="basicappdetailssectionstyler_"], [class*="appdetailsplaysection_"]',
    quickaccess: '[class*="quickaccessmenu_"]',
    settings: '[class*="gamepadpagedsettings_"]',
    downloads: '[class*="downloads_DownloadsPage_"]',
    menu: '[class*="mainmenu_Menu_"]',
    keyboard: '[class*="virtualkeyboard_"], [class*="keyboard_Keyboard_"]'
  };
  const surfaces = Object.keys(probes).filter(name => document.querySelector(probes[name]));
  if (!surfaces.length) { remove(); return { applied: false, reason: "waiting-for-supported-surface", surfaces }; }
  let style = document.getElementById(ID);
  if (style && style.tagName !== "STYLE") { remove(); style = null; }
  if (!style) { style = document.createElement("style"); style.id = ID; document.head.appendChild(style); }
  if (style.textContent !== config.css) style.textContent = config.css;
  root.setAttribute("data-gfg-shell", "v1");
  if (previous?.timer) clearTimeout(previous.timer);
  const state = { revision: config.revision, timer: null };
  window[KEY] = state;
  state.timer = setTimeout(() => { if (window[KEY] === state) remove(); },
    Math.max(1000, Math.min(30000, Number(config.leaseMs) || 15000)));
  return { applied: true, revision: config.revision, surfaces };
}
