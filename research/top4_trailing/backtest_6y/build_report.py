"""Build the offline interactive six-year report (report.html) from results.json."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text())
CSS3M = (HERE.parent / "live_3m" / "build_report.py").read_text().split('CSS = r"""', 1)[1].split('"""', 1)[0]
U, SEL, FULL = list(r["periods"])
S = r["strategies"]
usd = lambda v: ("−$" if v < 0 else "$") + f"{abs(v):,.0f}"
pc = lambda v, d=1: f"{v*100:+.{d}f}%".replace("-", "−")
f2 = lambda v: f"{v:.2f}"


def row(name, x, spy=False):
    tr = "" if spy else f"<td>{x.get('trades', '')}</td><td>{x.get('win_rate', 0)*100:.0f}%</td><td>{pc(x.get('avg_win', 0), 0)} / {pc(x.get('avg_loss', 0), 0)}</td>"
    blank = "<td>–</td><td>–</td><td>–</td>" if spy else ""
    return (f"<tr><td class='t'>{name}</td><td class='{'pos' if x['profit'] > 0 else 'neg'}'>{usd(x['profit'])}</td><td>{pc(x['return'])}</td>"
            f"<td>{pc(x['cagr'])}</td><td>{f2(x['sharpe'])}</td><td class='neg'>{pc(x['max_dd'])}</td>{tr}{blank}</tr>")


def period_table(p):
    rows = row("SPY buy &amp; hold ($24,000)", r["spy"][p], spy=True)
    for k in S:
        rows += row(f"<b>{k}</b> {r['names'][k]}", S[k]["periods"][p])
    return ("<div class='tw'><table><thead><tr><th class='t'>Strategy</th><th>Profit</th><th>Return</th><th>Per year</th><th>Sharpe</th>"
            "<th>Worst drawdown</th><th>Trades</th><th>Winners</th><th>Avg win / loss</th></tr></thead><tbody>" + rows + "</tbody></table></div>")


crit_rows = ""
for k in S:
    c = S[k]["criteria"]
    mark = lambda b: "<span class='pos'>✓</span>" if b else "<span class='neg'>✗</span>"
    crit_rows += (f"<tr><td class='t'><b>{k}</b> {r['names'][k]}</td><td>{mark(c['profit_beats_spy'])}</td><td>{mark(c['sharpe_beats_spy'])}</td>"
                  f"<td>{mark(c['dd_smaller_than_spy'])}</td><td><b class='{'pos' if S[k]['pass'] else 'neg'}'>{'PASS' if S[k]['pass'] else 'FAIL'}</b></td></tr>")
years = list(r["spy"].keys())[3:]
yr_rows = ""
for y in years:
    yr_rows += f"<tr><td class='t'>{y}{' (Nov-Dec)' if y == years[0] else ' (to Nov 4)' if y == years[-1] else ''}</td><td class='{'pos' if r['spy'][y]['profit']>0 else 'neg'}'>{usd(r['spy'][y]['profit'])}</td>"
    for k in S:
        v = S[k]["years"][y]["profit"]
        better = v > r["spy"][y]["profit"]
        yr_rows += f"<td class='{'pos' if v > 0 else 'neg'}'>{usd(v)}{' ▲' if better else ''}</td>"
    yr_rows += "</tr>"
s1u, spyu = S["S1"]["periods"][U], r["spy"][U]
s1s = S["S1"]["periods"][SEL]

def clean(o):
    """JSON has no NaN: turn NaN/inf into null."""
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


pack = {"names": r["names"], "spy": r["spy_daily"], "dates": r["dates"],
        "strats": {k: {"daily": S[k]["daily"], "trades": S[k]["trades"], "years": S[k]["years"], "sectors": S[k]["sectors"],
                       "top": S[k]["top_trades"], "worst": S[k]["worst_trades"]} for k in S},
        "spyYears": {y: r["spy"][y] for y in years}, "years": years}

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const NS='http://www.w3.org/2000/svg',W=760,COL={S1:'var(--c0)',S2:'var(--c1)',S3:'#8b5cc4',SPY:'var(--mute)'};
const st={k:'S1',sort:{k:'buy_day',dir:-1},q:'',show:'all',sel:null,yr:'all'};
const P=(v,d=1,s=true)=>v==null||!isFinite(v)?'–':((s&&v>0?'+':'')+(v*100).toFixed(d)+'%').replace('-','−');
const USD=v=>(v<0?'−$':'$')+Math.abs(Math.round(v)).toLocaleString('en-US');const cls=v=>v>0?'pos':v<0?'neg':'';
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function tx(p,x,y,s,a){const t=el('text',Object.assign({x,y},a||{}),p);t.textContent=s;return t}
function tip(n,s){el('title',{},n).textContent=s}
function svg(id,H){const c=document.getElementById(id);c.innerHTML='';return el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},c)}
function ticks(a,b,n){const sp=(b-a)||1,s0=sp/n,m=Math.pow(10,Math.floor(Math.log10(s0)));const s=[1,2,2.5,5,10].map(x=>x*m).find(q=>sp/q<=n)||10*m;const o=[];for(let v=Math.ceil(a/s)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(8));return o}
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/((d1-d0)||1)*(r1-r0);
function h(tag,txt,c){const e=document.createElement(tag);if(txt!=null)e.textContent=txt;if(c)e.className=c;return e}
const series=()=>{const o={SPY:D.spy.map(q=>[q[0],q[1]])};for(const k in D.strats)o[k]=D.strats[k].daily.map(q=>[q[0],q[1]]);return o};
function lineChart(id,dd){const S=series(),H=dd?220:340,g=svg(id,H),L=66,R=W-12,T=12,B=H-26;const keys=['SPY','S3','S2','S1'];
 const conv=arr=>{if(!dd)return arr.map(q=>q[1]);let pk=0;return arr.map(q=>{pk=Math.max(pk,q[1]);return q[1]/pk-1})};
 const vals=keys.flatMap(k=>conv(S[k]));const lo=Math.min(...vals),hi=Math.max(...vals);const tk=ticks(lo,hi,5);const y=lin(Math.min(lo,tk[0]),Math.max(hi,tk[tk.length-1]),B,T);
 const n=S.SPY.length,x=lin(0,n-1,L,R);for(const t of tk){el('line',{x1:L,x2:R,y1:y(t),y2:y(t),class:'grid'},g);tx(g,L-6,y(t)+4,dd?P(t,0):USD(t),{'text-anchor':'end'})}
 let ly='',lx=-99;S.SPY.forEach((q,i)=>{const yr=q[0].slice(0,4);if(yr!==ly){ly=yr;if(x(i)-lx>40){tx(g,x(i),H-6,yr);lx=x(i)}}});
 const ui=S.SPY.findIndex(q=>q[0]>='2025-11-03');if(ui>0){el('line',{x1:x(ui),x2:x(ui),y1:T,y2:B,class:'ref'},g);if(!dd)tx(g,x(ui)+4,T+10,'selection year →')}
 for(const k of keys){const a=conv(S[k]);el('path',{d:'M'+a.map((v,i)=>x(i).toFixed(1)+','+y(v).toFixed(1)).join('L'),fill:'none',stroke:COL[k],'stroke-width':k==='S1'?2.4:k==='SPY'?2:1.4,'stroke-dasharray':k==='SPY'?'5 3':'none'},g)}
 const ov=el('g',{},g);const step=Math.max(1,Math.floor(n/300));for(let i=0;i<n;i+=step){const r=el('rect',{x:x(i),width:(R-L)/n*step,y:T,height:B-T,fill:'transparent'},ov);
  tip(r,S.SPY[i][0]+'\n'+keys.slice().reverse().map(k=>`${k}: ${dd?P(conv(S[k])[i]):USD(S[k][i][1])}`).join('\n'))}}
function yearBars(){const ys=D.years,H=260,g=svg('c-years',H),L=60,R=W-10,T=12,B=H-26;const keys=['SPY','S1','S2','S3'];
 const v=k=>ys.map(y=>k==='SPY'?D.spyYears[y].profit:D.strats[k].years[y].profit);const all=keys.flatMap(v);const tk=ticks(Math.min(0,...all),Math.max(...all),5);
 const y=lin(tk[0],tk[tk.length-1],B,T);for(const t of tk){el('line',{x1:L,x2:R,y1:y(t),y2:y(t),class:'grid'},g);tx(g,L-6,y(t)+4,USD(t),{'text-anchor':'end'})}
 el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'axis'},g);const gw=(R-L)/ys.length,bw=Math.min(22,gw*0.8/keys.length);
 ys.forEach((yr,i)=>{tx(g,L+i*gw+gw/2,H-6,yr,{'text-anchor':'middle'});keys.forEach((k,j)=>{const val=v(k)[i];const r=el('rect',{x:L+i*gw+(gw-bw*keys.length)/2+j*bw+1,width:bw-2,y:Math.min(y(val),y(0)),height:Math.max(1,Math.abs(y(val)-y(0))),fill:COL[k],rx:2},g);tip(r,`${yr} · ${k}: ${USD(val)}`)})})}
const COLS=[['ticker','Stock','t'],['sector','Sector','t'],['drop_day','Drop day','t'],['drop','Fell',''],['buy_day','Bought','t'],['buy','Buy $',''],['sell_day','Sold / marked','t'],['sell','Sell $',''],['days','Days',''],['ret','Return',''],['pnl','P&L $','']];
function TR(){return D.strats[st.k].trades}
function table(){const tr=TR().filter(t=>(st.yr==='all'||t.buy_day.startsWith(st.yr))&&(st.show==='all'||(st.show==='open'?t.exit==='open':st.show==='win'?t.ret>0:t.ret<=0))&&(!st.q||t.ticker.includes(st.q.toUpperCase())));
 const {k,dir}=st.sort;tr.sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*dir);const th=document.getElementById('t-head');th.innerHTML='';
 COLS.forEach(([c,l,cc])=>{const e=h('th',l+(k===c?(dir>0?' ▲':' ▼'):''),cc);e.addEventListener('click',()=>{st.sort={k:c,dir:k===c?-dir:(c==='ticker'||c.endsWith('day')||c==='sector'?1:-1)};table()});th.append(e)});
 const tb=document.getElementById('t-body');tb.innerHTML='';const tot=tr.reduce((a,t)=>a+t.pnl,0),w=tr.filter(t=>t.ret>0).length;
 for(const t of tr.slice(0,1500)){const r=h('tr');if(st.sel===t)r.className='sel';const tc=h('td',t.ticker,'t');if(t.earnings_in_hold)tc.append(h('span','E','tag e'));if(t.exit==='open')tc.append(h('span','open','tag o'));
  r.append(tc,h('td',t.sector,'t muted'),h('td',t.drop_day,'t'),h('td',P(t.drop),'neg'),h('td',t.buy_day,'t'),h('td',t.buy.toFixed(2)),h('td',t.sell_day,'t'),h('td',t.sell.toFixed(2)),h('td',t.days),h('td',P(t.ret,2),cls(t.ret)),h('td',USD(t.pnl),cls(t.pnl)));r.addEventListener('click',()=>pick(t));tb.append(r)}
 document.getElementById('t-count').textContent=`${tr.length} trades · ${tr.length?Math.round(w/tr.length*100):0}% winners · total ${USD(tot)}`}
function pick(t){if(!t)return;st.sel=t;table();const H=220,g=svg('c-trade',H),L=50,R=W-10,T=14,B=H-26;const p=t.marks.length?t.marks:[1];let hw=1;const stop=p.map(v=>{const s=hw*0.88;hw=Math.max(hw,v);return s});
 const vals=p.concat(stop);const tk=ticks(Math.min(...vals)*0.99,Math.max(...vals)*1.01,5);const y=lin(tk[0],tk[tk.length-1],B,T),x=lin(0,Math.max(1,p.length-1),L+10,R-10);
 for(const v of tk){el('line',{x1:L,x2:R,y1:y(v),y2:y(v),class:'grid'},g);tx(g,L-6,y(v)+4,P(v-1,0),{'text-anchor':'end'})}el('line',{x1:L,x2:R,y1:y(1),y2:y(1),class:'axis'},g);
 el('path',{d:'M'+stop.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--bad)','stroke-dasharray':'5 4','stroke-width':1.5},g);
 el('path',{d:'M'+p.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--c0)','stroke-width':2.2},g);
 tx(g,L+10,H-6,t.buy_day);tx(g,R-10,H-6,t.sell_day,{'text-anchor':'end'});
 document.getElementById('trade-title').textContent=`${t.ticker}: bought ${t.buy_day} at $${t.buy.toFixed(2)}, ${t.exit==='open'?'still open, marked':'sold'} ${t.sell_day} at $${t.sell.toFixed(2)} (${P(t.ret,2)}, ${USD(t.pnl)}), ${t.days} days`}
function side(){const s=D.strats[st.k];const sec=document.getElementById('sec');sec.innerHTML='';Object.entries(s.sectors).slice(0,6).forEach(([k,v])=>{const li=h('li');li.textContent=`${k}: ${Math.round(v*100)}%`;sec.append(li)});
 const tp=document.getElementById('top');tp.innerHTML='';s.top.forEach(t=>{const li=h('li');li.innerHTML=`<b>${t.ticker}</b> ${t.buy_day}: <span class="pos">${P(t.ret,0)}</span> (${USD(t.pnl)})`;tp.append(li)});
 const ws=document.getElementById('worst');ws.innerHTML='';s.worst.forEach(t=>{const li=h('li');li.innerHTML=`<b>${t.ticker}</b> ${t.buy_day}: <span class="neg">${P(t.ret,0)}</span> (${USD(t.pnl)})`;ws.append(li)})}
function yrSel(){const s=document.getElementById('yr');s.innerHTML='';[['all','All years'],...D.years.map(y=>[y,y])].forEach(([v,l])=>{const o=h('option',l);o.value=v;s.append(o)});s.value=st.yr}
function render(){document.querySelectorAll('[data-k]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.k===st.k)));side();table();const tr=TR();pick(tr.slice().sort((a,b)=>b.pnl-a.pnl)[0])}
document.querySelectorAll('[data-k]').forEach(b=>b.addEventListener('click',()=>{st.k=b.dataset.k;st.sel=null;render()}));
document.querySelectorAll('[data-show]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-show]').forEach(o=>o.setAttribute('aria-pressed',String(o===b)));st.show=b.dataset.show;table()}));
document.getElementById('q').addEventListener('input',e=>{st.q=e.target.value.trim();table()});
document.getElementById('yr').addEventListener('change',e=>{st.yr=e.target.value;table()});
lineChart('c-eq',false);lineChart('c-dd',true);yearBars();yrSel();render();
"""

