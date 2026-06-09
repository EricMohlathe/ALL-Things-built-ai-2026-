#!/usr/bin/env python3
"""Generate the OpenAlice Hub dashboard (index.html + PWA + icons). Stdlib only."""
import os, json, zlib, struct, html

HUB = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HUB, "dashboard")
os.makedirs(OUT, exist_ok=True)

def load(p, d):
    try: return json.load(open(os.path.join(HUB, p)))
    except Exception: return d

cfg = load("config.json", {})
conns = load("registry/connectors.json", [])
ais = load("registry/ai_backends.json", [])
strats = load("registry/strategies.json", [])

# ---- icon: green candlestick / up-arrow on dark, stdlib PNG ----
def _intri(px,py,x1,y1,x2,y2,x3,y3):
    d1=(px-x2)*(y1-y2)-(x1-x2)*(py-y2); d2=(px-x3)*(y2-y3)-(x2-x3)*(py-y3); d3=(px-x1)*(y3-y1)-(x3-x1)*(py-y1)
    return not(((d1<0)or(d2<0)or(d3<0)) and ((d1>0)or(d2>0)or(d3>0)))
def write_png(path,size):
    top=(16,185,129); bot=(5,90,120)  # emerald -> teal
    cx=size*0.5
    ax,ay=size*0.5,size*0.20; al,ar=size*0.30,size*0.70; aw=size*0.12  # up-arrow head
    raw=bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            f=(x+y)/(2*(size-1))
            r=int(top[0]+(bot[0]-top[0])*f); g=int(top[1]+(bot[1]-top[1])*f); b=int(top[2]+(bot[2]-top[2])*f)
            white=False
            # up arrow head (triangle)
            if _intri(x+0.5,y+0.5, al,size*0.46, ar,size*0.46, ax,ay): white=True
            # shaft
            if abs(x-cx)<aw and size*0.44<y<size*0.80: white=True
            if white: r=g=b=255
            raw+=bytes((r,g,b,255))
    comp=zlib.compress(bytes(raw),9)
    def ch(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    open(path,"wb").write(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",size,size,8,6,0,0,0))+ch(b"IDAT",comp)+ch(b"IEND",b""))
for s in (1024,512,192,180): write_png(os.path.join(OUT,f"icon-{s}.png"),s)

json.dump({"name":"OpenAlice Hub","short_name":"OpenAlice","start_url":".","display":"standalone",
 "background_color":"#0a0f0d","theme_color":"#0a0f0d","icons":[
 {"src":"icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},
 {"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]},
 open(os.path.join(OUT,"manifest.webmanifest"),"w"),indent=2)
open(os.path.join(OUT,"sw.js"),"w").write("const C='oa-v1';const A=['./','./index.html','./manifest.webmanifest','./icon-192.png','./icon-512.png','./icon-180.png'];self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(A)));self.skipWaiting()});self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).catch(()=>caches.match('./index.html')))))")

mode = cfg.get("mode","paper"); live = cfg.get("live_enabled",False)
banner = ("🔴 LIVE — real money, per-order confirmation required" if (mode=="live" and live)
          else "🟡 TESTNET — sandbox" if mode=="testnet" else "🟢 PAPER — simulated only, nothing sent to any exchange")
def esc(s): return html.escape(str(s))
def rows_conn():
    return "".join(f'<div class=card><h3>{esc(c["name"])} <span class="k {("exec" if c.get("exec_capable") else "read")}">{"⚡exec" if c.get("exec_capable") else "read"}</span></h3><p>{esc(c.get("note",""))}</p><div class=cmd><code>{esc(c.get("mcp_cmd") or c.get("url"))}</code></div></div>' for c in conns)
def rows_ai():
    return "".join(f'<div class=card><h3>{esc(b["name"])} <span class="k ai">{esc(b["kind"])}</span></h3><p>{esc(b.get("note",""))}</p><div class=cmd><code>{esc(b.get("base_url") or "native")} · {esc(b.get("model") or "-")}</code></div></div>' for b in ais)
def rows_strat():
    out=""
    for s in strats:
        ex="⚡" if s.get("exec_surface") else ""
        out+=f'<div class=card><h3>{esc(s["name"])} <span class="k {esc(s.get("kind","").split("-")[0])}">{esc(s.get("kind"))}</span> {ex}</h3><p>{esc(s.get("run_hint",""))}</p></div>'
    return out

HTML=f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>OpenAlice Hub</title><link rel=manifest href=manifest.webmanifest>
<meta name=theme-color content=#0a0f0d><meta name=apple-mobile-web-app-capable content=yes>
<link rel=apple-touch-icon href=icon-180.png><link rel=icon href=icon-192.png>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(160deg,#0a0f0d,#0c1512);color:#e6f2ec;font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}
header{{padding:24px 20px 12px;position:sticky;top:0;background:#0a0f0deb;backdrop-filter:blur(10px);border-bottom:1px solid #ffffff14;z-index:5}}
h1{{margin:0;font-size:21px;display:flex;align-items:center;gap:10px}}
.logo{{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#10b981,#0e7490);display:flex;align-items:center;justify-content:center}}
.safety{{margin:12px 0 0;padding:12px 14px;border-radius:12px;font-weight:600;background:#10b98118;border:1px solid #10b98140;color:#a7f3d0}}
.stats{{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0 0;color:#8fb3a6;font-size:13px}}.stats b{{color:#e6f2ec}}
main{{padding:8px 20px 60px;max-width:1100px;margin:0 auto}}
h2{{margin:22px 2px 8px;font-size:13px;text-transform:uppercase;letter-spacing:1px;color:#8fb3a6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.card{{background:#12201b;border:1px solid #ffffff12;border-radius:13px;padding:13px 14px}}
.card h3{{margin:0 0 6px;font-size:14.5px;display:flex;align-items:center;gap:7px}}
.card p{{margin:0 0 8px;color:#8fb3a6;font-size:12.5px}}
.k{{font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;border-radius:6px;background:#ffffff14;color:#8fb3a6}}
.k.exec,.k.bot{{color:#fca5a5;background:#ef444422}}.k.read{{color:#93c5fd;background:#3b82f622}}.k.ai,.k.agent{{color:#c4b5fd;background:#8b5cf622}}.k.connector,.k.base{{color:#6ee7b7;background:#10b98122}}
.cmd{{background:#0a120f;border:1px solid #ffffff12;border-radius:8px;padding:7px 9px;font:11.5px ui-monospace,Menlo,monospace;color:#bfe6d6;overflow:auto}}
.note{{background:#f59e0b14;border:1px solid #f59e0b33;border-radius:11px;padding:11px 13px;margin:14px 0;color:#fcd9a0;font-size:12.5px}}
footer{{padding:22px;text-align:center;color:#6f8d80;font-size:12px;border-top:1px solid #ffffff12}}
</style></head><body>
<header><h1><span class=logo>📈</span> OpenAlice Hub</h1>
<div class=safety>{banner}</div>
<div class=stats><span><b>{len(conns)}</b> connectors</span><span><b>{len(ais)}</b> AI backends</span><span><b>{len(strats)}</b> strategy modules</span><span>mode: <b>{mode}</b></span></div>
</header><main>
<div class=note><b>How orders work:</b> every order routes through one ExecutionGate. PAPER = simulated. LIVE requires a human-typed, per-order token (no AI can self-confirm). Analysis &amp; data are unrestricted. This is by design — there is no autonomous money-mover here.</div>
<h2>Platform connectors (MCP) — "see what I see"</h2><div class=grid>{rows_conn()}</div>
<div class=note>Add ANY trading platform: <code>python3 hub.py add-connector --name X --mcp "npx -y X-mcp" --exec</code> &nbsp;→ it prints the <code>claude mcp add</code> line.</div>
<h2>AI backends — Claude · Hermes · your own</h2><div class=grid>{rows_ai()}</div>
<div class=note>Attach your own AI: <code>python3 hub.py add-ai --name mybrain --base-url http://host:1234/v1 --model m --key sk-...</code>. Hermes attaches via the <b>hermes-9router</b> slot.</div>
<h2>Backtesting — real data, no keys</h2>
<div class=grid>
<div class=card><h3>sma_cross <span class="k base">run</span></h3><p>20/50 SMA trend. Crypto via Binance, stocks via Yahoo.</p><div class=cmd><code>python3 hub.py backtest sma_cross BTCUSDT</code></div></div>
<div class=card><h3>donchian <span class="k base">run</span></h3><p>20/10 channel breakout (trend).</p><div class=cmd><code>python3 hub.py backtest donchian BTCUSDT</code></div></div>
<div class=card><h3>rsi2 <span class="k base">run</span></h3><p>Connors RSI(2) mean-reversion above 200-SMA.</p><div class=cmd><code>python3 hub.py backtest rsi2 AAPL --source yahoo</code></div></div>
</div>
<div class=note>Tearsheet reports return vs <b>buy&amp;hold + alpha</b>, Sharpe/Sortino, max drawdown, win-rate, profit factor. No lookahead (fills next-open), fees charged, every fill logged through the paper gate. See <code>BACKTESTING.md</code>.</div>
<h2>Strategy / agent modules ({len(strats)})</h2><div class=grid>{rows_strat()}</div>
</main>
<footer>OpenAlice Hub · ~/ai-tools/trading/openalice-hub · paper-safe by default<br>⚡ = module has a live-order surface (always gated). Not financial advice. Trading risks real loss.</footer>
<script>if('serviceWorker'in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{{}}))</script>
</body></html>"""
open(os.path.join(OUT,"index.html"),"w").write(HTML)
print("dashboard written:",len(HTML),"bytes |",len(conns),"connectors,",len(ais),"ai,",len(strats),"strategies")
