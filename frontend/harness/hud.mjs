import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
// The status line exactly as governor_hud.status_line writes it (MangoHud draws it top right).
const rows = {
  minimal: "<b>90</b> FPS  <i>x3  (30)</i>",
  standard: "<b>90</b> FPS  <i>x3  (30)  sc100  TDP 9W  APU 8W  2h32  easy</i>",
  detailed: "<b>90</b> FPS  <i>x3  (30)  sc100  TDP 9W  APU 8W  2h32  easy  locked</i>",
  // Frame OS Act boosting in a fight: 45 real frames at 90 Hz.
  "frame-os": "<b>90</b> FPS  <i>x2  (45)  sc100  TDP 12W  APU 11W  2h05  med  FOS boost 45</i>",
};
const box = (k) => `<div class=h>${rows[k]}</div>`;
const html = (k) => `<html><body style="margin:0;width:1280px;height:800px;background:radial-gradient(90% 80% at 60% 30%,#2a3a52,#10141c 70%);font-family:Inter,sans-serif;position:relative;overflow:hidden">
<div style="position:absolute;left:0;right:0;bottom:0;height:260px;background:linear-gradient(#1a1f27,#0b0d11)"></div>
<div style="position:absolute;right:20px;bottom:14px;color:#556;font-size:12px">illustrative scene · mock of overlay layout</div>
<style>.h{position:absolute;right:10px;top:10px;background:rgba(0,0,0,.4);border-radius:6px;padding:5px 10px;color:#fff;font:600 16px/1.3 "DejaVu Sans Mono",monospace;white-space:pre}
.h b{color:#fb0d00;font-weight:700}.h i{font-style:normal;color:#fff;border-left:1px solid rgba(255,255,255,.3);padding-left:10px;margin-left:2px}</style>${box(k)}</body></html>`;
const b = await chromium.launch({ args: ["--no-sandbox"], ...(process.env.GFG_CHROMIUM ? { executablePath: process.env.GFG_CHROMIUM } : {}) });
for (const k of Object.keys(rows)) { const p = await b.newPage({ viewport: { width: 1280, height: 800 } }); await p.setContent(html(k)); await p.screenshot({ path: new URL(`../../docs/img/hud-ingame-${k}.png`, import.meta.url).pathname }); await p.close(); }
await b.close();
