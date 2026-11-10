'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'voodoo_product/static/control_room.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'voodoo_product/static/index.html'), 'utf8');
assert.match(html, /value="github-read-ref"/);
assert.match(html, /id="canonical-read-feedback"/);
assert.match(html, /id="canonical-read-result"/);
class Element {
  constructor(id) {
    this.id = id; this.listeners = {}; this.dataset = {}; this.disabled = false;
    this.value = ''; this.textContent = ''; this.innerHTML = ''; this.className = '';
    this.classList = {
      current: new Set(['hidden']),
      add: name => this.classList.current.add(name),
      remove: name => this.classList.current.delete(name),
      toggle: (name, on) => on ? this.classList.current.add(name) : this.classList.current.delete(name),
      contains: name => this.classList.current.has(name),
    };
  }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  closest(selector) { return selector === 'button[data-change-action]' ? this : null; }
}
const elements = new Map();
function el(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); }
const storage = new Map();
const sessionStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, val) => storage.set(key, String(val)),
  removeItem: key => storage.delete(key),
};
const requestId = 'cr_g8_test_001';
const executionId = 'exec_g8_test_001';
let runtimeReady = false, approved = true, confirmed = false, verdict = 'VERIFIED', forceNetworkFailure = false;
let requests = [], postCalls = [], confirmCalls = 0, generatedKeys = 0;
const request = {
  id: requestId, status: 'APPROVED', environment: 'staging', adapter: 'github-read-ref',
  payload: {repository: 'eimyroot/Voodoo-One', ref: 'refs/heads/main'},
};
const legacy = {
  id: 'cr_legacy_001', status: 'APPROVED', environment: 'local',
  adapter: 'echo', payload: {message: 'hello'},
};
const write = {
  id: 'cr_github_write_001', status: 'APPROVED', environment: 'staging',
  adapter: 'github-create-ref', payload: {repository: 'eimyroot/Voodoo-One'},
};
const plans = {
  plans: {items: [
    {request_id: requestId, status: 'APPROVED', risk: 'R1', title: 'Observe exact ref',
      environment: 'staging', approval_count: 1, approval_required: 1},
    {request_id: legacy.id, status: 'APPROVED', risk: 'R0', title: 'Legacy echo',
      environment: 'local', approval_count: 1, approval_required: 1},
    {request_id: write.id, status: 'APPROVED', risk: 'R2', title: 'Denied provider write',
      environment: 'staging', approval_count: 1, approval_required: 1},
  ]},
  runs: {queue_depth: 0, active_count: 0, completed_count: 0, failed_count: 0, recent: []},
};
const passport = {
  execution_id: executionId, operation: {}, authority: {}, dispatch: {}, runtime: {},
  verification: {status: 'NOT_PERSISTED', verdict: 'UNKNOWN', independent_verification_exposed: false},
  integrity: {canonical_json_validated: true, lineage_bindings_validated: true,
    independent_verification_validated: false},
};
async function fetchStub(url, options = {}) {
  const pathname = String(url).replace(/^\/api\/v1/, '');
  const method = options.method || 'GET';
  requests.push({pathname, method, options});
  let body;
  if (pathname === '/bootstrap/status') body = {required: false};
  else if (pathname === '/control-room') body = plans;
  else if (pathname === '/change-requests') body = [request, legacy, write];
  else if (pathname === '/approvals?pending_only=true') body = [];
  else if (pathname === '/operations/status') body = {
    configured: runtimeReady, read_terminal_configured: runtimeReady,
    write_routes_exposed: false, provider_write_effects_exposed: false,
  };
  else if (pathname === '/change-requests/' + requestId) {
    body = {...request, status: approved ? 'APPROVED' : 'REVIEW_REQUIRED'};
  } else if (pathname === '/operations/' + requestId + '/read') {
    postCalls.push({pathname, method, options});
    if (forceNetworkFailure) throw new Error('simulated network ambiguity');
    body = {
      schema: 'vone.canonical-operation-read/v1',
      operation: {request_id: requestId, execution_id: executionId},
      execution: {status: 'SUCCEEDED'},
      verification: {verdict, strength_class: 'INDEPENDENT_PROVIDER_READBACK',
        result_digest: 'v1-digest'},
    };
  } else if (pathname === '/operations/' + executionId + '/passport') body = passport;
  else throw Error('Unexpected API call: ' + method + ' ' + pathname);
  return {ok: true, status: 200, json: async () => body};
}
const ctx = vm.createContext({
  document: {getElementById: el, querySelectorAll: () => []},
  fetch: fetchStub, sessionStorage, Element,
  crypto: {randomUUID: () => 'canonical-read-test-key-' + (++generatedKeys)},
  setTimeout: () => 0, console,
  loadEcosystemBoard: () => {}, loadLifecycleBoard: () => {},
  loadAuthorityBoard: () => {}, loadLineageBoard: () => {}, loadOverlaysBoard: () => {},
  confirm: () => {confirmCalls++; return confirmed;},
});
vm.runInContext(source, ctx, {filename: 'control_room.js'});
vm.runInContext("state.token='test-token'", ctx);
const run = expression => vm.runInContext(expression, ctx);

