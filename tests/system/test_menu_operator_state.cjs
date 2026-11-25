const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const client = fs.readFileSync('voodoo_product/static/control_room.js', 'utf8');
const html = fs.readFileSync('voodoo_product/static/index.html', 'utf8');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {});
  return elements.get(id);
};
let snapshot;
const context = vm.createContext({
  $: element,
  fact: () => '',
  controlRoom: async () => {
    if (!snapshot) throw Error('unavailable');
    return snapshot;
  }
});
vm.runInContext(client.slice(client.indexOf('function showStopState('), client.indexOf('async function loadLearning(')), context);
(async () => {
  assert.equal(html.match(/data-view="plans"/g).length, 1);
  for (const active of [true, false, undefined]) {
    snapshot = {runtime_health: [], overview: {environment: 'staging', emergency_stop: active}};
    await context.loadRuntimeHealth();
    assert.equal(element('activate-stop').disabled, active !== false);
    assert.equal(element('clear-stop').disabled, active !== true);
    assert.match(element('stop-state').textContent, /staging/);
  }
  snapshot = null;
  await assert.rejects(context.loadRuntimeHealth(), /unavailable/);
  assert.equal(element('activate-stop').disabled, true);
  assert.equal(element('clear-stop').disabled, true);
  console.log('PASS: one plans destination and fail-closed stop controls');
})().catch(error => {console.error(error); process.exitCode = 1;});
