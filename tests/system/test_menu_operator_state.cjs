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
const context=vm.createContext({
  document:{getElementById:element,querySelectorAll:selector=>selector==='.view'?['view-health','view-overview','view-casebook','view-governance'].map(element):[]},
  sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,val)=>storage.set(key,String(val)),removeItem:key=>storage.delete(key)},
  setTimeout:()=>0,console,
  fetch:async(url,options={})=>{
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
  // Contradictory stop snapshots do not enable either control.
  live.status='HEALTHY';await context.loadRuntimeHealth();buttonsDisabled();
  assert.match(element('health-problems').innerHTML,/Rozpor mezi čteními/);
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
})().catch(error=>{console.error(error);process.exitCode=1});