body = f"""
<div class="wrap">
<header><h1>Six-year backtest: top-4 unexplained losers</h1>
<p class="lede">The three best versions from the one-year test, run unchanged from November 2020 to November 4, 2026 on a $24,000 account ($1,000 per trade, at most 24 positions, 12% trailing stop). The rules and pass marks were committed before the run. The five years from November 2020 to October 2025 were never used to choose these strategies, so they decide pass or fail.</p></header>

<section aria-labelledby="h-v"><h2 id="h-v">Verdict</h2>
 <div class="verdict"><p><b>Strategy S1 passed</b> on the five unseen years: <b class="pos">{usd(s1u['profit'])}</b> ({pc(s1u['return'])}, {pc(s1u['cagr'])} a year) vs SPY's {usd(spyu['profit'])} ({pc(spyu['return'])}) on the same $24,000, with a higher Sharpe ratio ({f2(s1u['sharpe'])} vs {f2(spyu['sharpe'])}) and a smaller worst drawdown ({pc(s1u['max_dd'])} vs {pc(spyu['max_dd'])}). S2 and S3 failed: they made less than SPY.</p></div>
 <div class="verdict warn small"><p><b>How strong is the pass?</b> On profit it beat SPY by only {usd(s1u['profit']-spyu['profit'])} over five years, which a little more cost or slippage could erase. Its clearer advantages are risk: a better Sharpe ratio and a smaller drawdown, helped most by 2022 (S1 {usd(S['S1']['years']['2022']['profit'])} vs SPY {usd(r['spy']['2022']['profit'])}). Stocks removed from the S&amp;P 500 during these years are missing from the data, which flatters dip buying. Idle cash earned nothing here; T-bill interest would add a little.</p></div>
 <div class="card"><h3>Pre-registered checks (unseen five years)</h3><div class="tw"><table><thead><tr><th class="t">Strategy</th><th>Profit beats SPY</th><th>Sharpe beats SPY</th><th>Smaller drawdown</th><th>Result</th></tr></thead><tbody>{crit_rows}</tbody></table></div></div>
</section>

<section aria-labelledby="h-p"><h2 id="h-p">Results by period</h2>
 <div class="card"><h3>Unseen five years: Nov 2020 to Oct 2025 (decides pass/fail)</h3>{period_table(U)}</div>
 <div class="card"><h3>Selection year: Nov 2025 to Nov 2026</h3>{period_table(SEL)}<p class="small muted">Lower than the one-year ledger (+$7,821 for S1) because here the strategy runs continuously: positions opened earlier still hold slots at the start of the year, cool-offs carry over, and stocks count only from the date they joined the index.</p></div>
 <div class="card"><h3>Full six years</h3>{period_table(FULL)}</div>
</section>

<section aria-labelledby="h-c"><h2 id="h-c">Account value and drawdown</h2>
 <div class="card"><div class="legend"><span><i style="background:var(--c0)"></i>S1</span><span><i style="background:var(--c1)"></i>S2</span><span><i style="background:#8b5cc4"></i>S3</span><span><i style="background:var(--mute)"></i>SPY (dashed)</span></div>
 <h3>Account value ($24,000 start)</h3><div class="chart" id="c-eq"></div><h3>Drawdown from peak</h3><div class="chart" id="c-dd"></div><p class="small muted">Hover for values. The dashed vertical line marks the start of the selection year.</p></div>
 <div class="card"><h3>Profit by calendar year</h3><div class="chart" id="c-years"></div>
 <div class="tw"><table><thead><tr><th class="t">Year</th><th>SPY</th><th>S1</th><th>S2</th><th>S3</th></tr></thead><tbody>{yr_rows}</tbody></table></div><p class="small muted">▲ = beat SPY that year.</p></div>
</section>

<section aria-labelledby="h-t"><h2 id="h-t">Trades</h2>
 <div class="bar" role="toolbar" aria-label="Strategy"><div class="ctl" role="group" aria-label="Strategy"><span>Strategy</span><button class="seg" type="button" data-k="S1">S1</button><button class="seg" type="button" data-k="S2">S2</button><button class="seg" type="button" data-k="S3">S3</button></div></div>
 <div class="cols3"><div class="card small"><h3>Biggest winners</h3><ul id="top"></ul></div><div class="card small"><h3>Biggest losers</h3><ul id="worst"></ul></div><div class="card small"><h3>Sectors bought</h3><ul id="sec"></ul></div></div>
 <div class="card"><div class="daynav"><input type="search" id="q" placeholder="Find a ticker" aria-label="Find a ticker"><select id="yr" aria-label="Year bought"></select>
  <div class="ctl" role="group" aria-label="Show"><span>Show</span><button class="seg" type="button" data-show="all" aria-pressed="true">All</button><button class="seg" type="button" data-show="win" aria-pressed="false">Winners</button><button class="seg" type="button" data-show="loss" aria-pressed="false">Losers</button><button class="seg" type="button" data-show="open" aria-pressed="false">Open</button></div>
  <span class="small muted" id="t-count"></span></div>
  <div class="tw"><table><thead><tr id="t-head"></tr></thead><tbody id="t-body"></tbody></table></div>
  <p class="small muted">Click a column to sort, a row to see its price path. <span class="tag e">E</span> = reported earnings during the hold.</p></div>
 <div class="card"><h3 id="trade-title"></h3><div class="legend"><span><i style="background:var(--c0)"></i>Close vs entry</span><span><i style="background:var(--bad)"></i>12% trailing stop</span></div><div class="chart" id="c-trade"></div></div>
</section>

<section aria-labelledby="h-r"><h2 id="h-r">Rules and limits</h2><div class="card small"><ul>
 <li><b>S1:</b> top 4 S&amp;P 500 losers (down 2%+, $20+, 1M+ shares) after skipping explained drops (earnings that day or the evening before, 8%+ gap down at the open) and stocks reporting in the next 10 trading days. <b>S2:</b> same without the upcoming-earnings skip. <b>S3:</b> only the 10 biggest losers are checked.</li>
 <li>All: buy at the next open, $1,000 each; sell when the price falls 12% below the highest close since entry; at most 24 positions, 2 new buys per sector per day, no re-buying within 10 days of a stop-out. Costs 0.05% per side plus 0.10% on stop sales.</li>
 <li>Data: Yahoo Finance prices and earnings dates; today's S&amp;P 500 members counted from their date added (removed stocks missing). After-hours moves not counted. Idle cash earns nothing.</li>
 <li>Pre-registered in <code>research/top4_trailing/backtest_6y/PREREGISTRATION.md</code>; code <code>bt6y.py</code>, <code>build_report.py</code>. Research only, not financial advice; no trades were sent.</li></ul></div></section>
</div>
"""

CSS = CSS3M + """
code{word-break:break-all;font-size:.85em}
.verdict{border-left:4px solid var(--ok);background:var(--panel);border-radius:6px;padding:12px 16px}.verdict.warn{border-left-color:var(--warn)}
"""
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Top-4 Losers Six-Year Backtest</title><style>{CSS}</style></head><body>{body}
<script id="data" type="application/json">{json.dumps(clean(pack), separators=(',', ':')).replace('</', '<\\/')}</script>
<script>{JS}</script></body></html>"""
(HERE / "report.html").write_text(page, encoding="utf-8")
print(f"wrote {HERE / 'report.html'} ({(HERE / 'report.html').stat().st_size / 1024:.0f} KB)")
