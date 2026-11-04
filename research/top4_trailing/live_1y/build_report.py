"""Build the offline interactive one-year report (report.html).

Reads data.json from ledger_1y.py. Keeps the summary and daily P&L of all 32
versions (for the comparison table) and full trade, path and day-by-day
detail for the "top 4 after removing explained" versions with 8% and 12%
stops. One self-contained file: inline data, CSS and JavaScript, no network.

  python build_report.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "data.json").read_text())
w = d["window"]
CSS3M = (HERE.parent / "live_3m" / "build_report.py").read_text().split('CSS = r"""', 1)[1].split('"""', 1)[0]

versions, detail, cands = [], {}, {}
for k, v in d["variants"].items():
    stop, filt, mode, ctl = [x.strip() for x in k.split("|")]
    versions.append({"key": k, "stop": stop, "earnings": filt, "selection": mode, "controls": ctl, **v["summary"],
                     "daily": [[x["date"], x["pnl"], x["realized"], x["open"]] for x in v["daily"]]})
    if mode == "after" and stop in ("8%", "12%"):
        detail[k] = v["trades"]
        cands[k] = d["candidates"].get(f"{filt} | {mode} | {ctl} | {stop}")
BEST = "12% | skip earnings ahead | after | controls"
best = d["variants"][BEST]["summary"]
spy = d["spy"]
spy_ret = spy[-1]["ret"]
pack = {"versions": versions, "detail": detail, "cands": cands, "spy": [[x["date"], x["ret"]] for x in spy],
        "dates": d["dates"], "best": BEST}

nice = lambda s: dt.date.fromisoformat(s).strftime("%b %-d, %Y")
usd = lambda v: ("−$" if v < 0 else "$") + f"{abs(v):,.0f}"
pc = lambda v, dd=1: (f"{v*100:+.{dd}f}%").replace("-", "−")
spyv = [24000 * (1 + x["ret"]) for x in spy]
peak, sdd = 0, 0
for x in spyv:
    peak = max(peak, x); sdd = min(sdd, x / peak - 1)
half = w["half_split"]
spy_h1 = next(x["ret"] for x in spy if x["date"] == half)
spy_h2 = (1 + spy_ret) / (1 + spy_h1) - 1
top10_share = sum(sorted((t["pnl"] for t in detail[BEST]), reverse=True)[:10]) / sum(t["pnl"] for t in detail[BEST])

CSS = CSS3M + r"""
tr.best td{background:var(--hi)}td.k{font-weight:600}
.verdict{border-left:4px solid var(--ok);background:var(--panel);border-radius:6px;padding:12px 16px;display:flex;flex-direction:column;gap:6px}
.verdict.warn{border-left-color:var(--warn)}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:6px 18px}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const NS='http://www.w3.org/2000/svg',W=760;
const st={stop:'12%',filt:'skip earnings ahead',ctl:'controls',day:null,sort:{k:'buy_day',dir:-1},q:'',show:'all',sel:null,vsort:{k:'pnl',dir:-1}};
const key=()=>`${st.stop} | ${st.filt} | after | ${st.ctl}`;
const VER=k=>D.versions.find(v=>v.key===k), V=()=>VER(key()), TR=()=>D.detail[key()]||[], CA=()=>D.cands[key()]||[];
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
const spyMap=Object.fromEntries(D.spy);

// ---- comparison table of all 32 versions
const VC=[['selection','Pick','t',v=>v==='after'?'Top 4 after removal':'First 10, then remove'],['earnings','Earnings','t',v=>v==='all unexplained'?'Skip same-day':'Also skip next 10 days'],['stop','Stop','t'],['controls','Risk controls','t',v=>v==='controls'?'Yes (cap 24)':'No'],
 ['trades','Trades',''],['win_rate','Winners','',v=>P(v,0,false)],['pnl','Total P&L','',USD],['realized','Closed','',USD],['open_pnl','Open','',USD],['max_dd_usd','Worst drawdown','',USD],['peak_open','Peak capital','',v=>'$'+(v*1000).toLocaleString()],['return_on_peak_capital','P&L / peak capital','',v=>P(v)],['h1_pnl','1st half','',USD],['h2_pnl','2nd half','',USD],['months_up','Months up','',(v,r)=>`${v} of ${r.months}`]];
