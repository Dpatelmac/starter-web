"""HTML report for test 10 (called by run_20y.py; can also be run alone:
python3 build_report.py  -> rebuilds report.html from results.json)."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS3M = (HERE.parent / "live_3m" / "build_report.py").read_text().split('CSS = r"""', 1)[1].split('"""', 1)[0]
usd = lambda v: "–" if v is None else ("−$" if v < 0 else "$") + f"{abs(v):,.0f}"
pc = lambda v, d=1: "–" if v is None else f"{v*100:+.{d}f}%".replace("-", "−")
f2 = lambda v: "–" if v is None else f"{v:.2f}"


def _row(label, s, tr=None):
    if not s:
        return ""
    t = (f"<td>{tr.get('trades','')}</td><td>{tr.get('win_rate',0)*100:.0f}%</td><td>{pc(tr.get('avg_win'),0)} / {pc(tr.get('avg_loss'),0)}</td>"
         if tr else "<td>–</td><td>–</td><td>–</td>")
    return (f"<tr><td class='t'>{label}</td><td class='{'pos' if s['profit']>0 else 'neg'}'>{usd(s['profit'])}</td><td>{pc(s['return'])}</td>"
            f"<td>{pc(s['cagr'])}</td><td>{f2(s['sharpe'])}</td><td class='neg'>{pc(s['max_dd'])}</td>{t}</tr>")


def _ptable(blk):
    return ("<div class='tw'><table><thead><tr><th class='t'></th><th>Profit</th><th>Return</th><th>Per year</th><th>Sharpe</th><th>Worst drawdown</th>"
            "<th>Trades</th><th>Winners</th><th>Avg win / loss</th></tr></thead><tbody>"
            + _row("SPY buy &amp; hold ($24,000)", blk["SPY"]) + _row("<b>S1</b> with T-bill interest on cash", blk["S1"], blk["trades"])
            + _row("S1 without interest", blk["S1_no_interest"]) + "</tbody></table></div>")


def build(o: dict, path: Path) -> Path:
    P = o["periods"]
    T = P["Never tested: 2005 - Oct 2020"]
    mark = lambda b: "<span class='pos'>✓ yes</span>" if b else "<span class='neg'>✗ no</span>"
    c, c10 = o["criteria"], o["criteria_2010"]
    verdict = "PASSED" if o["pass"] else "FAILED"
    unrel = [y for y, v in o["quality"].items() if v["unreliable"]]
    yr_rows = ""
    for y, blk in o["years"].items():
        s, sp = blk["S1"], blk["SPY"]
        if not s or not sp:
            continue
        q = o["quality"].get(y, {})
        yr_rows += (f"<tr><td class='t'>{y}{' ⚠' if q.get('unreliable') else ''}</td><td class='{'pos' if sp['profit']>0 else 'neg'}'>{usd(sp['profit'])}</td>"
                    f"<td class='{'pos' if s['profit']>0 else 'neg'}'>{usd(s['profit'])}{' ▲' if s['profit']>sp['profit'] else ''}</td>"
                    f"<td class='neg'>{pc(sp['max_dd'],0)}</td><td class='neg'>{pc(s['max_dd'],0)}</td><td>{blk['trades'].get('trades','–')}</td>"
                    f"<td>{(blk['trades'].get('win_rate') or 0)*100:.0f}%</td><td class='muted'>{q.get('share',0)*100:.0f}%</td></tr>")
    # Fair comparison in % per year, and implied exposure (positions x $1,000 / account value).
    import pandas as _pd, numpy as _np
    s1c = _pd.Series({d: v for d, v in o["curves"]["S1"]}); spc = _pd.Series({d: v for d, v in o["curves"]["SPY"]})
    s1c.index = _pd.to_datetime(s1c.index); spc.index = _pd.to_datetime(spc.index)
    yr = lambda x: x.resample("YE").last().pct_change().fillna(x.resample("YE").last().iloc[0] / x.iloc[0] - 1)
    ys1, yspy = yr(s1c), yr(spc)
    pct_rows = "".join(f"<tr><td class='t'>{d.year}</td><td class='{'pos' if b>0 else 'neg'}'>{pc(b)}</td><td class='{'pos' if a>0 else 'neg'}'>{pc(a)}{' ▲' if a>b else ''}</td></tr>" for d, a, b in zip(ys1.index, ys1.values, yspy.values))
    wins = int((ys1.values > yspy.values).sum())
    openc = _np.zeros(len(s1c))
    for x in o["trades"]:
        a_ = _pd.Timestamp(x["buy_day"]); b_ = _pd.Timestamp(x["sell_day"]) if x["exit"] != "open" else s1c.index[-1]
        openc += (s1c.index >= a_) & (s1c.index <= b_)
    expo = _pd.Series(openc * 1000 / s1c.values, index=s1c.index)
    howto = f"""<section aria-labelledby="hx"><h2 id="hx">How to read this</h2>
