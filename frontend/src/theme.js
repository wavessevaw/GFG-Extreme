// GFG design tokens + stylesheet. Palette: near-black, graphite surfaces, white/grey text, ONE red accent.
export const css = `
.gfg{--bg:#0a0a0c;--s1:#141417;--s2:#1c1c21;--s3:#26262d;--line:#2e2e36;--tx:#f5f5f7;--tx2:#a1a1ab;--tx3:#6b6b76;--red:#fb0d00;--red2:#d40b00;--redbg:rgba(251,13,0,.12);
 font-family:"Motiva Sans","Inter","Segoe UI",system-ui,sans-serif;color:var(--tx);background:var(--bg);box-sizing:border-box;-webkit-font-smoothing:antialiased;
 padding:12px 12px 20px;min-height:100%;letter-spacing:.005em}
.gfg *{box-sizing:border-box}
.gfg .top{display:flex;align-items:center;justify-content:space-between;margin:2px 2px 12px}
.gfg .brand{font-weight:800;letter-spacing:.2em;font-size:13px}.gfg .brand b{color:var(--red)}
.gfg .chip{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;color:var(--tx2);background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:4px 10px}
.gfg .chip i{width:6px;height:6px;border-radius:50%;background:var(--tx3)}.gfg .chip.on i{background:var(--red);box-shadow:0 0 8px var(--red)}
.gfg .card{background:var(--s1);border:1px solid var(--line);border-radius:18px;padding:16px}
.gfg .hero{display:flex;flex-direction:column;align-items:center;padding:18px 14px 14px;background:radial-gradient(120% 90% at 50% 0%,#1d1416 0%,var(--s1) 60%)}
.gfg .ring{position:relative;width:176px;height:176px}
.gfg .ring svg{position:absolute;inset:0;transform:rotate(-90deg)}
.gfg .ring .num{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gfg .ring .big{font-size:52px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.gfg .ring .sub{font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--tx2);margin-top:4px}
.gfg .hero-col{display:flex;flex-direction:column;align-items:center}
.gfg .ring.compact .big{font-size:38px}.gfg .ring.compact .sub{font-size:9.5px;letter-spacing:.14em;margin-top:3px}
.gfg .hero-side{display:flex;align-items:center;gap:14px;width:100%}
.gfg .ring.side .big{font-size:27px}
.gfg .status.left{margin-top:0;text-align:left;flex:1;min-width:0}.gfg .status .k{font-size:10px;font-weight:700;letter-spacing:.16em;color:var(--tx3);margin-bottom:3px}
.gfg .arc{position:relative;width:190px;height:100px}.gfg .arc .num{position:absolute;left:0;right:0;bottom:0;display:flex;flex-direction:column;align-items:center}
.gfg .arc .big{font-size:36px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}.gfg .arc .sub{font-size:9.5px;font-weight:700;letter-spacing:.14em;color:var(--tx2);margin-top:3px}
.gfg .flowhero .status{margin-top:0}
.gfg .bigflow{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:end;gap:6px;width:100%;margin-top:14px}
.gfg .bigflow .a{color:var(--tx3);font-size:14px;padding-bottom:16px}.gfg .bigflow .stat .v{font-size:22px}.gfg .bigflow .stat.main .v{font-size:30px;font-weight:800}
.gfg .filters{padding:12px 12px 12px}
.gfg .fgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.gfg .ftile{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 2px 7px;border-radius:12px;border:1px solid transparent;background:var(--s2);cursor:pointer}
.gfg .ftile .sw{position:relative;width:38px;height:38px;border-radius:11px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);overflow:hidden}
.gfg .ftile .slash{position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;background:var(--tx3);transform:rotate(45deg)}
.gfg .ftile .fl{font-size:10.5px;font-weight:700;color:var(--tx2);white-space:nowrap}
.gfg .ftile.on{border-color:var(--red);background:var(--redbg)}.gfg .ftile.on .fl{color:var(--tx)}
.gfg .ftile.dis{opacity:.4}
.gfg .fmore{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;padding:9px 10px;border-radius:11px;background:var(--s2);font-size:11.5px;color:var(--tx2);cursor:pointer}
.gfg .fmore span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.gfg .fmore b{color:var(--tx);font-weight:700;flex:none}
.gfg .fnote{font-size:11px;line-height:1.35;color:var(--tx3);margin:8px 2px 0}.gfg .fnote.ok{color:#2fd27a}.gfg .fnote.warn{color:#ffb4ae}
.gfg .pill.live{background:rgba(47,210,122,.16);color:#2fd27a}
.gfg .egrid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
.gfg .echip{display:flex;align-items:center;gap:8px;padding:8px 9px;border-radius:11px;background:var(--s1);border:1px solid var(--line);cursor:pointer;min-width:0}
.gfg .echip .en{font-size:12px;font-weight:600;color:var(--tx2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .echip.on{border-color:rgba(251,13,0,.6);background:var(--redbg)}.gfg .echip.on .en{color:var(--tx)}
.gfg .eord{width:20px;height:20px;border-radius:6px;background:var(--s3);color:var(--tx3);font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}
.gfg .eord.on{background:var(--red);color:#fff}
.gfg .bar.thin{height:3px}.gfg .bar.thin>div{background:#8d8d96}
.gfg .status{margin-top:10px;text-align:center}
.gfg .status .h{font-size:15px;font-weight:700}.gfg .status .p{font-size:12px;color:var(--tx2);margin-top:3px;line-height:1.35}
.gfg .flow{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:6px;width:100%;margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
.gfg .flow .a{color:var(--tx3);font-size:14px}
.gfg .stat{text-align:center}.gfg .stat .v{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums}.gfg .stat .l{font-size:10px;letter-spacing:.14em;color:var(--tx3);font-weight:700;margin-top:2px}
.gfg .stat.hot .v{color:var(--red)}
.gfg .effort{display:flex;justify-content:space-between;align-items:center;width:100%;margin-top:12px;font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--tx3)}
.gfg .effort .lv{font-size:12px;letter-spacing:.12em;color:var(--tx2)}
.gfg .effort .lv.hard,.gfg .effort .lv.nightmare{color:var(--red)}
.gfg .effort .lv .why{font-size:10px;font-weight:600;letter-spacing:.04em;color:var(--tx3);text-transform:none}
.gfg .power{width:100%;margin-top:12px}
.gfg .power .r{display:flex;justify-content:space-between;font-size:11px;color:var(--tx2);margin-bottom:6px;font-weight:600}
.gfg .bar{height:6px;background:var(--s3);border-radius:6px;overflow:hidden}.gfg .bar>div{height:100%;background:var(--red);border-radius:6px}
.gfg .run{margin-top:12px;width:100%;height:58px;border-radius:16px;border:0;display:flex;align-items:center;justify-content:center;gap:10px;font-size:17px;font-weight:800;letter-spacing:.18em;color:#fff;background:linear-gradient(180deg,#ff3b2a 0%,#fb0d00 50%,#d10b00 100%);box-shadow:0 8px 24px rgba(251,13,0,.30);cursor:pointer}
.gfg .run.stop{background:var(--s2);border:1px solid var(--line);box-shadow:none;color:var(--tx)}
.gfg .run svg{width:18px;height:18px}
.gfg .hint{font-size:11.5px;color:var(--tx2);text-align:center;margin:10px 6px 0;line-height:1.4}
.gfg .list{margin-top:14px;background:var(--s1);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.gfg .row{display:flex;align-items:center;gap:12px;padding:13px 14px;border-top:1px solid var(--line);cursor:pointer;min-height:50px}
.gfg .row:first-child{border-top:0}
.gfg .row .ic{width:30px;height:30px;border-radius:9px;background:var(--s3);display:flex;align-items:center;justify-content:center;color:var(--tx2)}
.gfg .row .t{flex:1;min-width:0}.gfg .row .t b{display:block;font-size:14px;font-weight:600}.gfg .row .t span{display:block;font-size:11.5px;color:var(--tx2);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gfg .row .chev{color:var(--tx3);font-size:18px}
.gfg .row .val{font-size:12.5px;color:var(--tx2);font-weight:600}
.gfg [tabindex]:focus,.gfg .gpfocus,.gfg .gpfocuswithin:focus-within,.gfg .focus{outline:2px solid var(--red);outline-offset:-2px}
.gfg .bar-top{display:flex;align-items:center;gap:8px;margin:0 0 12px}
.gfg .back{width:38px;height:38px;border-radius:12px;background:var(--s2);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:20px;color:var(--tx);cursor:pointer}
.gfg .title{font-size:17px;font-weight:700}
.gfg .sec{font-size:10.5px;letter-spacing:.16em;color:var(--tx3);font-weight:700;margin:16px 4px 8px}
.gfg .seg{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;background:var(--s2);border:1px solid var(--line);border-radius:14px;padding:3px;gap:3px}
.gfg .seg .segb{display:flex;align-items:center;justify-content:center;border:0;background:transparent;color:var(--tx2);font:inherit;font-size:12.5px;font-weight:700;padding:10px 4px;border-radius:11px;cursor:pointer}
.gfg .seg .segb.on{background:var(--red);color:#fff}
.gfg .tog{width:46px;height:28px;border-radius:999px;background:var(--s3);position:relative;flex:none;transition:.15s}
.gfg .tog::after{content:"";position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#d8d8de;transition:.15s}
.gfg .tog.on{background:var(--red)}.gfg .tog.on::after{left:21px;background:#fff}
.gfg .step{display:flex;align-items:center;gap:6px}
.gfg .step .stepb{display:flex;align-items:center;justify-content:center;width:36px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--s2);color:var(--tx);font-size:18px;font-weight:700;cursor:pointer}
.gfg .step .v{min-width:48px;text-align:center;font-weight:700;font-variant-numeric:tabular-nums}
.gfg .note{display:flex;gap:10px;background:var(--redbg);border:1px solid rgba(251,13,0,.35);border-radius:14px;padding:11px 12px;font-size:12px;line-height:1.4;color:#ffd4d1;margin-top:12px}
.gfg .note.quiet{background:var(--s2);border-color:var(--line);color:var(--tx2)}
.gfg .kv{display:grid;grid-template-columns:auto 1fr;gap:7px 12px;font-size:12.5px;padding:2px 2px}
.gfg .kv span{color:var(--tx2)}.gfg .kv b{font-weight:600;text-align:right;font-variant-numeric:tabular-nums}
.gfg .fos{margin-top:12px;padding:12px 12px 14px}
.gfg .fos-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font-size:10.5px;letter-spacing:.16em;color:var(--tx3);font-weight:700}
.gfg .pill{font-size:10px;font-weight:800;letter-spacing:.12em;padding:3px 8px;border-radius:999px;background:var(--s3);color:var(--tx2)}
.gfg .pill.boost{background:rgba(47,210,122,.16);color:#2fd27a}.gfg .pill.rest{background:#2a2f3a;color:#cfd6e4}
.gfg .pill.would{background:transparent;border:1px dashed var(--tx3);color:var(--tx2)}
.gfg .pill.ab{background:rgba(150,190,255,.16);color:#96beff}
.gfg .abline{margin-top:10px;text-align:center;font-size:11px;color:var(--tx3);letter-spacing:.02em}
.gfg .rings{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.gfg .mini{display:flex;flex-direction:column;align-items:center;gap:7px}
.gfg .mring{position:relative}.gfg .mring svg{position:absolute;inset:0;transform:rotate(-90deg)}
.gfg .mnum{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.gfg .mnum.dim{color:var(--tx3)}
.gfg .mlab{font-size:10px;font-weight:600;letter-spacing:.06em;color:var(--tx2)}
.gfg .cols{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.gfg .col{background:var(--s2);border:1px solid var(--line);border-radius:12px;padding:10px}
.gfg .col h4{margin:0 0 6px;font-size:10px;letter-spacing:.16em;color:var(--tx3)}
.gfg .col.hot{border-color:rgba(251,13,0,.5)}.gfg .col.hot h4{color:var(--red)}
.gfg .col div{font-size:12px;display:flex;justify-content:space-between;padding:2px 0}.gfg .col div span{color:var(--tx2)}
`;