function vtable(){const th=document.getElementById('v-head');th.innerHTML='';const {k,dir}=st.vsort;
 VC.forEach(([c,l,cc])=>{const e=h('th',l+(k===c?(dir>0?' ▲':' ▼'):''),cc);e.setAttribute('aria-sort',k===c?(dir>0?'ascending':'descending'):'none');e.addEventListener('click',()=>{st.vsort={k:c,dir:k===c?-dir:-1};vtable()});th.append(e)});
 const rows=D.versions.slice().sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*dir);const tb=document.getElementById('v-body');tb.innerHTML='';
 for(const r of rows){const tr=h('tr');if(r.key===D.best)tr.className='best';
  VC.forEach(([c,l,cc,f])=>{const v=r[c];const td=h('td',f?f(v,r):String(v),cc);if(['pnl','realized','open_pnl','h1_pnl','h2_pnl','return_on_peak_capital'].includes(c))td.classList.add(cls(v));tr.append(td)});
  if(r.selection==='after'&&(r.stop==='8%'||r.stop==='12%')){tr.title='Click to show this version below';tr.addEventListener('click',()=>{st.stop=r.stop;st.filt=r.earnings;st.ctl=r.controls;syncSeg();render();document.getElementById('s-sel').scrollIntoView({behavior:'smooth'})})}else tr.style.cursor='default';
  tb.append(tr)}}

function tiles(){const s=V(),box=document.getElementById('tiles');box.innerHTML='';const spy=D.spy[D.spy.length-1][1],cap=s.peak_open*1000;
 const items=[['Trades',s.trades,`${s.open} still open`],['Winning trades',P(s.win_rate,1,false),`closed only: ${P(s.closed_win_rate,1,false)}`],
  ['Total profit/loss',USD(s.pnl),`closed ${USD(s.realized)} + open ${USD(s.open_pnl)}`,cls(s.pnl)],['Return on peak capital',P(s.return_on_peak_capital),`peak $${cap.toLocaleString()} in use`,cls(s.pnl)],
  ['Average win / loss',`${P(s.avg_win,0)} / ${P(s.avg_loss,0)}`,`average trade ${P(s.avg,2)}`],['Worst drawdown',USD(s.max_dd_usd),`${P(s.max_dd_usd/cap)} of peak capital`,'neg'],
  ['Months up',`${s.months_up} of ${s.months}`,`halves: ${USD(s.h1_pnl)} / ${USD(s.h2_pnl)}`],['SPY on same capital',USD(cap*spy),`${P(spy)} over the year`,cls(spy)]];
 for(const [l,v,sub,c] of items){const t=h('div',null,'tile');t.append(h('span',l,'l'),h('span',String(v),'v '+(c||'')),h('span',sub,'s'));box.append(t)}}