async function test() {
  await run('loadPlans()');
  assert.match(el('plans-table').innerHTML, /READ DISABLED/);
  assert.doesNotMatch(
    el('plans-table').innerHTML.split('cr_g8_test_001')[1].split('</tr>')[0],
    /Execute \(legacy\)/,
  );
  runtimeReady = true;
  await run('loadPlans()');
  assert.match(el('plans-table').innerHTML, /data-change-action="canonical-read"/);
  assert.match(el('plans-table').innerHTML, /Execute \(legacy\)/);
  assert.doesNotMatch(el('plans-table').innerHTML.split('cr_github_write_001')[1].split('</tr>')[0], /Execute \(legacy\)|Canonical READ/);

  const button = new Element('canonical-button');
  button.dataset = {changeAction: 'canonical-read', requestId};
  confirmed = false;
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 0, 'operator cancellation must never execute');
  assert.equal(generatedKeys, 0, 'cancellation must not reserve execution idempotency');

  approved = false;
  confirmed = true;
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 0, 'stale approval must fail closed');
  assert.match(el('canonical-read-feedback').textContent, /UNKNOWN|NEOVĚŘENO/);

  approved = true;
  runtimeReady = false;
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 0, 'unavailable runtime must fail closed');

  runtimeReady = true;
  forceNetworkFailure = true;
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 1, 'only one canonical read should be attempted');
  const first = postCalls[0];
  assert.equal(first.method, 'POST');
  assert.equal(first.pathname, '/operations/' + requestId + '/read');
  assert.match(first.options.headers['Idempotency-Key'], /^canonical-read-test-key-/);
  assert.equal(JSON.parse(first.options.body).correlation_id, first.options.headers['Idempotency-Key']);
  assert.match(el('canonical-read-feedback').textContent, /UNKNOWN/);

  forceNetworkFailure = false;
  verdict = 'UNVERIFIED';
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 2);
  assert.equal(
    postCalls[0].options.headers['Idempotency-Key'],
    postCalls[1].options.headers['Idempotency-Key'],
    'an ambiguous READ attempt must retain the same key across explicit retry'
  );
  assert.equal(generatedKeys, 1);
  assert.match(el('canonical-read-feedback').textContent, /UNKNOWN/);
  assert.equal(el('canonical-read-result').classList.contains('hidden'), true);

  verdict = 'VERIFIED';
  await el('plans-table').listeners.click({target: button});
  assert.equal(postCalls.length, 3);
  assert.equal(generatedKeys, 1, 'explicit later attempts must reuse the original key');
  assert.match(el('canonical-read-result').textContent, /READ API: VERIFIED/);
  assert.match(el('canonical-read-result').textContent, /Passport uvádí pouze vlastní dostupnou durable evidenci/);
  assert.match(el('operation-passport-content').innerHTML, /NOT_PERSISTED/);
  assert.match(el('operation-passport-content').innerHTML, /UNKNOWN/);
  assert.equal(el('operation-passport-panel').classList.contains('hidden'), false);
  assert.equal(button.disabled, false);
  assert.ok(requests.some(x => x.pathname === '/operations/' + executionId + '/passport'));
  assert.equal(requests.filter(x=>x.method==='POST' && x.pathname.includes('/change-requests/') && x.pathname.endsWith('/execute')).length, 0);
  assert.ok(confirmCalls >= 3);
  console.log('OPERATOR_CANONICAL_READ_UX_PASS RUNTIME_FAIL_CLOSED_APPROVAL_DENIAL_CANCEL_AMBIGUITY_SAME_IDEMPOTENCY_VERIFIER_PASSPORT');
}
test().catch(error => {console.error(error); process.exitCode = 1;});
