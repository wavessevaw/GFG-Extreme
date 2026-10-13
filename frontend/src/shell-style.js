export const shellStyle = `
.gfg-shell-controls { color:#f5f5f7; font-size:14px; text-align:left; }
.gfg-shell-controls * { box-sizing:border-box; }
.gfg-shell-controls header { display:flex; justify-content:space-between; align-items:center; gap:12px; margin:0 0 14px; }
.gfg-shell-controls header strong { font-size:20px; }
.gfg-shell-controls header span { border:1px solid #35373f; border-radius:8px; padding:4px 8px; font-size:11px; max-width:45%; overflow-wrap:anywhere; }
.gfg-shell-card { border:1px solid #35373f; background:#17181b; border-radius:12px; margin-bottom:12px; overflow:hidden; }
.gfg-shell-switch { display:flex; align-items:center; justify-content:space-between; gap:12px; width:100%; min-height:68px; padding:12px; color:inherit; background:transparent; border:0; text-align:left; }
.gfg-shell-switch + .gfg-shell-switch { border-top:1px solid #35373f; }
.gfg-shell-switch strong { display:block; font-size:14px; }
.gfg-shell-controls small { display:block; color:#b0b2bf; font-size:11px; line-height:1.4; margin-top:4px; }
.gfg-shell-track { width:44px; height:26px; flex:0 0 44px; border-radius:99px; background:#35373f; padding:3px; }
.gfg-shell-track i { display:block; width:20px; height:20px; border-radius:50%; background:#f5f5f7; }
.gfg-shell-track.is-on { background:#fc0700; }
.gfg-shell-track.is-on i { transform:translateX(18px); }
.gfg-shell-priority { padding:0 12px 12px; }
.gfg-shell-segments { display:flex; padding:3px; gap:3px; margin-top:8px; background:#25262b; border-radius:10px; }
.gfg-shell-segments > * { flex:1; min-width:0; text-align:center; padding:9px 3px; border-radius:8px; font-size:11px; }
.gfg-shell-controls button { font:inherit; cursor:pointer; }
.gfg-shell-controls nav { display:flex; gap:8px; }
.gfg-shell-controls nav > * { flex:1; padding:12px 8px; border:1px solid #35373f; background:#17181b; color:inherit; text-align:center; border-radius:10px; }
.gfg-shell-segments > * { border:0; background:transparent; color:inherit; }
.gfg-shell-segments .selected { background:#fc0700; color:white; }
.gfg-shell-controls [aria-disabled=true], .gfg-shell-controls button:disabled { opacity:.5; }
.gfg-shell-controls .gpfocus, .gfg-shell-controls :focus-visible { outline:2px solid #fc0700; outline-offset:-2px; }
.gfg-shell-controls p { font-size:12px; line-height:1.45; overflow-wrap:anywhere; }
`;