function pnlChart(){const s=V(),dl=s.daily,H=320,g=svg('c-pnl',H),L=64,R=W-10,T=12,B=H-62,B2=H-22,cap=s.peak_open*1000;
 const spyL=dl.map(x=>cap*(spyMap[x[0]]??0));const vals=dl.flatMap(x=>[x[1],x[2]]).concat(spyL);const lo=Math.min(0,...vals),hi=Math.max(0,...vals);const tk=ticks(lo,hi,5);
 const y=lin(Math.min(lo,tk[0]),Math.max(hi,tk[tk.length-1]),B,T),x=lin(0,dl.length-1,L,R);
 for(const t of tk){el('line',{x1:L,x2:R,y1:y(t),y2:y(t),class:'grid'},g);tx(g,L-6,y(t)+4,USD(t),{'text-anchor':'end'})}
 el('line',{x1:L,x2:R,y1:y(0),y2:y(0),class:'axis'},g);
 const mo=Math.max(...dl.map(q=>q[3]))||1,yb=lin(0,mo,B2,B+12),bw=(R-L)/dl.length;
 dl.forEach((q,i)=>{el('rect',{x:x(i)-bw/2,width:Math.max(0.6,bw-0.2),y:yb(q[3]),height:B2-yb(q[3]),fill:'var(--mute)',opacity:.55},g)});
 tx(g,L-6,yb(mo)+4,String(mo),{'text-anchor':'end'});tx(g,R,B+8,'Grey bars: open positions',{'text-anchor':'end'});
 let lm='';dl.forEach((q,i)=>{const m=q[0].slice(0,7);if(m!==lm){lm=m;if(i<dl.length-8)tx(g,x(i),B2+14,new Date(q[0]+'T12:00').toLocaleString('en-US',{month:'short'}))}});
 const line=(arr,c,wd,dash)=>el('path',{d:'M'+arr.map((v,i)=>x(i).toFixed(1)+','+y(v).toFixed(1)).join('L'),fill:'none',stroke:c,'stroke-width':wd,'stroke-dasharray':dash||'none','stroke-linejoin':'round'},g);
 line(spyL,'var(--mute)',1.6,'4 3');line(dl.map(q=>q[2]),'var(--c1)',1.5);line(dl.map(q=>q[1]),'var(--c0)',2.2);
 const ov=el('g',{},g);dl.forEach((q,i)=>{const r=el('rect',{x:x(i)-bw/2,width:bw,y:T,height:B2-T,fill:'transparent',style:'cursor:pointer'},ov);tip(r,`${q[0]}\nTotal ${USD(q[1])} (closed ${USD(q[2])})\nSPY on same capital ${USD(spyL[i])}\n${q[3]} open`);r.addEventListener('click',()=>{st.day=q[0];dayView()})});
 tx(g,R-2,y(dl[dl.length-1][1])-6,USD(dl[dl.length-1][1]),{'text-anchor':'end',class:'st'})}

function monthly(){const tr=TR(),m={};for(const t of tr){const k=t.buy_day.slice(0,7);m[k]=m[k]||{n:0,w:0,p:0};m[k].n++;if(t.ret>0)m[k].w++;m[k].p+=t.pnl}
 const dl=V().daily,mm={};dl.forEach(q=>{mm[q[0].slice(0,7)]=q[1]});let prev=0;const chg={};for(const k of Object.keys(mm).sort()){chg[k]=mm[k]-prev;prev=mm[k]}
 const tb=document.getElementById('t-month');tb.innerHTML='';for(const k of Object.keys(chg).sort()){const r=m[k]||{n:0,w:0,p:0},tr_=h('tr');
  tr_.append(h('td',new Date(k+'-15T12:00').toLocaleString('en-US',{month:'short',year:'numeric'}),'t'),h('td',USD(chg[k]),cls(chg[k])),h('td',r.n),h('td',r.n?P(r.w/r.n,0,false):'–'),h('td',USD(r.p),cls(r.p)));tb.append(tr_)}}

