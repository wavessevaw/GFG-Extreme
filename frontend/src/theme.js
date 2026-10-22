// GFG Extreme 3.0 stylesheet: the approved mockup v3 (near-black, graphite, one red accent,
// soft glow and light gradients). Scoped under .gfg.
export const css = `
.gfg{--bg:#0a0a0c;--s1:#141417;--s2:#1c1c21;--s3:#26262d;--line:#2e2e36;--tx:#f5f5f7;--tx2:#a1a1ab;--tx3:#6b6b76;--red:#fb0d00;--redbg:rgba(251,13,0,.13);--ok:#3ecf6e;--warn:#e3c04a;
 font-family:"Motiva Sans","Inter","Segoe UI",system-ui,sans-serif;color:var(--tx);box-sizing:border-box;-webkit-font-smoothing:antialiased;
 padding:10px 10px 18px;min-height:100%;background:linear-gradient(180deg,#120c0d 0%,var(--bg) 22%,var(--bg) 100%)}
.gfg *{box-sizing:border-box}
.gfg .top{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 10px;margin:4px 2px 12px;line-height:1.2}
.gfg .brand{display:flex;align-items:center;font-weight:800;letter-spacing:.14em;font-size:12px;white-space:nowrap}
.gfg .brand img{width:20px;height:20px;margin-right:6px;filter:drop-shadow(0 0 6px rgba(251,13,0,.6))}
.gfg .brand b{color:var(--red);text-shadow:0 0 12px rgba(251,13,0,.65);margin-left:5px}
.gfg .chip{display:inline-flex;align-items:center;gap:5px;font-size:9.5px;font-weight:600;color:var(--tx2);background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:3px 8px;white-space:nowrap;margin-left:auto}
.gfg .chip i{width:5px;height:5px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red)}
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
.gfg .minis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 4px;background:linear-gradient(160deg,#18161a 0%,var(--s1) 55%,#121214 100%);border:1px solid var(--line);border-radius:16px;padding:10px 4px 8px;margin-bottom:10px}
.gfg .mini{display:flex;flex-direction:column;align-items:center}
.gfg .mring{position:relative;width:62px;height:62px}.gfg .mring svg{position:absolute;inset:0;transform:rotate(-90deg);overflow:visible}
.gfg .mring .mg{transition:stroke-dashoffset .6s,stroke .6s}
.gfg .mn{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1}
.gfg .mn b{font-weight:800;font-variant-numeric:tabular-nums;line-height:1}.gfg .mn i{font-style:normal;line-height:1;font-size:8px;font-weight:700;color:var(--tx3);margin-top:2px;letter-spacing:.04em}
.gfg .mini>span{font-size:8.5px;font-weight:800;letter-spacing:.08em;color:var(--tx3);margin-top:4px}
.gfg .fgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.gfg .ftile{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 2px 7px;border-radius:12px;border:1px solid transparent;background:var(--s2)}
.gfg .ftile .sw{position:relative;width:38px;height:38px;border-radius:11px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);overflow:hidden}
.gfg .ftile .slash{position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;background:var(--tx3);transform:rotate(45deg)}
.gfg .ftile .fl{font-size:10.5px;font-weight:700;color:var(--tx2);white-space:nowrap}
.gfg .ftile.on{border-color:var(--red);background:var(--redbg);box-shadow:0 0 14px rgba(251,13,0,.22)}.gfg .ftile.on .fl{color:var(--tx)}
.gfg .fmore{margin-top:10px;padding:9px 10px;border-radius:11px;background:var(--s2);font-size:11.5px;color:var(--tx2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gfg .egrid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
.gfg .echip{display:flex;align-items:center;gap:8px;padding:8px 9px;border-radius:11px;background:var(--s2);border:1px solid var(--line);min-width:0}
.gfg .echip .en{font-size:12px;font-weight:600;color:var(--tx2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .echip.on{border-color:rgba(251,13,0,.6);background:var(--redbg)}.gfg .echip.on .en{color:var(--tx)}
.gfg .eord{width:20px;height:20px;border-radius:6px;background:var(--s3);color:var(--tx3);font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}
.gfg .eord.on{background:var(--red);color:#fff}
.gfg .t2 b{display:block;font-size:12.5px;font-weight:600}.gfg .t2 span{font-size:10px;color:var(--tx3)}
.gfg .tile.mode{display:flex;align-items:center;gap:8px;position:relative;overflow:hidden;padding:7px 8px;line-height:1.2}
.gfg .tile.mode>div:last-child{min-width:0}
.gfg .tile.mode b{font-size:12.5px;line-height:1.2}.gfg .tile.mode span{display:block;font-size:10px;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .mico{width:26px;height:26px;flex:none;border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--tx2);
 background:linear-gradient(160deg,#33333b,#1c1c21);box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 0 0 1px var(--line)}
.gfg .tile.mode{background:linear-gradient(160deg,#222228 0%,var(--s2) 60%,#18181c 100%)}
.gfg .tile.mode.on .mico{color:#fff;background:linear-gradient(160deg,#ff2d1a,#b30800);box-shadow:0 0 12px rgba(251,13,0,.5)}
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
.gfg .note.bad{color:#ffb4a8;background:#2a1010}
.gfg .btns{display:flex;gap:6px;margin-top:9px}.gfg .btns>div{flex:1}
.gfg .btn{text-align:center;font-size:11.5px;font-weight:800;padding:9px 0;border-radius:10px;background:var(--s3)}
.gfg .btn.red{background:linear-gradient(180deg,#ff2d1a,#d10a00);box-shadow:0 0 14px rgba(251,13,0,.45)}
.gfg .check{display:flex;gap:7px;font-size:11.5px;padding:3px 0;color:var(--tx2)}.gfg .check b{color:var(--ok)}.gfg .check b.x{color:var(--red)}
.gfg .warn{border-color:#5a2a10;background:linear-gradient(180deg,#22140d,var(--s1))}
.gfg .sub{font-size:10.5px;color:var(--tx3);line-height:1.4}
.gfg .err{font-size:11px;color:#ffb4a8;background:#2a1010;border:1px solid #5a1a10;border-radius:10px;padding:7px 9px;margin-bottom:8px}
.gfg .row{display:block}
/* Gamepad focus: Steam marks the element under the stick / D-pad with .gpfocus, but our own
   backgrounds hide its ring. As in 2.x, the focused control turns white; a selected one gets a white ring. */
.gfg .gpfocus,.gfg :focus-visible{outline:none}
.gfg .tab.gpfocus,.gfg .seg .o.gpfocus,.gfg .pre.gpfocus,.gfg .ec.gpfocus,.gfg .ftile.gpfocus,.gfg .echip.gpfocus,.gfg .btn.gpfocus,.gfg .step .b.gpfocus,.gfg .bump.gpfocus,.gfg .gpfocus>.tile,
.gfg .tab:focus-visible,.gfg .seg .o:focus-visible,.gfg .pre:focus-visible,.gfg .ec:focus-visible,.gfg .btn:focus-visible,.gfg .step .b:focus-visible,.gfg :focus-visible>.tile{background:linear-gradient(180deg,#fff 0%,#dcdce2 100%)!important;color:#0a0a0c!important;border-color:#fff!important;box-shadow:0 0 16px rgba(255,255,255,.35)!important}
.gfg .gpfocus>.tile span,.gfg :focus-visible>.tile span{color:#3a3a44!important}
.gfg .tab.on.gpfocus,.gfg .seg .o.on.gpfocus,.gfg .pre.on.gpfocus,.gfg .ec.on.gpfocus,.gfg .ftile.on.gpfocus,.gfg .echip.on.gpfocus,.gfg .btn.red.gpfocus,.gfg .gpfocus>.tile.on,
.gfg .tab.on:focus-visible,.gfg .seg .o.on:focus-visible,.gfg .pre.on:focus-visible,.gfg .ec.on:focus-visible,.gfg .btn.red:focus-visible,.gfg :focus-visible>.tile.on{background:linear-gradient(180deg,#ff2d1a,#d10a00)!important;color:#fff!important;box-shadow:0 0 0 2px #fff,0 0 18px rgba(251,13,0,.6)!important}
.gfg .gpfocus>.tile.on span,.gfg :focus-visible>.tile.on span{color:#ffd9d4!important}
.gfg .tog.gpfocus,.gfg .tog:focus-visible,.gfg .herotap.gpfocus,.gfg .herotap:focus-visible{box-shadow:0 0 0 2px #fff,0 0 14px rgba(255,255,255,.4)!important}
.gfg .gpfocus>.lrow,.gfg :focus-visible>.lrow{background:var(--s3);border-radius:10px;box-shadow:0 0 0 2px #fff}
.gfg .gate{text-align:center;padding:18px 12px 16px}
.gfg .gate .wolf{display:block;width:60px;height:60px;margin:2px auto 10px;filter:drop-shadow(0 0 16px rgba(251,13,0,.7))}
.gfg .gate .gh{font-size:14px;font-weight:800;margin:0 0 6px;line-height:1.25}
.gfg .gate .gp{font-size:10.5px;color:var(--tx2);line-height:1.45;margin:0 0 12px}
.gfg .steps{display:flex;gap:5px;margin:0 0 12px}
.gfg .st{flex:1;min-width:0;border-radius:10px;padding:7px 2px;background:var(--s2);border:1px solid var(--line);font-size:9.5px;font-weight:700;color:var(--tx3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .st b{display:block;font-size:12.5px;margin-bottom:1px}
.gfg .st.on{color:var(--tx);border-color:rgba(251,13,0,.6);background:linear-gradient(180deg,rgba(251,13,0,.22),rgba(251,13,0,.06));box-shadow:0 0 14px rgba(251,13,0,.25)}
.gfg .st.done{color:var(--ok)}
.gfg .gate>.steps,.gfg .gate>.btn,.gfg .gate>.btns,.gfg .gate>.note{align-self:stretch;width:100%}
.gfg .gate .btn{white-space:nowrap}
.gfg .gate .small{font-size:9.5px;color:var(--tx3);margin-top:9px;line-height:1.4}
.gfg .gate .note{text-align:left}
`;
