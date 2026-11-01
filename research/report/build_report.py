"""Build the offline research report: one self-contained HTML file.

Reads the saved results of every study in research/ and writes
research/report/trading-research.html. No external scripts, fonts or
stylesheets: charts are drawn by inline JavaScript into SVG, data is inlined
as JSON, so the page works with no internet connection.

  python build_report.py
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DIP = R / "dip_rebound" / "results"
MOM = R / "momentum_regime" / "results"
PW = R / "putwrite" / "results"
OUT = Path(__file__).resolve().parent / "trading-research.html"


def rcsv(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(v, d=1, sign=False):
    if v is None:
        return "–"
    s = f"{v*100:+.{d}f}%" if sign else f"{v*100:.{d}f}%"
    return s.replace("-", "−")


def f2(v):
    return "–" if v is None else f"{v:.2f}".replace("-", "−")


def monthly(dates: list[str], values: list[float]) -> tuple[list[str], list[float]]:
    last = {}
    for d, v in zip(dates, values):
        last[d[:7]] = (d, v)
    ks = sorted(last)
    return [last[k][0] for k in ks], [last[k][1] for k in ks]


# ---------------------------------------------------------------- load data
head = {int(num(r["hold"])): {k: num(v) for k, v in r.items()} for r in rcsv(DIP / "dashboard" / "headline.csv")}
rules = rcsv(DIP / "dashboard" / "rules.csv")
port = {r["strategy"]: {k: num(v) for k, v in r.items() if k != "strategy"} for r in rcsv(DIP / "dashboard" / "portfolio.csv")}
hold = rcsv(DIP / "dashboard" / "holdout.csv")
sweep = rcsv(DIP / "dashboard" / "sweep.csv")
pull = rcsv(DIP / "dashboard" / "pullback.csv")
weekly = rcsv(DIP / "dashboard" / "weekly.csv")
wspy = rcsv(DIP / "dashboard" / "weekly_spy.csv")
mom = json.loads((MOM / "momentum.json").read_text())
snap = json.loads((MOM / "snapshot.json").read_text())
pw = json.loads((PW / "putwrite.json").read_text())

curves1 = {}
for r in rcsv(DIP / "dashboard" / "curves.csv"):
    curves1.setdefault(r["strategy"], ([], []))
    curves1[r["strategy"]][0].append(r["date"]); curves1[r["strategy"]][1].append(num(r["value"]))
c1_names = {"SPY buy & hold": "SPY", "All dips, 3d hold, 5 bps/side": "Every 2% drop",
            "Best rule, 5d hold, 5 bps/side": "Best test-1 rule", "Best rule, 5d hold, hedged, 5 bps/side": "Best rule, hedged"}
c1 = []
for k, lab in c1_names.items():
    if k in curves1:
        d, v = monthly(*curves1[k]); c1.append({"name": lab, "dates": d, "values": v})

mrows = rcsv(MOM / "curves_weekly.csv")
mcols = [c for c in mrows[0] if c != "date"]
m_names = {"SPY buy & hold": "SPY", "SPY with regime switch": "SPY + 200-day switch",
           "A: top-20 momentum, equal weight, always invested": "Plain momentum (A)",
           "D: full strategy (C + 15% vol target + 20% loss limit)": "Full strategy (D)"}
c5 = []
for k in mcols:
    pts = [(r["date"], num(r[k])) for r in mrows if num(r[k])]
    d, v = monthly([p[0] for p in pts], [p[1] for p in pts])
    c5.append({"name": m_names.get(k, k), "dates": d, "values": v})

H1N = next(r for r in hold if r["id"] == "H1" and r["universe"] == "New stocks")
BEST = next(r for r in sweep if r["combo"] == "multi5|0.02|5|1M+ shares")
n_robust = sum(1 for r in sweep if r["robust"].lower() == "true")
wvars = [r for r in weekly if r["kind"] == "variant"]
w_pass = sum(1 for r in wvars if r["passes"].lower() == "true")
turn = [num(r["turnover"]) for r in wvars]
SPYC = port["SPY buy & hold"]["cagr"]
MD = "D: full strategy (C + 15% vol target + 20% loss limit)"

data = {
    "head": [{"hold": h, "dip": head[h]["dip_raw"], "any": head[h]["anyday_raw"], "edge": head[h]["edge"]} for h in sorted(head)],
    "c1": c1,
    "holdout": [{"id": r["id"], "rule": r["rule"], "uni": r["universe"], "edge": num(r["edge"]), "t": num(r["t_stat"])} for r in hold],
    "sweep": [{"m": r["measure"], "c": num(r["cutoff"]), "cl": r["cutoff_label"], "h": int(num(r["hold"])), "v": r["volume"],
               "e": [num(r["edge_sp_2005_15"]), num(r["edge_sp_2016_26"]), num(r["edge_new"])],
               "t": [num(r["t_sp_2005_15"]), num(r["t_sp_2016_26"]), num(r["t_new"])]} for r in sweep],
    "pull": [{"u": r["universe"], "s": r["strategy"], "c": int(num(r["cost_bps"])), "cagr": num(r["cagr"]),
              "sharpe": num(r["sharpe"]), "dd": num(r["max_dd"])} for r in pull],
    "weekly": [{"name": r["variant"], "bench": r["kind"] == "benchmark", "turn": num(r["turnover"]),
                **{k: num(r[f"cagr_{k}"]) for k in ("sp_2005_15", "sp_2016_26", "new")},
                **{"s_" + k: num(r[f"sharpe_{k}"]) for k in ("sp_2005_15", "sp_2016_26", "new")}} for r in weekly],
    "wspy": {r["key"]: {"cagr": num(r["cagr"]), "sharpe": num(r["sharpe"])} for r in wspy},
    "c5": c5,
    "pwyears": pw["stress_years"],
}

# ---------------------------------------------------------------- tables
def table(cols: list[str], rows: list[list], cls: str = "") -> str:
    th = "".join(f"<th{' class=\"t\"' if i == 0 else ''}>{escape(c)}</th>" for i, c in enumerate(cols))
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td{' class=\"t\"' if i == 0 else ''}>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


hold_rows = sorted(snap["holdings"], key=lambda h: -h["weight"])
t_hold = table(["Stock", "Shares", "Last close", "Value", "Share of NAV", "Vs 200-day avg", "Last month"],
               [[escape(h["ticker"]), int(h["shares"]), f"${h['price']:,.2f}", f"${h['value']:,.0f}", pct(h["weight"]),
                 pct(h["vs_200d"], 1, True), pct(h["ret_1m"], 1, True)] for h in hold_rows])
sec_names = {"SPY": "S&P 500 (SPY)", "XLK": "Technology", "XLV": "Health care", "XLF": "Financials", "XLE": "Energy",
             "XLU": "Utilities", "XLI": "Industrials", "XLP": "Consumer staples"}
t_sec = table(["Market / sector ETF", "Vs 200-day avg", "Last month", "From 52-week high"],
              [[sec_names[k], pct(v["vs_200d"], 1, True), pct(v["ret_1m"], 1, True), pct(v["from_high"], 1, True)]
               for k, v in snap["sectors"].items()])
t_rules = table(["Rule added to the 2% drop", "Edge 2005–15", "t", "Edge 2016–26", "t"],
                [[escape(r["rule"]), pct(num(r["edge_is"]), 2, True), f2(num(r["t_is"])), pct(num(r["edge_oos"]), 2, True),
                  f2(num(r["t_oos"]))] for r in rules[:8]], "pick1")

mom_rows = []
for s in ["S&P 2005-15", "S&P 2016-26", "New stocks 2005-26"]:
    d, sp, sr = mom["strategies"][MD][s]["5bps"], mom["spy"][s], mom["spy_regime"][s]["5bps"]
    mom_rows.append([s.replace("-", "–"), f"{pct(d['cagr'])} / {f2(d['sharpe'])} / {pct(d['max_dd'], 0)}",
                     f"{pct(sp['cagr'])} / {f2(sp['sharpe'])} / {pct(sp['max_dd'], 0)}",
                     f"{pct(sr['cagr'])} / {f2(sr['sharpe'])} / {pct(sr['max_dd'], 0)}",
                     "Yes" if mom["criteria"][s]["sharpe_beats_spy"] else "<b class='bad'>No</b>"])
t_mom = table(["Sample", "Strategy: return / Sharpe / worst fall", "SPY", "SPY + 200-day switch", "Sharpe beats SPY?"], mom_rows)

pw_rows = []
for lab, blk in pw["periods"].items():
    g = lambda n: blk[f"{n} | base | after tax"]
    p, s, m = g("Put-write layer"), g("SPY buy & hold"), g("50/50 SPY / T-bills")
    ok = pw["criteria"][lab]
    pw_rows.append([lab.replace(" to ", "–"), f"{pct(p['cagr'])} / {f2(p['sharpe'])} / {pct(p['max_dd_monthly'], 0)}",
                    f"{pct(s['cagr'])} / {f2(s['sharpe'])} / {pct(s['max_dd_monthly'], 0)}",
                    f"{pct(m['cagr'])} / {f2(m['sharpe'])} / {pct(m['max_dd_monthly'], 0)}",
                    "Pass" if all(ok.values()) else "<b class='bad'>Fail</b>"])
t_pw = table(["Period (after tax)", "Put-write: return / Sharpe / worst fall", "SPY", "50/50 SPY / T-bills", "All 4 checks"], pw_rows)
vrp = pw["vrp"]
xy = pw["xyld_check"]

h3 = head[3]
mt = mom["target"]

# ---------------------------------------------------------------- page
CSS = r"""
:root{--bg:#f6f7f9;--panel:#ffffff;--fg:#17202b;--muted:#5b6675;--line:#dfe3e8;--grid:#e9ecf0;--ref:#9aa3ae;
--c0:#2563c9;--c1:#d9762b;--c2:#2f9e6e;--c3:#8b5cc4;--mute:#a7b0bb;--ok:#1f8a55;--warn:#a86b00;--bad:#c0392b;--pick:#fff4d6}
@media (prefers-color-scheme:dark){:root{--bg:#11161d;--panel:#1a212b;--fg:#e8edf3;--muted:#9aa6b4;--line:#2c3542;--grid:#252e3a;
--ref:#6c7785;--c0:#6ea0ff;--c1:#f0a35e;--c2:#5cc79a;--c3:#b48cf0;--mute:#55606d;--ok:#5cc79a;--warn:#e0b04a;--bad:#ff7a6b;--pick:#3a3320}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-left)) 64px max(16px,env(safe-area-inset-right))}
h1{font:400 2rem/1.2 Georgia,"Times New Roman",serif;margin:0 0 8px;text-wrap:balance}
h2{font:400 1.55rem/1.25 Georgia,"Times New Roman",serif;margin:0;text-wrap:balance}
h3{font-size:1.02rem;margin:0 0 4px}
p{margin:0}.muted{color:var(--muted)}.small{font-size:.85rem}
.lede{max-width:46rem;font-size:1.05rem}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 14px;margin:14px 0 0;font-size:.9rem}
nav.toc a{color:var(--c0);text-decoration:none}nav.toc a:hover{text-decoration:underline}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:12px;margin:22px 0}
.step{display:flex;flex-direction:column;gap:6px;padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:10px;color:inherit;text-decoration:none}
.step:hover{border-color:var(--ref)}.step .n{font-size:.78rem;color:var(--muted)}.step .q{font-weight:600;line-height:1.35}
.pill{align-self:flex-start;font-size:.75rem;font-weight:600;padding:1px 9px;border-radius:999px;border:1px solid currentColor}
.pill.bad{color:var(--bad)}.pill.warn{color:var(--warn)}.pill.ok{color:var(--ok)}
section.ch{margin-top:44px;padding-top:22px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:14px}
.kick{font-size:.8rem;color:var(--muted);letter-spacing:.03em}
.qa{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:12px 24px}
.qa h4{margin:0 0 2px;font-size:.78rem;color:var(--muted);letter-spacing:.03em;text-transform:uppercase}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr));gap:10px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:2px}
.tile .l{font-size:.8rem;color:var(--muted)}.tile .v{font:400 1.6rem/1.2 Georgia,serif;font-variant-numeric:tabular-nums}.tile .v.bad{color:var(--bad)}
.tile .s{font-size:.8rem;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:8px;min-width:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,28rem),1fr));gap:12px}
.verdict{border-left:4px solid var(--bad);background:var(--panel);border-radius:6px;padding:12px 16px}
.verdict.warn{border-left-color:var(--warn)}.verdict.ok{border-left-color:var(--ok)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{color:var(--muted);font-weight:600}th.t,td.t{text-align:left;white-space:normal}
table.pick1 tbody tr:first-child td{background:var(--pick)}
b.bad,.bad{color:var(--bad)}.ok{color:var(--ok)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.8rem;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.ctl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.82rem}
.ctl span{color:var(--muted);margin-right:4px}
.ctl button{font:inherit;color:var(--fg);background:transparent;border:1px solid var(--line);border-radius:6px;padding:3px 9px;cursor:pointer}
.ctl button[aria-pressed=true]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.ctl button:focus-visible{outline:2px solid var(--c0);outline-offset:2px}
.chart svg{width:100%;height:auto;display:block}
.chart text{fill:var(--muted);font-size:11px;font-family:inherit}.chart text.st{fill:var(--fg)}
.chart .grid{stroke:var(--grid)}.chart .axis{stroke:var(--ref)}.chart .ref{stroke:var(--ref);stroke-dasharray:4 3}
.k0{stroke:var(--c0)}.k1{stroke:var(--c1)}.k2{stroke:var(--c2)}.k3{stroke:var(--c3)}.km{stroke:var(--mute)}
.f0{fill:var(--c0)}.f1{fill:var(--c1)}.f2{fill:var(--c2)}.f3{fill:var(--c3)}.fm{fill:var(--mute)}.fp{fill:var(--panel)}
.b0{background:var(--c0)}.b1{background:var(--c1)}.b2{background:var(--c2)}.b3{background:var(--c3)}.bm{background:var(--mute)}
.zone{fill:var(--ok);opacity:.09}
dl.gl{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:8px 22px;margin:0}
dl.gl dt{font-weight:600}dl.gl dd{margin:0 0 4px;color:var(--muted);font-size:.86rem}
ul{margin:0;padding-left:1.15rem}li{margin:3px 0}
code{font-size:.84em;background:var(--grid);padding:1px 5px;border-radius:4px;word-break:break-all}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const NS='http://www.w3.org/2000/svg',W=720;
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function tx(p,x,y,s,a){const t=el('text',Object.assign({x,y},a||{}),p);t.textContent=s;return t}
function tip(n,s){el('title',{},n).textContent=s}
function svg(id,H){const c=document.getElementById(id);c.innerHTML='';return el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},c)}
function ticks(a,b,n){const sp=(b-a)||1,s0=sp/n,m=Math.pow(10,Math.floor(Math.log10(s0)));const st=[1,2,2.5,5,10].map(x=>x*m).find(s=>sp/s<=n)||10*m;const o=[];for(let v=Math.ceil(a/st)*st;v<=b+1e-12;v+=st)o.push(+v.toFixed(10));return o}
const P=(d,sg)=>v=>v==null?'–':((sg&&v>0?'+':'')+(v*100).toFixed(d)+'%').replace('-','−');
const F2=v=>v==null?'–':v.toFixed(2).replace('-','−');
function lin(d0,d1,r0,r1){return v=>r0+(v-d0)/(d1-d0||1)*(r1-r0)}
function yaxis(s,y,tk,fmt,x0,x1){for(const t of tk){el('line',{x1:x0,x2:x1,y1:y(t),y2:y(t),class:'grid'},s);tx(s,x0-6,y(t)+4,fmt(t),{'text-anchor':'end'})}}
function bars(id,cats,series,fmt,H){H=H||250;const s=svg(id,H),L=58,R=W-8,T=10,B=H-28;
 const vals=series.flatMap(x=>x.values);const lo=Math.min(0,...vals),hi=Math.max(...vals);const tk=ticks(lo,hi,5);
 const y=lin(Math.min(lo,tk[0]),Math.max(hi,tk[tk.length-1]),B,T);yaxis(s,y,tk,fmt,L,R);
 const gw=(R-L)/cats.length,bw=Math.min(28,gw*0.75/series.length);
 cats.forEach((c,i)=>{const g0=L+i*gw+(gw-bw*series.length)/2;tx(s,L+i*gw+gw/2,H-8,c,{'text-anchor':'middle'});
  series.forEach((se,j)=>{const v=se.values[i];const r=el('rect',{x:g0+j*bw+1,width:bw-2,y:Math.min(y(v),y(0)),height:Math.max(1,Math.abs(y(v)-y(0))),rx:2,class:se.cls},s);tip(r,`${c} · ${se.name}: ${fmt(v)}`)})});
 el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'axis'},s)}
