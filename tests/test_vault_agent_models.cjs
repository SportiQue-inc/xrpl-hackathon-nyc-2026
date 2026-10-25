const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {test}=require('node:test');
const base=path.resolve(__dirname,'../prototypes/data-vault-market/server/vaultmarket/static');

function settingsBrowser(){
 const nodes=new Map(),requests=[];
 const node=id=>{
  if(nodes.has(id))return nodes.get(id);
  const classes=new Set();
  const n={id,value:'',dataset:{},type:'',max:'',textContent:'',open:false,contains:()=>false,
   classList:{toggle(c,on){if(on===undefined)on=!classes.has(c);on?classes.add(c):classes.delete(c);},contains:c=>classes.has(c)}};
  nodes.set(id,n);
  if(id==='agents'){
   let html='';
   Object.defineProperty(n,'innerHTML',{get:()=>html,set:value=>{
    html=value;n.modes=[];n.chips=[];
    for(const [,attrs] of value.matchAll(/<input\b([^>]+)>/g)){
     const id=/\bid="([^"]+)"/.exec(attrs)?.[1];if(!id)continue;
     const r=node(id);r.value=/\bvalue="([^"]*)"/.exec(attrs)?.[1]||'';r.type=/\btype="([^"]*)"/.exec(attrs)?.[1]||'';r.max=/\bmax="([^"]*)"/.exec(attrs)?.[1]||'';r.dataset={};
    }
    for(const [,id,options] of value.matchAll(/<select\b[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g))node(id).value=/<option\b[^>]*value="([^"]*)"[^>]*\bselected\b/.exec(options)?.[1]||'';
    for(const [,attrs] of value.matchAll(/<button\b([^>]+)>/g)){
     const mode=/data-mode="([^"]*)"/.exec(attrs)?.[1],block=/data-block="([^"]*)"/.exec(attrs)?.[1];
     if(mode===undefined&&block===undefined)continue;
     const b=node(mode===undefined?'chip-'+block:'mode-'+mode);b.dataset=mode===undefined?{block}:{mode};b.classList.toggle('on',/class="[^"]*\bon\b/.test(attrs));(mode===undefined?n.chips:n.modes).push(b);
    }
   }});
   n.querySelectorAll=selector=>selector==='input[type=range]'?[...nodes.values()].filter(r=>r.type==='range'):selector==='.chip'?n.chips:selector==='.chip.on'?n.chips.filter(r=>r.classList.contains('on')):selector==='[data-mode]'?n.modes:[];
   n.querySelector=selector=>selector==='[data-mode].on'?n.modes.find(r=>r.classList.contains('on')):null;
  }
  return n;
 };
 const context=vm.createContext({document:{getElementById:node,activeElement:null},window:{addEventListener(){}},location:{pathname:'/'},console,
  fetch:async(url,opts={})=>{if(opts.body)requests.push({path:url,body:JSON.parse(opts.body)});return {ok:true,json:async()=>({ok:true,account:{}})};}});
 vm.runInContext(fs.readFileSync(path.join(base,'common.js'),'utf8'),context);
 const market=fs.readFileSync(path.join(base,'market.html'),'utf8');
 const start=market.indexOf('function renderAgents('),end=market.indexOf('\nasync function openContract',start);
 assert.ok(start>=0&&end>start,'Find the current modal settings implementation');
 vm.runInContext(market.slice(start,end),context);
 vm.runInContext(`META={models:['auto','allowed-a','allowed-b'],kinds:{sleep_log:{label:'Sleep',price:7},gps_track:{label:'GPS',price:10},step_count:{label:'Steps',price:3},commute:{label:'Commute',price:4},screen_time:{label:'Screen time',price:5},energy_use:{label:'Energy',price:6},audio:{label:'Audio',price:8},air:{label:'Air',price:4},purchase_receipts:{label:'Receipts',price:2},data_package:{label:'Mixed package'}},unit_xrp:1,asset:'test USD',ledger:'mock'};
  ME='u-owner';USER={user:{account:'u-owner'}};
  let ACC={account:{sell_agent:{mode:'ask',min:{sleep_log:7.123456},blocks:[],model:'allowed-a'},buy_agent:{auto_limit:41.234567,min_trust:.7,model:'allowed-b'}}};renderAgents();`,context);
 return {context,node,requests};
}

