// Dependency-free behavior regression for the browser view renderers.
// Not a substitute for an actual Safari/Chromium accessibility acceptance run.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const source = fs.readFileSync(
  path.resolve(__dirname, '../../voodoo_product/static/workflow_boards.js'), 'utf8'
);
const names = ['ecosystem', 'lifecycle', 'authority', 'lineage', 'overlays'];
const nodes = Object.fromEntries(names.map(name => [name, { innerHTML: '' }]));
let fail = false;
let omitSignals = false;
const context = {
  document: { getElementById: id => nodes[id.replace('view-', '')] || null },
  escapeHtml: value => String(value ?? '').replace(/[&<>"']/g,
    ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[ch]),
  status: value => '<span class="status">' + String(value) + '</span>',
  controlRoom: async () => {
    if (fail) throw new Error('Connection failed');
    if (omitSignals) return { policy_gates: [], evidence_timeline: [], verifier_center: { recent_checks: [] } };
    return {
      architecture: { flows: [{
        id: 'READ', label: 'Read path', status: 'UNKNOWN',
        nodes: [{ label: '<img src=x>', source: 'Runtime', status: 'UNKNOWN' }]
      }] },
      overview: { trust_state: 'UNKNOWN', emergency_stop: false },
      runs: { active_count: 0, queue_depth: 0, completed_count: 0, failed_count: 0, recent: [] },
      plans: { pending_approvals: 0 },
      policy_gates: [{ name: 'Provider WRITE', source: 'policy', status: 'BLOCKED' }],
      capability_registry: { fail_closed_default: true, production_effects_enabled: false },
      evidence_timeline: [],
      verifier_center: { independent_verification_exposed: false, recent_checks: [] }
    };
  },
  state: { workspaces: [{ id: 'w1', name: '<img src=x>', environment: 'local' }] }
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'workflow_boards.js' });

(async () => {
  const namesAndFunctions = [
    ['ecosystem', 'loadEcosystemBoard'],
    ['lifecycle', 'loadLifecycleBoard'],
    ['authority', 'loadAuthorityBoard'],
    ['lineage', 'loadLineageBoard'],
    ['overlays', 'loadOverlaysBoard']
  ];
  for (const [name, fn] of namesAndFunctions) {
    await context[fn]();
    assert.ok(nodes[name].innerHTML.length > 400, name + ': missing content');
    assert.ok(!nodes[name].innerHTML.includes('<img src=x>'), name + ': unescaped data');
    assert.match(nodes[name].innerHTML, /REFERENČNÍ MODEL · NEJDE O RUNTIME STAV/, name + ': model provenance missing');
    assert.match(nodes[name].innerHTML, /DATA Z AUTORIZOVANÉHO API/, name + ': API provenance missing');
  }
  assert.match(nodes.ecosystem.innerHTML, /&lt;img src=x&gt;/);
  assert.match(nodes.overlays.innerHTML, /&lt;img src=x&gt;/);
  assert.match(nodes.authority.innerHTML, /BLOCKED/);
  assert.match(nodes.lineage.innerHTML, /Bez doložené nezávislé verifikace/);
  assert.match(nodes.lifecycle.innerHTML, /Nebyly vráceny žádné nedávné běhy/);
  assert.match(nodes.lifecycle.innerHTML, /tabindex="0" role="region" aria-label="Devět kroků/);
  assert.match(nodes.lineage.innerHTML, /tabindex="0" role="region" aria-label="Osm kroků/);
  assert.match(nodes.overlays.innerHTML, /tabindex="0" role="region" aria-label="Pět kroků/);
  assert.match(nodes.ecosystem.innerHTML, /tabindex="0" role="region" aria-label="Architektonická projekce/);
  for (const name of ['lifecycle', 'lineage', 'overlays']) {
    assert.match(nodes[name].innerHTML, /Diagram lze posouvat vodorovně/, name + ': scroll guidance missing');
  }
  const css = fs.readFileSync(
    path.resolve(__dirname, '../../voodoo_product/static/workflow_boards.css'), 'utf8'
  );
  assert.match(css, /\.wb-provenance-live\{/);
  assert.match(css, /\.wb-provenance-model\{/);
  assert.match(css, /\.wb-steps-evidence\{grid-template-columns:repeat\(8,minmax\(164px,1fr\)\)/);
  assert.match(css, /\.wb-profiles\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(css, /\.wb-steps:focus-visible/);
  assert.ok(css.includes('@media (max-width: 900px)'), '900px responsive breakpoint missing');
  assert.ok(css.includes('.board-view .wb-stats,') &&
    css.includes('grid-template-columns:repeat(2,minmax(0,1fr))'), 'two-column responsive stats missing');
  assert.ok(css.includes('#orchestration-graph .architecture-node .status'), 'architecture status layout missing');
  assert.ok(css.includes('align-content:start;overflow-wrap:anywhere'), 'architecture node compact alignment missing');
  assert.ok(css.includes('#orchestration-graph .architecture-path {align-items:flex-start}'), 'architecture flex stretch fix missing');
  assert.ok(css.includes('grid-auto-rows:max-content;'), 'architecture cards must fit content height');
  omitSignals = true;
  await context.loadAuthorityBoard();
  assert.match(nodes.authority.innerHTML, /UNKNOWN/);
  assert.doesNotMatch(nodes.authority.innerHTML, /INACTIVE/);
  assert.doesNotMatch(nodes.authority.innerHTML, /DISABLED/);
  await context.loadLineageBoard();
  assert.match(nodes.lineage.innerHTML, /UNKNOWN/);
  fail = true;
  await context.loadEcosystemBoard();
  assert.match(nodes.ecosystem.innerHTML, /UNKNOWN \/ NOT CONNECTED/);
  assert.doesNotMatch(nodes.ecosystem.innerHTML, /LIVE API DATA/);
  console.log('5_BOARD_RENDER_PASS EMPTY_STATE_PASS FAILURE_FAIL_CLOSED_PASS ESCAPING_PASS UNKNOWN_SIGNAL_PASS PROVENANCE_PASS SCROLL_REGION_PASS READABILITY_CSS_PASS MOBILE_BREAKPOINT_PASS ARCHITECTURE_STATUS_LAYOUT_PASS ARCHITECTURE_CARD_HEIGHT_PASS');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