function lines(id,series,opt){const H=opt.H||300,s=svg(id,H),L=52,T=10,B=H-24;
 const labs=series.map(se=>`${se.name} ${opt.endfmt(se.values[se.values.length-1])}`);
 const R=W-Math.min(230,Math.max(...labs.map(l=>l.length))*6.2+14);
 const all=series.flatMap(se=>se.values).filter(v=>v>0);const lg=v=>Math.log(v);
 const lo=Math.min(...all)*0.95,hi=Math.max(...all)*1.05;const y=lin(lg(lo),lg(hi),B,T);
 const tk=[0.25,0.5,1,2,4,8,16,32].filter(t=>t>=lo&&t<=hi);
 for(const t of tk){el('line',{x1:L,x2:R,y1:y(lg(t)),y2:y(lg(t)),class:'grid'},s);tx(s,L-6,y(lg(t))+4,'$'+t,{'text-anchor':'end'})}
 const d0=Date.parse(series[0].dates[0]),d1=Math.max(...series.map(se=>Date.parse(se.dates[se.dates.length-1])));const x=lin(d0,d1,L,R);
 const y0=new Date(d0).getFullYear(),y1=new Date(d1).getFullYear(),step=Math.ceil((y1-y0)/7);
 for(let yr=Math.ceil(y0/step)*step;yr<=y1;yr+=step){const xx=x(Date.parse(yr+'-01-01'));if(xx>=L&&xx<=R)tx(s,xx,H-6,String(yr),{'text-anchor':'middle'})}
 el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'ref'},s);
 const ends=[];
 series.forEach((se,i)=>{const pts=se.dates.map((d,k)=>[x(Date.parse(d)),y(lg(se.values[k]))]);
  const p=el('path',{d:'M'+pts.map(q=>q[0].toFixed(1)+','+q[1].toFixed(1)).join('L'),fill:'none',class:se.cls,'stroke-width':2,'stroke-linejoin':'round'},s);tip(p,labs[i]);
  ends.push({y:pts[pts.length-1][1],t:labs[i],cls:se.cls.replace('k','f'),x:pts[pts.length-1][0]})});
 ends.sort((a,b)=>a.y-b.y);for(let i=1;i<ends.length;i++)if(ends[i].y-ends[i-1].y<14)ends[i].y=ends[i-1].y+14;
 for(const e of ends){el('circle',{cx:e.x,cy:e.y,r:3,class:e.cls},s);tx(s,R+8,e.y+4,e.t,{class:'st'})}}
