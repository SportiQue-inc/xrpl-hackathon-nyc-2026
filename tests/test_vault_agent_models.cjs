const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const base = path.resolve(__dirname, '../prototypes/data-vault-market/server/vaultmarket/static');

test('settings show independent allowed preferences and submit both selected values', async () => {
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {innerHTML: '', textContent: '', value: '', contains: () => false});
    return nodes.get(id);
  };
  let sent;
  const context = vm.createContext({
    document: {getElementById: node, activeElement: null}, window: {addEventListener() {}},
    location: {pathname: '/'}, console,
    fetch: async (url,opts) => {sent={path:url,body:JSON.parse(opts.body)};return {ok:true,json:async()=>({ok:true})};},
  });
  vm.runInContext(fs.readFileSync(path.join(base, 'common.js'), 'utf8'), context);
  const market = fs.readFileSync(path.join(base, 'market.html'), 'utf8');
  vm.runInContext(market.slice(market.indexOf('function renderAgents()'), market.indexOf('\nasync function openContract')), context);
  vm.runInContext(`META={models:['auto','allowed-a','allowed-b'], kinds:{sleep_log:{label:'Sleep',price:7}}, unit_xrp:1, asset:'test USD', ledger:'mock'};
    ME='u-owner';USER={user:{account:'u-owner'}};
    let ACC={account:{sell_agent:{mode:'ask',min:{sleep_log:7},blocks:[],model:'allowed-a'},buy_agent:{auto_limit:50,min_trust:.7,model:'allowed-b'}}};
    renderAgents();`, context);
  assert.match(node('agents').innerHTML, /id="sellModel"[\s\S]*value="allowed-a" selected/);
  assert.match(node('agents').innerHTML, /id="buyModel"[\s\S]*value="allowed-b" selected/);
  assert.match(node('agents').innerHTML, /actual model or rules/i);
  Object.entries({sellModel:'allowed-b',buyModel:'auto',mode:'ask','min-sleep_log':'7',blocks:'',limit:'50',trust:'.7'})
    .forEach(([id,value]) => {node(id).value=value;});
  await node('save').onclick();
  assert.deepEqual(sent, {
    path:'/api/account/u-owner/settings', body:{sell_agent:{model:'allowed-b',mode:'ask',min:{sleep_log:7},blocks:[]},buy_agent:{model:'auto',auto_limit:50,min_trust:.7}},
  });
});

test('a removed saved model is visible and requires an allowed replacement', () => {
  const context = vm.createContext({document:{},window:{addEventListener(){}},console});
  vm.runInContext(fs.readFileSync(path.join(base, 'common.js'), 'utf8'), context);
  vm.runInContext("META={models:['auto','allowed-a']};", context);
  const options = vm.runInContext("modelOptions('retired-model')", context);
  assert.match(options, /disabled selected[^>]*>[^<]*Unavailable: retired-model/);
  assert.match(options, /value="auto"/);
});
