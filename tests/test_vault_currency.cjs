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