function hbars(id,rows,keys,fmt){const per=14*keys.length+22,H=rows.length*per+26,s=svg(id,H);const L=Math.min(330,Math.max(...rows.map(r=>r.label.length))*6.3+10),R=W-10;
 const vals=rows.flatMap(r=>r.bars.map(b=>b.v));const ext=Math.max(...vals.map(Math.abs))*1.1;const tk=ticks(-ext,ext,6);const x=lin(tk[0],tk[tk.length-1],L,R);
 for(const t of tk){el('line',{x1:x(t),x2:x(t),y1:0,y2:H-22,class:'grid'},s);tx(s,x(t),H-6,fmt(t),{'text-anchor':'middle'})}
 el('line',{x1:x(0),x2:x(0),y1:0,y2:H-22,class:'axis'},s);
 rows.forEach((r,i)=>{const top=i*per+6;tx(s,L-8,top+keys.length*7+4,r.label,{'text-anchor':'end',class:'st'});
  r.bars.forEach((b,j)=>{const rr=el('rect',{x:Math.min(x(0),x(b.v)),width:Math.max(1,Math.abs(x(b.v)-x(0))),y:top+j*14,height:11,rx:2,class:b.cls},s);tip(rr,`${r.label} · ${b.name}: ${fmt(b.v)} (t ${F2(b.t)})`)})})}