function dayList(){const all=[...new Set([...V().daily.map(q=>q[0]),...CA().map(c=>c.drop_day)])].sort();const sel=document.getElementById('day');const cur=st.day||all[all.length-1];sel.innerHTML='';
 for(const d of all){const o=h('option',new Date(d+'T12:00').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',year:'2-digit'}));o.value=d;sel.append(o)}sel.value=all.includes(cur)?cur:all[all.length-1];st.day=sel.value;return all}
function markOn(t,d){const i=D.dates.indexOf(d)-t.i0;return i>=0&&i<t.marks.length?t.marks[i]:null}
function dayView(){const all=dayList(),d=st.day,tr=TR();const cand=CA().filter(c=>c.drop_day===d);
 const buys=tr.filter(t=>t.buy_day===d),sells=tr.filter(t=>t.exit!=='open'&&t.sell_day===d),open=tr.filter(t=>t.buy_day<=d&&(t.exit==='open'||t.sell_day>d));
 const c1=document.getElementById('d-cand');c1.innerHTML='';if(!cand.length)c1.append(h('p','Not a drop day in this window, or no losers down 2%+.','muted small'));
 else{const t=h('table');t.innerHTML='<thead><tr><th class="t">#</th><th class="t">Stock</th><th>Fell</th><th class="t">Decision</th></tr></thead>';const b=h('tbody');
  for(const c of cand){const r=h('tr');r.append(h('td',c.rank,'t'),h('td',c.ticker,'t'),h('td',P(c.drop),'neg'),h('td',c.picked?'Bought next open':'Skipped: '+c.excluded,'t '+(c.picked?'pos':'muted')));b.append(r)}t.append(b);c1.append(t)}
 const list=(id,arr,f)=>{const e=document.getElementById(id);e.innerHTML='';if(!arr.length){e.append(h('p','None','muted small'));return}const u=h('ul');arr.forEach(t=>{const li=h('li');li.innerHTML=f(t);li.style.cursor='pointer';li.addEventListener('click',()=>pick(t));u.append(li)});e.append(u)};
 list('d-buy',buys,t=>`<b>${t.ticker}</b> at $${t.buy.toFixed(2)} <span class="muted">(fell ${P(t.drop)} on ${t.drop_day})</span>`);
 list('d-sell',sells,t=>`<b>${t.ticker}</b> at $${t.sell.toFixed(2)} <span class="${cls(t.ret)}">${P(t.ret)}</span> <span class="muted">after ${t.days}d</span>`);
 list('d-open',open,t=>{const v=markOn(t,d);return `<b>${t.ticker}</b> since ${t.buy_day} <span class="${cls(v-1)}">${v?P(v-1):''}</span>`});
 const i=all.indexOf(d);document.getElementById('prev').disabled=i<=0;document.getElementById('next').disabled=i>=all.length-1}

const COLS=[['ticker','Stock','t'],['sector','Sector','t'],['drop_day','Drop day','t'],['drop','Fell',''],['buy_day','Bought','t'],['buy','Buy $',''],['sell_day','Sold / marked','t'],['sell','Sell $',''],['days','Days',''],['ret','Return',''],['pnl','P&L $','']];
function table(){const tr=TR().filter(t=>(st.show==='all'||(st.show==='open'?t.exit==='open':st.show==='closed'?t.exit!=='open':t.earnings_in_hold))&&(!st.q||t.ticker.includes(st.q.toUpperCase())));
 const {k,dir}=st.sort;tr.sort((a,b)=>(a[k]>b[k]?1:a[k]<b[k]?-1:0)*dir);const th=document.getElementById('t-head');th.innerHTML='';
 COLS.forEach(([c,l,cc])=>{const e=h('th',l+(k===c?(dir>0?' ▲':' ▼'):''),cc);e.setAttribute('aria-sort',k===c?(dir>0?'ascending':'descending'):'none');e.addEventListener('click',()=>{st.sort={k:c,dir:k===c?-dir:(c==='ticker'||c.endsWith('day')||c==='sector'?1:-1)};table()});th.append(e)});
 const tb=document.getElementById('t-body');tb.innerHTML='';
 for(const t of tr){const r=h('tr');if(st.sel&&st.sel.ticker===t.ticker&&st.sel.buy_day===t.buy_day)r.className='sel';const tc=h('td',t.ticker,'t');if(t.earnings_in_hold)tc.append(h('span','E','tag e'));if(t.exit==='open')tc.append(h('span','open','tag o'));
  r.append(tc,h('td',t.sector,'t muted'),h('td',t.drop_day,'t'),h('td',P(t.drop),'neg'),h('td',t.buy_day,'t'),h('td',t.buy.toFixed(2)),h('td',t.sell_day,'t'),h('td',t.sell.toFixed(2)),h('td',t.days),h('td',P(t.ret,2),cls(t.ret)),h('td',USD(t.pnl),cls(t.pnl)));r.addEventListener('click',()=>pick(t));tb.append(r)}
 document.getElementById('t-count').textContent=`${tr.length} trades shown`}

function pick(t){if(!t)return;st.sel=t;table();const H=230,g=svg('c-trade',H),L=50,R=W-10,T=14,B=H-26;const p=t.marks.length?t.marks:[1];const trail=parseFloat(st.stop)/100;
 let hw=1;const stop=p.map(v=>{const sv=hw*(1-trail);hw=Math.max(hw,v);return sv});const vals=p.concat(stop);const tk=ticks(Math.min(...vals)*0.99,Math.max(...vals)*1.01,5);
 const y=lin(tk[0],tk[tk.length-1],B,T),x=lin(0,Math.max(1,p.length-1),L+10,R-10);
 for(const v of tk){el('line',{x1:L,x2:R,y1:y(v),y2:y(v),class:'grid'},g);tx(g,L-6,y(v)+4,P(v-1,0),{'text-anchor':'end'})}el('line',{x1:L,x2:R,y1:y(1),y2:y(1),class:'axis'},g);
 el('path',{d:'M'+stop.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--bad)','stroke-dasharray':'5 4','stroke-width':1.5},g);
 el('path',{d:'M'+p.map((v,i)=>x(i)+','+y(v)).join('L'),fill:'none',stroke:'var(--c0)','stroke-width':2.2},g);
 p.forEach((v,i)=>{const c=el('circle',{cx:x(i),cy:y(v),r:p.length>60?1.5:3,fill:'var(--c0)'},g);tip(c,`${D.dates[t.i0+i]}: close ${P(v-1)} vs entry; stop ${P(stop[i]-1)}`)});
 tx(g,L+10,H-6,t.buy_day);tx(g,R-10,H-6,t.sell_day,{'text-anchor':'end'});
 document.getElementById('trade-title').textContent=`${t.ticker}: bought ${t.buy_day} at $${t.buy.toFixed(2)}, ${t.exit==='open'?'still open, marked':'sold'} ${t.sell_day} at $${t.sell.toFixed(2)} (${P(t.ret,2)}, ${USD(t.pnl)})${t.earnings_in_hold?' · reported earnings during the hold':''}`}

function syncSeg(){document.querySelectorAll('[data-stop]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.stop===st.stop)));document.querySelectorAll('[data-filt]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filt===st.filt)));document.querySelectorAll('[data-ctl]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.ctl===st.ctl)))}
function render(){document.getElementById('sel-name').textContent=`${st.stop} trailing stop · ${st.filt==='all unexplained'?'skip same-day earnings':'also skip stocks reporting in the next 10 days'} · ${st.ctl==='controls'?'risk controls on (max 24 positions)':'no risk controls'}${key()===D.best?' (recommended version)':''}`;
 tiles();pnlChart();monthly();dayView();table();const tr=TR();pick(st.sel&&tr.find(t=>t.ticker===st.sel.ticker&&t.buy_day===st.sel.buy_day)||tr.slice().sort((a,b)=>b.ret-a.ret)[0])}
function seg(attr,k){const bs=document.querySelectorAll(`[${attr}]`);bs.forEach(b=>b.addEventListener('click',()=>{st[k]=b.getAttribute(attr);syncSeg();render()}))}
seg('data-stop','stop');seg('data-filt','filt');seg('data-ctl','ctl');
document.querySelectorAll('[data-show]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-show]').forEach(o=>o.setAttribute('aria-pressed',String(o===b)));st.show=b.dataset.show;table()}));
document.getElementById('day').addEventListener('change',e=>{st.day=e.target.value;dayView()});
document.getElementById('prev').addEventListener('click',()=>{const a=dayList(),i=a.indexOf(st.day);if(i>0){st.day=a[i-1];dayView()}});
document.getElementById('next').addEventListener('click',()=>{const a=dayList(),i=a.indexOf(st.day);if(i<a.length-1){st.day=a[i+1];dayView()}});
document.getElementById('q').addEventListener('input',e=>{st.q=e.target.value.trim();table()});
vtable();syncSeg();render();
"""

body = f"""
<div class="wrap">
<header>
  <h1>Top-4 unexplained losers: one-year test</h1>
  <p class="lede">Every trading day from {nice(w['first_drop_day'])} to {nice(w['last_drop_day'])} ({w['drop_days']} days): rank the S&amp;P 500 losers (down 2%+, price $20+, 1M+ shares), skip the ones with an obvious reason (earnings that day or the evening before, or an 8%+ gap down at the open), buy the 4 biggest remaining losers at the next open, $1,000 each, and sell only by trailing stop. 32 versions compared; open positions valued at the close of {nice(w['marked_at'])}.</p>
</header>

<section aria-labelledby="s-best"><h2 id="s-best">Which version is best</h2>
  <div class="verdict">
    <p><b>Best version you could actually run: 12% trailing stop, top 4 after removing explained, also skip stocks reporting in the next 10 days, with risk controls</b> (at most 24 open positions, at most 2 new buys per sector per day, no re-buying a stock within 10 days of a stop-out).</p>
    <div class="kv small">
      <span>Total profit/loss: <b class="pos">{usd(best['pnl'])}</b> on $24,000 of peak capital ({pc(best['return_on_peak_capital'])})</span>
      <span>SPY on the same $24,000: <b>{usd(24000*spy_ret)}</b> ({pc(spy_ret)})</span>
      <span>Worst drawdown: <b class="neg">{usd(best['max_dd_usd'])}</b> ({pc(best['max_dd_usd']/24000)}); SPY: {pc(sdd)}</span>
      <span>Both halves positive: {usd(best['h1_pnl'])} and {usd(best['h2_pnl'])} (SPY {pc(spy_h1)} and {pc(spy_h2)})</span>
      <span>Months up: {best['months_up']} of {best['months']}; winning trades {pc(best['win_rate'],0).replace('+','')}</span>
      <span>Average win {pc(best['avg_win'],0)} vs average loss {pc(best['avg_loss'],0)}</span>
    </div>
  </div>
  <div class="verdict warn small"><p><b>Why not trade it yet.</b> It was the best of 32 versions on one year, which flatters it. {round(top10_share*100)}% of its profit came from just 10 of its {best['trades']} trades (MU +119%, LITE +105%, VLO +76%), so missing a couple of big winners would erase most of the edge. Picks lean heavily to tech, and this was a rising market (SPY {pc(spy_ret)}). A wider stop in a bull year mostly means more time invested. The 20-year test of the same idea with an 8% stop (test 8) roughly tracked the market, and random picks did about as well. Next step: pre-register this exact version and test it over 20 years, then paper-trade it.</p></div>
  <div class="card small"><h3>What the 32 versions show</h3><ul>
    <li><b>Wider stops win every time:</b> 12% beats 8%, which beats 5%; no 3% version made money. Tight stops sell the rebound before it happens.</li>
    <li><b>"Top 4 after removing explained" beats "first 10, then remove"</b> in most matched pairs, because news-heavy days no longer crowd out clean candidates.</li>
    <li><b>Skipping upcoming earnings helps</b> with the 12% stop and controls (+$7,821 vs +$6,982), and costs little elsewhere.</li>
    <li><b>Without risk controls the dollar totals look huge</b> (up to +$26,513) but need up to 155 open positions ($155,000), and drawdowns reach about $9,800.</li>
  </ul></div>
</section>

<section aria-labelledby="s-cmp"><h2 id="s-cmp">All 32 versions</h2>
  <div class="card"><p class="small muted">Click a column to sort. The highlighted row is the recommended version. Rows with "Top 4 after removal" and an 8% or 12% stop open in the detail below when clicked.</p>
  <div class="tw"><table><thead><tr id="v-head"></tr></thead><tbody id="v-body"></tbody></table></div></div>
</section>

<div class="bar" role="toolbar" aria-label="Version shown below" id="s-sel">
  <div class="ctl" role="group" aria-label="Trailing stop"><span>Stop</span><button class="seg" type="button" data-stop="12%">12%</button><button class="seg" type="button" data-stop="8%">8%</button></div>
  <div class="ctl" role="group" aria-label="Earnings"><span>Earnings</span><button class="seg" type="button" data-filt="skip earnings ahead">Also skip next 10 days</button><button class="seg" type="button" data-filt="all unexplained">Skip same-day only</button></div>
  <div class="ctl" role="group" aria-label="Risk controls"><span>Risk controls</span><button class="seg" type="button" data-ctl="controls">On (max 24)</button><button class="seg" type="button" data-ctl="no controls">Off</button></div>
</div>
<p class="small muted" id="sel-name"></p>

<section aria-labelledby="s-res"><h2 id="s-res">Results for this version</h2><div class="tiles" id="tiles"></div>
  <div class="card"><h3>Profit/loss over the year</h3><p class="small muted">Total (closed plus open positions at each close), closed trades only, and SPY bought with the same peak capital. Click a day to open it below.</p>
  <div class="legend"><span><i style="background:var(--c0)"></i>Total P&amp;L</span><span><i style="background:var(--c1)"></i>Closed trades</span><span><i style="background:var(--mute)"></i>SPY on same capital (dashed) / open positions (bars)</span></div>
  <div class="chart" id="c-pnl"></div></div>
  <div class="card"><h3>By month</h3><div class="tw"><table><thead><tr><th class="t">Month</th><th>P&amp;L change</th><th>Trades bought</th><th>Winners</th><th>P&amp;L of those trades</th></tr></thead><tbody id="t-month"></tbody></table></div></div>
</section>

<section aria-labelledby="s-day"><h2 id="s-day">Day by day</h2>
  <div class="daynav"><button class="seg" type="button" id="prev" aria-label="Previous day">◀</button><select id="day" aria-label="Choose a day"></select><button class="seg" type="button" id="next" aria-label="Next day">▶</button><span class="small muted">Losers checked that day, in order (buys happen the next morning).</span></div>
  <div class="cols3"><div class="card"><h3>Losers checked</h3><div class="tw" id="d-cand"></div></div>
    <div class="card"><h3>Bought at the open</h3><div id="d-buy"></div><h3 style="margin-top:8px">Sold</h3><div id="d-sell"></div></div>
    <div class="card"><h3>Open at the close</h3><div id="d-open" class="small tw"></div></div></div>
</section>

<section aria-labelledby="s-tr"><h2 id="s-tr">Every trade</h2>
  <div class="card"><div class="daynav"><input type="search" id="q" placeholder="Find a ticker" aria-label="Find a ticker">
    <div class="ctl" role="group" aria-label="Show"><span>Show</span><button class="seg" type="button" data-show="all" aria-pressed="true">All</button><button class="seg" type="button" data-show="closed" aria-pressed="false">Closed</button><button class="seg" type="button" data-show="open" aria-pressed="false">Open</button><button class="seg" type="button" data-show="earn" aria-pressed="false">Held through earnings</button></div>
    <span class="small muted" id="t-count"></span></div>
    <div class="tw"><table><thead><tr id="t-head"></tr></thead><tbody id="t-body"></tbody></table></div>
    <p class="small muted">Click a column to sort, a row to see its price path. <span class="tag e">E</span> = reported earnings during the hold.</p></div>
  <div class="card"><h3 id="trade-title"></h3><div class="legend"><span><i style="background:var(--c0)"></i>Close vs entry</span><span><i style="background:var(--bad)"></i>Trailing stop</span></div><div class="chart" id="c-trade"></div></div>
</section>

<section aria-labelledby="s-how"><h2 id="s-how">How it was calculated</h2>
  <div class="card small"><ul>
    <li>Prices and earnings dates: Yahoo Finance (daily bars; returns split/dividend adjusted). Universe: current S&amp;P 500 members, so stocks removed from the index during the year are missing.</li>
    <li>Trailing stop: highest close since entry (or the entry price) × (1 − stop). Opens below the stop → sold at the open; day's low touches it → sold at the stop. After-hours moves are not included.</li>
    <li>Costs: 0.05% per side plus 0.10% extra on stop sales; $1,000 per trade.</li>
    <li>Risk controls: at most 24 open positions; at most 2 new buys per sector per day; no buying a stock already held or stopped out in the last 10 trading days; when a candidate is skipped the next unexplained loser is checked.</li>
    <li>Halves split after {nice(half)}. Not pre-registered; no trades were sent. Built by <code>research/top4_trailing/live_1y/ledger_1y.py</code> and <code>build_report.py</code>. Research only, not financial advice.</li>
  </ul></div>
</section>
</div>
"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Top-4 Losers One-Year Test</title><style>{CSS}</style></head><body>{body}
<script id="data" type="application/json">{json.dumps(pack, separators=(',', ':')).replace('</', '<\\/')}</script>
<script>{JS}</script></body></html>"""
(HERE / "report.html").write_text(page, encoding="utf-8")
print(f"wrote {HERE / 'report.html'} ({(HERE / 'report.html').stat().st_size / 1024:.0f} KB)")
