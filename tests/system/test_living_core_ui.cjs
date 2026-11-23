'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const staticRoot=path.resolve(__dirname,'../../voodoo_product/static');
const source=fs.readFileSync(path.join(staticRoot,'living_core.js'),'utf8');
const index=fs.readFileSync(path.join(staticRoot,'index.html'),'utf8');
const css=fs.readFileSync(path.join(staticRoot,'living_core.css'),'utf8');
assert.match(index,/assets\/living_core\.css/);
assert.match(index,/assets\/living_core\.js/);
assert.ok(index.indexOf('assets\/control_room.js')<index.indexOf('assets\/living_core.js'));
const ids=[...index.matchAll(/id="([^"]+)"/g)].map(match=>match[1]);
assert.equal(new Set(ids).size,ids.length,'HTML IDs must be unique');
assert.ok(css.includes('@media (prefers-reduced-motion:reduce)'));
assert.match(css,/@media \(max-width:560px\)[\s\S]*?\.sidebar \{[\s\S]*?grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/,'small screens must use a wrapping nav instead of horizontal overflow');
assert.ok(css.includes('@supports not (backdrop-filter:blur(1px))'));
const elements=new Map();
function element(id){
  if(!elements.has(id))elements.set(id,{id,innerHTML:'',textContent:'',classList:{contains:name=>id==='view-overview'&&name==='active'}});
  return elements.get(id);
}
const stages=new Map();
function stage(name){
  if(!stages.has(name)){
    const parts={
      '.lc-stage-state':{textContent:'',className:''},
      '.lc-stage-detail':{textContent:''},
      '.lc-stage-source':{textContent:''},
    };
    stages.set(name,{dataset:{},querySelector:selector=>parts[selector]||null,parts});
  }
  return stages.get(name);
}
const document={
  getElementById:element,
  querySelector(selector){
    const match=selector.match(/^\.lc-stage\[data-stage="([^"]+)"\]$/);
    return match?stage(match[1]):null;
  },
};
const sample={
  overview:{trust_state:'HEALTHY',receipt_integrity:{valid:true},audit_integrity:{valid:true}},
  plans:{pending_approvals:1,items:[{request_id:'cr_12345',title:'<Deploy candidate>',status:'REVIEW_REQUIRED',risk:'R1',environment:'staging'}]},
  runs:{active_count:1,queue_depth:2,completed_count:4,failed_count:0,recent:[{id:'ex_12345',title:'<run>',status:'RUNNING',environment:'staging',adapter:'echo'}]},
  verifier_center:{recent_checks:[{source:'LEGACY_RECEIPT',execution_id:'ex_12345',verification_status:'UNKNOWN'}]},
  evidence_timeline:[
    {kind:'INTENT_CAPTURED',title:'Pipeline request captured',status:'OBSERVED',source:'AUDIT',timestamp:'2026-11-23T17:59:00Z'},
    {kind:'APPROVAL',title:'Review recorded',status:'OBSERVED',source:'AUDIT',timestamp:'2026-11-23T18:00:00Z'}
  ],
};
let backendFails=false;
const context=vm.createContext({document,Date});
context.window=context;
context.controlRoom=async()=>{if(backendFails)throw new Error('projection unavailable');return sample};
context.loadOverview=async()=>{const data=await context.controlRoom();element('lc-metrics-content').innerHTML='Legacy KPI';return data};
vm.runInContext(source,context);
context.sample=sample;

(async()=>{
  vm.runInContext('window.voodooLivingCore.renderProjection(sample)',context);
  assert.equal(stage('intent').parts['.lc-stage-state'].textContent,'OBSERVED');
  assert.match(stage('intent').parts['.lc-stage-detail'].textContent,/Pipeline request captured/);
  assert.equal(stage('approval').parts['.lc-stage-detail'].textContent,
    '1 čekajících');
  assert.equal(stage('jit').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.match(stage('jit').parts['.lc-stage-detail'].textContent,/Nedostupné/);
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'RUNNING');
  assert.equal(stage('verification').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.equal(stage('evidence').parts['.lc-stage-state'].textContent,'OBSERVED');
  assert.match(element('lc-delivery-content').innerHTML,/&lt;run&gt;/);
  assert.match(element('lc-approvals-content').innerHTML,/&lt;Deploy candidate&gt;/);
  assert.match(element('lc-metrics-content').innerHTML,/Nedostupné/);
  assert.doesNotMatch(element('lc-metrics-content').innerHTML,/98\.7%|142 ms|1,248/);

  context.idleProjection={
    overview:{trust_state:'HEALTHY',receipt_integrity:{valid:true},audit_integrity:{valid:true}},
    plans:{pending_approvals:0,items:[]},
    runs:{active_count:0,queue_depth:1,completed_count:0,failed_count:2,recent:[{id:'ex_failed',status:'FAILED'}]},
    verifier_center:{recent_checks:[]},evidence_timeline:[]
  };
  vm.runInContext('window.voodooLivingCore.renderProjection(idleProjection)',context);
  assert.equal(stage('approval').parts['.lc-stage-state'].textContent,'NO_PENDING',
    'zero pending requests does not imply an approval was granted');
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'IDLE',
    'zero active runs does not imply a successful execution');
  assert.match(stage('execution').parts['.lc-stage-detail'].textContent,/1 ve frontě · 0 dokončených · 2 selhalo/);
  assert.match(css,/status\.NO_PENDING/);
  assert.match(css,/status\.IDLE/);

  await context.loadOverview();
  assert.doesNotMatch(element('lc-metrics-content').innerHTML,/Legacy KPI/,
    'the legacy overview renderer must not overwrite the Living Core projection');

  backendFails=true;
  await assert.rejects(vm.runInContext('window.controlRoom()',context),/projection unavailable/);
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.match(element('lc-evidence-content').textContent,/Nedostupné/);
  assert.equal(element('health-badge').textContent,'UNKNOWN');
  assert.equal(element('health-badge').className,'status UNKNOWN');
  assert.equal(element('environment-badge').textContent,'Nedostupné');
  assert.doesNotMatch(element('overview-kpis').innerHTML,/HEALTHY|PASS/);
  console.log('PASS: actual event mapping, unavailable JIT, escaped data, no invented metrics, fail-closed API and stale KPI clearing');
})().catch(error=>{console.error(error);process.exitCode=1});