<div class="cols3"><div class="card small"><h3>Dollars vs percent</h3><p>S1 always trades $1,000 positions, while the SPY account compounds as it grows, so later-year dollar profits favor SPY. Year by year in percent, S1 beat SPY in {wins} of {len(ys1)} years, mostly years when the market fell or went sideways.</p></div>
<div class="card small"><h3>Hidden borrowing in 2008-09</h3><p>Losses took the account down to {usd(s1c.min())} ({s1c.idxmin().date()}), but the fixed-size rule kept opening $1,000 positions, so open positions reached {expo.max():.2f}x the account's value ({expo.idxmax().date()}). That implicit margin deepened the {pc(T['S1']['max_dd'],0)} drawdown. On average {expo.mean()*100:.0f}% of the account was invested.</p></div>
<div class="card small"><h3>Earnings data</h3><p>Yahoo had earnings history for all {o['meta']['tickers_with_earnings']} stocks; no year had more than 30% of candidates skipped for missing history, so no year is flagged.</p></div></div>
<div class="card"><h3>Return by calendar year (percent of start-of-year value)</h3><div class="tw"><table><thead><tr><th class="t">Year</th><th>SPY</th><th>S1</th></tr></thead><tbody>{pct_rows}</tbody></table></div><p class="small muted">▲ S1 beat SPY that year.</p></div></section>"""
    sub = "".join(f"<div class='card'><h3>{p}</h3>{_ptable(P[p])}</div>" for p in ("2005-2009", "2010-2014", "2015-2019", "2020-2026", "Full period") if P[p]["S1"])
    pack = {"curves": o["curves"], "trades": o["trades"], "dates": o["dates"], "years": {y: b for y, b in o["years"].items() if b["S1"]},
            "top": o["top_trades"], "worst": o["worst_trades"], "sectors": o["sectors"]}
    smoke = "<div class='verdict warn small'><p><b>Smoke test only</b> (2024-2026, cached earnings dates): checks the code, not the strategy.</p></div>" if o["meta"]["smoke"] else ""
    body = f"""
