const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const client = fs.readFileSync('voodoo_product/static/control_room.js', 'utf8');
const html = fs.readFileSync('voodoo_product/static/index.html', 'utf8');
const css = fs.readFileSync('voodoo_product/static/living_core.css', 'utf8');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    const classes = new Set();
    elements.set(id, {
      id, listeners: {}, dataset: {}, disabled: false, hidden: false, value: '',
      _html: '', _text: '',
      get innerHTML(){return this._html},
      set innerHTML(value){this._html=String(value);this._text=''},
      get textContent(){return this._text},
      set textContent(value){this._text=String(value);this._html=''},
      replaceChildren(){this.innerHTML=''},
      addEventListener(name,callback){this.listeners[name]=callback},
      setAttribute(name,value){this[name]=value},
      classList:{
        contains:name=>classes.has(name),add:name=>classes.add(name),
        remove:name=>classes.delete(name),toggle(name,on){if(on)classes.add(name);else classes.delete(name)}
      }
    });
  }
  return elements.get(id);
}
const normal = {
  overview:{environment:'staging',trust_state:'HEALTHY',emergency_stop:false,production_effects_enabled:false,
    receipt_integrity:{valid:true},audit_integrity:{valid:true}},
  runtime_health:[
    {name:'API',status:'HEALTHY',detail:'FastAPI product surface'},
    {name:'Database',status:'HEALTHY',detail:'sqlite'},
    {name:'Evidence',status:'NOT_CHECKED_BY_LIVENESS',detail:'liveness projection'},
    {name:'Identity',status:'BUILTIN_SESSION',detail:'configured provider'},
    {name:'Canonical runtime',status:'DISABLED',detail:'read path activation'}
  ],
  evidence_timeline:[
    {kind:'AUDIT_EVENT',source:'AUDIT_LEDGER',status:'RECORDED',title:'<audit>',timestamp:'2026-11-26T00:00:00Z'},
    {kind:'EXECUTION',source:'LEGACY_EXECUTION',status:'SUCCEEDED',title:'not audit'}
  ],
  governance:{environment:'staging',production_effects_enabled:false,approval_policy_compatibility_enabled:false,identity_provider:'builtin_session',trusted_hosts:['localhost','<host>'],cors_origins:[],unexpected_secret:'never-render-this'}
};
let snapshot=structuredClone(normal),live={status:'HEALTHY',database:'HEALTHY',database_backend:'sqlite',schema_version:15},
  operations={schema:'vone.canonical-operation-api-status/v1',configured:false,read_terminal_configured:false,
    write_routes_exposed:false,provider_write_effects_exposed:false,server_time_utc:'2026-11-26T00:00:00Z'},
  principal={id:'user1',username:'<operator>',role:'administrator'},postCalls=[],postDeferred=null,primaryDeferred=null,postError=false,meDenied=false;
const response=(body,status=200)=>({ok:status>=200&&status<300,status,json:async()=>body});
function deferred(){
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no});
  return {promise,resolve,reject};
}
const storage=new Map();
const passportRequests=[];
class RunPassportButton {
  constructor(id){this.dataset={passportExecutionId:id}}
  closest(selector){return selector==='button[data-passport-execution-id]'?this:null}
}

