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
.gfg .cols{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.gfg .col{background:var(--s2);border:1px solid var(--line);border-radius:12px;padding:10px}
.gfg .col h4{margin:0 0 6px;font-size:10px;letter-spacing:.16em;color:var(--tx3)}
.gfg .col.hot{border-color:rgba(251,13,0,.5)}.gfg .col.hot h4{color:var(--red)}
.gfg .col div{font-size:12px;display:flex;justify-content:space-between;padding:2px 0}.gfg .col div span{color:var(--tx2)}
`;
