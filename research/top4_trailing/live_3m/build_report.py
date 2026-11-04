"""Build the offline interactive report for the 3-month ledger.

Reads data.json (from ledger3m.py) and writes report.html: one self-contained
file (inline data, CSS and JavaScript; no network), so it opens offline.

  python build_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "data.json").read_text())
w = data["window"]

CSS = r"""
:root{--bg:#f5f6f8;--panel:#fff;--fg:#16202a;--muted:#5d6876;--line:#dde2e8;--grid:#eaedf1;--ref:#98a2ad;
--c0:#2563c9;--c1:#d9762b;--mute:#a9b2bc;--ok:#1f8a55;--bad:#c0392b;--warn:#a86b00;--sel:#e8f0fd;--hi:#fff4d6}
@media (prefers-color-scheme:dark){:root{--bg:#10151c;--panel:#19202a;--fg:#e8edf3;--muted:#9aa6b4;--line:#2b3441;--grid:#242d38;
--ref:#6c7785;--c0:#6ea0ff;--c1:#f0a35e;--mute:#56616e;--ok:#5cc79a;--bad:#ff7a6b;--warn:#e0b04a;--sel:#1f2d44;--hi:#3a3320}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px max(16px,env(safe-area-inset-left)) 60px max(16px,env(safe-area-inset-right))}
h1{font:400 1.9rem/1.2 Georgia,serif;margin:0 0 6px}h2{font:400 1.35rem/1.25 Georgia,serif;margin:0}h3{margin:0;font-size:1rem}
p{margin:0}.muted{color:var(--muted)}.small{font-size:.84rem}
.lede{max-width:48rem}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;margin:10px 0 4px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center}
.ctl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.85rem}.ctl>span{color:var(--muted);margin-right:2px}
button.seg{font:inherit;color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:4px 10px;cursor:pointer}
button.seg[aria-pressed=true]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--c0);outline-offset:2px}
section{margin-top:26px;display:flex;flex-direction:column;gap:12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,10.5rem),1fr));gap:10px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px 13px;display:flex;flex-direction:column;gap:2px}
.tile .l{font-size:.78rem;color:var(--muted)}.tile .v{font:400 1.5rem/1.2 Georgia,serif;font-variant-numeric:tabular-nums}.tile .s{font-size:.78rem;color:var(--muted)}
.pos{color:var(--ok)}.neg{color:var(--bad)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;min-width:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,30rem),1fr));gap:12px}
.chart svg{width:100%;height:auto;display:block}.chart text{fill:var(--muted);font-size:11px;font-family:inherit}.chart text.st{fill:var(--fg)}
.grid{stroke:var(--grid)}.axis{stroke:var(--ref)}.ref{stroke:var(--ref);stroke-dasharray:4 3}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.8rem;color:var(--muted)}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.tw{overflow:auto;max-height:28rem}table{border-collapse:collapse;width:100%;font-size:.84rem;font-variant-numeric:tabular-nums}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;cursor:pointer;user-select:none}
th.t,td.t{text-align:left}tbody tr{cursor:pointer}tbody tr:hover td{background:var(--sel)}tr.sel td{background:var(--hi)}
.tag{display:inline-block;font-size:.72rem;padding:0 6px;border-radius:999px;border:1px solid currentColor;margin-left:4px}
.tag.e{color:var(--warn)}.tag.o{color:var(--c0)}
input[type=search],select{font:inherit;color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
.daynav{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.cols3{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:12px}
ul{margin:0;padding-left:1.1rem}li{margin:2px 0}
.note{border-left:4px solid var(--warn);background:var(--panel);border-radius:6px;padding:10px 14px}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const NS='http://www.w3.org/2000/svg',W=760;
const st={trail:'8%',filt:'all unexplained',mode:'after',day:null,sort:{k:'buy_day',dir:-1},q:'',show:'all',sel:null};
const key=()=>`${st.trail} | ${st.filt} | ${st.mode}`, V=()=>D.variants[key()], CANDS=()=>D.candidates[`${st.filt} | ${st.mode}`];
const P=(v,d=1,s=true)=>v==null||!isFinite(v)?'–':((s&&v>0?'+':'')+(v*100).toFixed(d)+'%').replace('-','−');
const USD=v=>(v<0?'−$':'$')+Math.abs(Math.round(v)).toLocaleString('en-US');
const cls=v=>v>0?'pos':v<0?'neg':'';
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function tx(p,x,y,s,a){const t=el('text',Object.assign({x,y},a||{}),p);t.textContent=s;return t}
function tip(n,s){el('title',{},n).textContent=s}
function svg(id,H){const c=document.getElementById(id);c.innerHTML='';return el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'},c)}
function ticks(a,b,n){const sp=(b-a)||1,s0=sp/n,m=Math.pow(10,Math.floor(Math.log10(s0)));const s=[1,2,2.5,5,10].map(x=>x*m).find(q=>sp/q<=n)||10*m;const o=[];for(let v=Math.ceil(a/s)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(8));return o}
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/((d1-d0)||1)*(r1-r0);
function h(tag,txt,c){const e=document.createElement(tag);if(txt!=null)e.textContent=txt;if(c)e.className=c;return e}

function tiles(){const s=V().summary,box=document.getElementById('tiles');box.innerHTML='';
 const spy=D.spy[D.spy.length-1].ret;
 const items=[['Trades',s.trades,`${s.open} still open`],['Winning trades',P(s.win_rate,1,false),`closed only: ${P(s.closed_win_rate,1,false)}`],
  ['Total profit/loss',USD(s.pnl),'$1,000 per trade',cls(s.pnl)],['Average trade',P(s.avg,2),`win ${P(s.avg_win)} / loss ${P(s.avg_loss)}`,cls(s.avg)],
  ['Worst drawdown',USD(s.max_dd_usd),'peak-to-trough of total P&L','neg'],['Most open at once',s.peak_open,`= $${(s.peak_open*1000).toLocaleString()} deployed`],
  ['Held through earnings',s.earnings_in_hold,'trades with a report during the hold'],['SPY same window',P(spy),'context only',cls(spy)]];
 for(const [l,v,sub,c] of items){const t=h('div',null,'tile');t.append(h('span',l,'l'),h('span',String(v),'v '+(c||'')),h('span',sub,'s'));box.append(t)}}

function pnlChart(){const dl=V().daily,H=300,s=svg('c-pnl',H),L=60,R=W-10,T=12,B=H-60,B2=H-22;
 const vals=dl.flatMap(d=>[d.pnl,d.realized]);const lo=Math.min(0,...vals),hi=Math.max(0,...vals);const tk=ticks(lo,hi,5);
 const y=lin(Math.min(lo,tk[0]),Math.max(hi,tk[tk.length-1]),B,T);const x=lin(0,dl.length-1,L,R);
 for(const t of tk){el('line',{x1:L,x2:R,y1:y(t),y2:y(t),class:'grid'},s);tx(s,L-6,y(t)+4,USD(t),{'text-anchor':'end'})}
 el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'axis'},s);
 const mo=Math.max(...dl.map(d=>d.open))||1,yb=lin(0,mo,B2,B+10),bw=(R-L)/dl.length;
 dl.forEach((d,i)=>{const r=el('rect',{x:x(i)-bw/2+0.5,width:Math.max(1,bw-1),y:yb(d.open),height:B2-yb(d.open),fill:'var(--mute)',opacity:.6},s);tip(r,`${d.date}: ${d.open} open positions`)});
 tx(s,L-6,B2,'0',{'text-anchor':'end'});tx(s,L-6,yb(mo)+4,String(mo),{'text-anchor':'end'});tx(s,R,H-4,'Grey bars: open positions',{'text-anchor':'end'});
 let lastM='';dl.forEach((d,i)=>{const m=d.date.slice(0,7);if(m!==lastM){lastM=m;tx(s,x(i),B2+14,new Date(d.date+'T12:00').toLocaleString('en-US',{month:'short'}),{'text-anchor':'start'})}});
 for(const [k,c,wd] of [['realized','var(--c1)',1.5],['pnl','var(--c0)',2.2]]){
  el('path',{d:'M'+dl.map((d,i)=>x(i).toFixed(1)+','+y(d[k]).toFixed(1)).join('L'),fill:'none',stroke:c,'stroke-width':wd,'stroke-linejoin':'round'},s)}
 const ov=el('g',{},s);dl.forEach((d,i)=>{const r=el('rect',{x:x(i)-bw/2,width:bw,y:T,height:B2-T,fill:'transparent',style:'cursor:pointer'},ov);
  tip(r,`${d.date}\nTotal P&L ${USD(d.pnl)} (realized ${USD(d.realized)})\n${d.open} open`);r.addEventListener('click',()=>{st.day=d.date;dayView()})});
 const e=dl[dl.length-1];tx(s,R-2,y(e.pnl)-6,USD(e.pnl),{'text-anchor':'end',class:'st'})}

function monthly(){const tr=V().trades,m={};for(const t of tr){const k=t.buy_day.slice(0,7);m[k]=m[k]||{n:0,w:0,p:0};m[k].n++;if(t.ret>0)m[k].w++;m[k].p+=t.pnl}
 const tb=document.getElementById('t-month');tb.innerHTML='';for(const k of Object.keys(m).sort()){const r=m[k],tr_=h('tr');
  tr_.append(h('td',new Date(k+'-15T12:00').toLocaleString('en-US',{month:'long',year:'numeric'}),'t'),h('td',r.n),h('td',P(r.w/r.n,0,false)),h('td',USD(r.p),cls(r.p)),h('td',P(r.p/r.n/1000,2),cls(r.p)));tb.append(tr_)}}

function dayList(){const dl=V().daily.map(d=>d.date),cs=[...new Set(CANDS().map(c=>c.drop_day))];
 const all=[...new Set([...dl,...cs])].sort();const sel=document.getElementById('day');const cur=st.day||all[all.length-1];sel.innerHTML='';
 for(const d of all){const o=h('option',new Date(d+'T12:00').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'}));o.value=d;sel.append(o)}
 sel.value=all.includes(cur)?cur:all[all.length-1];st.day=sel.value;return all}
function dayView(){const all=dayList();const d=st.day,tr=V().trades;
 const cand=CANDS().filter(c=>c.drop_day===d);
 const buys=tr.filter(t=>t.buy_day===d),sells=tr.filter(t=>t.exit!=='open'&&t.sell_day===d),open=tr.filter(t=>t.buy_day<=d&&(t.exit==='open'||t.sell_day>d));
 const c1=document.getElementById('d-cand');c1.innerHTML='';if(!cand.length)c1.append(h('p','No drop day (or no stock fell 2%+ in the top 10).','muted small'));
 else{const t=h('table');t.innerHTML='<thead><tr><th class="t">#</th><th class="t">Stock</th><th>Fell</th><th class="t">Decision</th></tr></thead>';const b=h('tbody');
  for(const c of cand){const r=h('tr');r.append(h('td',c.rank,'t'),h('td',c.ticker,'t'),h('td',P(c.drop),'neg'),h('td',c.picked?'Bought next open':(c.excluded?'Skipped: '+c.excluded:'Not needed (4 already picked)'),'t '+(c.picked?'pos':'muted')));b.append(r)}t.append(b);c1.append(t)}
 const list=(id,arr,f)=>{const e=document.getElementById(id);e.innerHTML='';if(!arr.length){e.append(h('p','None','muted small'));return}const u=h('ul');arr.forEach(t=>{const li=h('li');li.innerHTML=f(t);li.style.cursor='pointer';li.addEventListener('click',()=>pick(t));u.append(li)});e.append(u)};
 list('d-buy',buys,t=>`<b>${t.ticker}</b> at $${t.buy.toFixed(2)} <span class="muted">(fell ${P(t.drop)} on ${t.drop_day})</span>`);
 list('d-sell',sells,t=>`<b>${t.ticker}</b> at $${t.sell.toFixed(2)} <span class="${cls(t.ret)}">${P(t.ret)}</span> <span class="muted">after ${t.days}d, ${t.exit.replace('stop: ','')}</span>`);
 list('d-open',open,t=>{const v=(Object.fromEntries(t.path))[d];return `<b>${t.ticker}</b> since ${t.buy_day} <span class="${cls(v-1)}">${v?P(v-1):''}</span>`});
 const i=all.indexOf(d);document.getElementById('prev').disabled=i<=0;document.getElementById('next').disabled=i>=all.length-1}

const COLS=[['ticker','Stock','t'],['drop_day','Drop day','t'],['drop','Fell',''],['buy_day','Bought','t'],['buy','Buy $',''],['sell_day','Sold / marked','t'],['sell','Sell $',''],['days','Days',''],['ret','Return',''],['pnl','P&L $',''],['exit','Exit','t']];
function table(){const tr=V().trades.filter(t=>(st.show==='all'||(st.show==='open'?t.exit==='open':st.show==='closed'?t.exit!=='open':st.show==='earn'?t.earnings_in_hold:true))&&(!st.q||t.ticker.includes(st.q.toUpperCase())));
 const {k,dir}=st.sort;tr.sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*dir);
 const th=document.getElementById('t-head');th.innerHTML='';COLS.forEach(([c,l,ccls])=>{const e=h('th',l+(k===c?(dir>0?' ▲':' ▼'):''),ccls);e.setAttribute('aria-sort',k===c?(dir>0?'ascending':'descending'):'none');e.addEventListener('click',()=>{st.sort={k:c,dir:k===c?-dir:(c==='ticker'||c.endsWith('day')?1:-1)};table()});th.append(e)});
 const tb=document.getElementById('t-body');tb.innerHTML='';
 for(const t of tr){const r=h('tr');if(st.sel&&st.sel.ticker===t.ticker&&st.sel.buy_day===t.buy_day)r.className='sel';
  const tcell=h('td',t.ticker,'t');if(t.earnings_in_hold)tcell.append(h('span','E','tag e'));if(t.exit==='open')tcell.append(h('span','open','tag o'));
  r.append(tcell,h('td',t.drop_day,'t'),h('td',P(t.drop),'neg'),h('td',t.buy_day,'t'),h('td',t.buy.toFixed(2)),h('td',t.sell_day,'t'),h('td',t.sell.toFixed(2)),h('td',t.days),h('td',P(t.ret,2),cls(t.ret)),h('td',USD(t.pnl),cls(t.pnl)),h('td',t.exit.replace('stop: ',''),'t muted'));
  r.addEventListener('click',()=>pick(t));tb.append(r)}
 document.getElementById('t-count').textContent=`${tr.length} trades shown`}

function pick(t){st.sel=t;table();const H=230,s=svg('c-trade',H),L=50,R=W-10,T=14,B=H-26;const p=t.path.length?t.path:[[t.buy_day,1]];
 const trail=st.trail==='8%'?0.08:0.03;let hw=1;const stop=p.map(([d,v])=>{const sv=hw*(1-trail);hw=Math.max(hw,v);return sv});
 const vals=p.map(q=>q[1]).concat(stop,[t.sell/t.buy*(1)]);const lo=Math.min(...vals)*0.99,hi=Math.max(...vals)*1.01;const tk=ticks(lo,hi,5);const y=lin(tk[0],tk[tk.length-1],B,T);const x=lin(0,Math.max(1,p.length-1),L+10,R-10);
 for(const v of tk){el('line',{x1:L,x2:R,y1:y(v),y2:y(v),class:'grid'},s);tx(s,L-6,y(v)+4,P(v-1,0),{'text-anchor':'end'})}
 el('line',{x1:L,x2:R,y1:y(1),y2:y(1),class:'axis'},s);
 el('path',{d:'M'+stop.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--bad)','stroke-dasharray':'5 4','stroke-width':1.5},s);
 el('path',{d:'M'+p.map((q,i)=>x(i)+','+y(q[1])).join('L'),fill:'none',stroke:'var(--c0)','stroke-width':2.2},s);
 p.forEach((q,i)=>{const c=el('circle',{cx:x(i),cy:y(q[1]),r:3,fill:'var(--c0)'},s);tip(c,`${q[0]}: close ${P(q[1]-1)} vs entry; stop ${P(stop[i]-1)}`)});
 tx(s,L+10,H-6,p[0][0]);tx(s,R-10,H-6,p[p.length-1][0],{'text-anchor':'end'});
 document.getElementById('trade-title').textContent=`${t.ticker}: bought ${t.buy_day} at $${t.buy.toFixed(2)}, ${t.exit==='open'?'still open, marked':'sold'} ${t.sell_day} at $${t.sell.toFixed(2)} (${P(t.ret,2)}, ${USD(t.pnl)})${t.earnings_in_hold?' · reported earnings during the hold':''}`}

function render(){tiles();pnlChart();monthly();dayView();table();const tr=V().trades;pick(st.sel&&tr.find(t=>t.ticker===st.sel.ticker&&t.buy_day===st.sel.buy_day)||tr.slice().sort((a,b)=>b.ret-a.ret)[0])}
function seg(attr,k){const bs=document.querySelectorAll(`[${attr}]`);bs.forEach(b=>b.addEventListener('click',()=>{bs.forEach(o=>o.setAttribute('aria-pressed',String(o===b)));st[k]=b.getAttribute(attr);render()}))}
seg('data-trail','trail');seg('data-filt','filt');seg('data-mode','mode');seg('data-show','show');
document.getElementById('day').addEventListener('change',e=>{st.day=e.target.value;dayView()});
document.getElementById('prev').addEventListener('click',()=>{const a=dayList(),i=a.indexOf(st.day);if(i>0){st.day=a[i-1];dayView()}});
document.getElementById('next').addEventListener('click',()=>{const a=dayList(),i=a.indexOf(st.day);if(i<a.length-1){st.day=a[i+1];dayView()}});
document.getElementById('q').addEventListener('input',e=>{st.q=e.target.value.trim();table()});
render();
"""

def short(d):
    import datetime as dt
    return dt.date.fromisoformat(d).strftime("%b %-d, %Y")

body = f"""
<div class="wrap">
<header>
  <h1>Top-4 unexplained losers: 3-month ledger</h1>
  <p class="lede">Each trading day from {short(w['first_drop_day'])} to {short(w['last_drop_day'])} ({w['drop_days']} days): rank the S&amp;P 500 losers (down 2%+, price $20+, 1M+ shares), skip the ones with an obvious reason (earnings that day or the evening before, or an 8%+ gap down at the open), and buy the 4 biggest remaining losers at the next morning's open, $1,000 each, and sell only when the trailing stop is hit. Open positions are valued at the close of {short(w['marked_at'])}.</p>
</header>

<div class="bar" role="toolbar" aria-label="Settings">
  <div class="ctl" role="group" aria-label="Selection"><span>Pick</span><button class="seg" type="button" data-mode="after" aria-pressed="true">Top 4 after removing explained</button><button class="seg" type="button" data-mode="top10" aria-pressed="false">First 10, then remove</button></div>
  <div class="ctl" role="group" aria-label="Trailing stop"><span>Trailing stop</span><button class="seg" type="button" data-trail="8%" aria-pressed="true">8%</button><button class="seg" type="button" data-trail="3%" aria-pressed="false">3%</button></div>
  <div class="ctl" role="group" aria-label="Earnings rule"><span>Earnings</span><button class="seg" type="button" data-filt="all unexplained" aria-pressed="true">Skip only same-day earnings</button><button class="seg" type="button" data-filt="skip earnings ahead" aria-pressed="false">Also skip if reporting in next 10 days</button></div>
</div>

<section aria-labelledby="s-sum"><h2 id="s-sum">Results</h2><div class="tiles" id="tiles"></div>
  <div class="note small"><b>Illustration, not proof.</b> Three months is a short window, the rules weren't pre-registered, and analyst actions and other news weren't checked. No trades were sent.</div></section>

<section aria-labelledby="s-pnl"><h2 id="s-pnl">Profit/loss over time</h2>
  <div class="card"><p class="small muted">Total P&amp;L (closed trades plus open positions valued at each close) and realized P&amp;L from closed trades only. Click a day to open it below; hover for values.</p>
  <div class="legend"><span><i style="background:var(--c0)"></i>Total P&amp;L</span><span><i style="background:var(--c1)"></i>Realized (closed trades)</span><span><i style="background:var(--mute)"></i>Open positions</span></div>
  <div class="chart" id="c-pnl"></div></div>
  <div class="card"><h3>By month bought</h3><div class="tw"><table><thead><tr><th class="t">Month</th><th>Trades</th><th>Winners</th><th>P&amp;L</th><th>Avg trade</th></tr></thead><tbody id="t-month"></tbody></table></div></div>
</section>

<section aria-labelledby="s-day"><h2 id="s-day">Day by day</h2>
  <div class="daynav"><button class="seg" type="button" id="prev" aria-label="Previous day">◀</button><select id="day" aria-label="Choose a day"></select><button class="seg" type="button" id="next" aria-label="Next day">▶</button><span class="small muted">The list on the left is that day's losers in order, with why each was bought or skipped (buys happen the next morning).</span></div>
  <div class="cols3">
    <div class="card"><h3>Losers checked that day</h3><div class="tw" id="d-cand"></div></div>
    <div class="card"><h3>Bought at the open</h3><div id="d-buy"></div><h3 style="margin-top:8px">Sold</h3><div id="d-sell"></div></div>
    <div class="card"><h3>Open at the close</h3><div id="d-open" class="small tw"></div></div>
  </div>
</section>

<section aria-labelledby="s-tr"><h2 id="s-tr">Every trade</h2>
  <div class="card">
    <div class="daynav"><input type="search" id="q" placeholder="Find a ticker" aria-label="Find a ticker">
      <div class="ctl" role="group" aria-label="Show"><span>Show</span><button class="seg" type="button" data-show="all" aria-pressed="true">All</button><button class="seg" type="button" data-show="closed" aria-pressed="false">Closed</button><button class="seg" type="button" data-show="open" aria-pressed="false">Open</button><button class="seg" type="button" data-show="earn" aria-pressed="false">Held through earnings</button></div>
      <span class="small muted" id="t-count"></span></div>
    <div class="tw"><table><thead><tr id="t-head"></tr></thead><tbody id="t-body"></tbody></table></div>
    <p class="small muted">Click a column to sort, a row to see its price path. <span class="tag e">E</span> = reported earnings during the hold.</p>
  </div>
  <div class="card"><h3 id="trade-title"></h3><div class="legend"><span><i style="background:var(--c0)"></i>Close vs entry price</span><span><i style="background:var(--bad)"></i>Trailing stop level</span></div><div class="chart" id="c-trade"></div></div>
</section>

<section aria-labelledby="s-cons"><h2 id="s-cons">Things to consider before trading this</h2>
  <div class="card small"><ul>
    <li><b>Most of the profit is not locked in.</b> With the 8% stop, closed trades are negative and the total depends on positions still open; a market drop would take much of it back.</li>
    <li><b>Earnings during the hold are a coin flip.</b> APP gained after its Nov 4 report, but fell 19.7% after its Aug 5 report. Use the earnings switch to see results without them.</li>
    <li><b>After-hours moves aren't included.</b> Everything is valued at regular-session prices; earnings reactions often happen after the close.</li>
    <li><b>Capital.</b> With no position limit, up to 60 trades were open at once (about $60,000 at $1,000 each). A cap of 20-30 positions would change which trades get taken.</li>
    <li><b>Concentration.</b> Picks often cluster in one sector on the same day (chips in late October); a limit of one or two per sector per day would spread the risk.</li>
    <li><b>Repeat buys.</b> The same stock can be bought again soon after being stopped out (APP three times); a cool-off period is worth testing.</li>
    <li><b>Short history.</b> Three months, one market regime, rules not pre-registered. The 20-year test of a similar setup (test 8) found the 8% stop roughly tracks the market and random picks do about as well.</li>
    <li><b>Taxes.</b> Nearly all gains would be short-term.</li>
  </ul></div>
</section>

<section aria-labelledby="s-how"><h2 id="s-how">How it was calculated</h2>
  <div class="card small"><ul>
    <li>Prices: Yahoo Finance daily bars, split/dividend adjusted for returns; buy and sell prices shown as traded. Earnings dates: Yahoo Finance. {('Missing data: ' + ', '.join(data['notes']['missing_tickers']) + '.') if data['notes']['missing_tickers'] else ''}</li>
    <li>Trailing stop: highest close since entry (or the entry price) × (1 − stop). If a day opens below the stop, the sale is at the open; otherwise, if the day's low touches it, at the stop price. The high-water mark updates at each close, so intraday highs don't raise the stop.</li>
    <li>Costs: 0.05% per side, plus 0.10% extra slippage on stop sales. $1,000 per trade; no limit on open positions.</li>
    <li>\"Top 4 after removing explained\" walks down the full list of losers until 4 unexplained ones are found; \"First 10, then remove\" only looks at the 10 biggest losers, so heavy news days can leave fewer than 4 buys.</li>
    <li>"Skip if reporting in next 10 days" uses earnings dates known before buying. "E" tags use the actual report dates during each hold.</li>
    <li>Built by <code>research/top4_trailing/live_3m/ledger3m.py</code> and <code>build_report.py</code>. Research only, not financial advice.</li>
  </ul></div>
</section>
</div>
"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Top-4 Losers Ledger</title><style>{CSS}</style></head><body>{body}
<script id="data" type="application/json">{json.dumps(data, separators=(',', ':')).replace('</', '<\\/')}</script>
<script>{JS}</script></body></html>"""
(HERE / "report.html").write_text(page, encoding="utf-8")
print(f"wrote {HERE / 'report.html'} ({(HERE / 'report.html').stat().st_size / 1024:.0f} KB)")
