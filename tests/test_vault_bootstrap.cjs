const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const {test} = require('node:test');

const root = path.resolve(__dirname, '..');
const load = name => {
  const file = `prototypes/data-vault-market/server/vaultmarket/static/${name}`;
  return process.env.VAULT_BOOTSTRAP_REF
    ? execFileSync('git', ['show', `${process.env.VAULT_BOOTSTRAP_REF}:${file}`], {cwd: root, encoding: 'utf8'})
    : fs.readFileSync(path.join(root, file), 'utf8');
};
const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };

function browser() {
  let releaseDemo, meReads = 0, nextTimer = 0, replacements = 0;
  const delayedDemo = new Promise(resolve => { releaseDemo = resolve; });
  const timers = new Map(), streams = [], nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {id, textContent: '', innerHTML: '', dataset: {}, style: {}, setAttribute() {}, removeAttribute() {}, after() {}});
    return nodes.get(id);
  };
  const app = {hidden: true, get innerHTML() { return 'original vault controls'; }, set innerHTML(value) { replacements++; }};
  const context = vm.createContext({
    console, document: {hidden: false, getElementById: node, querySelectorAll: () => [], querySelector: selector => ['.app', '.vault-app'].includes(selector) ? app : null},
    window: {addEventListener() {}}, location: {pathname: '/vault'},
    fetch: async url => {
      const reply = data => ({ok: true, json: async () => data});
      if (url === '/api/meta') return reply({asset: 'test USD', ledger: 'testnet'});
      if (url === '/api/me') return reply({public: true, user: ++meReads === 1 ? null : {username: 'Demo', account: 'demo-vault', demo: true}});
      if (url === '/api/demo-session') { await delayedDemo; return reply({ok: true}); }
      throw new Error(`Unexpected request: ${url}`);
    },
    EventSource: class {constructor() { streams.push(this); }},
    setTimeout: fn => { const id = ++nextTimer; timers.set(id, fn); return id; },
    clearTimeout: id => timers.delete(id), setInterval: () => 0,
  });
  vm.runInContext(load('common.js'), context);
  return {context, streams, releaseDemo, node, app, replacements: () => replacements, tick: async () => {
    const pending = [...timers.values()]; timers.clear();
    for (const fn of pending) fn();
    await flush();
  }};
}

test('SSE cannot refresh the vault between metadata and automatic demo login', async () => {
  const b = browser();
  vm.runInContext('let refreshes=0; function refresh(){refreshes++;} const boot=topbar("vault").then(refresh); live();', b.context);
  await flush();
  assert.equal(vm.runInContext('META.asset', b.context), 'test USD');
  assert.equal(vm.runInContext('ME', b.context), null);
  b.streams[0].onmessage();
  await b.tick();
  assert.equal(vm.runInContext('refreshes', b.context), 0, 'Live update ran before automatic login completed');
  b.releaseDemo(); await flush();
  assert.equal(vm.runInContext('ME', b.context), 'demo-vault');
  assert.equal(vm.runInContext('refreshes', b.context), 1, 'The initial authenticated refresh must still run');
  b.streams[0].onmessage(); await b.tick();
  assert.equal(vm.runInContext('refreshes', b.context), 2, 'Live updates must resume after login');
});

test('a pending identity never destroys the My DB page controls', async () => {
  const b = browser();
  const html = load('vault.html');
  const start = html.indexOf('async function refresh()');
  const end = html.indexOf('\nfunction collectionSelection()', start);
  assert.ok(start > 0 && end > start, 'Find the actual My DB refresh implementation');
  vm.runInContext(html.slice(start, end), b.context);
  vm.runInContext('META={asset:"test USD"};', b.context);
  await vm.runInContext('refresh()', b.context);
  assert.equal(b.replacements(), 0, 'An in-flight login replaced the entire vault with a sign-in screen');
});

function installStartVault(b) {
  const html = load('vault.html');
  const start = html.indexOf('async function startVault()');
  const end = html.indexOf("\n$('retryVault').onclick", start);
  assert.ok(start > 0 && end > start, 'Find the actual My DB startup implementation');
  vm.runInContext(html.slice(start, end), b.context);
}

test('startup reveals the original workspace only after login and its first refresh succeed', async () => {
  const b = browser();
  let finishLogin;
  b.context.delayedLogin = new Promise(resolve => { finishLogin = resolve; });
  vm.runInContext('topbar=async()=>{await delayedLogin;ME="demo-vault";}; refresh=async()=>true;', b.context);
  installStartVault(b);
  const pending = vm.runInContext('startVault()', b.context);
  assert.equal(b.app.hidden, true);
  assert.equal(b.node('vaultStartup').hidden, false);
  assert.equal(b.node('retryVault').hidden, true);
  finishLogin(); await pending;
  assert.equal(b.app.hidden, false);
  assert.equal(b.node('vaultStartup').hidden, true);
  assert.equal(b.replacements(), 0);
});

test('failed login or incomplete initial refresh keeps controls intact and offers retry', async () => {
  for (const setup of [
    'topbar=async()=>{throw new Error("offline");}; refresh=async()=>true;',
    'topbar=async()=>{}; refresh=async()=>false;',
  ]) {
    const b = browser();
    vm.runInContext(setup, b.context);
    installStartVault(b);
    await vm.runInContext('startVault()', b.context);
    assert.equal(b.app.hidden, true);
    assert.equal(b.node('vaultStartup').hidden, false);
    assert.equal(b.node('retryVault').hidden, false);
    assert.match(b.node('vaultStartupText').textContent, /could not open your vault/i);
    assert.equal(b.replacements(), 0);
  }
});
