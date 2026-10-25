const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {test}=require('node:test');
const base=path.resolve(__dirname,'../prototypes/data-vault-market/server/vaultmarket/static');
const html=fs.readFileSync(path.join(base,'vault.html'),'utf8');
const code=html.slice(html.indexOf('// Commercial packages'),html.indexOf('async function startVault()'));
test('generic category purchases cannot bypass the explicit package snapshot and terms',()=>{
 assert.ok(html.includes("Object.entries(k).filter(([id])=>id!=='data_package')"));
});
function setup(reply){
 const nodes=new Map(),requests=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',checked:false,disabled:false,textContent:'',innerHTML:'',className:'',dataset:{}});return nodes.get(id);};
 const context=vm.createContext({console,document:{getElementById:node},window:{addEventListener(){}},location:{pathname:'/vault'},
  fetch:async(url,opts={})=>{const body=opts.body?JSON.parse(opts.body):undefined;requests.push({url,body});const data=await reply(url,body);return {ok:true,json:async()=>data};}});
 vm.runInContext(fs.readFileSync(path.join(base,'common.js'),'utf8'),context);
 vm.runInContext("META={asset:'test USD',kinds:{}};ME='u-buyer';let COLLECTIONS=[];async function refresh(){}",context);
 vm.runInContext(code,context);
 vm.runInContext('renderPackages=()=>{};',context);
 const button=node('buyButton'),status=node('buyStatus'),resale=node('resale');
 context.card={querySelector:selector=>({'[data-buy-package]':button,'[data-package-status]':status,'[data-package-resale]':resale})[selector]};
 context.listing={id:17,name:'Sleep + routes',price:3.123456,asset:'test USD',purpose:'recovery research',resale:true,sha256:'fixed-snapshot'};
 return {context,node,requests,button,status,resale};
}
test('purchase accepts the exact displayed immutable snapshot, amount and lesser resale grant',async()=>{
 const b=setup(async url=>url.endsWith('/buy')?{contract:31,status:'settling',reason:'Waiting for validation'}:{contract:{status:'settled',reason:'Verified'}});
 await vm.runInContext('buyPackage(listing,card)',b.context);
 assert.deepEqual(b.requests[0],{url:'/api/account/u-buyer/packages/17/buy',body:{sha256:'fixed-snapshot',price:3.123456,purpose:'recovery research',resale:false}});
 assert.equal(b.requests[1].url,'/api/contract/31');
 assert.match(b.status.innerHTML,/Open C31/);assert.equal(b.button.textContent,'Purchased');assert.equal(b.button.disabled,true);
});
test('one pending click cannot create duplicate purchases',async()=>{
 let finish;const wait=new Promise(resolve=>{finish=resolve;});
 const b=setup(async()=>{await wait;return {contract:31,status:'settled'};});b.resale.checked=true;
 const first=vm.runInContext('buyPackage(listing,card)',b.context);
 await vm.runInContext('buyPackage(listing,card)',b.context);
 assert.equal(b.requests.length,1);assert.equal(b.button.disabled,true);assert.match(b.button.textContent,/Checking overlap/);
 finish();await first;assert.equal(b.requests[0].body.resale,true);
});
test('a missing confirmation never claims no payment and blocks immediate retries',async()=>{
 const b=setup(async()=>{throw new Error('Connection interrupted');});
 await vm.runInContext('buyPackage(listing,card)',b.context);
 assert.match(b.status.innerHTML,/Confirmation unavailable/);assert.match(b.status.innerHTML,/Check recorded activity/);assert.equal(b.button.disabled,true);
 await vm.runInContext('buyPackage(listing,card)',b.context);assert.equal(b.requests.length,1);
});
test('a confirmed paid result survives a failed workspace refresh',async()=>{
 const b=setup(async()=>({contract:31,status:'settled'}));
 vm.runInContext('refresh=async()=>{throw new Error("Refresh offline");};',b.context);
 await vm.runInContext('buyPackage(listing,card)',b.context);
 assert.equal(b.button.textContent,'Purchased');assert.match(b.status.innerHTML,/settled/);assert.doesNotMatch(b.status.innerHTML,/Not purchased/);
});
test('publish form uses the chosen collection revision and displayed asking price',async()=>{
 const b=setup(async url=>url.endsWith('/packages')?{name:'Sleep + routes',price:9.25,asset:'test USD',records:12}:{packages:[]});
 vm.runInContext('refreshPackages=async()=>{};',b.context);
 Object.entries({packageVersion:'4:2',packagePrice:'9.25',packagePurpose:'  recovery research  '}).forEach(([id,value])=>b.node(id).value=value);b.node('packageResale').checked=true;
 await b.node('packageForm').onsubmit({preventDefault(){}});
 assert.deepEqual(b.requests[0],{url:'/api/account/u-buyer/packages',body:{collection:4,version:2,price:9.25,purpose:'recovery research',resale:true}});
 assert.match(b.node('publishPackageStatus').textContent,/Published Sleep \+ routes/);assert.equal(b.node('publishPackage').disabled,false);
});
test('automatic package reads are throttled to one batch per four seconds',async()=>{
 const b=setup(async()=>({packages:[]}));
 await vm.runInContext('refreshPackages()',b.context);await vm.runInContext('refreshPackages()',b.context);
 assert.equal(b.requests.length,2);
 await vm.runInContext('refreshPackages(true)',b.context);assert.equal(b.requests.length,4);
});
test('own packages and another asset cannot trigger a purchase',async()=>{
 const b=setup(async()=>{throw new Error('must not call API');});
 vm.runInContext('listing.mine=true;',b.context);await vm.runInContext('buyPackage(listing,card)',b.context);
 vm.runInContext("listing.mine=false;listing.asset='XRP';",b.context);await vm.runInContext('buyPackage(listing,card)',b.context);
 assert.equal(b.requests.length,0);
});
test('catalog reuses unchanged cards and keeps the accepted budget equal to its visible snapshot',async()=>{
 const b=setup(async()=>({contract:31,status:'settled'}));
 const make=()=>({dataset:{},children:[],innerHTML:'',contains(node){return this===node;},querySelector(selector){return this.parts?.[selector]||null;},remove(){this.parent.children=this.parent.children.filter(n=>n!==this);}});
 const catalog=b.node('packageCatalog');catalog.children=[];catalog.querySelectorAll=()=>catalog.children;catalog.querySelector=()=>null;catalog.append=card=>{card.parent=catalog;catalog.children.push(card);};
 b.context.document.createElement=()=>{
  const card=make();let content='';card.replacements=0;
  Object.defineProperty(card,'innerHTML',{get:()=>content,set:value=>{content=value;card.replacements++;card.parts={'[data-buy-package]':{textContent:'',disabled:false},'[data-package-status]':{},'[data-package-resale]':{checked:false}};}});
  return card;
 };
 // Reinstall the actual renderer after setup's financial-handler test stub.
 const from=code.indexOf('function renderPackages()'),to=code.indexOf('async function readPackageContract');
 vm.runInContext(code.slice(from,to),b.context);
 vm.runInContext("listing.name='<img src=x onerror=bad>';PACKAGE_CATALOG=[listing];renderPackages();",b.context);
 const card=catalog.children[0];assert.match(card.innerHTML,/&lt;img/);assert.doesNotMatch(card.innerHTML,/<img/);
 vm.runInContext('renderPackages()',b.context);assert.equal(catalog.children[0],card);assert.equal(card.replacements,1);
 // While a card has focus, a newer API object must not silently replace its accepted snapshot.
 b.context.document.activeElement=card;
 vm.runInContext('PACKAGE_CATALOG=[{...listing,price:99,sha256:"new-snapshot"}];renderPackages();',b.context);
 assert.match(card.querySelector('[data-buy-package]').textContent,/3\.123456/);
 await card.querySelector('[data-buy-package]').onclick();
 assert.equal(b.requests[0].body.price,3.123456);assert.equal(b.requests[0].body.sha256,'fixed-snapshot');
});