<div class="wrap"><header><h1>Twenty-year backtest: strategy S1</h1>
<p class="lede">Top 4 unexplained S&amp;P 500 losers each day (skip earnings that day or the evening before, an 8%+ opening gap, and reports due in the next 10 days), bought at the next open, $1,000 each, sold by a 12% trailing stop; at most 24 positions, 2 new buys per sector per day, 10-day cool-off. $24,000 account; idle cash earns T-bills. {o['meta']['first_buy']} to {o['meta']['last']}. Rules and pass marks were committed before the run.</p></header>
{smoke}
<section aria-labelledby="h1"><h2 id="h1">Verdict</h2>
<div class="verdict {'warn' if not o['pass'] else ''}"><p><b>S1 {verdict}</b> on the never-tested period ({o['meta']['first_buy']} to Oct 2020): profit {usd(T['S1']['profit'])} vs SPY {usd(T['SPY']['profit'])}; Sharpe {f2(T['S1']['sharpe'])} vs {f2(T['SPY']['sharpe'])}; worst drawdown {pc(T['S1']['max_dd'])} vs {pc(T['SPY']['max_dd'])}.</p></div>
<div class="card"><h3>Pre-registered checks</h3><div class="tw"><table><thead><tr><th class="t">Check</th><th>2005 - Oct 2020 (decides)</th><th>2010 - Oct 2020 (robustness)</th></tr></thead><tbody>
<tr><td class="t">Profit beats SPY</td><td>{mark(c['profit_beats_spy'])}</td><td>{mark(c10['profit_beats_spy'])}</td></tr>
<tr><td class="t">Sharpe beats SPY</td><td>{mark(c['sharpe_beats_spy'])}</td><td>{mark(c10['sharpe_beats_spy'])}</td></tr>
<tr><td class="t">Smaller worst drawdown</td><td>{mark(c['dd_smaller_than_spy'])}</td><td>{mark(c10['dd_smaller_than_spy'])}</td></tr></tbody></table></div>
<p class="small muted">Years flagged for thin earnings history (over 30% of checked candidates skipped): {', '.join(unrel) if unrel else 'none'}.</p></div>
<div class="card"><h3>Never-tested period: 2005 to Oct 2020</h3>{_ptable(T)}</div>
<div class="card"><h3>2010 to Oct 2020</h3>{_ptable(P['2010 - Oct 2020 (robustness)'])}</div>
</section>
{howto}
<section aria-labelledby="h2"><h2 id="h2">Account value and drawdown</h2>
<div class="card"><div class="legend"><span><i style="background:var(--c0)"></i>S1 (with T-bill interest)</span><span><i style="background:var(--c1)"></i>S1 without interest</span><span><i style="background:var(--mute)"></i>SPY (dashed)</span></div>
<h3>Account value ($24,000 start, weekly)</h3><div class="chart" id="c-eq"></div><h3>Drawdown from peak</h3><div class="chart" id="c-dd"></div>
<p class="small muted">Dashed vertical lines: end of the never-tested period (Oct 2020) and start of the selection year (Nov 2025).</p></div>
<div class="card"><h3>By calendar year</h3><div class="tw"><table><thead><tr><th class="t">Year</th><th>SPY profit</th><th>S1 profit</th><th>SPY worst fall</th><th>S1 worst fall</th><th>Trades</th><th>Winners</th><th>Skipped: no earnings history</th></tr></thead><tbody>{yr_rows}</tbody></table></div><p class="small muted">▲ beat SPY that year. ⚠ thin earnings history.</p></div>
</section>
<section aria-labelledby="h3"><h2 id="h3">Sub-periods</h2>{sub}</section>
<section aria-labelledby="h4"><h2 id="h4">Trades</h2>
<div class="cols3"><div class="card small"><h3>Biggest winners</h3><ul id="top"></ul></div><div class="card small"><h3>Biggest losers</h3><ul id="worst"></ul></div><div class="card small"><h3>Sectors bought</h3><ul id="sec"></ul></div></div>
<div class="card"><div class="daynav"><input type="search" id="q" placeholder="Find a ticker" aria-label="Find a ticker"><select id="yr" aria-label="Year bought"></select>
<div class="ctl" role="group" aria-label="Show"><span>Show</span><button class="seg" type="button" data-show="all" aria-pressed="true">All</button><button class="seg" type="button" data-show="win" aria-pressed="false">Winners</button><button class="seg" type="button" data-show="loss" aria-pressed="false">Losers</button></div><span class="small muted" id="t-count"></span></div>
<div class="tw"><table><thead><tr id="t-head"></tr></thead><tbody id="t-body"></tbody></table></div><p class="small muted">Click a column to sort, a row to see its path.</p></div>
<div class="card"><h3 id="trade-title"></h3><div class="legend"><span><i style="background:var(--c0)"></i>Close vs entry</span><span><i style="background:var(--bad)"></i>12% trailing stop</span></div><div class="chart" id="c-trade"></div></div></section>
<section aria-labelledby="h5"><h2 id="h5">Limits</h2><div class="card small"><ul>
<li>Universe: today's S&amp;P 500 members counted from their date added; stocks removed from the index (often after big falls, including 2008) are missing, which flatters dip buying.</li>
<li>Earnings dates from Yahoo; candidates before a stock's first known report are skipped (share shown per year). After-hours moves not counted; gains would be short-term for tax.</li>
<li>Pre-registered in <code>PREREGISTRATION.md</code>; code <code>run_20y.py</code>, <code>build_report.py</code>. Research only, not financial advice.</li></ul></div></section>
</div>"""
    js = r"""
