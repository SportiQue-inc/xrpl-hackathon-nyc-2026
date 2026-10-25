const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {test}=require('node:test');
const source=fs.readFileSync(require('node:path').join(__dirname,'../prototypes/data-vault-market/server/vaultmarket/static/common.js'),'utf8');
test('asset aliases cannot change amounts or rewrite stored history',()=>{
 const context=vm.createContext({document:{getElementById(){}},window:{addEventListener(){}}});
 vm.runInContext(source,context);
 vm.runInContext("META={asset:'test USD',asset_label:'RLUSD'}",context);
 assert.match(vm.runInContext('amount(12)',context),/12.00 test USD$/);
 assert.match(vm.runInContext("amount(.137,'XRP')",context),/XRP$/);
 assert.equal(vm.runInContext("relabel('Paid 12 test USD')",context),'Paid 12 test USD');
});

test('walkthrough uses the open receipt rail and keeps test USD distinct from RLUSD',()=>{
 const tour=fs.readFileSync(require('node:path').join(__dirname,'../prototypes/data-vault-market/server/vaultmarket/static/tour.js'),'utf8');
 const receipt={dataset:{paymentRail:'xrpl'}};
 const context=vm.createContext({document:{getElementById:()=>receipt},META:{ap4m:true}});
 vm.runInContext(tour.slice(0,tour.indexOf('const tourGet')),context);
 const title=()=>vm.runInContext("JUDGE.find(s=>s.dialog&&typeof s.t==='function').t().en[0]",context);
 assert.equal(title(),'Paid on XRPL');
 receipt.dataset.paymentRail='ap4m';assert.equal(title(),'Paid through Mastercard AP4M');
 const assets=vm.runInContext("PAGE['/assets'].help.en",context);
 assert.match(assets,/stay separate/);assert.doesNotMatch(assets,/stands in|Amounts are in RLUSD/);
 const intro=vm.runInContext("JUDGE.find(s=>s.wait).t.en.join(' ')",context);
 assert.match(intro,/Rules when no model answered/);
});
