'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'voodoo_product/static/control_room.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'voodoo_product/static/index.html'), 'utf8');

assert.match(html, /id="change-review-button"/);
assert.match(html, /id="change-create-button" disabled/);
assert.match(html, /request_workflow\.css/);

class Element {
  constructor(id) {
    this.id = id;
    this.listeners = {};
    this.dataset = {};
    this.disabled = false;
    this.value = '';
    this.textContent = '';
    this.innerHTML = '';
    this.className = '';
    this.classList = {
      current: new Set(['hidden']),
      add: name => this.classList.current.add(name),
      remove: name => this.classList.current.delete(name),
      toggle: (name, on) => on ? this.classList.current.add(name) : this.classList.current.delete(name),
      contains: name => this.classList.current.has(name),
    };
  }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  closest() { return this; }
  replaceChildren() { this.innerHTML = ''; this.textContent = ''; }
  focus() {}
}

const elements = new Map();
function el(id) {
  if (!elements.has(id)) elements.set(id, new Element(id));
  return elements.get(id);
}

const storage = new Map();
const sessionStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: key => storage.delete(key),
};

const capabilities = [
  {id: 'echo', effect: 'INERT', verification: 'NOT_REQUIRED', environments: ['staging'], runtime_status: 'ACTIVE'},
  {id: 'github.read-ref/v1', effect: 'READ_ONLY', verification: 'INDEPENDENT_VERIFIER', environments: ['staging'], runtime_status: 'ENABLED'},
];
let approvalRows = [];
let approvalForbidden = false;
let controlRoomUnavailable = false;
const calls = [];

async function fetchStub(url, options = {}) {
  const pathname = String(url).replace(/^\/api\/v1/, '');
  const method = options.method || 'GET';
  calls.push({pathname, method, options});
  let body;
  if (pathname === '/bootstrap/status') body = {required: false};
  else if (pathname === '/control-room' && controlRoomUnavailable) {
    return {ok: false, status: 503, json: async () => ({detail: 'registry unavailable'})};
  } else if (pathname === '/control-room') body = {
    plans: {items: [], pending_approvals: approvalRows.length},
    capability_registry: {items: capabilities},
  };
  else if (pathname === '/change-requests' && method === 'GET') body = [];
  else if (pathname === '/change-requests' && method === 'POST') body = {id: 'cr_created'};
  else if (pathname === '/operations/status') body = {configured: false};
  else if (pathname === '/approvals?pending_only=true' && approvalForbidden) {
    return {ok: false, status: 403, json: async () => ({detail: 'permission denied'})};
  } else if (pathname === '/approvals?pending_only=true') body = approvalRows;
  else throw new Error(`Unexpected API call: ${method} ${pathname}`);
  return {ok: true, status: method === 'POST' ? 201 : 200, json: async () => body};
}

const context = vm.createContext({
  document: {getElementById: el, querySelectorAll: () => []},
  fetch: fetchStub,
  sessionStorage,
  Element,
  crypto: {randomUUID: () => 'request-workflow-key'},
  setTimeout: () => 0,
  console,
  confirm: () => false,
  prompt: () => null,
  loadEcosystemBoard: () => {},
  loadLifecycleBoard: () => {},
  loadAuthorityBoard: () => {},
  loadLineageBoard: () => {},
  loadOverlaysBoard: () => {},
});

vm.runInContext(source, context, {filename: 'control_room.js'});
const run = expression => vm.runInContext(expression, context);