let wallNow=100000,monotonicNow=5000,timerId=0;
const timers=new Map();
const advance=ms=>{wallNow+=ms;monotonicNow+=ms};
const context=vm.createContext({
  Element:RunPassportButton,
  document:{getElementById:element,querySelectorAll:selector=>selector==='.view'?['view-health','view-overview','view-casebook','view-governance','view-runs'].map(element):[]},
  sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,val)=>storage.set(key,String(val)),removeItem:key=>storage.delete(key)},
  Date:class extends Date{static now(){return wallNow}},
  performance:{now:()=>monotonicNow},
  setTimeout:fn=>{const id=++timerId;timers.set(id,fn);return id},
  clearTimeout:id=>timers.delete(id),console,
  fetch:async(url,options={})=>{
    if(url.startsWith('/api/v1/operations/')&&url.endsWith('/passport')){
      assert.equal(options.method||'GET','GET');
      const id=decodeURIComponent(url.slice('/api/v1/operations/'.length,-'/passport'.length));
      passportRequests.push(id);
      if(id==='ex_legacy_001')return response({detail:'not found'},404);
      return response({schema:'vone.operation-passport/v1',execution_id:id,
        operation:{},authority:{},dispatch:{},runtime:{status:'COMPLETED'},
        verification:{status:'NOT_PERSISTED',verdict:'UNKNOWN',independent_verification_exposed:false},
        integrity:{canonical_json_validated:true,lineage_bindings_validated:true,independent_verification_validated:false}});
    }
    switch(url){
      case '/api/v1/bootstrap/status':return response({required:false});
      case '/api/v1/auth/logout':return response({});
      case '/api/v1/casebook/tasks':return response({schema:'voodoo-casebook/bound-task-index/v1',items:[],has_more:false,journal_integrity:'NOT_CHECKED_BY_INDEX'});
      case '/api/v1/control-room':
        if(primaryDeferred){const d=primaryDeferred;primaryDeferred=null;return d.promise;}
        if(!snapshot)throw Error('unavailable');
        return response(snapshot);
      case '/api/v1/health':if(!live)throw Error('liveness unavailable');return response(live);
      case '/api/v1/operations/status':if(!operations)throw Error('ops unavailable');return response(operations);
      case '/api/v1/me':return meDenied?response({detail:'denied'},401):response(principal);
      case '/api/v1/system/emergency-stop':
        assert.equal(options.method,'POST');
        postCalls.push(JSON.parse(options.body));
        if(postDeferred){const d=postDeferred;postDeferred=null;return d.promise;}
        if(postError)throw Error('ambiguous');
        return response({});
      default:throw Error('Unexpected API '+url);
    }
  },
  loadEcosystemBoard:()=>{},loadLifecycleBoard:()=>{},loadAuthorityBoard:()=>{},loadLineageBoard:()=>{},loadOverlaysBoard:()=>{}
});
context.window=context;
context.voodooLivingCore={renderProjection:()=>{},renderUnavailable:()=>{}};
vm.runInContext(client,context,{filename:'control_room.js'});
const run=expression=>vm.runInContext(expression,context);
const login=()=>run("state.token='test-token';state.me={role:'administrator'}");
const buttonsDisabled=()=>{assert.equal(element('activate-stop').disabled,true);assert.equal(element('clear-stop').disabled,true)};
const reset=()=>{
  snapshot=structuredClone(normal);live={status:'HEALTHY',database:'HEALTHY',database_backend:'sqlite',schema_version:15};
  operations={schema:'vone.canonical-operation-api-status/v1',configured:false,read_terminal_configured:false,
    write_routes_exposed:false,provider_write_effects_exposed:false,server_time_utc:'2026-11-26T00:00:00Z'};
  principal={id:'user1',username:'<operator>',role:'administrator'};meDenied=false;postError=false;
};
(async()=>{
  assert.equal(html.match(/data-view="plans"/g).length,1);
  assert.match(html,/id="view-health" class="view lc-screen system-screen"/);
  assert.match(css,/#view-health .system-component-grid/);
  const ids=[...html.matchAll(/id="([^"]+)"/g)].map(match=>match[1]);
  assert.equal(ids.length,new Set(ids).size,'unique IDs');
  login();await context.loadView('health');
  assert.equal(element('health-overall').textContent,'HEALTHY');
  assert.equal(element('activate-stop').disabled,false);assert.equal(element('clear-stop').disabled,true);
  assert.match(element('stop-state').textContent,/staging/);
  assert.match(element('health-perimeter').innerHTML,/Receipt řetězec/);
  assert.match(element('health-components').innerHTML,/Canonical runtime \/ G8 READ/);
  assert.match(element('health-components').innerHTML,/CASEBOOK/);
  assert.match(element('health-components').innerHTML,/UNKNOWN/);
  assert.match(element('health-events').innerHTML,/&lt;audit&gt;/);
  assert.doesNotMatch(element('health-events').innerHTML,/not audit/);
  assert.match(element('health-versions').innerHTML,/15/);
  assert.match(element('health-versions').innerHTML,/NOT_EXPOSED/);
  // Configuration is not execution proof or live component health.
  operations.configured=true;operations.read_terminal_configured=true;
  snapshot.runtime_health[4].status='ENABLED';
  await context.loadRuntimeHealth();
  assert.match(element('health-components').innerHTML,/CONFIGURED/);
  assert.match(element('health-components').innerHTML,/Neprokazuje funkční provider/);
  assert.doesNotMatch(element('health-components').innerHTML,/VERIFIED/);
  reset();
  snapshot.overview.emergency_stop=true;snapshot.overview.trust_state='INCIDENT';snapshot.runtime_health[0].status='EMERGENCY_STOP';live.status='EMERGENCY_STOP';
  await context.loadRuntimeHealth();
  assert.equal(element('health-overall').textContent,'INCIDENT');
  assert.equal(element('activate-stop').disabled,true);assert.equal(element('clear-stop').disabled,false);
  live=null;await context.loadRuntimeHealth();buttonsDisabled();
  element('stop-reason').value='blocked clear';await context.setStop(false);assert.equal(postCalls.length,0);
  live={status:'EMERGENCY_STOP',database:'HEALTHY'};snapshot.overview.audit_integrity={valid:false};
  await context.loadRuntimeHealth();buttonsDisabled();
  await context.setStop(false);assert.equal(postCalls.length,0);
  snapshot.overview.audit_integrity={valid:true};live.database='UNAVAILABLE';await context.loadRuntimeHealth();buttonsDisabled();
  live.database='HEALTHY';snapshot.runtime_health[1].status='UNAVAILABLE';await context.loadRuntimeHealth();buttonsDisabled();
  snapshot.runtime_health[1].status='HEALTHY';await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  // Expiration is enforced synchronously even when the browser delays timers.
  element('stop-reason').value='freshness test';advance(30000);
  await context.setStop(false);buttonsDisabled();assert.equal(postCalls.length,0);
  assert.equal(element('stop-reason').value,'freshness test');
  assert.match(element('health-action-feedback').textContent,/vypršela/);
  await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  const oldExpiry=timers.get(timerId);await context.loadRuntimeHealth();oldExpiry();
  assert.equal(element('clear-stop').disabled,false,'old timer must not revoke new authority');
  const expiry=timers.get(timerId);advance(30000);expiry();buttonsDisabled();
  await context.setStop(false);assert.equal(postCalls.length,0);
  await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  wallNow-=1;await context.setStop(false);buttonsDisabled();assert.equal(postCalls.length,0);
  wallNow+=1;await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  // A slow diagnostic read cannot grant a new 30-second window on completion.
  const slow=deferred();primaryDeferred=slow;const slowLoad=context.loadRuntimeHealth();
  advance(30001);slow.resolve(response(snapshot));await slowLoad;buttonsDisabled();
  await context.setStop(false);assert.equal(postCalls.length,0);
  await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  // Contradictory stop snapshots do not enable either control.
  live.status='HEALTHY';await context.loadRuntimeHealth();buttonsDisabled();
  assert.match(element('health-problems').innerHTML,/Rozpor mezi čteními/);
  for(const missing of ['API','Database']){
    reset();snapshot.runtime_health=snapshot.runtime_health.filter(row=>row.name!==missing);
    await context.loadRuntimeHealth();assert.equal(element('health-overall').textContent,'UNKNOWN');
    assert.match(element('health-problems').innerHTML,/Neúplná diagnostika/);
  }
  reset();snapshot.runtime_health.push({...snapshot.runtime_health[0]});
  await context.loadRuntimeHealth();assert.equal(element('health-overall').textContent,'UNKNOWN');
  reset();snapshot.runtime_health[1].status='UNAVAILABLE';
  await context.loadRuntimeHealth();assert.equal(element('health-overall').textContent,'INCIDENT');
  reset();snapshot.overview.audit_integrity={valid:false};await context.loadRuntimeHealth();
  assert.equal(element('health-overall').textContent,'INCIDENT');
  assert.match(element('health-problems').innerHTML,/Integrita evidence/);
  reset();principal.role='viewer';await context.loadRuntimeHealth();buttonsDisabled();
  element('stop-reason').value='no permission';await context.setStop(true);assert.equal(postCalls.length,0);
  reset();snapshot.overview.emergency_stop=undefined;await context.loadRuntimeHealth();buttonsDisabled();
  assert.equal(element('health-overall').textContent,'UNKNOWN');
  reset();live=null;operations=null;await context.loadRuntimeHealth();
  assert.equal(element('health-overall').textContent,'UNKNOWN');
  assert.match(element('health-problems').innerHTML,/Neúplná diagnostika/);
  assert.equal(element('activate-stop').disabled,false,'protective activation remains available on explicit inactive primary state');
  reset();await context.loadRuntimeHealth();snapshot=null;
  await assert.rejects(context.loadRuntimeHealth(),/unavailable/);buttonsDisabled();
  assert.equal(element('health-overall').textContent,'UNKNOWN');
  assert.equal(element('health-json').textContent,'');
  assert.doesNotMatch(element('health-summary').innerHTML,/HEALTHY/);
  reset();meDenied=true;await assert.rejects(context.loadRuntimeHealth(),/denied/);buttonsDisabled();
  reset();
  // Late old success/failure cannot change newer health or controls.
  const stale=deferred();primaryDeferred=stale;const old=context.loadRuntimeHealth();
  buttonsDisabled();assert.equal(element('health-json').textContent,'');
  snapshot.overview.emergency_stop=true;snapshot.overview.trust_state='INCIDENT';snapshot.runtime_health[0].status='EMERGENCY_STOP';live.status='EMERGENCY_STOP';
  await context.loadRuntimeHealth();stale.resolve(response(normal));await old;
  assert.equal(element('health-overall').textContent,'INCIDENT');assert.equal(element('clear-stop').disabled,false);
  const oldError=deferred();primaryDeferred=oldError;const err=context.loadRuntimeHealth();
  await context.loadRuntimeHealth();oldError.reject(Error('stale failure'));await err;
  assert.equal(element('clear-stop').disabled,false);
  const leaving=deferred();primaryDeferred=leaving;const leave=context.loadRuntimeHealth();
  await context.loadView('overview');leaving.resolve(response(normal));await leave;buttonsDisabled();
  assert.equal(element('health-json').textContent,'');
  reset();await context.loadView('health');
  const logoutRace=deferred();primaryDeferred=logoutRace;const logging=context.loadRuntimeHealth();
  element('stop-reason').value='sensitive local reason';await element('logout-button').listeners.click();
  logoutRace.resolve(response(normal));await logging;buttonsDisabled();
  assert.equal(element('stop-reason').value,'');assert.equal(element('health-json').textContent,'');
  // Explicit stop click sends one request, blocks double click, readback only; no automatic retry.
  login();reset();await context.loadView('health');element('stop-reason').value='test stop';
  const pending=deferred();postDeferred=pending;const action=context.setStop(true);
  buttonsDisabled();await context.setStop(true);assert.equal(postCalls.length,1);
  snapshot.overview.emergency_stop=true;snapshot.overview.trust_state='INCIDENT';snapshot.runtime_health[0].status='EMERGENCY_STOP';live.status='EMERGENCY_STOP';
  pending.resolve(response({}));await action;
  assert.equal(postCalls.length,1);assert.equal(element('clear-stop').disabled,false);
  assert.match(element('health-action-feedback').textContent,/Server potvrdil/);
  postError=true;element('stop-reason').value='test clear';await context.setStop(false);
  assert.equal(postCalls.length,2);
  assert.match(element('health-action-feedback').textContent,/není potvrzen/);
  assert.equal(element('clear-stop').disabled,false);
  // A reply after logout cannot repaint or dispatch a new action.
  postError=false;const late=deferred();postDeferred=late;element('stop-reason').value='late clear';const lateAction=context.setStop(false);
  await element('logout-button').listeners.click();late.resolve(response({}));await lateAction;
  buttonsDisabled();assert.equal(postCalls.length,3);assert.equal(element('health-json').textContent,'');
  assert.equal(element('health-action-feedback').textContent,'');
  // Same-session leave/return: the old POST must not mutate newer UI or authority.
  login();reset();await context.loadView('health');element('stop-reason').value='old intent';
  const race=deferred();postDeferred=race;const oldAction=context.setStop(true);
  await context.loadView('overview');await context.loadView('health');buttonsDisabled();
  element('stop-reason').value='new operator intent';
  const newerFeedback=element('health-action-feedback').textContent;
  snapshot.overview.emergency_stop=true;snapshot.overview.trust_state='INCIDENT';snapshot.runtime_health[0].status='EMERGENCY_STOP';live.status='EMERGENCY_STOP';
  race.resolve(response({}));await oldAction;
  assert.equal(element('stop-reason').value,'new operator intent');
  assert.equal(element('health-action-feedback').textContent,newerFeedback);
  buttonsDisabled();await context.setStop(true);await context.setStop(false);assert.equal(postCalls.length,4);
  await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  // A refresh begun during a POST is not action authority even if it finishes later.
  element('stop-reason').value='old clear';const clearRace=deferred();postDeferred=clearRace;
  const oldClear=context.setStop(false);
  const delayedRead=deferred();primaryDeferred=delayedRead;const newerRead=context.loadRuntimeHealth();
  element('stop-reason').value='new reason after refresh';
  clearRace.reject(Error('ambiguous old POST'));await oldClear;
  delayedRead.resolve(response(snapshot));await newerRead;
  assert.equal(element('stop-reason').value,'new reason after refresh');
  assert.match(element('health-action-feedback').textContent,/Čtení začalo během/);
  buttonsDisabled();await context.setStop(false);assert.equal(postCalls.length,5);
  await context.loadRuntimeHealth();assert.equal(element('clear-stop').disabled,false);
  await element('logout-button').listeners.click();
  console.log('PASS: native Systém diagnostics, real source truth, asymmetric safety guard, malformed/failed reads, refresh/navigation/logout races, explicit single POST and readback');
  // Settings: actual allowlisted fields, no arbitrary configuration or secret rendering.
  login();reset();await context.loadView('governance');
  assert.equal(element('settings-configuration-state').textContent,'OBSERVED');
  assert.match(element('settings-identity').innerHTML,/&lt;operator&gt;/);
  assert.match(element('settings-network').innerHTML,/&lt;host&gt;/);
  assert.match(element('settings-network').innerHTML,/Žádné položky/);
  for(const id of ['settings-identity','governance-grid','settings-network','settings-integrations'])
    assert.doesNotMatch(element(id).innerHTML,/never-render-this|unexpected_secret/);
  assert.match(element('settings-integrations').innerHTML,/DISABLED/);
  snapshot.governance.production_effects_enabled=true;await context.loadGovernance();
  assert.equal(element('settings-configuration-state').textContent,'UNKNOWN');
  assert.doesNotMatch(element('governance-grid').innerHTML,/ENABLED/);
  reset();snapshot.governance.trusted_hosts='malformed';await context.loadGovernance();
  assert.match(element('settings-network').innerHTML,/UNKNOWN/);
  reset();element('settings-reduced-motion').checked=true;
  element('settings-reduced-motion').listeners.change();
  assert.equal(element('app-shell').classList.contains('settings-reduced-motion'),true);
  assert.equal(storage.size,0,'local motion preference must not store server or session data');
  await context.loadView('overview');assert.equal(element('app-shell').classList.contains('settings-reduced-motion'),true);
  await context.loadView('governance');
  const staleSettings=deferred();primaryDeferred=staleSettings;const staleRead=context.loadGovernance();
  assert.equal(element('settings-identity').innerHTML,'');
  snapshot.governance.environment='local';snapshot.overview.environment='local';await context.loadGovernance();
  staleSettings.resolve(response(normal));await staleRead;
  assert.match(element('governance-grid').innerHTML,/LOCAL/);
  const staleSettingsError=deferred();primaryDeferred=staleSettingsError;const staleFail=context.loadGovernance();
  await context.loadGovernance();staleSettingsError.reject(Error('stale settings'));await staleFail;
  assert.match(element('governance-grid').innerHTML,/LOCAL/);
  const settingsLeave=deferred();primaryDeferred=settingsLeave;const leavingSettings=context.loadGovernance();
  await context.loadView('overview');settingsLeave.resolve(response(normal));await leavingSettings;
  assert.equal(element('settings-network').innerHTML,'');
  reset();await context.loadView('governance');snapshot=null;
  await assert.rejects(context.loadGovernance(),/unavailable/);assert.equal(element('settings-configuration-state').textContent,'UNKNOWN');
  reset();meDenied=true;await assert.rejects(context.loadGovernance(),/denied/);
  assert.equal(element('settings-identity').innerHTML,'');
  reset();const settingsLogout=deferred();primaryDeferred=settingsLogout;const logoutSettings=context.loadGovernance();
  await element('logout-button').listeners.click();settingsLogout.resolve(response(normal));await logoutSettings;
  assert.equal(element('settings-identity').innerHTML,'');
  assert.equal(element('app-shell').classList.contains('settings-reduced-motion'),false);
  assert.equal(element('settings-reduced-motion').checked,false);
  assert.equal(postCalls.length,5,'Settings must not issue mutations');
  console.log('PASS: native Nastavení, allowlisted read-only config, escaped identity/network, contradictions UNKNOWN, local motion preference, refresh/navigation/logout races');
  // Runs must display only the current authenticated projection. These
  // synthetic records have no real execution or independent verifier effect.
  login();reset();
  const emptyRuns={queue_depth:0,active_count:0,completed_count:0,failed_count:0,recent:[]};
  const populatedRuns={queue_depth:1,active_count:1,completed_count:0,failed_count:0,recent:[
    {id:'exec_private_old',title:'<old run>',status:'ACTIVE',risk:'R1',environment:'staging',adapter:'echo',updated_at:'2026-11-26T00:00:00Z',request_id:'cr_fixture_001',receipt_id:null}
  ]};
  snapshot.runs=structuredClone(populatedRuns);
  await context.loadView('runs');
  assert.match(element('runs-table').innerHTML,/exec_private_old/);
  assert.match(element('runs-table').innerHTML,/&lt;old run&gt;/);
  const oldRuns=deferred();primaryDeferred=oldRuns;const oldLoad=context.loadRuns();
  snapshot.runs=structuredClone(emptyRuns);
  await context.loadRuns();
  oldRuns.resolve(response({...normal,runs:populatedRuns}));await oldLoad;
  assert.match(element('runs-table').innerHTML,/Žádné běhy/,'old response must not replace a fresh empty result');
  assert.doesNotMatch(element('runs-table').innerHTML,/exec_private_old/);
  assert.equal(element('runs-kpis').hidden,true);
  // The actual list contract is not the narrow request-ID contract.
  const legacy={...populatedRuns.recent[0],id:'ex_legacy_001',status:'SUCCEEDED',receipt_id:'rc_fixture_001'};
  const canonical={...populatedRuns.recent[0],id:'exec_'+'a'.repeat(251),status:'COMPLETED',
    adapter:'github.read-ref/v1',source:'OPERATION_PASSPORT',lifecycle_stage:'EXECUTION_COMPLETED',verification_status:'UNKNOWN'};
  assert.equal(canonical.id.length,256);
  const oldLegacy={...legacy,id:'x'};
  const escapedLegacy={...legacy,id:'old id <&>'};
  snapshot.runs={...emptyRuns,completed_count:4,recent:[legacy,canonical,oldLegacy,escapedLegacy]};
  await context.loadRuns();
  assert.match(element('runs-table').innerHTML,new RegExp(canonical.id),'valid 256-character Passport ID is supported');
  assert.match(element('runs-table').innerHTML,/ex_legacy_001/);
  assert.match(element('runs-table').innerHTML,/old id &lt;&amp;&gt;/);
  assert.doesNotMatch(element('runs-table').innerHTML,/data-passport-execution-id="x"|data-passport-execution-id="old id/);
  assert.doesNotMatch(element('runs-table').innerHTML,/VERIFIED/);
  await element('runs-table').listeners.click({target:new RunPassportButton(legacy.id)});
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(element('operation-passport-content').innerHTML,/není pro tento execution dostupný/);
  await element('runs-table').listeners.click({target:new RunPassportButton(canonical.id)});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(passportRequests,[legacy.id,canonical.id]);
  assert.match(element('operation-passport-content').innerHTML,new RegExp(canonical.id));
  assert.match(element('operation-passport-content').innerHTML,/NOT_PERSISTED/);
  await element('runs-table').listeners.click({target:new RunPassportButton('x')});
  assert.deepEqual(passportRequests,[legacy.id,canonical.id],'invalid drilldown ID must not call API');
  // Only the canonical server projection carries a verification verdict.
  const verified={...canonical,id:'exec_verified_fixture',verification_status:'VERIFIED'};
  snapshot.runs={...emptyRuns,completed_count:2,recent:[legacy,verified]};
  await context.loadRuns();
  const rendered=element('runs-table').innerHTML;
  assert.doesNotMatch(rendered.split(legacy.id)[1].split('</tr>')[0],/VERIFIED/);
  assert.match(rendered.split(verified.id)[1].split('</tr>')[0],/VERIFIED/);
  // Every base field is emitted by the backend, including nullable keys.
  for(const key of ['id','title','status','risk','environment','adapter','updated_at','request_id','receipt_id']){
    const missing={...legacy};delete missing[key];
    for(const badRow of [missing,{...legacy,[key]:{unexpected:true}}]){
      snapshot.runs={...emptyRuns,recent:[badRow]};
      await assert.rejects(context.loadRuns(),/projekce běhů/,key);
      assert.match(element('runs-table').innerHTML,/UNKNOWN/);
    }
  }
  for(const badRow of [
    {...legacy,source:'UNRECOGNIZED'},
    {...legacy,verification_status:'VERIFIED'},
    {...canonical,verification_status:undefined},
    {...canonical,verification_status:'FAKE'},
    {...canonical,lifecycle_stage:null},
    {...canonical,request_id:null},
    {...canonical,receipt_id:'legacy-receipt'},
    {...canonical,id:'a'.repeat(257)}
  ]){
    snapshot.runs={...emptyRuns,recent:[badRow]};
    await assert.rejects(context.loadRuns(),/projekce běhů/);
    assert.match(element('runs-table').innerHTML,/UNKNOWN/);
  }
  // Current malformed or unavailable projections are UNKNOWN, not empty.
  snapshot.runs={...emptyRuns,active_count:'0'};
  await assert.rejects(context.loadRuns(),/projekce běhů/);
  assert.match(element('runs-table').innerHTML,/UNKNOWN/);
  assert.doesNotMatch(element('runs-table').innerHTML,/Žádné běhy/);
  snapshot.runs={...emptyRuns,recent:[null]};
  await assert.rejects(context.loadRuns(),/projekce běhů/);
  snapshot.runs=structuredClone(populatedRuns);await context.loadRuns();
  const oldRunsError=deferred();primaryDeferred=oldRunsError;const oldFail=context.loadRuns();
  await context.loadRuns();oldRunsError.reject(Error('stale runs failure'));await oldFail;
  assert.match(element('runs-table').innerHTML,/exec_private_old/);
  snapshot=null;await assert.rejects(context.loadRuns(),/unavailable/);
  assert.match(element('runs-table').innerHTML,/UNKNOWN/);
  assert.equal(element('runs-kpis').hidden,true);
  assert.doesNotMatch(element('runs-table').innerHTML,/exec_private_old/);
  reset();snapshot.runs=structuredClone(populatedRuns);await context.loadView('runs');
  const leavingRuns=deferred();primaryDeferred=leavingRuns;const leavingLoad=context.loadRuns();
  await context.loadView('overview');
  leavingRuns.resolve(response({...normal,runs:populatedRuns}));await leavingLoad;
  assert.doesNotMatch(element('runs-table').innerHTML,/exec_private_old/);
  await context.loadView('runs');
  const logoutRuns=deferred();primaryDeferred=logoutRuns;const logoutLoad=context.loadRuns();
  await element('logout-button').listeners.click();
  // Even if a mock/new session reused the same token string, the old
  // generation cannot reveal rows across the logout boundary.
  login();logoutRuns.resolve(response({...normal,runs:populatedRuns}));await logoutLoad;
  assert.doesNotMatch(element('runs-table').innerHTML,/exec_private_old/);
  assert.equal(element('runs-kpis').hidden,true);
  await element('logout-button').listeners.click();
  assert.equal(postCalls.length,5,'Runs read paths never issue effects');
  console.log('PASS: Runs authenticated freshness, positive projection, true empty vs UNKNOWN, malformed/outage, old refresh/error, leave/logout races, no effects');

})().catch(error=>{console.error(error);process.exitCode=1});
