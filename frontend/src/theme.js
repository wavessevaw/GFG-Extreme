// GFG Extreme 3.0 stylesheet: the approved mockup v3 (near-black, graphite, one red accent,
// soft glow and light gradients). Scoped under .gfg.
export const css = `
.gfg{--bg:#0a0a0c;--s1:#141417;--s2:#1c1c21;--s3:#26262d;--line:#2e2e36;--tx:#f5f5f7;--tx2:#a1a1ab;--tx3:#6b6b76;--red:#fb0d00;--redbg:rgba(251,13,0,.13);--ok:#3ecf6e;--warn:#e3c04a;
 font-family:"Motiva Sans","Inter","Segoe UI",system-ui,sans-serif;color:var(--tx);box-sizing:border-box;-webkit-font-smoothing:antialiased;
 padding:10px 10px 18px;min-height:100%;background:linear-gradient(180deg,#120c0d 0%,var(--bg) 22%,var(--bg) 100%)}
.gfg *{box-sizing:border-box}
.gfg .top{display:flex;align-items:center;justify-content:space-between;margin:2px 2px 10px}
.gfg .brand{display:flex;align-items:center;font-weight:800;letter-spacing:.2em;font-size:13px;white-space:nowrap}
.gfg .brand img{width:22px;height:22px;margin-right:7px;filter:drop-shadow(0 0 6px rgba(251,13,0,.6))}
.gfg .brand b{color:var(--red);text-shadow:0 0 12px rgba(251,13,0,.65);margin-left:6px}
.gfg .chip{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;color:var(--tx2);background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:4px 9px;white-space:nowrap}
.gfg .chip i{width:6px;height:6px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red)}
.gfg .tabs{display:flex;align-items:center;gap:3px;background:var(--s1);border:1px solid var(--line);border-radius:14px;padding:4px;margin-bottom:10px}
.gfg .bump{font-size:10px;font-weight:800;color:var(--tx3);background:var(--s3);border-radius:6px;padding:3px 5px}
.gfg .tab{flex:1;text-align:center;font-size:11.5px;font-weight:700;color:var(--tx2);padding:7px 0;border-radius:10px}
.gfg .tab.on{color:var(--tx);background:linear-gradient(180deg,rgba(251,13,0,.24),rgba(251,13,0,.08));box-shadow:inset 0 -2px 0 var(--red),0 0 14px rgba(251,13,0,.28)}
.gfg .card{background:linear-gradient(160deg,#18161a 0%,var(--s1) 55%,#121214 100%);border:1px solid var(--line);border-radius:16px;padding:12px;margin-bottom:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
.gfg .sec{font-size:10.5px;font-weight:800;letter-spacing:.14em;color:var(--tx3);margin:0 0 9px}
.gfg .sec2{margin-top:12px}
.gfg .hero{display:flex;gap:12px;align-items:center;background:radial-gradient(120% 110% at 22% 20%,rgba(251,13,0,.16) 0%,#1a1214 38%,var(--s1) 72%)}
.gfg .hero.col{flex-direction:column;text-align:center}
.gfg .herotap{flex:none;border-radius:50%}
.gfg .ring{position:relative;flex:none}.gfg .ring svg{position:absolute;inset:0;transform:rotate(-90deg);overflow:visible}
.gfg .ring .arcg{filter:drop-shadow(0 0 6px rgba(251,13,0,.75));transition:stroke-dashoffset .6s}
.gfg .ring .n,.gfg .arc .n{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gfg .arc{position:relative;width:190px;height:104px}.gfg .arc svg{overflow:visible}.gfg .arc .n{top:auto;justify-content:flex-end}
.gfg .wolfimg{display:block;filter:drop-shadow(0 0 6px rgba(251,13,0,.6))}
.gfg .big{font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.gfg .sm{font-weight:700;letter-spacing:.14em;color:var(--tx2);margin-top:2px}
.gfg .st h3{margin:0 0 3px;font-size:19px;font-weight:800}.gfg .st h3 b{color:var(--red)}
.gfg .st p{margin:0;font-size:11.5px;color:var(--tx2);line-height:1.35}
.gfg .phase{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}.gfg .hero.col .phase{justify-content:center}
.gfg .phase span{font-size:8px;font-weight:800;letter-spacing:.06em;padding:3px 5px;border-radius:6px;background:var(--s3);color:var(--tx3)}
.gfg .phase span.on{background:linear-gradient(135deg,#ff2d1a,#b30800);color:#fff;box-shadow:0 0 10px rgba(251,13,0,.55)}
.gfg .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:6px}
.gfg .stat{background:linear-gradient(180deg,#222228,var(--s2));border-radius:10px;padding:6px 2px;text-align:center}
.gfg .stat b{display:block;font-size:14px;font-variant-numeric:tabular-nums}.gfg .stat span{font-size:9px;color:var(--tx3);font-weight:700;letter-spacing:.08em}
.gfg .grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.gfg .tile{background:var(--s2);border:1px solid var(--line);border-radius:12px;padding:9px 10px;height:100%}
.gfg .tile b{display:block;font-size:13px}.gfg .tile span{font-size:10.5px;color:var(--tx2)}
.gfg .tile.on,.gfg .pre.on,.gfg .ec.on{border-color:var(--red);background:linear-gradient(160deg,rgba(251,13,0,.22),rgba(251,13,0,.06));box-shadow:0 0 16px rgba(251,13,0,.25);color:var(--tx)}
.gfg .seg{display:flex;background:var(--s2);border-radius:11px;padding:3px;gap:2px}
.gfg .seg>div{flex:1}
.gfg .seg .o{text-align:center;font-size:11.5px;font-weight:700;color:var(--tx2);padding:7px 0;border-radius:9px;white-space:nowrap}
.gfg .seg .o.on{background:linear-gradient(180deg,#ff2d1a,#d10a00);color:#fff;box-shadow:0 0 14px rgba(251,13,0,.45)}
.gfg .lrow{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 2px;border-top:1px solid var(--line);font-size:12.5px}
.gfg .lrow.first{border-top:0}
.gfg .lrow .v{color:var(--tx);font-weight:700;font-size:11.5px;text-align:right}
.gfg .tog{width:34px;height:20px;border-radius:999px;background:var(--s3);position:relative;flex:none}
.gfg .tog::after{content:"";position:absolute;top:3px;left:3px;width:14px;height:14px;border-radius:50%;background:var(--tx3)}
.gfg .tog.on{background:linear-gradient(180deg,#ff2d1a,#c40900);box-shadow:0 0 10px rgba(251,13,0,.55)}.gfg .tog.on::after{left:17px;background:#fff}
.gfg .step{display:flex;align-items:center;gap:6px}
.gfg .step .b{width:26px;height:26px;border-radius:8px;background:var(--s3);display:flex;align-items:center;justify-content:center;font-weight:800}
.gfg .step .val{min-width:44px;text-align:center;font-weight:800;font-variant-numeric:tabular-nums}
.gfg .chips{display:flex;flex-wrap:wrap;gap:5px}
.gfg .ec{font-size:10.5px;font-weight:700;padding:5px 8px;border-radius:999px;background:var(--s2);border:1px solid var(--line);color:var(--tx2)}
.gfg .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.gfg .pre{background:var(--s2);border:1px solid var(--line);border-radius:10px;text-align:center;padding:8px 0;font-size:10.5px;font-weight:700;color:var(--tx2)}
.gfg .note{font-size:10.5px;color:var(--tx2);background:var(--s2);border-radius:10px;padding:8px 9px;line-height:1.4;margin-top:8px}
.gfg .btns{display:flex;gap:6px;margin-top:9px}.gfg .btns>div{flex:1}
.gfg .btn{text-align:center;font-size:11.5px;font-weight:800;padding:9px 0;border-radius:10px;background:var(--s3)}
.gfg .btn.red{background:linear-gradient(180deg,#ff2d1a,#d10a00);box-shadow:0 0 14px rgba(251,13,0,.45)}
.gfg .check{display:flex;gap:7px;font-size:11.5px;padding:3px 0;color:var(--tx2)}.gfg .check b{color:var(--ok)}.gfg .check b.x{color:var(--red)}
.gfg .warn{border-color:#5a2a10;background:linear-gradient(180deg,#22140d,var(--s1))}
.gfg .sub{font-size:10.5px;color:var(--tx3);line-height:1.4}
.gfg .err{font-size:11px;color:#ffb4a8;background:#2a1010;border:1px solid #5a1a10;border-radius:10px;padding:7px 9px;margin-bottom:8px}
.gfg .row{display:block}
`;
