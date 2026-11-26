'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const staticRoot=path.resolve(__dirname,'../../voodoo_product/static');
const source=fs.readFileSync(path.join(staticRoot,'living_core.js'),'utf8');
const nativeSource=fs.readFileSync(path.join(staticRoot,'control_room.js'),'utf8');
const index=fs.readFileSync(path.join(staticRoot,'index.html'),'utf8');
const css=fs.readFileSync(path.join(staticRoot,'living_core.css'),'utf8');
assert.match(index,/assets\/living_core\.css/);
assert.match(index,/assets\/living_core\.js/);
assert.ok(index.indexOf('assets\/control_room.js')<index.indexOf('assets\/living_core.js'));
const ids=[...index.matchAll(/id="([^"]+)"/g)].map(match=>match[1]);
assert.equal(new Set(ids).size,ids.length,'HTML IDs must be unique');

const plansNav=[...index.matchAll(/<button\b[^>]*data-view="plans"[^>]*class="nav"[^>]*>([^<]*)<\/button>/g)];
assert.equal(plansNav.length,1,'Approvals and JIT must be a single navigation destination');
assert.equal(plansNav[0][1],'Požadavky');
assert.doesNotMatch(index,/data-view="plans"[^>]*>JIT Execution<\/button>/);
assert.match(index,/<h1>Požadavky<\/h1>/);
assert.match(index,/Spuštění zůstává dostupné jen u způsobilého požadavku a podléhá serverové kontrole oprávnění\./);
assert.match(index,/id="plans-table"/,'native request execution surface must remain available');
assert.doesNotMatch(index,/<button data-view="registry" class="nav">/,'capability registry is contextual, not primary navigation');
assert.match(index,/id="request-capability-context"/);
assert.match(index,/id="change-review-button"/);

