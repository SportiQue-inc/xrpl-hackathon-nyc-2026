/* Pure views of recorded cohort data. No generated outcomes or client-side polling. */
(function () {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const fmt = value => new Intl.NumberFormat('en', {maximumFractionDigits:6}).format(value);
  const agents = D => Array.isArray(D?.agents) ? D.agents : [];
  const period = D => {
    const start = number(D?.start) ?? 0;
    return [start, Math.max(start + 1, number(D?.end) ?? start + 1)];
  };
  function receipts(a, D, asset) {
    const [start, end] = period(D);
    return (Array.isArray(a.receipts) ? a.receipts : []).filter(r =>
      r.asset === asset && number(r.amount) !== null && number(r.at) !== null &&
      Number(r.at) >= start && Number(r.at) <= end
    ).map(r => ({at:Number(r.at), amount:Number(r.amount)})).sort((a,b) => a.at-b.at);
  }
  const total = rows => rows.reduce((sum, r) => sum+r.amount, 0);
  function heatColor(value, max) {
    const v = number(value) ?? 0, top = number(max) ?? 0;
    const t = top > 0 ? Math.max(0, Math.min(1, v/top)) : 0;
    return 'rgb(' + [83-72*t,104-22*t,94-38*t].map(Math.round).join(',') + ')';
  }
  function range(values) {
    const low = Math.min(0, ...values), high = Math.max(0, ...values);
    const raw = (high-low || 1)/4, power = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1,2,2.5,5,10].find(v => v*power >= raw)*power;
    const min = Math.floor(low/step)*step, max = Math.ceil(high/step)*step || step*4;
    const ticks = [];
    for (let v=min; v<=max+step/100; v+=step) ticks.push(Math.abs(v)<step/100 ? 0 : v);
    return {min,max,ticks};
  }
  const box = {W:720,H:300,L:68,R:24,T:25,B:65};
  function frame(yRange, xTicks, asset) {
    const {W,H,L,R,T,B} = box, right=W-R, bottom=H-B;
    const y = v => bottom-(v-yRange.min)/(yRange.max-yRange.min)*(bottom-T);
    return yRange.ticks.map(v => '<g class="dv-tick"><path d="M'+L+','+y(v)+'H'+right+'"/><text x="'+(L-11)+'" y="'+(y(v)+4)+'" text-anchor="end">'+fmt(v)+'</text></g>').join('') +
      '<path class="dv-axis" d="M'+L+','+T+'V'+bottom+'H'+right+'"/>' +
      xTicks.map(t => '<g class="dv-tick"><path d="M'+t.x+','+T+'V'+bottom+'"/><text x="'+t.x+'" y="'+(bottom+23)+'" text-anchor="'+(t.anchor||'middle')+'">'+esc(t.label)+'</text></g>').join('') +
      '<text class="dv-unit" x="'+L+'" y="13">'+esc(asset||'Recorded receipts')+'</text>';
  }
  function quantile(sorted, p) {
    const n=(sorted.length-1)*p, lo=Math.floor(n), hi=Math.ceil(n);
    return sorted[lo]+(sorted[hi]-sorted[lo])*(n-lo);
  }
  function timeLabel(t, D) {
    const [start,end]=period(D);
    if (D.mode === 'synthetic' && end-start >= 7*86400) return 'Week '+Math.max(1,Math.ceil((t-start)/(7*86400)));
    return new Date(t*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  }
  function incomeChart(D, selected, asset) {
    const cohort=agents(D);
    if (!cohort.length) return '<p class="dv-empty">No recorded participants for this period.</p>';
    const [start,end]=period(D), rows=cohort.map(a => ({a, r:receipts(a,D,asset)}));
    const times=[...new Set([start,end,...rows.flatMap(s=>s.r.map(r=>r.at))])].sort((a,b)=>a-b);
    const series=rows.map(s => {
      let sum=0, cursor=0;
      return {...s, values:times.map(t => {while(cursor<s.r.length && s.r[cursor].at<=t)sum+=s.r[cursor++].amount;return sum;})};
    });
    const bands=times.map((t,i) => {
      const values=series.map(s=>s.values[i]).sort((a,b)=>a-b);
      return {lo:quantile(values,.25),median:quantile(values,.5),hi:quantile(values,.75)};
    });
    const chosen=series.find(s=>s.a.id===selected);
    const yr=range([...bands.flatMap(b=>[b.lo,b.hi]),...(chosen?.values||[])]);
    const {W,H,L,R,T,B}=box, bottom=H-B;
    const x=t=>L+(t-start)/(end-start)*(W-L-R), y=v=>bottom-(v-yr.min)/(yr.max-yr.min)*(bottom-T);
    const stepPath=values => values.map((v,i) => i ? 'H'+x(times[i]).toFixed(2)+'V'+y(v).toFixed(2) : 'M'+x(times[0]).toFixed(2)+','+y(v).toFixed(2)).join('');
    const lower=bands.map(b=>b.lo), upper=bands.map(b=>b.hi);
    let band=stepPath(upper)+'L'+x(end).toFixed(2)+','+y(lower.at(-1)).toFixed(2);
    for(let i=times.length-2;i>=0;i--)band+='V'+y(lower[i]).toFixed(2)+'H'+x(times[i]).toFixed(2);
    band+='Z';
    const ticks=[0,1/3,2/3,1].map((v,i)=>({x:x(start+(end-start)*v),label:timeLabel(start+(end-start)*v,D),anchor:i===0?'start':i===3?'end':'middle'}));
    const selectedLabel=chosen ? esc(chosen.a.name)+' · '+fmt(total(chosen.r))+' '+esc(asset) : 'Choose an agent';
    return '<div class="dv-chart"><div class="dv-chart-key"><span><i class="dv-band-key"></i>25–75% of participants</span><span><i class="dv-median-key"></i>Median</span><span><i class="dv-selected-key"></i>Selected</span></div>' +
      '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc('Cumulative recorded receipts in '+asset+'. Median, 25 to 75 percent band and selected participant.')+'">' +
      frame(yr,ticks,asset)+'<path class="dv-band" d="'+band+'"/><path class="dv-median" d="'+stepPath(bands.map(b=>b.median))+'"/>'+
      (chosen?'<path class="dv-selected-line" d="'+stepPath(chosen.values)+'"/><circle class="dv-selected-end" cx="'+x(end)+'" cy="'+y(chosen.values.at(-1))+'" r="4"/>':'')+
      '<text class="dv-x-title" x="'+L+'" y="'+(H-13)+'">Same observation window · steps follow recorded receipt times</text></svg>'+
      '<div class="dv-chart-caption"><b>'+selectedLabel+'</b><span>'+cohort.length+' participants · '+rows.reduce((n,s)=>n+s.r.length,0)+' receipts in this asset</span></div></div>';
  }
  function settingsChart(D, selected, asset) {
    const points=agents(D).filter(a=>number(a.floor_ratio)!==null).map(a=>({a,x:Number(a.floor_ratio),r:receipts(a,D,asset)}));
    if(!points.length)return '<p class="dv-empty">No recorded settings for this period.</p>';
    const xs=points.map(p=>p.x), lo=Math.min(...xs), hi=Math.max(...xs), pad=(hi-lo || Math.max(.1,Math.abs(lo)*.2))*.12;
    const min=lo-pad, max=hi+pad, yr=range(points.map(p=>total(p.r)));
    const {W,H,L,R,T,B}=box, bottom=H-B;
    const x=v=>L+(v-min)/(max-min)*(W-L-R), y=v=>bottom-(v-yr.min)/(yr.max-yr.min)*(bottom-T);
    const ticks=[0,.25,.5,.75,1].map((v,i)=>({x:L+v*(W-L-R),label:fmt((min+v*(max-min))*100)+'%',anchor:i===0?'start':i===4?'end':'middle'}));
    const groups=new Map();
    for(const p of points){const k=p.x+':'+total(p.r);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(p);}
    const circles=[...groups.values()].sort((a,b)=>Number(a.some(p=>p.a.id===selected))-Number(b.some(p=>p.a.id===selected))).map(group=>{
      const first=group[0], sum=total(first.r), count=group.reduce((n,p)=>n+p.r.length,0), active=group.some(p=>p.a.id===selected);
      const tooltip=group.map(p=>p.a.name+' · minimum '+fmt(p.x*100)+'% · '+fmt(sum)+' '+asset+' · '+p.r.length+' receipts · '+(p.a.approval==='ask'?'owner approval':'owner rules')).join('\n');
      const radius=Math.min(12,4+Math.sqrt(count)*1.4);
      return '<g class="dv-point'+(active?' dv-point-selected':'')+'" tabindex="0" role="img" aria-label="'+esc(tooltip)+'"><title>'+esc(tooltip)+'</title><circle cx="'+x(first.x)+'" cy="'+y(sum)+'" r="'+radius+'"/>'+
        (group.length>1?'<text x="'+x(first.x)+'" y="'+(y(sum)+3.5)+'" text-anchor="middle">'+group.length+'</text>':'')+'</g>';
    }).join('');
    return '<div class="dv-chart"><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Actual minimum price settings and observed receipts">'+frame(yr,ticks,asset)+circles+
      '<text class="dv-x-title" x="'+L+'" y="'+(H-13)+'">Minimum price as % of starting price · actual observed range</text></svg>'+
      '<p class="dv-chart-caption">Range: '+fmt(lo*100)+'%–'+fmt(hi*100)+'%. Coincident points are grouped; no position jitter. Circle size shows receipt count.</p></div>';
  }
  const statusClass=status=>status==='settled'?'settled':['rejected','refunded','cancelled','canceled'].includes(status)?'rejected':['negotiating','settling','awaiting buyer','awaiting seller','pending'].includes(status)?'pending':'recorded';
  const sourceLabel=source=>!source?'Source not recorded':source==='rules'?'Written rules':'Model: '+source;
  function network(D, selected) {
    const cohort=agents(D).slice().sort((a,b)=>String(a.id).localeCompare(String(b.id)));
    if(!cohort.length)return '<p class="dv-empty">Waiting for recorded participants and activity.</p>';
    const activity=(Array.isArray(D.activity)?D.activity:[]).slice().sort((a,b)=>(number(b.created)??0)-(number(a.created)??0)).slice(0,6);
    const known=new Map(cohort.map(a=>[a.id,a]));
    const participant=e=>known.has(e.seller)?e.seller:known.has(e.buyer)?e.buyer:null;
    const other=e=>participant(e)===e.seller?e.buyer:e.seller;
    const external=[...new Set(activity.filter(participant).map(other).filter(Boolean))].sort().slice(0,8);
    const W=960, rows=Math.max(1,Math.ceil(cohort.length/5)), H=Math.max(450,rows*34+90,external.length*44+85), mid=H/2;
    const positions=new Map(cohort.map((a,i)=>[a.id,{x:38+(i%5)*65,y:63+Math.floor(i/5)*34}]));
    const counterpartPositions=new Map(external.map((id,i)=>[id,{x:790,y:65+i*44}]));
    const label=id=>known.get(id)?.name||String(id||'Unknown counterparty');
    const connections=activity.map((e,i)=>{
      const a=positions.get(participant(e)),b=counterpartPositions.get(other(e));
      if(!a||!b)return '';
      const center=480, bend=80, state=statusClass(e.status), highlight=[e.buyer,e.seller].includes(selected);
      const path='M'+a.x+','+a.y+'C'+(a.x<center?a.x+bend:a.x-bend)+','+a.y+' '+center+','+(mid-45)+' '+center+','+mid+
        'C'+center+','+(mid+45)+' '+(b.x<center?b.x+bend:b.x-bend)+','+b.y+' '+b.x+','+b.y;
      return '<path class="dv-flow dv-flow-'+state+(highlight?' dv-flow-selected':'')+'" data-flow="'+esc(e.id+':'+state)+'" data-party="'+esc(participant(e))+'" data-other="'+esc(other(e))+'" style="--dv-order:'+i+'" d="'+path+'"><title>'+esc('C'+e.id+' · '+e.kind+' · '+e.status+' · '+sourceLabel(e.source))+'</title></path>';
    }).join('');
    const asset=D.default_asset||D.assets?.[0], totals=cohort.map(a=>total(receipts(a,D,asset))), top=Math.max(0,...totals);
    const nodes=cohort.map((a,i)=>{
      const p=positions.get(a.id), short=String(a.name||a.id).split(' ')[0].slice(0,10);
      return '<g class="dv-agent-node'+(a.id===selected?' dv-agent-selected':'')+'" tabindex="0" role="img" aria-label="'+esc(a.name+' · '+a.style)+'"><title>'+esc(a.name+' · '+a.style+' · '+fmt(totals[i])+' '+(asset||'recorded asset'))+'</title>'+
        '<circle cx="'+p.x+'" cy="'+p.y+'" r="8.5" fill="'+heatColor(totals[i],top)+'"/><text x="'+p.x+'" y="'+(p.y+21)+'" text-anchor="middle">'+esc(short)+'</text></g>';
    }).join('');
    const counterparties=external.map(id=>{const p=counterpartPositions.get(id),title=label(id);return '<g class="dv-counterparty" data-counterparty="'+esc(id)+'"><rect x="696" y="'+(p.y-15)+'" width="230" height="32" rx="9"/><text x="708" y="'+(p.y+5)+'">'+esc(title.length>30?title.slice(0,29)+'…':title)+'</text><title>'+esc(title)+'</title></g>';}).join('');
    const kindName=k=>({gps_track:'Running GPS tracks',sleep_log:'Sleep logs',purchase_receipts:'Purchase receipts',audio:'Voice clips',air:'Air quality'}[k]||k||'Data');
    const events=activity.map(e=>'<li data-flow="'+esc(e.id+':'+statusClass(e.status))+'"><span class="dv-event-dot dv-event-'+statusClass(e.status)+'"></span><div><b>'+esc(kindName(e.kind))+'</b><span>'+esc(e.status||'State not recorded')+' · C'+esc(e.id)+'</span></div><small>'+esc(sourceLabel(e.source))+'</small></li>').join('');
    return '<section class="dv-network"><div class="dv-network-head"><div><h3>Recorded agent activity</h3><p>'+cohort.length+' participants · signals → matching → counterparty</p></div><div class="dv-chart-key"><span><i class="dv-dot-amber"></i>Negotiating</span><span><i class="dv-dot-green"></i>Settled</span><span><i class="dv-dot-red"></i>Rejected / refunded</span></div></div>'+
      '<div class="dv-network-scroll"><svg class="dv-network-svg" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Recorded buyer and seller activity through market matching">'+connections+nodes+counterparties+
      '<g class="dv-market-node"><rect x="409" y="'+(mid-38)+'" width="142" height="76" rx="18"/><text x="480" y="'+(mid-8)+'" text-anchor="middle">Market</text><text class="dv-market-note" x="480" y="'+(mid+14)+'" text-anchor="middle">Matching only</text></g>'+
      '<text class="dv-network-label" x="28" y="25">Participant agents</text><text class="dv-network-label" x="696" y="25">Recorded counterparties</text></svg></div>'+
      (events?'<ul class="dv-events">'+events+'</ul>':'<p class="dv-empty">Waiting for a recorded negotiation. No activity is invented.</p>')+
      '<p class="dv-network-note">Only recorded events are drawn. Market matching does not imply custody of funds. Model names appear only when recorded as the message source.</p></section>';
  }
  window.DemoViz=Object.freeze({incomeChart,settingsChart,network,heatColor});
})();