function seg(attr,cb){const bs=document.querySelectorAll(`[${attr}]`);bs.forEach(b=>b.addEventListener('click',()=>{bs.forEach(o=>o.setAttribute('aria-pressed',String(o===b)));cb(b.getAttribute(attr))}))}

// Test 1
bars('c-head',D.head.map(r=>`Hold ${r.hold} day${r.hold>1?'s':''}`),[{name:'After a drop',cls:'f0',values:D.head.map(r=>r.dip)},{name:'Same stocks, any day',cls:'fm',values:D.head.map(r=>r.any)},{name:'Edge',cls:'f1',values:D.head.map(r=>r.edge)}],P(1,false));
lines('c-curve1',D.c1.map((c,i)=>Object.assign({cls:c.name==='SPY'?'km':'k'+(i%4)},c)),{endfmt:v=>'$'+v.toFixed(2)});
// Test 2
const order=['H1','H2','H3','H0'];
hbars('c-hold',order.map(id=>{const rs=D.holdout.filter(r=>r.id===id);return{label:rs[0].rule,bars:[['New stocks','f0'],['S&P 500/400','fm']].map(([u,c])=>{const r=rs.find(q=>q.uni===u);return{name:u,cls:c,v:r.edge,t:r.t}})}}),[0,1],P(2,true));
// Test 3: sweep explorer
const st={m:'One-day drop',h:3,v:'1M+ shares'};
function drawSweep(){const rows=D.sweep.filter(r=>r.m===st.m&&r.h===st.h&&r.v===st.v).sort((a,b)=>a.c-b.c);const H=300,s=svg('c-sweep',H),L=58,R=W-14,T=10,B=H-34;
 const vals=rows.flatMap(r=>r.e).filter(v=>v!=null);const lo=Math.min(-0.001,...vals),hi=Math.max(0.001,...vals);const tk=ticks(lo,hi,5);const y=lin(Math.min(lo,tk[0]),Math.max(hi,tk[tk.length-1]),B,T);
 yaxis(s,y,tk,P(2,true),L,R);el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'axis'},s);
 const x=i=>L+30+i*(R-L-60)/Math.max(1,rows.length-1);rows.forEach((r,i)=>tx(s,x(i),H-14,r.cl+'+',{'text-anchor':'middle'}));tx(s,R,H-1,'Bigger drops →',{'text-anchor':'end'});
 const names=['S&P 2005–15','S&P 2016–26','New stocks'],cl=['1','0','2'];
 [0,1,2].forEach(k=>{const pts=rows.map((r,i)=>[x(i),y(r.e[k]),r]);el('path',{d:'M'+pts.map(p=>p[0]+','+p[1]).join('L'),fill:'none',class:'k'+cl[k],'stroke-width':2},s);
  pts.forEach(p=>{const c=el('circle',{cx:p[0],cy:p[1],r:4.5,class:'k'+cl[k]+' '+(Math.abs(p[2].t[k])>=2?'f'+cl[k]:'fp'),'stroke-width':2},s);tip(c,`${names[k]} · ${st.m} ${p[2].cl}+, hold ${st.h}d: ${P(2,true)(p[2].e[k])} (t ${F2(p[2].t[k])})`)})})}