assert.ok(css.includes('@media (prefers-reduced-motion:reduce)'));
assert.match(css,/@media \(max-width:560px\)[\s\S]*?\.sidebar \{[\s\S]*?grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/,'small screens must use a wrapping nav instead of horizontal overflow');
assert.ok(css.includes('@supports not (backdrop-filter:blur(1px))'));
assert.match(index,/id="lc-focus-open"[^>]*data-refresh="plans"/,'native navigation attaches to the button on initial DOM load');
const elements=new Map();
function element(id){
  if(!elements.has(id)){
    const classes=new Set(id==='view-overview'?['active']:[]);
    elements.set(id,{
      id,_html:'',_text:'',value:'',disabled:false,dataset:{},listeners:{},
      get innerHTML(){return this._html},
      set innerHTML(value){this._html=String(value);this._text=''},
      get textContent(){return this._text},
      set textContent(value){this._text=String(value);this._html=''},
      setAttribute(name,value){this[name]=value},
      addEventListener(name,callback){
        const old=this.listeners[name];
        this.listeners[name]=old?event=>Promise.all([old(event),callback(event)]):callback;
      },
      replaceChildren(){this.innerHTML='';this.value=''},
      focus(){this.didFocus=true},
      classList:{
        contains:name=>classes.has(name),add:name=>classes.add(name),remove:name=>classes.delete(name),
        toggle(name,on){if(on)classes.add(name);else classes.delete(name)}
      }
    });
  }
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
  querySelectorAll(selector){return selector==='.view'?['view-overview','view-casebook'].map(element):[]},
  querySelector(selector){
    const match=selector.match(/^\.lc-stage\[data-stage="([^"]+)"\]$/);
    return match?stage(match[1]):null;
  },
};
const sample={
  overview:{environment:'staging',trust_state:'HEALTHY',emergency_stop:false,receipt_integrity:{valid:true},audit_integrity:{valid:true}},
  plans:{pending_approvals:1,items:[{request_id:'cr_12345',title:'<Deploy candidate>',status:'REVIEW_REQUIRED',risk:'R1',environment:'staging'}]},
  runs:{active_count:1,queue_depth:2,completed_count:4,failed_count:0,recent:[{id:'ex_12345',title:'<run>',status:'RUNNING',environment:'staging',adapter:'echo'}]},
  verifier_center:{canonical_result_count:0,recent_checks:[{source:'LEGACY_RECEIPT',execution_id:'ex_12345',verification_status:'UNKNOWN'}]},
  evidence_timeline:[
    {kind:'INTENT_CAPTURED',title:'Pipeline request captured',status:'OBSERVED',source:'AUDIT',timestamp:'2026-11-23T17:59:00Z'},
    {kind:'APPROVAL',title:'Review recorded',status:'OBSERVED',source:'AUDIT',timestamp:'2026-11-23T18:00:00Z'}
  ],
};
let backendFails=false,snapshot=sample,nextResponse=null,overviewCalls=0;
const response=body=>({ok:true,status:200,json:async()=>body});
function deferOverview(){
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no});
  nextResponse=promise;
  return {resolve:body=>resolve(response(body)),reject};
}
const storage=new Map();
const context=vm.createContext({
  document,Date,setTimeout:()=>0,
  sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,String(value)),removeItem:key=>storage.delete(key)},
  fetch:async (url,options)=>{
    if(url==='/api/v1/control-room'){
      overviewCalls++;
      if(nextResponse){const pending=nextResponse;nextResponse=null;return pending}
      if(backendFails)throw new Error('projection unavailable');
      return response(snapshot);
    }
    if(url==='/api/v1/bootstrap/status')return response({required:false});
    if(url==='/api/v1/auth/logout')return response({ok:true});
    if(url==='/api/v1/casebook/tasks')return response({schema:'voodoo-casebook/bound-task-index/v1',items:[],has_more:false,journal_integrity:'NOT_CHECKED_BY_INDEX'});
    throw new Error('Unexpected fetch: '+url);
  },
  loadEcosystemBoard:()=>{},loadLifecycleBoard:()=>{},loadAuthorityBoard:()=>{},
  loadLineageBoard:()=>{},loadOverlaysBoard:()=>{}
});
context.window=context;
vm.runInContext(nativeSource,context,{filename:'control_room.js'});
vm.runInContext(source,context,{filename:'living_core.js'});
vm.runInContext("state.token='test-token'",context);
context.sample=sample;

