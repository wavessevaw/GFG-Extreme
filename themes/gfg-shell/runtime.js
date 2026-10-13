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
    root?.removeAttribute("data-gfg-shell-page");
    root?.removeAttribute("data-gfg-shell-role");
    delete window[KEY];
  };
  if (!config.enabled) { remove(); return { applied: false, restored: true }; }
  const isShared = location.protocol === "https:" && location.hostname === "steamloopback.host";
  // Steam's real Big Picture and overlay CEF windows have about:blank URLs.
  // The Python CDP target filter verifies their title AND internal query flag,
  // and the backend supplies this role (never the frontend user).
  const isNativeWindow = location.protocol === "about:" && location.pathname === "blank"
    && ((config.targetRole === "main" && new URLSearchParams(location.search).has("createflags"))
      || (config.targetRole === "overlay" && new URLSearchParams(location.search).has("browserviewpopup")));
  if ((!isShared && !isNativeWindow) || !root || !document.head) {
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
  const dom_nodes = document.body ? document.body.getElementsByTagName("*").length : 0;
  // Real Steam Deck builds can have hundreds of DOM nodes without the CSS
  // module prefixes seen in mock Steam screens. Do not gate a *verified*
  // native Big Picture/popup target on the installed Steam version's hashes.
  // The backend has already whitelisted its CDP title + internal URL flags;
  // the runtime independently verifies the document shape above.
  const nativeFallback = !surfaces.length && isNativeWindow && dom_nodes >= 40;
  // A shared-context target is only eligible when a Steam UI marker is present.
  // A bare SharedJSContext document is not an independent visible UI surface.
  const sharedFallback = !surfaces.length && isShared && config.targetRole === "shared"
    && dom_nodes >= 40 && !!document.querySelector(
      ".BasicUI, .gpfocus, .DialogButton, [class*='gamepad'], [class*='quickaccess'], [class*='mainmenu']");
  if (!surfaces.length && !nativeFallback && !sharedFallback) {
    remove(); return { applied: false, reason: "waiting-for-supported-surface", surfaces, dom_nodes };
  }
  const mode = nativeFallback ? "native-target" : sharedFallback ? "shared-steam-marker" : "module-probe";
  if (nativeFallback) surfaces.push(config.targetRole === "main" ? "steam-main" : "steam-overlay");
  if (sharedFallback) surfaces.push("steam-shared");
  let style = document.getElementById(ID);
  if (style && style.tagName !== "STYLE") { remove(); style = null; }
  if (!style) { style = document.createElement("style"); style.id = ID; document.head.appendChild(style); }
  if (style.textContent !== config.css) style.textContent = config.css;
  root.setAttribute("data-gfg-shell", "v1");
  root.setAttribute("data-gfg-shell-role", isNativeWindow ? config.targetRole : "shared");
  // Only full-page surfaces own the canvas; overlay windows stay transparent.
  root.toggleAttribute("data-gfg-shell-page", (isNativeWindow && config.targetRole === "main") ||
    surfaces.some(s => ["home", "library", "game", "settings", "downloads"].includes(s)));
  if (previous?.timer) clearTimeout(previous.timer);
  const state = { revision: config.revision, timer: null };
  window[KEY] = state;
  state.timer = setTimeout(() => { if (window[KEY] === state) remove(); },
    Math.max(1000, Math.min(30000, Number(config.leaseMs) || 15000)));
  return { applied: true, revision: config.revision, surfaces, mode, dom_nodes };
}