seg('data-m',v=>{st.m=v;drawSweep()});seg('data-h',v=>{st.h=+v;drawSweep()});seg('data-v',v=>{st.v=v;drawSweep()});drawSweep();
let cost=5;function drawPull(){const us=['S&P 500/400','New stocks'],ss=[['Pullback strategy','f0'],['Same schedule, all stocks','f1'],['SPY buy & hold','fm']];
 bars('c-pull',us,ss.map(([n,c])=>({name:n,cls:c,values:us.map(u=>(D.pull.find(r=>r.u===u&&r.s===n&&r.c===cost)||{}).cagr)})),P(1,false),260)}
seg('data-cost',v=>{cost=+v;drawPull()});drawPull();
// Test 4: scatter
let smp='sp_2016_26';function drawScatter(){const H=340,s=svg('c-scatter',H),L=50,R=W-10,T=10,B=H-34;const sp=D.wspy[smp];
 const pts=D.weekly.map(r=>({x:r['s_'+smp],y:r[smp],n:r.name,b:r.bench,t:r.turn}));const xs=pts.map(p=>p.x).concat(sp.sharpe),ys=pts.map(p=>p.y).concat(sp.cagr);
 const xt=ticks(Math.min(0,...xs),Math.max(...xs)*1.08,6),yt=ticks(Math.min(0,...ys),Math.max(...ys)*1.08,5);
 const x=lin(xt[0],xt[xt.length-1],L,R),y=lin(yt[0],yt[yt.length-1],B,T);
 el('rect',{x:x(sp.sharpe),y:T,width:Math.max(0,R-x(sp.sharpe)),height:Math.max(0,y(sp.cagr)-T),class:'zone'},s);
 yaxis(s,y,yt,P(0,false),L,R);xt.forEach(t=>tx(s,x(t),B+16,t.toFixed(1),{'text-anchor':'middle'}));
 tx(s,R,H-2,'Sharpe ratio →',{'text-anchor':'end'});tx(s,L+4,T+12,'↑ yearly return');
 el('line',{x1:x(sp.sharpe),x2:x(sp.sharpe),y1:T,y2:B,class:'ref'},s);el('line',{x1:L,x2:R,y1:y(sp.cagr),y2:y(sp.cagr),class:'ref'},s);
 tx(s,x(sp.sharpe)+6,y(sp.cagr)-6,`SPY ${P(1)(sp.cagr)}, Sharpe ${F2(sp.sharpe)}`,{class:'st'});tx(s,R-4,T+12,'Beats SPY on both',{'text-anchor':'end'});
 let n=0;pts.forEach(p=>{const win=!p.b&&p.y>sp.cagr&&p.x>sp.sharpe;if(win)n++;const c=el('circle',{cx:x(p.x),cy:y(p.y),r:p.b?6:5,class:p.b?'k1 fp':(win?'f0':'fm'),'stroke-width':2},s);tip(c,`${p.n}: ${P(1)(p.y)} a year, Sharpe ${F2(p.x)}, turnover ${p.t.toFixed(0)}x`)});
 document.getElementById('w-count').textContent=String(n)}
seg('data-s',v=>{smp=v;drawScatter()});drawScatter();
// Test 5
lines('c-curve5',D.c5.map(c=>Object.assign({cls:c.name==='SPY'?'km':c.name.startsWith('SPY +')?'k2':c.name.startsWith('Full')?'k0':'k1'},c)),{endfmt:v=>'$'+v.toFixed(2)});
// Test 6
const yrs=Object.keys(D.pwyears['Put-write layer']);
bars('c-pwyears',yrs,[['Put-write layer','f0'],['SPY buy & hold','fm'],['50/50 SPY / T-bills','f1']].map(([n,c])=>({name:n,cls:c,values:yrs.map(k=>D.pwyears[n][k])})),P(0,false),250);
"""


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i class="{c}"></i>{escape(n)}</span>' for n, c in items) + "</div>"


def ctl(label, attr, opts, default):
    b = "".join(f'<button type="button" {attr}="{escape(v)}" aria-pressed="{str(v == default).lower()}">{escape(t)}</button>' for v, t in opts)
    return f'<div class="ctl" role="group" aria-label="{escape(label)}"><span>{escape(label)}</span>{b}</div>'


hold_d = {r["universe"]: r for r in hold if r["id"] == "H1"}
d_now = mom["strategies"][MD]
body = f"""
<div class="wrap">
<header id="top">
  <h1>Trading research notebook</h1>
  <p class="lede">Six strategy ideas tested on 22+ years of US market data, each with trading costs and a fair out-of-sample check, plus a review of your paper portfolio. Every number below comes from the saved results of the scripts in <code>research/</code>; assumptions are labelled. Data through {snap['as_of']}.</p>
  <nav class="toc"><a href="#portfolio">Portfolio and market</a><a href="#words">Words used</a><a href="#t1">1 · 2% drops</a><a href="#t2">2 · Holdout</a><a href="#t3">3 · Drop sizes</a><a href="#t4">4 · Weekly pullbacks</a><a href="#t5">5 · Momentum</a><a href="#t6">6 · Put-writing</a><a href="#now">Recommendation</a></nav>
</header>