async function test() {
  run(`state.workspaces=[{id:'wrk_request_test',name:'Test',environment:'staging'}]; state.capabilities=${JSON.stringify(capabilities)}`);
  el('change-workspace').value = 'wrk_request_test';
  el('change-title').value = 'Observe exact main ref';
  el('change-risk').value = 'R1';
  el('change-environment').value = 'staging';
  el('change-adapter').value = 'github-read-ref';
  el('change-description').value = 'Read-only observation';
  el('change-payload').value = JSON.stringify({repository: 'eimyroot/Voodoo-One', ref: 'refs/heads/main'});

  el('change-create-button').disabled = true;
  await el('change-review-button').listeners.click();
  assert.equal(el('change-create-button').disabled, false);
  assert.match(el('change-review-facts').innerHTML, /READ_ONLY/);
  assert.match(el('change-review-facts').innerHTML, /INDEPENDENT_VERIFIER/);
  assert.match(el('change-review-facts').innerHTML, /eimyroot\/Voodoo-One/);
  assert.match(el('change-review-note').textContent, /Nevydává oprávnění/);

  // A live registry change must invalidate an otherwise identical request.
  capabilities[1].verification = 'CHANGED_REQUIREMENT';
  const beforeMetadataPosts = calls.filter(c => c.pathname === '/change-requests' && c.method === 'POST').length;
  await el('change-form').listeners.submit({preventDefault() {}});
  assert.equal(calls.filter(c => c.pathname === '/change-requests' && c.method === 'POST').length, beforeMetadataPosts);
  assert.equal(el('change-create-button').disabled, true);
  assert.match(el('toast').textContent, /Nejdřív zkontrolujte/);
  capabilities[1].verification = 'INDEPENDENT_VERIFIER';
  await el('change-review-button').listeners.click();

  el('change-title').value = 'Changed after review';
  el('change-form').listeners.input();
  assert.equal(el('change-create-button').disabled, true, 'changed input invalidates reviewed impact');
  const postsBefore = calls.filter(call => call.pathname === '/change-requests' && call.method === 'POST').length;
  await el('change-form').listeners.submit({preventDefault() {}});
  assert.equal(calls.filter(call => call.pathname === '/change-requests' && call.method === 'POST').length, postsBefore);
  assert.match(el('toast').textContent, /Nejdřív zkontrolujte/);

  await el('change-review-button').listeners.click();
  await el('change-form').listeners.submit({preventDefault() {}});
  const posts = calls.filter(call => call.pathname === '/change-requests' && call.method === 'POST');
  assert.equal(posts.length, 1);
  const created = JSON.parse(posts[0].options.body);
  assert.equal(created.environment, 'staging');
  assert.equal(created.adapter, 'github-read-ref');
  assert.deepEqual(created.payload, {repository: 'eimyroot/Voodoo-One', ref: 'refs/heads/main'});

  approvalRows = [{
    request_id: 'cr_waiting', title: '<Sensitive request>', risk: 'R2',
    environment: 'staging', approved_count: 0, required_count: 1,
  }];
  await run('loadApprovals(new Map())');
  assert.doesNotMatch(el('approvals-list').innerHTML, /data-decision=/);
  assert.match(el('approvals-list').innerHTML, /Rozhodnutí je v tomto pohledu zablokováno/);

  run(`approvalRequestMap=new Map([['cr_waiting',{
    id:'cr_waiting',title:'<Sensitive request>',risk:'R2',status:'REVIEW_REQUIRED',
    adapter:'github-read-ref',environment:'staging',
    payload:{repository:'eimyroot/<unsafe>',ref:'refs/heads/main'}
  }]])`);
  await run('loadApprovals(approvalRequestMap)');
  assert.match(el('approvals-list').innerHTML, /data-decision="APPROVED"/);
  assert.match(el('approvals-list').innerHTML, /READ_ONLY/);
  assert.match(el('approvals-list').innerHTML, /INDEPENDENT_VERIFIER/);
  assert.match(el('approvals-list').innerHTML, /&lt;unsafe&gt;/);
  assert.doesNotMatch(el('approvals-list').innerHTML, /<Sensitive request>/);

  approvalForbidden = true;
  await run('loadApprovals(approvalRequestMap)');
  assert.match(el('approvals-list').innerHTML, /approval\.review/);
  assert.match(el('approvals-list').innerHTML, /Požadavky můžete dále vytvářet/);

  approvalForbidden = false;
  await el('change-review-button').listeners.click();
  await run('loadApprovals(approvalRequestMap)');
  assert.match(el('approvals-list').innerHTML, /data-decision="APPROVED"/);
  const beforeOutagePosts = calls.filter(c => c.pathname === '/change-requests' && c.method === 'POST').length;
  controlRoomUnavailable = true;
  await el('change-form').listeners.submit({preventDefault() {}});
  assert.equal(calls.filter(c => c.pathname === '/change-requests' && c.method === 'POST').length, beforeOutagePosts);
  assert.equal(el('change-create-button').disabled, true);
  assert.equal(el('change-review-facts').innerHTML, '');
  assert.doesNotMatch(el('approvals-list').innerHTML, /data-decision=/);
  assert.match(el('plans-table').innerHTML, /UNKNOWN/);
  await assert.rejects(run('loadPlans()'), /registry unavailable/);
  await el('change-review-button').listeners.click();
  assert.equal(el('change-create-button').disabled, true);
  assert.equal(el('change-review-state').textContent, 'BLOKOVÁNO');
  controlRoomUnavailable = false;
  await el('change-review-button').listeners.click();
  assert.equal(el('change-create-button').disabled, false);
  assert.match(el('change-review-facts').innerHTML, /INDEPENDENT_VERIFIER/);
  assert.ok(calls.filter(c => c.pathname === '/control-room').every(c => c.options.cache === 'no-store'));
  console.log('PASS: changed capability metadata, registry outage, fail-closed context and recovery');
  console.log('PASS: exact request impact review, stale-review invalidation and fail-closed approval context');
}

test().catch(error => {console.error(error); process.exitCode = 1;});
