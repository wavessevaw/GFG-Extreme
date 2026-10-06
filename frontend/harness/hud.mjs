import { createRequire } from "node:module";
const require = createRequire("/opt/npm-tools/node_modules/");
const { chromium } = require("playwright");
const rows = {
  minimal: [["FPS", "90"], ["FRAME", "11.1 ms"], ["", "x2 | 45 > 90"]],
  standard: [["FPS", "90"], ["FRAME", "11.1 ms"], ["", "x2 | 45 > 90 | scale 100% | 9W | medium"]],
  detailed: [["FPS", "90"], ["FRAME", "11.1 ms"], ["GPU", "71%  6.1W"], ["BAT", "86%  9.2W"], ["", "x2 | 45 > 90 | scale 90% | 9W | medium | locked"]],
};
const box = (k) => `<div class=h><div class=t>${rows[k].map(([a, b]) => a ? `<div class=r><b>${a}</b><span>${b}</span></div>` : `<div class="r g"><span>${b}</span></div>`).join("")}</div></div>`;
const html = (k) => `<html><body style="margin:0;width:1280px;height:800px;background:radial-gradient(90% 80% at 60% 30%,#2a3a52,#10141c 70%);font-family:Inter,sans-serif;position:relative;overflow:hidden">
<div style="position:absolute;left:0;right:0;bottom:0;height:260px;background:linear-gradient(#1a1f27,#0b0d11)"></div>
<div style="position:absolute;right:20px;bottom:14px;color:#556;font-size:12px">illustrative scene · mock of overlay layout</div>
<style>.h{position:absolute;right:14px;top:14px;background:rgba(0,0,0,.45);border-radius:8px;padding:8px 12px;color:#fff;font:600 20px/1.35 "DejaVu Sans Mono",monospace}
.r{display:flex;gap:14px}.r b{color:#ff6b62;min-width:62px}.r.g{color:#fff;margin-top:4px;padding-top:4px;border-top:1px solid rgba(255,255,255,.25)}</style>${box(k)}</body></html>`;
const b = await chromium.launch({ args: ["--no-sandbox"] });
for (const k of Object.keys(rows)) { const p = await b.newPage({ viewport: { width: 1280, height: 800 } }); await p.setContent(html(k)); await p.screenshot({ path: `/tmp/claude-0/shots/hud-ingame-${k}.png` }); await p.close(); }
await b.close();