<div class="steps">
  <a class="step" href="#t1"><span class="n">Test 1</span><span class="q">Buy every stock that drops 2% in a day</span><span class="pill bad">No edge</span><span class="small muted">Beat same-morning stocks by {pct(h3['edge'], 2, True)} per trade (t {f2(h3['t_stat'])}).</span></a>
  <a class="step" href="#t2"><span class="n">Test 2</span><span class="q">Best-looking rule on stocks it never saw</span><span class="pill bad">Failed</span><span class="small muted">t-stat {f2(num(H1N['t_stat']))} on new stocks; needed 2.</span></a>
  <a class="step" href="#t3"><span class="n">Test 3</span><span class="q">Every drop size and definition</span><span class="pill warn">Real, but tiny</span><span class="small muted">{n_robust} of {len(sweep)} settings held up; weekly pullbacks bounce a little.</span></a>
  <a class="step" href="#t4"><span class="n">Test 4</span><span class="q">Trade the pullback weekly</span><span class="pill bad">Failed</span><span class="small muted">{w_pass} of {len(wvars)} versions beat SPY in all samples.</span></a>
  <a class="step" href="#t5"><span class="n">Test 5</span><span class="q">Regime-gated momentum portfolio</span><span class="pill bad">Failed</span><span class="small muted">Sharpe {f2(d_now['S&P 2016-26']['5bps']['sharpe'])} vs SPY {f2(mom['spy']['S&P 2016-26']['sharpe'])} in 2016–26.</span></a>
  <a class="step" href="#t6"><span class="n">Test 6</span><span class="q">Put-write income layer on idle cash</span><span class="pill bad">Failed</span><span class="small muted">Lost to SPY and a 50/50 mix on Sharpe after 2007, after tax.</span></a>
</div>

<section class="ch" id="portfolio">
  <span class="kick">Starting point</span><h2>Your paper portfolio and the market</h2>
  <div class="tiles">
    <div class="tile"><span class="l">Net asset value</span><span class="v">${snap['nav']:,.0f}</span><span class="s">IBKR paper, via SIGNUM bot TR-GC-Stocks-4</span></div>
    <div class="tile"><span class="l">Cash</span><span class="v">{pct(1 - snap['invested_share'], 0)}</span><span class="s">${snap['cash']:,.0f} idle</span></div>
    <div class="tile"><span class="l">Stock sleeve beta vs SPY</span><span class="v bad">{snap['sleeve_beta']:.2f}</span><span class="s">annual volatility {pct(snap['sleeve_vol'], 0)}</span></div>
    <div class="tile"><span class="l">VIX / T-bill yield</span><span class="v">{snap['vix']:.1f} / {snap['tbill']:.2f}%</span><span class="s">VIX 1-year median {snap['vix_1y_median']:.1f}</span></div>
    <div class="tile"><span class="l">S&amp;P 500/400 stocks above 200-day avg</span><span class="v">{pct(snap['breadth'], 0)}</span><span class="s">market breadth</span></div>
  </div>
  <div class="grid2">
    <div class="card"><h3>Holdings (close of {snap['as_of']})</h3>{t_hold}<p class="small muted">Eight of ten holdings are chip or tech names. The bot logged no trades after 2026-10-14.</p></div>
    <div class="card"><h3>Market and sectors</h3>{t_sec}
      <p class="small muted">Reported in the news (not computed here): the Fed held at 3.75–4.00% on Oct 28 with two dissents for a hike, and futures priced about an 83% chance of a hike on Dec 9; the S&amp;P 500 traded near 18.7× forward earnings (FactSet); the week of Nov 2 brings the midterm elections, Apple, AMD and Qualcomm results and the October jobs report.</p></div>
  </div>
</section>

<section class="ch" id="words">
  <span class="kick">Reference</span><h2>Words used on this page</h2>
  <dl class="gl">
    <div><dt>Edge</dt><dd>How much better a signal did than other stocks bought the same morning and sold the same day. It removes the whole market's move.</dd></div>
    <div><dt>t-stat</dt><dd>How sure we can be an edge isn't luck. About 2 or more is the usual bar; under 1 is indistinguishable from chance.</dd></div>
    <div><dt>In-sample / out-of-sample</dt><dd>Rules are picked on one period and judged on another they never saw. Real patterns hold up in both.</dd></div>
    <div><dt>Pre-registered</dt><dd>The rules and pass marks were committed to git before the test ran, so they couldn't be adjusted after seeing results.</dd></div>
    <div><dt>bps</dt><dd>Basis points, hundredths of a percent. 5 bps per side = 0.05% lost on each buy and each sell.</dd></div>
    <div><dt>CAGR, Sharpe, worst fall</dt><dd>Average yearly return; return per unit of risk above T-bills (higher is better); largest drop from a peak.</dd></div>
  </dl>
</section>

<section class="ch" id="t1">
  <span class="kick">Test 1 of 6</span><h2>Buy every stock that drops 2% in a day</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Your evening prompt scores big stocks that fell over 2% on heavy volume. Does the drop itself predict a bounce?</p></div>
    <div><h4>Test</h4><p>S&amp;P 500 and 400 stocks, 2005–Oct 2026. Down 2%+, 1M+ shares, price over $20. Buy at the next open, sell 1–5 days later.</p></div>
    <div><h4>Finding</h4><p>The 3-day gain of {pct(h3['dip_raw'], 2, True)} is mostly the market bouncing; vs same-morning stocks the drop added {pct(h3['edge'], 2, True)}.</p></div>
  </div>
  <div class="tiles">
    <div class="tile"><span class="l">Drops tested</span><span class="v">{int(h3['signals']):,}</span></div>
    <div class="tile"><span class="l">Avg 3-day gain after a drop</span><span class="v">{pct(h3['dip_raw'], 2, True)}</span><span class="s">vs {pct(h3['anyday_raw'], 2, True)} on any day</span></div>
    <div class="tile"><span class="l">Edge vs same-morning stocks</span><span class="v">{pct(h3['edge'], 2, True)}</span><span class="s">t-stat {f2(h3['t_stat'])}</span></div>
    <div class="tile"><span class="l">Yearly return after costs</span><span class="v">{pct(port['All dips, 3d hold, 5 bps/side']['cagr'])}</span><span class="s">SPY: {pct(SPYC)}</span></div>
  </div>
  <div class="grid2">
    <div class="card"><h3>Where the gain comes from</h3><p class="small muted">Before costs. Hover a bar for its value.</p>{legend([('After a drop','b0'),('Same stocks, any day','bm'),('Edge','b1')])}<div class="chart" id="c-head"></div></div>
    <div class="card"><h3>Growth of $1 after costs (log scale)</h3><p class="small muted">5 bps per side. Simply holding SPY beat every dip strategy.</p><div class="chart" id="c-curve1"></div></div>
  </div>
  <div class="card"><h3>Searching for a better rule backfired</h3><p class="small muted">Rules ranked on 2005–15 only. The top one (highlighted) vanished on 2016–26: overfitting.</p>{t_rules}</div>
  <div class="verdict"><b>Verdict: no edge.</b> A one-day 2% drop doesn't predict a bounce beyond the market's own move, and costs turn the small raw gain into a loss vs the index.</div>