test('modal settings show independent requested models and submit both selected values',async()=>{
 const b=settingsBrowser(),html=b.node('agents').innerHTML;
 assert.match(html,/id="sellModel"[\s\S]*value="allowed-a" selected/);
 assert.match(html,/id="buyModel"[\s\S]*value="allowed-b" selected/);
 assert.match(html,/actual model or rules/i);
 b.node('sellModel').value='allowed-b';b.node('buyModel').value='auto';
 b.node('min-sleep_log').value='7';b.node('min-sleep_log').dataset.dirty='1';
 await b.node('save').onclick();
 assert.equal(b.requests.length,1);
 const body=b.requests[0].body;
 assert.equal(b.requests[0].path,'/api/account/u-owner/settings');
 assert.equal(body.sell_agent.model,'allowed-b');assert.equal(body.buy_agent.model,'auto');
 assert.equal(body.sell_agent.mode,'ask');assert.equal(body.sell_agent.min.sleep_log,7);
 assert.equal(body.buy_agent.auto_limit,41.234567);assert.equal(body.buy_agent.min_trust,.7);
 assert.equal(Object.keys(body.sell_agent.min).length,9);assert.ok(!('data_package' in body.sell_agent.min));
});

test('saving untouched fractional prices preserves exact values and excludes package presets',async()=>{
 const b=settingsBrowser(),html=b.node('agents').innerHTML;
 assert.match(html,/id="min-sleep_log"[^>]*step="any"[^>]*value="7\.123456"/);
 assert.match(html,/id="limit"[^>]*step="any"[^>]*value="41\.234567"/);
 assert.doesNotMatch(html,/id="min-data_package"|NaN|value="undefined"/);
 await b.node('save').onclick();
 assert.equal(b.requests[0].body.sell_agent.min.sleep_log,7.123456);
 assert.equal(b.requests[0].body.buy_agent.auto_limit,41.234567);
});

test('editing fractional prices and the preset does not quantize them to half units',async()=>{
 const b=settingsBrowser();
 b.node('min-sleep_log').value='7.234567';b.node('min-sleep_log').oninput();
 b.node('limit').value='2.345678';b.node('limit').oninput();
 await b.node('save').onclick();
 assert.equal(b.requests[0].body.sell_agent.min.sleep_log,7.234567);
 assert.equal(b.requests[0].body.buy_agent.auto_limit,2.345678);
 const c=settingsBrowser();c.node('firm').value='123.45';c.node('firm').oninput();
 await c.node('save').onclick();
 assert.equal(c.requests[0].body.sell_agent.min.sleep_log,7*123.45/100);
 assert.ok(!('data_package' in c.requests[0].body.sell_agent.min));
});

test('open settings are not replaced by a background refresh',()=>{
 const b=settingsBrowser(),original=b.node('agents').innerHTML;b.node('agentDlg').open=true;b.node('sellModel').value='allowed-b';
 vm.runInContext('ACC.account.sell_agent.model="auto";renderAgents();',b.context);
 assert.equal(b.node('agents').innerHTML,original);assert.equal(b.node('sellModel').value,'allowed-b');
});

test('a removed saved model is visible and requires an allowed replacement',()=>{
 const context=vm.createContext({document:{},window:{addEventListener(){}},console});
 vm.runInContext(fs.readFileSync(path.join(base,'common.js'),'utf8'),context);
 vm.runInContext("META={models:['auto','allowed-a']};",context);
 const options=vm.runInContext("modelOptions('retired-model')",context);
 assert.match(options,/disabled selected[^>]*>[^<]*Unavailable: retired-model/);assert.match(options,/value="auto"/);
});