const D=JSON.parse(document.getElementById('data').textContent);const NS='http://www.w3.org/2000/svg',W=760;
const P=(v,d=1,s=true)=>v==null||!isFinite(v)?'–':((s&&v>0?'+':'')+(v*100).toFixed(d)+'%').replace('-','−');
const USD=v=>(v<0?'−$':'$')+Math.abs(Math.round(v)).toLocaleString('en-US');const cls=v=>v>0?'pos':v<0?'neg':'';
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function tx(p,x,y,s,a){const t=el('text',Object.assign({x,y},a||{}),p);t.textContent=s;return t}
function tip(n,s){el('title',{},n).textContent=s}
function svg(id,H){const c=document.getElementById(id);c.innerHTML='';return el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},c)}
function ticks(a,b,n){const sp=(b-a)||1,s0=sp/n,m=Math.pow(10,Math.floor(Math.log10(s0)));const s=[1,2,2.5,5,10].map(x=>x*m).find(q=>sp/q<=n)||10*m;const o=[];for(let v=Math.ceil(a/s)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(8));return o}
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/((d1-d0)||1)*(r1-r0);function h(t,x,c){const e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e}
const K=[['SPY','var(--mute)',2,'5 3'],['S1_no_interest','var(--c1)',1.4,''],['S1','var(--c0)',2.4,'']];
function chart(id,dd){const H=dd?220:340,g=svg(id,H),L=66,R=W-12,T=12,B=H-26;const base=D.curves.SPY;const n=base.length;
 const conv=a=>{if(!dd)return a.map(q=>q[1]);let pk=0;return a.map(q=>{pk=Math.max(pk,q[1]);return q[1]/pk-1})};
 const vals=K.flatMap(([k])=>conv(D.curves[k]));const tk=ticks(Math.min(...vals),Math.max(...vals),5);const y=lin(tk[0],tk[tk.length-1],B,T),x=lin(0,n-1,L,R);
 for(const t of tk){el('line',{x1:L,x2:R,y1:y(t),y2:y(t),class:'grid'},g);tx(g,L-6,y(t)+4,dd?P(t,0):USD(t),{'text-anchor':'end'})}
 let ly='',lx=-99;base.forEach((q,i)=>{const yr=q[0].slice(0,4);if(yr!==ly){ly=yr;if(x(i)-lx>34&&+yr%2===0){tx(g,x(i),H-6,yr);lx=x(i)}}});
 for(const dte of ['2020-10-30','2025-11-03']){const i=base.findIndex(q=>q[0]>=dte);if(i>0)el('line',{x1:x(i),x2:x(i),y1:T,y2:B,class:'ref'},g)}
 for(const [k,c,w,da] of K){const a=conv(D.curves[k]);el('path',{d:'M'+a.map((v,i)=>x(i).toFixed(1)+','+y(v).toFixed(1)).join('L'),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':da||'none'},g)}
 const ov=el('g',{},g);for(let i=0;i<n;i+=2){const r=el('rect',{x:x(i),width:(R-L)/n*2,y:T,height:B-T,fill:'transparent'},ov);tip(r,base[i][0]+'\n'+K.slice().reverse().map(([k])=>`${k}: ${dd?P(conv(D.curves[k])[i]):USD(D.curves[k][i][1])}`).join('\n'))}}
const st={sort:{k:'buy_day',dir:-1},q:'',show:'all',yr:'all',sel:null};
const COLS=[['ticker','Stock','t'],['sector','Sector','t'],['drop_day','Drop day','t'],['drop','Fell',''],['buy_day','Bought','t'],['buy','Buy $',''],['sell_day','Sold / marked','t'],['sell','Sell $',''],['days','Days',''],['ret','Return',''],['pnl','P&L $','']];
function table(){const tr=D.trades.filter(t=>(st.yr==='all'||t.buy_day.startsWith(st.yr))&&(st.show==='all'||(st.show==='win'?t.ret>0:t.ret<=0))&&(!st.q||t.ticker.includes(st.q.toUpperCase())));
 const {k,dir}=st.sort;tr.sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*dir);const th=document.getElementById('t-head');th.innerHTML='';
 COLS.forEach(([c,l,cc])=>{const e=h('th',l+(k===c?(dir>0?' ▲':' ▼'):''),cc);e.addEventListener('click',()=>{st.sort={k:c,dir:k===c?-dir:(c==='ticker'||c.endsWith('day')||c==='sector'?1:-1)};table()});th.append(e)});
 const tb=document.getElementById('t-body');tb.innerHTML='';const tot=tr.reduce((a,t)=>a+t.pnl,0),w=tr.filter(t=>t.ret>0).length;
 for(const t of tr.slice(0,1500)){const r=h('tr');if(st.sel===t)r.className='sel';r.append(h('td',t.ticker,'t'),h('td',t.sector,'t muted'),h('td',t.drop_day,'t'),h('td',P(t.drop),'neg'),h('td',t.buy_day,'t'),h('td',t.buy.toFixed(2)),h('td',t.sell_day,'t'),h('td',t.sell.toFixed(2)),h('td',t.days),h('td',P(t.ret,2),cls(t.ret)),h('td',USD(t.pnl),cls(t.pnl)));r.addEventListener('click',()=>pick(t));tb.append(r)}
 document.getElementById('t-count').textContent=`${tr.length} trades · ${tr.length?Math.round(w/tr.length*100):0}% winners · total ${USD(tot)}${tr.length>1500?' (first 1,500 shown)':''}`}
function pick(t){if(!t)return;st.sel=t;table();const H=220,g=svg('c-trade',H),L=50,R=W-10,T=14,B=H-26;const p=t.marks.length?t.marks:[1];let hw=1;const stop=p.map(v=>{const s=hw*0.88;hw=Math.max(hw,v);return s});
 const vals=p.concat(stop);const tk=ticks(Math.min(...vals)*0.99,Math.max(...vals)*1.01,5);const y=lin(tk[0],tk[tk.length-1],B,T),x=lin(0,Math.max(1,p.length-1),L+10,R-10);
 for(const v of tk){el('line',{x1:L,x2:R,y1:y(v),y2:y(v),class:'grid'},g);tx(g,L-6,y(v)+4,P(v-1,0),{'text-anchor':'end'})}
 el('path',{d:'M'+stop.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--bad)','stroke-dasharray':'5 4','stroke-width':1.5},g);el('path',{d:'M'+p.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--c0)','stroke-width':2.2},g);
 tx(g,L+10,H-6,t.buy_day);tx(g,R-10,H-6,t.sell_day,{'text-anchor':'end'});document.getElementById('trade-title').textContent=`${t.ticker}: bought ${t.buy_day} at $${t.buy.toFixed(2)}, ${t.exit==='open'?'still open':'sold'} ${t.sell_day} at $${t.sell.toFixed(2)} (${P(t.ret,2)}, ${USD(t.pnl)})`}
const li=(id,arr,f)=>{const u=document.getElementById(id);arr.forEach(x=>{const e=h('li');e.innerHTML=f(x);u.append(e)})};
li('top',D.top,t=>`<b>${t.ticker}</b> ${t.buy_day}: <span class="pos">${P(t.ret,0)}</span> (${USD(t.pnl)})`);li('worst',D.worst,t=>`<b>${t.ticker}</b> ${t.buy_day}: <span class="neg">${P(t.ret,0)}</span> (${USD(t.pnl)})`);
li('sec',Object.entries(D.sectors).slice(0,6),([k,v])=>`${k}: ${Math.round(v*100)}%`);
const ys=document.getElementById('yr');[['all','All years'],...Object.keys(D.years).map(y=>[y,y])].forEach(([v,l])=>{const o=h('option',l);o.value=v;ys.append(o)});
ys.addEventListener('change',e=>{st.yr=e.target.value;table()});document.getElementById('q').addEventListener('input',e=>{st.q=e.target.value.trim();table()});
document.querySelectorAll('[data-show]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-show]').forEach(o=>o.setAttribute('aria-pressed',String(o===b)));st.show=b.dataset.show;table()}));
chart('c-eq',false);chart('c-dd',true);table();pick(D.trades.slice().sort((a,b)=>b.pnl-a.pnl)[0]);
"""
    css = CSS3M + "\ncode{word-break:break-all;font-size:.85em}\n.verdict{border-left:4px solid var(--ok);background:var(--panel);border-radius:6px;padding:12px 16px}.verdict.warn{border-left-color:var(--warn)}\n"
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
            f"<title>S1 Twenty-Year Backtest</title><style>{css}</style></head><body>{body}"
            f"<script id='data' type='application/json'>{json.dumps(pack, separators=(',', ':'), default=lambda x: None).replace('</', '<\\/')}</script><script>{js}</script></body></html>")
    path.write_text(page, encoding="utf-8")
    return path


if __name__ == "__main__":
    o = json.loads((HERE / "results.json").read_text())
    print(build(o, HERE / "report.html"))