</section>

<section class="ch" id="t2">
  <span class="kick">Test 2 of 6</span><h2>Check the best-looking rule on stocks it never saw</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Stock down 5%+ over the prior week and the S&amp;P down 1%+ that day: an oversold stock in a broad selloff.</p></div>
    <div><h4>Test</h4><p>Pre-registered, then run on 835 US stocks over $2B outside the S&amp;P 500/400.</p></div>
    <div><h4>Finding</h4><p>{pct(num(H1N['raw3']), 2, True)} over 3 days with {pct(num(H1N['win_rate']))} winners, but same-morning stocks did about as well: edge {pct(num(H1N['edge']), 2, True)}, t {f2(num(H1N['t_stat']))}.</p></div>
  </div>
  <div class="card"><h3>3-day edge of each rule</h3>{legend([('New stocks (fresh test)','b0'),('S&P 500/400 (where the idea came from)','bm')])}<div class="chart" id="c-hold"></div></div>
  <div class="verdict"><b>Verdict: failed.</b> Edge 2005–15 {pct(num(H1N['edge_2005_15']), 2, True)}, 2016–26 {pct(num(H1N['edge_2016_26']), 2, True)}; t-stat {f2(num(H1N['t_stat']))} vs the 2.0 required.</div>
</section>

<section class="ch" id="t3">
  <span class="kick">Test 3 of 6</span><h2>Try every drop size and definition</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Maybe 2% was the wrong number, or several bad days matter more than one.</p></div>
    <div><h4>Test</h4><p>{len(sweep)} settings: 5 drop measures, many cutoffs, holds of 1–10 days, 3 volume filters, on three samples.</p></div>
    <div><h4>Finding</h4><p>One-day drops: nothing at any size. Multi-day pullbacks bounce a little in all three samples, about as much as trading costs.</p></div>
  </div>
  <div class="tiles">
    <div class="tile"><span class="l">Robust in all three samples</span><span class="v">{n_robust} of {len(sweep)}</span></div>
    <div class="tile"><span class="l">Best: 5-day drop 2%+, hold 5 days</span><span class="v">{pct(num(BEST['edge_sp_2005_15']), 2, True)} · {pct(num(BEST['edge_sp_2016_26']), 2, True)} · {pct(num(BEST['edge_new']), 2, True)}</span><span class="s">S&amp;P 05–15 · S&amp;P 16–26 · new stocks; a round trip costs 0.10%</span></div>
  </div>
  <div class="card"><h3>Explore the drop sizes</h3><p class="small muted">Each line is one sample. Filled dots have |t| ≥ 2. Try “5-day drop” with a 5-day hold.</p>
    {ctl('Drop measured as', 'data-m', [('One-day drop','One-day'),('Drop vs normal daily move','Vs normal move'),('3-day drop','3-day'),('5-day drop','5-day'),('Drop vs sector ETF','Vs sector')], 'One-day drop')}
    {ctl('Hold', 'data-h', [('1','1 day'),('2','2'),('3','3'),('5','5'),('10','10')], '3')}
    {ctl('Volume', 'data-v', [('1M+ shares','1M+'),('1M+ and 1.5x normal','1.5x normal'),('1M+ and 3x normal','3x normal')], '1M+ shares')}
    {legend([('S&P 2005–15','b1'),('S&P 2016–26','b0'),('New stocks','b2')])}<div class="chart" id="c-sweep"></div></div>
  <div class="card"><h3>Does the weekly pullback make money in an account?</h3><p class="small muted">5-day drop 2%+, hold 5 days, 2005–2026. "Same schedule" buys everything on the same timetable, so the gap is the pullback effect.</p>
    {ctl('Cost per side', 'data-cost', [('0','None'),('2','2 bps'),('5','5 bps')], '5')}
    {legend([('Pullback strategy','b0'),('Same schedule, all stocks','b1'),('SPY buy & hold','bm')])}<div class="chart" id="c-pull"></div></div>
  <div class="verdict warn"><b>Verdict: real, but too small.</b> The pullback effect exists but trading it costs about what it earns.</div>
</section>

<section class="ch" id="t4">
  <span class="kick">Test 4 of 6</span><h2>Trade the pullback once a week</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Cut costs: weekly rebalance, top 10/20/50 pullbacks, keep names that still qualify.</p></div>
    <div><h4>Test</h4><p>{len(wvars)} pre-registered versions; must beat SPY on return and Sharpe at 5 bps in all three samples.</p></div>
    <div><h4>Finding</h4><p>Holdings still turned over {min(turn):.0f}–{max(turn):.0f} times a year, eating the edge. {w_pass} versions passed.</p></div>
  </div>
  <div class="card"><h3>Every weekly version against SPY</h3><p class="small muted">Shaded corner = beats SPY on both return and Sharpe. <b id="w-count">–</b> versions land there in the selected sample.</p>
    {ctl('Sample', 'data-s', [('sp_2005_15','S&P 2005–15'),('sp_2016_26','S&P 2016–26'),('new','New stocks')], 'sp_2016_26')}
    {legend([('Beats SPY on both','b0'),('Does not','bm'),('Buy all stocks weekly (benchmark)','b1')])}<div class="chart" id="c-scatter"></div></div>
  <div class="verdict"><b>Verdict: failed.</b> No version beats SPY in more than one sample. The pullback idea is dropped.</div>