(async()=>{
  vm.runInContext('window.voodooLivingCore.renderProjection(sample)',context);
  assert.equal(stage('intent').parts['.lc-stage-state'].textContent,'OBSERVED');
  assert.match(stage('intent').parts['.lc-stage-detail'].textContent,/Pipeline request captured/);
  assert.equal(element('lc-focus-state').textContent,'REVIEW_REQUIRED');
  assert.equal(element('lc-focus-open').dataset.refresh,'plans');
  assert.equal(element('lc-focus-open').disabled,false);
  assert.match(element('lc-focus-summary').textContent,/1 čekajících/);
  assert.equal(stage('approval').parts['.lc-stage-detail'].textContent,
    '1 čekajících');
  assert.equal(stage('jit').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.match(stage('jit').parts['.lc-stage-detail'].textContent,/Nedostupné/);
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'RUNNING');
  assert.equal(stage('verification').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.equal(stage('evidence').parts['.lc-stage-state'].textContent,'OBSERVED');
  assert.match(element('lc-delivery-content').innerHTML,/&lt;run&gt;/);
  assert.match(element('lc-approvals-content').innerHTML,/&lt;Deploy candidate&gt;/);
  assert.match(element('lc-metrics-content').innerHTML,/Kanonické výsledky \(výřez\)/);
  assert.doesNotMatch(element('lc-metrics-content').innerHTML,/98\.7%|142 ms|1,248|Agents|Latency|Throughput|Success rate/);

  context.idleProjection={
    overview:sample.overview,
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
  assert.equal(element('lc-focus-state').textContent,'REVIEW_REQUIRED','queued work must precede historical failures');
  assert.equal(element('lc-focus-open').dataset.refresh,'plans');
  assert.match(element('lc-focus-summary').textContent,/1 rozpracovaných/);
  context.idleProjection.runs.queue_depth=0;
  vm.runInContext('window.voodooLivingCore.renderProjection(idleProjection)',context);
  assert.equal(element('lc-focus-state').textContent,'FAILED');
  assert.equal(element('lc-focus-open').dataset.refresh,'runs');
  assert.match(element('lc-focus-summary').textContent,/2 neúspěšných/);
  context.noPending={
    overview:sample.overview,plans:{pending_approvals:0,items:[]},
    runs:{active_count:0,queue_depth:0,failed_count:0,recent:[]},
    verifier_center:{recent_checks:[]},evidence_timeline:[]
  };
  vm.runInContext('window.voodooLivingCore.renderProjection(noPending)',context);
  assert.equal(element('lc-focus-state').textContent,'NO_PENDING');
  assert.equal(element('lc-focus-open').dataset.refresh,'casebook');
  assert.match(element('lc-focus-title').textContent,/načteném výřezu/);
  const render=projection=>context.voodooLivingCore.renderProjection(projection);
  render({...sample,overview:{...sample.overview,emergency_stop:true}});
  assert.equal(element('lc-focus-state').textContent,'BLOCKED');
  assert.equal(element('lc-focus-open').dataset.refresh,'health');
  render({...sample,overview:{...sample.overview,audit_integrity:{valid:false}}});
  assert.equal(element('lc-focus-state').textContent,'BLOCKED');
  assert.equal(element('lc-focus-open').dataset.refresh,'evidence');
  render({...sample,overview:{...sample.overview,audit_integrity:{}}});
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN');
  render({...context.noPending,plans:{pending_approvals:-1},runs:{active_count:-1}});
  assert.equal(stage('approval').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN');
  render({...context.noPending,verifier_center:{recent_checks:[
    {source:'LEGACY_RECEIPT',verification_status:'UNKNOWN'},
    {source:'VERIFICATION_RESULT_V1',verification_status:'NOT_VERIFIED'}
  ]}});
  assert.equal(element('lc-focus-state').textContent,'NOT_VERIFIED');
  assert.equal(element('lc-focus-open').dataset.refresh,'verifier');
  for(const verdict of ['VERIFIED','FAILED','verified',null]){
    render({...context.noPending,verifier_center:{recent_checks:[{source:'VERIFICATION_RESULT_V1',verification_status:verdict}]}});
    assert.equal(stage('verification').parts['.lc-stage-state'].textContent,verdict==='VERIFIED'?'VERIFIED':'UNKNOWN');
    assert.equal(element('lc-focus-state').textContent,verdict==='VERIFIED'?'NO_PENDING':'UNKNOWN');
    assert.equal(element('lc-focus-open').dataset.refresh,verdict==='VERIFIED'?'casebook':'verifier');
  }
  render({...context.noPending,verifier_center:{recent_checks:[{source:'LEGACY_RECEIPT',verification_status:'VERIFIED'}]}});
  assert.equal(stage('verification').parts['.lc-stage-state'].textContent,'UNKNOWN');

  const before=overviewCalls;
  await context.loadOverview();
  assert.equal(overviewCalls,before+1,'one native refresh, no duplicate projection fetch');
  assert.equal(element('lc-focus-state').textContent,'REVIEW_REQUIRED');
  assert.equal(element('health-badge').textContent,'HEALTHY');
  await context.loadView('casebook');
  assert.equal(element('health-badge').textContent,'UNKNOWN','header must not imply freshness outside Overview');
  assert.equal(element('environment-badge').textContent,'Nedostupné');
  await context.loadView('overview');
  const old=deferOverview(),oldLoad=context.loadOverview();
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN','refresh must immediately invalidate old focus');
  snapshot=context.noPending;
  await context.loadOverview();
  old.resolve(sample);await oldLoad;
  assert.equal(element('lc-focus-state').textContent,'NO_PENDING','late success cannot overwrite newer overview');
  const staleError=deferOverview(),errorLoad=context.loadOverview();
  await context.loadOverview();
  staleError.reject(new Error('old failure'));await errorLoad;
  assert.equal(element('lc-focus-state').textContent,'NO_PENDING','late failure cannot clear newer overview');
  const leaving=deferOverview(),leaveLoad=context.loadOverview();
  await context.loadView('casebook');
  leaving.resolve(sample);await leaveLoad;
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN','late response must not repopulate hidden overview');
  await context.loadView('overview');
  assert.equal(element('lc-focus-state').textContent,'NO_PENDING');
  const other=deferOverview(),otherReader=context.controlRoom();
  await context.loadOverview();other.resolve(sample);await otherReader;
  assert.equal(element('lc-focus-state').textContent,'NO_PENDING','other readers must not render Overview');
  const logoutRace=deferOverview(),logoutLoad=context.loadOverview();
  await element('logout-button').listeners.click();
  logoutRace.resolve(sample);await logoutLoad;
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN');
  assert.doesNotMatch(element('risk-overview').innerHTML,/R0/);
  vm.runInContext("state.token='new-token'",context);
  snapshot=sample;
  await context.loadView('overview');
  assert.equal(element('lc-focus-state').textContent,'REVIEW_REQUIRED');

  backendFails=true;
  await assert.rejects(vm.runInContext('window.loadOverview()',context),/projection unavailable/);
  assert.equal(stage('execution').parts['.lc-stage-state'].textContent,'UNKNOWN');
  assert.match(element('lc-evidence-content').textContent,/Nedostupné/);
  assert.match(element('integrity-overview').textContent,/Nedostupné/);
  assert.match(element('risk-overview').textContent,/Nedostupné/);
  assert.equal(element('health-badge').textContent,'UNKNOWN');
  assert.equal(element('health-badge').className,'status UNKNOWN');
  assert.equal(element('environment-badge').textContent,'Nedostupné');
  assert.doesNotMatch(element('overview-kpis').innerHTML,/HEALTHY|PASS/);
  assert.equal(element('lc-focus-state').textContent,'UNKNOWN');
  assert.equal(element('lc-focus-open').disabled,true,'stale priority must not remain actionable');
  assert.equal(element('lc-focus-open').dataset.refresh,'');

  const readCalls=[];
  const viewCalls=[];
  context.loadView=async name=>{viewCalls.push(name);return true};
  context.loadCasebookTask=async session=>readCalls.push(session);
  const session='voodoo-one-p0-desktop-20261123';
  element('lc-casebook-id').value=session;
  await element('lc-casebook-form').listeners.submit({preventDefault(){}});
  assert.deepEqual(viewCalls,['casebook']);
  assert.deepEqual(readCalls,[session],'must use native scoped CASEBOOK reader');
  assert.equal(element('casebook-session-id').value,session);
  assert.equal(element('casebook-session-id').didFocus,true);
  element('lc-casebook-id').value='../unscoped';
  await element('lc-casebook-form').listeners.submit({preventDefault(){}});
  assert.equal(readCalls.length,1,'invalid ID must never call the API');
  assert.match(element('lc-casebook-hint').textContent,/Neplatné/);
  let resolveNavigation;
  context.loadView=()=>new Promise(resolve=>{resolveNavigation=resolve});
  element('lc-casebook-id').value=session;
  const pending=element('lc-casebook-form').listeners.submit({preventDefault(){}});
  element('logout-button').listeners.click();
  resolveNavigation(false);
  await pending;
  assert.equal(readCalls.length,1,'stale navigation must not start a task read');
  assert.equal(element('lc-casebook-id').value,'','logout must clear session context');
  console.log('PASS: native Overview lifecycle, safety-first focus, real scoped summaries, escaped data, refresh/navigation/logout races and native journal route');
})().catch(error=>{console.error(error);process.exitCode=1});