</section>

<section class="ch" id="t5">
  <span class="kick">Test 5 of 6 · first portfolio review</span><h2>Regime-gated, risk-budgeted momentum</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Replace concentrated chip trades with a monthly portfolio: top 20 stocks by 12-1 month momentum, max 5 per sector, inverse-volatility sizing, 15% volatility target, cash when SPY is below its 200-day average, sell all at a 20% loss from peak.</p></div>
    <div><h4>Test</h4><p>Pre-registered; 5 and 10 bps per side; cash earns T-bills; three samples; ablations A–D.</p></div>
    <div><h4>Finding</h4><p>Smaller worst falls everywhere, but lower Sharpe than SPY in 2 of 3 samples. Momentum picking added nothing beyond the market switch.</p></div>
  </div>
  <div class="card"><h3>Results at 5 bps per side</h3>{t_mom}</div>
  <div class="card"><h3>Growth of $1, S&amp;P universe (log scale)</h3><div class="chart" id="c-curve5"></div></div>
  <div class="verdict"><b>Verdict: failed.</b> Not adopted. A design flaw was also found: inverse-volatility sizing gave the biggest weight to a stock pinned by a pending acquisition.</div>
</section>

<section class="ch" id="t6">
  <span class="kick">Test 6 of 6 · second portfolio review</span><h2>Put-write income layer on idle cash</h2>
  <div class="qa">
    <div><h4>Idea</h4><p>Use half the account (cash-secured, no leverage) to sell 1-month at-the-money S&amp;P 500 puts each month, collecting the premium option buyers pay for crash insurance.</p></div>
    <div><h4>Test</h4><p>Pre-registered on the CBOE PutWrite index (^PUT, real data from 1996). Split at the index launch (2007). Assumed 0.5%/yr costs and US taxes.</p></div>
    <div><h4>Finding</h4><p>VIX beat later realized volatility on {pct(vrp['2007-2019']['share_vix_above_realized'], 0)}–{pct(vrp['1996-2007']['share_vix_above_realized'], 0)} of days, but after costs and annual taxes the layer didn't beat SPY or a 50/50 mix per unit of risk after 2007.</p></div>
  </div>
  <div class="card"><h3>After-tax results (base cost)</h3>{t_pw}
    <p class="small muted">Assumptions: 0.5% a year trading drag; taxes 32% ordinary income, 15% dividends and long-term gains, 21.8% Section 1256 option profits. Index data verified (Yahoo Finance).</p></div>
  <div class="grid2">
    <div class="card"><h3>Calendar-year returns in stress years (pre-tax)</h3>{legend([('Put-write layer','b0'),('SPY buy & hold','bm'),('50/50 SPY / T-bills','b1')])}<div class="chart" id="c-pwyears"></div></div>
    <div class="card"><h3>Can you actually trade it?</h3>
      <ul><li>One SPY put needs about $75,600 of collateral; the planned layer was about $12,000, so not even one contract fits.</li>
      <li>XYLD, the closest liquid fund (buy-write, from 2013): {pct(xy['XYLD (buy-write fund)']['cagr'])} a year, Sharpe {f2(xy['XYLD (buy-write fund)']['sharpe'])}, vs SPY {pct(xy['SPY buy & hold']['cagr'])} and {f2(xy['SPY buy & hold']['sharpe'])} (pre-tax).</li>
      <li>Today VIX ({vrp['now']['vix']:.1f}) is well above last month's realized volatility ({vrp['now']['realized_21d_past']:.1f}): premiums are rich now, which is a fact about today, not proof of an edge.</li></ul></div>
  </div>
  <div class="verdict"><b>Verdict: failed.</b> Keep idle cash in T-bills rather than adding an options layer.</div>
</section>

<section class="ch" id="now">
  <span class="kick">Summary</span><h2>Current recommendation</h2>
  <div class="verdict ok"><b>Hold. No new trades.</b> None of the six ideas cleared its pre-registered test. Keep idle cash earning the T-bill rate (about {snap['tbill']:.1f}%).</div>
  <div class="grid2">
    <div class="card"><h3>Risks to review</h3><ul>
      <li>The stock sleeve is concentrated in chips/tech, with beta {snap['sleeve_beta']:.2f} to the S&amp;P 500, into chip earnings and a likely December rate hike.</li>
      <li>The SIGNUM bot logged no activity after 2026-10-14; check that its routine is running.</li></ul></div>
    <div class="card"><h3>Lessons</h3><ul>
      <li>Measure signals against stocks bought the same day, or market bounces look like skill.</li>
      <li>Search enough rules and one will look great by chance; only unseen data tells.</li>
      <li>Costs and taxes decide short-term and options strategies.</li>
      <li>Lead for a future pre-registered test: SPY with a 200-day switch cut worst falls by more than half in every window, but lagged in the 2016–26 bull market.</li></ul></div>
  </div>
  <div class="card"><h3>How it was tested</h3><ul class="small">
    <li>Daily prices from Yahoo Finance (adjusted for splits and dividends); index membership from Wikipedia; T-bill yield ^IRX.</li>
    <li>Trades buy at the next open after a signal; costs charged on traded value; cash earns T-bills where stated.</li>
    <li>Tests 2, 4, 5 and 6 were committed to git before running. Stocks that went bankrupt or were acquired are missing from the data, which flatters stock-picking results.</li>
    <li>Code: <code>research/dip_rebound</code>, <code>research/momentum_regime</code>, <code>research/putwrite</code>; this page: <code>research/report/build_report.py</code>.</li></ul></div>
  <p class="small muted">Research only, not financial advice. Past results do not guarantee future returns.</p>
</section>
</div>
"""

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Trading Research Notebook</title><style>{CSS}</style></head>
<body>{body}
<script id="data" type="application/json">{json.dumps(data, separators=(',', ':')).replace('</', '<\\/')}</script>
<script>{JS}</script>
</body></html>"""
OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
