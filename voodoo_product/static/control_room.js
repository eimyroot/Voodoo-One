const state={token:sessionStorage.getItem('voodoo_token')||'',me:null,workspaces:[],capabilities:[]};
const $=id=>document.getElementById(id);
let viewEpoch=0;
function toast(message,error=false){const el=$('toast');el.textContent=message;el.classList.toggle('toast-error',error);el.classList.remove('hidden');setTimeout(()=>el.classList.add('hidden'),3500)}
async function api(path,options={}){const bearer=state.token;const headers={'Content-Type':'application/json',...(options.headers||{})};if(bearer)headers.Authorization=`Bearer ${bearer}`;const response=await fetch(`/api/v1${path}`,{...options,headers});let body={};try{body=await response.json()}catch{}if(bearer&&bearer!==state.token)throw new Error('Relace se změnila.');if(!response.ok){const error=new Error(body.detail||`HTTP ${response.status}`);error.statusCode=response.status;throw error}return body}
function status(value){const text=String(value??'UNKNOWN');const className=/^[A-Z][A-Z0-9_]{0,31}$/.test(text)?text:'UNKNOWN';return `<span class="status ${className}">${escapeHtml(text)}</span>`}
function escapeHtml(value){return String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]))}
async function authReady(){const bearer=state.token;if(!bearer)return false;try{const me=await api('/me');if(bearer!==state.token)return false;state.me=me;$('current-user').textContent=`${me.username} · ${me.role}`;return true}catch{if(bearer===state.token){sessionStorage.removeItem('voodoo_token');state.token=''}return false}}
async function showApp(){const bearer=state.token;if(!(await authReady())){if(!state.token)showAuth();return}if(bearer!==state.token)return;$('auth-screen').classList.add('hidden');$('app-shell').classList.remove('hidden');await loadWorkspaces();if(bearer===state.token)await loadView('overview')}
function showAuth(){$('app-shell').classList.add('hidden');$('auth-screen').classList.remove('hidden');api('/bootstrap/status').then(x=>$('bootstrap-panel').open=x.required).catch(()=>{})}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify({username:$('login-username').value,password:$('login-password').value})});state.token=result.token;sessionStorage.setItem('voodoo_token',result.token);$('auth-error').textContent='';await showApp()}catch(err){$('auth-error').textContent=err.message}})
$('bootstrap-form').addEventListener('submit',async e=>{e.preventDefault();try{const result=await api('/auth/bootstrap',{method:'POST',body:JSON.stringify({username:$('bootstrap-username').value,password:$('bootstrap-password').value,bootstrap_token:$('bootstrap-token').value})});state.token=result.token;sessionStorage.setItem('voodoo_token',result.token);await showApp()}catch(err){$('auth-error').textContent=err.message}})
$('logout-button').addEventListener('click',async()=>{
  const bearer=state.token;
  const epoch=++viewEpoch;
  state.token='';state.me=null;state.workspaces=[];state.capabilities=[];
  sessionStorage.removeItem('voodoo_token');
  $('app-shell').classList.add('hidden');
  $('current-user').textContent='';
  ++requestContextEpoch;++timelineRefreshEpoch;++verifierRefreshEpoch;
  clearCasebookContext();clearOperationPassport();clearOverviewContext({clearHeader:true});clearRuntimeHealthContext({clearReason:true});clearSettingsContext({resetPreference:true});
  $('canonical-read-result').textContent='';$('canonical-read-result').classList.add('hidden');
  $('canonical-read-feedback').textContent='';$('canonical-read-feedback').classList.add('hidden');
  showAuth();$('auth-error').textContent='';
  if(!bearer)return;
  try{
    // The old bearer is used only for revocation; local logout never waits for it.
    await api('/auth/logout',{method:'POST',headers:{Authorization:`Bearer ${bearer}`}});
  }catch{
    if(!state.token&&epoch===viewEpoch)
      $('auth-error').textContent='Serverové odvolání relace se nepodařilo potvrdit. Lokální token byl odstraněn.';
  }
})
document.querySelectorAll('.nav').forEach(button=>button.addEventListener('click',()=>loadView(button.dataset.view)))
document.querySelectorAll('[data-refresh]').forEach(button=>button.addEventListener('click',()=>loadView(button.dataset.refresh)))
function revealActiveNavOnCompactViewport(name){
  if(typeof window==='undefined'||typeof window.matchMedia!=='function'
    ||!window.matchMedia('(max-width:900px)').matches)return;
  const current=[...document.querySelectorAll('.nav')].find(button=>button.dataset.view===name);
  if(current&&typeof current.scrollIntoView==='function'){
    current.scrollIntoView({block:'nearest',inline:'center',behavior:'auto'});
  }
}
async function loadView(name){const bearer=state.token;if(!bearer)return false;const epoch=++viewEpoch;if(name!=='governance')clearSettingsContext();if(name!=='health')clearRuntimeHealthContext({clearReason:true});if(name!=='overview')clearOverviewContext({clearHeader:true});if(name!=='casebook')clearCasebookContext();if(name!=='runs')clearOperationPassport();document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));document.querySelectorAll('.nav').forEach(v=>v.classList.toggle('active',v.dataset.view===name));revealActiveNavOnCompactViewport(name);const view=$(`view-${name}`);if(!view){toast(`Neznámý pohled: ${name}`,true);return false}view.classList.add('active');const loaders={ecosystem:loadEcosystemBoard,lifecycle:loadLifecycleBoard,authority:loadAuthorityBoard,lineage:loadLineageBoard,overlays:loadOverlaysBoard,projectmap:loadProjectMap,overview:loadOverview,runs:loadRuns,plans:loadPlans,registry:loadRegistry,evidence:loadTimeline,casebook:loadCasebookTasks,policy:loadPolicy,verifier:loadVerifier,health:loadRuntimeHealth,learning:loadLearning,governance:loadGovernance};try{await loaders[name]()}catch(err){if(epoch===viewEpoch&&bearer===state.token)toast(err.message,true)}return epoch===viewEpoch&&bearer===state.token}
const casebookSessionIdPattern=/^[A-Za-z0-9_-]{5,128}$/;
let casebookRequestGeneration=0;
let casebookCorrelationGeneration=0;
let casebookCorrelationSession=null;
function clearCasebookTask(){
  casebookRequestGeneration+=1;
  ++casebookCorrelationGeneration;
  casebookCorrelationSession=null;
  $('casebook-correlation-panel').classList.add('hidden');
  $('casebook-correlation-id').value='';
  $('casebook-correlation-feedback').textContent='';
  $('casebook-task-detail').classList.add('hidden');
  $('casebook-task-state').replaceChildren();
  $('casebook-task-timeline').replaceChildren();
  $('casebook-task-goal').textContent='';
  $('casebook-task-meta').textContent='';
  $('casebook-task-next').textContent='';
  $('casebook-task-signals').replaceChildren();
}
let casebookIndexGeneration=0;
function clearCasebookIndex(){
  ++casebookIndexGeneration;
  $('casebook-bound-session').replaceChildren();
  $('casebook-bound-session').value='';
  $('casebook-bound-open').disabled=true;
  $('casebook-index-feedback').textContent='';
}
function clearCasebookContext(){
  clearCasebookTask();clearCasebookIndex();
  $('casebook-session-id').value='';
  $('casebook-task-feedback').textContent='';
}
async function loadCasebookTasks(){
  if(!state.token)return;
  clearCasebookTask();
  clearCasebookIndex();
  const generation=casebookIndexGeneration;
  const bearer=state.token;
  $('casebook-task-feedback').textContent='Vyberte autorizovanou relaci nebo zadejte její přesné ID.';
  $('casebook-index-feedback').textContent='Ověřuji dostupné vazby…';
  try{
    const data=await api('/casebook/tasks',{cache:'no-store'});
    if(generation!==casebookIndexGeneration||bearer!==state.token)return;
    if(data?.schema!=='voodoo-casebook/bound-task-index/v1'
      ||data.journal_integrity!=='NOT_CHECKED_BY_INDEX'
      ||typeof data.has_more!=='boolean'||!Array.isArray(data.items)||data.items.length>50
      ||!data.items.every(item=>typeof item.session_id==='string'
        &&casebookSessionIdPattern.test(item.session_id)
        &&typeof item.project==='string'&&typeof item.workspace_id==='string'
        &&['local','development','staging'].includes(item.environment)))
      throw new Error('Neúplný seznam autorizovaných vazeb.');
    $('casebook-bound-session').innerHTML=data.items.map(item=>
      '<option value="'+escapeHtml(item.session_id)+'">'+escapeHtml(item.project+' · '+item.session_id)+'</option>'
    ).join('');
    $('casebook-bound-open').disabled=!data.items.length;
    $('casebook-index-feedback').textContent=data.items.length
      ?'Dostupné vazby: '+data.items.length+(data.has_more?'+':'')+'. Integrita se ověří až při otevření relace.'
      :'Žádné aktuálně dostupné autorizované vazby.';
  }catch(err){
    if(generation!==casebookIndexGeneration||bearer!==state.token)return;
    $('casebook-index-feedback').textContent='UNKNOWN · seznam vazeb není dostupný. Lze zkusit přesné ID relace.';
  }
}
$('casebook-bound-form').addEventListener('submit',event=>{
  event.preventDefault();
  const id=$('casebook-bound-session').value;
  if(!casebookSessionIdPattern.test(id))return;
  $('casebook-session-id').value=id;
  loadCasebookTask(id);
});
async function loadCasebookTask(sessionId){
  if(!state.token)return;
  clearCasebookTask();
  const generation=casebookRequestGeneration;
  const bearer=state.token;
  const feedback=$('casebook-task-feedback');
  if(!casebookSessionIdPattern.test(sessionId)){
    feedback.textContent='Neplatné ID relace. Nebyla odeslána žádná žádost.';
    return;
  }
  feedback.textContent='Ověřuji oprávnění a integritu CASEBOOK journalu…';
  try{
    const data=await api('/casebook/tasks/'+encodeURIComponent(sessionId),{cache:'no-store'});
    if(generation!==casebookRequestGeneration || bearer!==state.token)return;
    if(data?.schema!=='voodoo-casebook/task-view/v1'
      ||data.session_id!==sessionId
      ||data.journal_integrity!=='LOCAL_HASH_CHAIN_VERIFIED_ONLY'
      ||data.native_approval!=='NOT_ATTESTED'
      ||data.isolated_runner_execution!=='NOT_ATTESTED'
      ||data.independent_verifier!=='NOT_ATTESTED'
      ||(data.execution_verified_by_this_view!==undefined
        &&data.execution_verified_by_this_view!==false)
      ||(data.execution_authorized_by_this_view!==undefined
        &&data.execution_authorized_by_this_view!==false)
      ||!Array.isArray(data.timeline)){
      throw new Error('Neúplná nebo neověřená projekce CASEBOOK.');
    }
    feedback.textContent='Čtení: pouze lokální integrita journalu ověřena. Externí schválení, Runner a Verifier nejsou doloženy.';
    $('casebook-task-goal').textContent=data.goal;
    $('casebook-task-meta').textContent=[data.project,data.workspace_id,data.session_id].filter(Boolean).join(' · ');
    const nextSteps=new Map([
      ['PREPARE_AND_AUTHORIZE_CASER_HANDOFF','Připravit předání CASERu a získat příslušné schválení.'],
      ['AUTHORIZE_AND_EXECUTE_THROUGH_VOODOO_ONE','Ověřit oprávnění a provést operaci řízeným postupem VOODOO One.'],
      ['VERIFY_NATIVE_APPROVAL_EXECUTION_AND_INDEPENDENT_RESULT','Doložit nativní schválení, skutečný běh a nezávislé ověření.'],
    ]);
    $('casebook-task-next').textContent=nextSteps.get(data.next_action)||'Další krok není doložen.';
    const groups=[
      ['Rozhodnutí',['DECISION']],
      ['Otevřené překážky a rizika',['BLOCKER','ISSUE','RISK'],'OPEN'],
      ['Otevřené úkoly',['TODO'],'OPEN'],
      ['Poznatky',['LEARNING']],
    ];
    $('casebook-task-signals').innerHTML=groups.map(([label,types,claim])=>{
      const events=data.timeline.filter(event=>types.includes(event.type)&&(!claim||event.status_claim===claim));
      const latest=events.at(-1);
      return '<div class="casebook-signal"><span>'+escapeHtml(label)+'</span><strong>'+events.length+'</strong><p>'+
        escapeHtml(latest?.summary||'Žádný odpovídající zápis')+'</p></div>';
    }).join('');
    const facts=[
      ['Stav',data.display_state],
      ['Počet událostí',data.timeline.length],
      ['CASER handoff',data.handoff],
      ['Schválení',data.native_approval],
      ['Runner',data.isolated_runner_execution],
      ['Verifier',data.independent_verifier],
      ['Výsledek',data.result],
    ];
    $('casebook-task-state').innerHTML=facts.map(([label,value])=>
      '<div class="fact"><span>'+escapeHtml(label)+'</span><strong>'+escapeHtml(value)+'</strong></div>'
    ).join('');
    $('casebook-task-timeline').innerHTML=data.timeline.map(event=>
      '<article class="timeline-item"><div class="timeline-marker">'+
        status(event.type)+'</div><div class="timeline-body"><header><strong>'+
        escapeHtml(event.summary)+'</strong><span class="mono muted">#'+
        escapeHtml(event.seq)+'</span></header><time>'+
        escapeHtml(event.timestamp)+'</time><p class="muted">'+
        escapeHtml(event.source_claim)+' · '+escapeHtml(event.status_claim)+
      '</p><details class="casebook-event-source"><summary>Původ zápisu</summary><p>ID: '+escapeHtml(event.event_id||'UNKNOWN')+'</p><p class="mono">Hash: '+escapeHtml(event.event_hash||'UNKNOWN')+'</p></details></div></article>'
    ).join('');
    if(data.passport_correlation_available===true){
      casebookCorrelationSession=sessionId;
      $('casebook-correlation-panel').classList.remove('hidden');
    }
    $('casebook-task-detail').classList.remove('hidden');
  }catch(err){
    if(generation!==casebookRequestGeneration || bearer!==state.token)return;
    feedback.textContent='CASEBOOK: NEDOSTUPNÉ / NEOVĚŘENO — '+err.message+
      '. Nebyl proveden zápis ani spuštění.';
  }
}
$('casebook-task-form').addEventListener('submit',event=>{
  event.preventDefault();
  loadCasebookTask($('casebook-session-id').value.trim());
});

$('casebook-correlation-id').addEventListener('input',()=>{
  ++casebookCorrelationGeneration;
  $('casebook-correlation-feedback').textContent='';
});
$('casebook-correlation-form').addEventListener('submit',async event=>{
  event.preventDefault();
  const sessionId=casebookCorrelationSession;
  const executionId=$('casebook-correlation-id').value.trim();
  const generation=++casebookCorrelationGeneration;
  const bearer=state.token;
  const feedback=$('casebook-correlation-feedback');
  if(!bearer)return;
  if(!sessionId||!canonicalReadRequestPattern.test(executionId)){
    feedback.textContent='Zadejte přesné ID existujícího běhu.';
    return;
  }
  feedback.textContent='Ověřuji vazbu relace a Passportu…';
  try{
    const data=await api('/casebook/tasks/'+encodeURIComponent(sessionId)+'/passport/'+encodeURIComponent(executionId),{cache:'no-store'});
    if(generation!==casebookCorrelationGeneration||bearer!==state.token||casebookCorrelationSession!==sessionId)return;
    if(data?.schema!=='voodoo-one/casebook-passport-correlation/v1'
      ||data.verdict!=='LOCAL_STRUCTURAL_PASSPORT_MATCH'
      ||data.session_id!==sessionId||data.execution_id!==executionId
      ||data.execution_authorized_by_this_view!==false
      ||data.execution_verified_by_this_view!==false||data.resume_authorized!==false
      ||data.passport?.schema!=='vone.operation-passport/v1'
      ||data.passport.execution_id!==executionId
      ||data.passport.operation?.request_id!==data.request_id)
      throw new Error('Vazba Passportu není doložena.');
    feedback.textContent='Lokální strukturální shoda. Obnovení běhu nebylo autorizováno.';
    const loading=loadView('runs');
    ++passportSelectionEpoch;
    $('operation-passport-panel').classList.remove('hidden');
    renderOperationPassport(data.passport);
    await loading;
  }catch(err){
    if(generation!==casebookCorrelationGeneration||bearer!==state.token)return;
    feedback.textContent='UNKNOWN · vazba není ověřena. Nebyla spuštěna žádná operace.';
  }
});

function canonicalReadReady(runtime){
  return runtime?.configured===true && runtime.read_terminal_configured===true
    && runtime.write_routes_exposed===false && runtime.provider_write_effects_exposed===false;
}
// UI eligibility is advisory and FAIL-CLOSED. The server remains the only
// authority to issue a grant. The source of TTL is the canonical runtime's
// immutable policy; first_approved_at comes from the persisted approval rows.
// The UTC server timestamp avoids relying on the operator computer's clock.
function canonicalReadApprovalWindow(request,runtime){
  const seconds=runtime?.approval_validity_seconds;
  const serverUtc=runtime?.server_time_utc;
  const firstUtc=request?.first_approved_at;
  const validDate=value=>typeof value==='string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}\+00:00$/.test(value)
    ? Date.parse(value):NaN;
  const approved=validDate(firstUtc);
  const now=validDate(serverUtc);
  if(!Number.isSafeInteger(seconds)||seconds<1||seconds>86400
    ||!Number.isFinite(approved)||!Number.isFinite(now)
    ||request?.status!=='APPROVED'||!Number.isInteger(request?.approval_count)
    ||request.approval_count<1)
    return {eligible:false,reason:'UNKNOWN',label:'SCHVÁLENÍ NEOVĚŘENO · READ ZAKÁZÁN'};
  const until=approved+seconds*1000;
  if(!Number.isSafeInteger(until)||approved>now)
    return {eligible:false,reason:'UNKNOWN',label:'ČAS SCHVÁLENÍ NEOVĚŘEN · READ ZAKÁZÁN'};
  // Three-second guard prevents offering an action that is already about to
  // expire; the canonical server independently enforces the exact cutoff.
  if(until-now<=3000)
    return {eligible:false,reason:'EXPIRED',label:'SCHVÁLENÍ VYPRŠELO · založ nový požadavek jako g8-requester'};
  const localDeadline=new Date(until).toLocaleString('cs-CZ',{
    timeZone:'Europe/Prague',day:'2-digit',month:'2-digit',year:'numeric',
    hour:'2-digit',minute:'2-digit',second:'2-digit'
  });
  return {eligible:true,reason:'VALID',label:`Platnost schválení do ${localDeadline} (Praha)`};
}
const canonicalReadPending=new Set();
const canonicalReadRequestPattern=/^[A-Za-z0-9._:-]{5,80}$/;
function canonicalReadAttemptKey(requestId){
  const slot='voodoo_canonical_read_attempt:'+requestId;
  let key=sessionStorage.getItem(slot);
  if(!key){key=crypto.randomUUID();sessionStorage.setItem(slot,key)}
  return key;
}
function canonicalReadPayloadValid(payload){
  return payload && typeof payload==='object' && !Array.isArray(payload)
    && Object.keys(payload).sort().join(',')==='ref,repository'
    && typeof payload.repository==='string'
    && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(payload.repository)
    && typeof payload.ref==='string'
    && /^refs\/(heads|tags)\//.test(payload.ref);
}
function capabilityIdForAdapter(adapter){return adapter==='github-read-ref'?'github.read-ref/v1':adapter}
function capabilityForAdapter(adapter){
  const id=capabilityIdForAdapter(adapter);
  return state.capabilities.find(item=>item?.id===id)||null;
}
function requestTargetSummary(adapter,payload){
  if(adapter==='github-read-ref')return `${payload.repository||'REPOSITORY_NEUVEDEN'} · ${payload.ref||'REF_NEUVEDEN'}`;
  if(adapter==='write_artifact')return String(payload.path||'artifact.json');
  if(adapter==='run_validation')return String(payload.preset||'python_compile');
  if(adapter==='echo')return 'Bez externího účinku';
  return 'Cíl není bezpečně rozpoznán';
}
let reviewedChangeFingerprint='';
let requestContextEpoch=0;
let changeSubmitting=false;
function changeDraft(){
  const payload=JSON.parse($('change-payload').value||'{}');
  if(!payload||typeof payload!=='object'||Array.isArray(payload))throw new Error('Payload musí být JSON objekt.');
  const workspace=state.workspaces.find(item=>item.id===$('change-workspace').value);
  if(!workspace||workspace.environment!==$('change-environment').value)throw new Error('Workspace a environment nejsou bezpečně svázané.');
  const title=$('change-title').value.trim();
  if(title.length<3||title.length>200)throw new Error('Název musí mít 3 až 200 znaků.');
  const description=$('change-description').value.trim();
  if(description.length>10000)throw new Error('Popis je příliš dlouhý.');
  const risk=$('change-risk').value;
  if(!/^R[0-4]$/.test(risk))throw new Error('Riziko není platné.');
  const adapter=$('change-adapter').value;
  const capability=capabilityForAdapter(adapter);
  if(!capability)throw new Error('Účinek schopnosti není v živém registru dostupný. Požadavek nebyl vytvořen.');
  if(!Array.isArray(capability.environments)||!capability.environments.includes(workspace.environment))
    throw new Error('Schopnost není pro vybrané prostředí povolená.');
  if(adapter==='github-read-ref'&&(!['local','development','staging'].includes(workspace.environment)
    ||!canonicalReadPayloadValid(payload)))
    throw new Error('GitHub READ vyžaduje neprodukční workspace a přesný repository/ref.');
  return {workspace_id:workspace.id,title,description,risk,environment:workspace.environment,adapter,payload,capability};
}
function changeFingerprint(draft){
  return JSON.stringify({workspace_id:draft.workspace_id,title:draft.title,description:draft.description,
    risk:draft.risk,environment:draft.environment,adapter:draft.adapter,payload:draft.payload,
    capability:{id:draft.capability.id,effect:draft.capability.effect,verification:draft.capability.verification,
      runtime_status:draft.capability.runtime_status,environments:draft.capability.environments}});
}
function invalidateChangeReview(){
  reviewedChangeFingerprint='';
  $('change-create-button').disabled=true;
  $('change-review').classList.add('hidden');
  $('change-review-facts').innerHTML='';
  $('change-review-note').textContent='';
  $('change-review-state').textContent='NEZKONTROLOVÁNO';
  $('change-review-state').className='status UNKNOWN';
}
function renderChangeReview(draft){
  const capability=draft.capability;
  $('change-review-facts').innerHTML=[
    fact('Workspace',draft.workspace_id,'OBSERVED'),
    fact('Prostředí',draft.environment.toUpperCase(),draft.environment.toUpperCase()),
    fact('Riziko',draft.risk,draft.risk),
    fact('Schopnost',capability.id,capability.runtime_status),
    fact('Účinek',capability.effect,'OBSERVED'),
    fact('Požadované ověření',capability.verification,'OBSERVED'),
    fact('Přesný cíl',requestTargetSummary(draft.adapter,draft.payload),'OBSERVED'),
  ].join('');
  $('change-review-note').textContent='Tato kontrola popisuje připravovaný požadavek. Nevydává oprávnění, neprovádí operaci a nenahrazuje serverovou policy.';
  $('change-review-state').textContent='PŘIPRAVENO K VYTVOŘENÍ';
  $('change-review-state').className='status OBSERVED';
  $('change-review').classList.remove('hidden');
  $('change-create-button').disabled=false;
  reviewedChangeFingerprint=changeFingerprint(draft);
}
function renderRequestCapabilityContext(){
  $('request-capability-context').innerHTML=state.capabilities.length?state.capabilities.map(item=>
    `<div class="capability-pill"><div><strong>${escapeHtml(item.id)}</strong><span>${escapeHtml(item.effect)} · ${escapeHtml(item.verification)}</span></div>${status(item.runtime_status)}</div>`
  ).join(''):'<p class="muted">Registr schopností není dostupný. Nový požadavek nelze bezpečně zkontrolovat.</p>';
}
function clearRequestContext(message){
  state.capabilities=[];
  invalidateChangeReview();
  renderRequestCapabilityContext();
  $('plans-table').innerHTML='<tr><td colspan="6" class="muted">'+escapeHtml(message)+'</td></tr>';
  $('approvals-list').innerHTML='<article class="panel">'+escapeHtml(message)+'</article>';
}
function updateRequestCapabilities(data){
  state.capabilities=Array.isArray(data.capability_registry?.items)?data.capability_registry.items:[];
  renderRequestCapabilityContext();
}
async function refreshRequestCapabilities(){
  const epoch=++requestContextEpoch;
  try{
    const data=await api('/control-room',{cache:'no-store'});
    if(epoch!==requestContextEpoch)throw new Error('Kontext požadavků se změnil. Obnovte kontrolu.');
    updateRequestCapabilities(data);
  }catch(err){
    if(epoch===requestContextEpoch)clearRequestContext('UNKNOWN · aktuální kontext požadavků není dostupný.');
    throw err;
  }
}
function canonicalReadFeedback(message,error=false){
  const el=$('canonical-read-feedback');
  el.textContent=message;
  el.classList.toggle('error',error);
  el.classList.remove('hidden');
}
async function runCanonicalRead(requestId,button){
  const bearer=state.token;
  if(!bearer||!canonicalReadRequestPattern.test(requestId)||canonicalReadPending.has(requestId))return;
  canonicalReadPending.add(requestId);
  let approvalExpired=false;
  button.disabled=true;
  $('canonical-read-result').textContent='';
  $('canonical-read-result').classList.add('hidden');
  canonicalReadFeedback('Ověřuji oprávnění a aktuální schválení. Kanonický READ ještě nebyl spuštěn.');
  try{
    const [runtime,request]=await Promise.all([
      api('/operations/status',{cache:'no-store'}),
      api(`/change-requests/${encodeURIComponent(requestId)}`,{cache:'no-store'})
    ]);
    if(bearer!==state.token)return;
    if(!canonicalReadReady(runtime))throw new Error('Kanonický READ runtime není dostupný. Nic nebylo spuštěno.');
    if(request?.id!==requestId||request.adapter!=='github-read-ref'||request.status!=='APPROVED'
      ||!['local','development','staging'].includes(request.environment)
      ||!canonicalReadPayloadValid(request.payload)){
      throw new Error('Požadavek nebo schválení nejsou platné pro kanonický GitHub READ.');
    }
    const approval=canonicalReadApprovalWindow(request,runtime);
    if(!approval.eligible){
      approvalExpired=approval.reason==='EXPIRED';
      canonicalReadFeedback(approval.label+' · nevykonáno, neopakovat původní požadavek.',true);
      await loadPlans();
      return;
    }
    if(!confirm(`Provést výhradně READ ${request.payload.repository} · ${request.payload.ref}? Server znovu ověří autoritu a schválení.`)){
      canonicalReadFeedback('Operátor akci zrušil. Žádná operace nebyla spuštěna.');
      return;
    }
    // Stable per request across a reload: an ambiguous network outcome MUST NOT mint a fresh grant.
    const key=canonicalReadAttemptKey(requestId);
    canonicalReadFeedback('READ požadavek odeslán. Výsledek zůstává UNKNOWN do potvrzení nezávislým Verifierem.');
    const result=await api(`/operations/${encodeURIComponent(requestId)}/read`,{
      method:'POST',headers:{'Idempotency-Key':key},body:JSON.stringify({correlation_id:key})
    });
    if(bearer!==state.token)return;
    if(result?.schema!=='vone.canonical-operation-read/v1'||result.operation?.request_id!==requestId
      ||!canonicalReadRequestPattern.test(result.operation?.execution_id||'')
      ||result.execution?.status!=='SUCCEEDED'||result.verification?.verdict!=='VERIFIED'
      ||result.verification?.strength_class!=='INDEPENDENT_PROVIDER_READBACK'
      ||typeof result.verification?.result_digest!=='string'||!result.verification.result_digest){
      throw new Error('Kanonický READ nemá ověřený výsledek. Stav UNKNOWN; neopakovat automaticky.');
    }
    const executionId=result.operation.execution_id;
    canonicalReadFeedback('Kanonický READ: nezávislý VERIFIER odpověděl VERIFIED. Otevírám Passport.');
    if(!(await loadView('runs'))||bearer!==state.token)return;
    const receipt=$('canonical-read-result');
    receipt.textContent=`READ API: VERIFIED · ${executionId} · ${result.verification.strength_class} · digest ${result.verification.result_digest}. Passport uvádí pouze vlastní dostupnou durable evidenci.`;
    receipt.classList.remove('hidden');
    await loadOperationPassport(executionId);
  }catch(err){
    if(bearer!==state.token)return;
    canonicalReadFeedback(`Kanonický READ: UNKNOWN / NEOVĚŘENO — ${err.message}. Bez automatického opakování; ověř stav a Passport podle request ID ${requestId}.`,true);
  }finally{
    canonicalReadPending.delete(requestId);
    button.disabled=approvalExpired;
  }
}
function syncChangeAdapter(){
  if($('change-adapter').value==='github-read-ref'){
    $('change-payload').value='{"repository":"","ref":"refs/heads/main"}';
  }else if($('change-payload').value==='{"repository":"","ref":"refs/heads/main"}'){
    $('change-payload').value='{"message":"VOODOO One ready"}';
  }
  invalidateChangeReview();
}
function syncChangeEnvironment(){const workspace=state.workspaces.find(w=>w.id===$('change-workspace').value);$('change-environment').value=workspace?.environment||'';invalidateChangeReview()}
async function loadWorkspaces(){state.workspaces=await api('/workspaces');$('change-workspace').innerHTML=state.workspaces.map(w=>`<option value="${escapeHtml(w.id)}">${escapeHtml(w.name)} · ${escapeHtml(w.environment)}</option>`).join('');syncChangeEnvironment()}
function fact(label,value,stateValue=value){return `<div class="fact"><span>${escapeHtml(label)}</span>${status(stateValue)}<strong>${escapeHtml(value)}</strong></div>`}
async function controlRoom(){return api('/control-room')}
function renderTable(target,rows,columns){$(target).innerHTML=rows.length?rows.map(row=>`<tr>${columns.map(column=>`<td>${column.status?status(row[column.key]):escapeHtml(row[column.key]??'—')}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${columns.length}" class="muted">Žádná data.</td></tr>`}
function renderArchitectureFlow(flow){const nodes=flow.nodes.map((node,index)=>`<div class="architecture-node">${status(node.status)}<strong>${escapeHtml(node.label)}</strong><span>${escapeHtml(node.source)}</span>${node.note?`<small>${escapeHtml(node.note)}</small>`:''}</div>${index<flow.nodes.length-1?'<span class="graph-link">→</span>':''}`).join('');return `<article class="panel architecture-flow"><div class="panel-heading"><div><h2>${escapeHtml(flow.label)}</h2><p>${escapeHtml(flow.id)}</p></div>${status(flow.status)}</div><div class="architecture-path">${nodes}</div></article>`}
// A single authenticated view owns Overview rendering. Other Control Room
// readers must never refresh a hidden or newly opened Overview implicitly.
let overviewRefreshEpoch=0;
function overviewRenderer(){
  return typeof window==='undefined'?null:window.voodooLivingCore;
}
function clearOverviewContext(options={}){
  ++overviewRefreshEpoch;
  overviewRenderer()?.renderUnavailable(options);
}
async function loadOverview(){
  const bearer=state.token;
  if(!bearer)return;
  const epoch=viewEpoch;
  const generation=++overviewRefreshEpoch;
  const current=()=>bearer===state.token&&epoch===viewEpoch
    &&generation===overviewRefreshEpoch&&$('view-overview').classList.contains('active');
  overviewRenderer()?.renderUnavailable({loading:true});
  try{
    const data=await api('/control-room',{cache:'no-store'});
    if(!current())return;
    const renderer=overviewRenderer();
    if(!renderer)throw new Error('Přehled není dostupný.');
    renderer.renderProjection(data);
  }catch(error){
    if(!current())return;
    overviewRenderer()?.renderUnavailable();
    throw error;
  }
}
async function loadRuns(){
  $('runs-kpis').textContent='';
  $('runs-table').textContent='Data běhů nejsou ověřena.';
  const data=await controlRoom();
  $('runs-kpis').hidden=[data.runs.queue_depth,data.runs.active_count,data.runs.completed_count,data.runs.failed_count].every(count=>count===0);
  $('runs-kpis').innerHTML=[['Queue',data.runs.queue_depth],['Active',data.runs.active_count],['Dokončeno',data.runs.completed_count],['Failed',data.runs.failed_count]].map(([label,value])=>`<div class="kpi"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join('');$('runs-table').innerHTML=data.runs.recent.length?data.runs.recent.map(run=>`<tr><td>${status(run.status)}</td><td><strong>${escapeHtml(run.id)}</strong><br><span class="muted">${escapeHtml(run.title)}</span></td><td>${escapeHtml(run.request_id||'—')}</td><td>${escapeHtml(run.risk)}</td><td>${escapeHtml(run.environment)}</td><td>${escapeHtml(run.adapter)}</td><td>${escapeHtml(run.receipt_id??'—')}<br><small>Ověření: ${status(run.verification_status||'UNKNOWN')}</small>${run.source==='OPERATION_PASSPORT'?'<br><small class="muted">Kanonický Passport</small>':''}</td><td><button class="secondary compact-button" type="button" data-passport-execution-id="${escapeHtml(run.id)}">Passport</button></td></tr>`).join(''):'<tr><td colspan="8" class="muted">Žádné běhy.</td></tr>'}
function passportFact(label,value,stateValue='OBSERVED'){return `<div class="fact"><span>${escapeHtml(label)}</span>${status(stateValue)}<strong>${escapeHtml(value??'—')}</strong></div>`}
function passportGroup(title,entries){return `<section class="passport-group"><h3>${escapeHtml(title)}</h3><div class="fact-grid">${entries.map(entry=>passportFact(entry[0],entry[1],entry[2]??'OBSERVED')).join('')}</div></section>`}
function passportTimelineEvent(label,timestamp,reference,stateValue='OBSERVED'){return `<article class="timeline-item"><div class="timeline-marker">${status(stateValue)}</div><div class="timeline-body"><header><strong>${escapeHtml(label)}</strong><span class="mono muted">${escapeHtml(reference||'NO_REFERENCE')}</span></header><time>${escapeHtml(timestamp||'TIME_NOT_AVAILABLE')}</time></div></article>`}
function passportEvidenceTimeline({snapshot,grant,consumption,outbox,runtime,verification}){const events=[];if(snapshot.authorized_at)events.push(passportTimelineEvent('Authorization snapshot',snapshot.authorized_at,snapshot.snapshot_digest));if(grant.issued_at)events.push(passportTimelineEvent('Execution grant issued',grant.issued_at,grant.grant_digest));if(consumption.consumed_at)events.push(passportTimelineEvent('Execution grant consumed',consumption.consumed_at,consumption.consumption_digest));if(outbox.created_at)events.push(passportTimelineEvent('Dispatch outbox recorded',outbox.created_at,outbox.entry_digest));if(runtime.completed_at||runtime.updated_at)events.push(passportTimelineEvent('Runtime state',runtime.completed_at||runtime.updated_at,runtime.completion_digest||runtime.execution_capsule_digest,runtime.status||'UNKNOWN'));if(verification.independent_verification_exposed)events.push(passportTimelineEvent('Independent verification',verification.checked_at,verification.result_digest,verification.verdict||'UNKNOWN'));else events.push(passportTimelineEvent('Independent verification',null,'NOT_PERSISTED','UNKNOWN'));return `<section class="passport-group"><h3>Canonical evidence timeline</h3><p class="muted">Derived only from validated Operation Passport facts. Missing evidence remains explicit.</p><div class="timeline passport-evidence-timeline">${events.join('')}</div></section>`}
function renderOperationPassport(data){const operation=data.operation||{};const authority=data.authority||{};const snapshot=authority.snapshot||{};const grant=authority.grant||{};const consumption=authority.consumption||{};const dispatch=data.dispatch||{};const outbox=dispatch.outbox||{};const inbox=dispatch.inbox||{};const runtime=data.runtime||{};const lease=runtime.current_lease||{};const verification=data.verification||{};const integrity=data.integrity||{};const verificationState=verification.verdict||'UNKNOWN';$('operation-passport-content').innerHTML=`<div class="passport-hero"><div><span class="mono muted">${escapeHtml(data.execution_id)}</span><h3>${escapeHtml(operation.capability||'Canonical operation')}</h3></div>${status(data.lifecycle_stage)}</div>${passportGroup('Intent & target',[['Request',operation.request_id],['Actor',operation.actor_id],['Workspace',operation.workspace_id],['Environment',operation.environment,String(operation.environment||'UNKNOWN').toUpperCase()],['Target kind',operation.target_kind],['Target digest',operation.target_digest],['Reviewed content SHA-256',operation.review_content_sha256]])}${passportGroup('Bounded authority',[['Snapshot',snapshot.snapshot_digest],['Policy version',snapshot.policy_version],['Authorized at',snapshot.authorized_at],['Approval valid until',snapshot.approval_valid_until],['Grant',grant.grant_digest||'NOT_ISSUED',grant.grant_digest?'OBSERVED':'UNKNOWN'],['Grant use',grant.use_semantics||'NOT_ISSUED',grant.use_semantics?'OBSERVED':'UNKNOWN'],['Grant expiry',grant.expires_at||'NOT_ISSUED',grant.expires_at?'OBSERVED':'UNKNOWN'],['Consumed at',consumption.consumed_at||'NOT_CONSUMED',consumption.consumed_at?'OBSERVED':'UNKNOWN']])}${passportGroup('Dispatch & runtime',[['Outbox',outbox.entry_digest||'NOT_ENQUEUED',outbox.entry_digest?'OBSERVED':'UNKNOWN'],['Inbox',inbox.admission_digest||'NOT_ADMITTED',inbox.admission_digest?'OBSERVED':'UNKNOWN'],['Runtime',runtime.status||'UNKNOWN',runtime.status||'UNKNOWN'],['Execution epoch',runtime.execution_epoch],['Runner class',runtime.runner_class],['Capsule digest',runtime.execution_capsule_digest],['Lease expiry',lease.expires_at||'NO_ACTIVE_LEASE',lease.expires_at?'OBSERVED':'UNKNOWN'],['Completed at',runtime.completed_at||'NOT_COMPLETED',runtime.completed_at?'OBSERVED':'UNKNOWN']])}<section class="passport-group verification-block"><div class="panel-heading"><div><h3>Independent verification</h3><p>${escapeHtml(verification.reason||'No verification explanation is available.')}</p></div>${status(verificationState)}</div><div class="fact-grid">${passportFact('Persistence status',verification.status||'UNKNOWN',verification.status||'UNKNOWN')}${passportFact('Verdict',verification.verdict||'UNKNOWN',verificationState)}${passportFact('Verification strength',verification.verification_strength_class||'NOT_AVAILABLE',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Checked at',verification.checked_at||'NOT_AVAILABLE',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Independent result exposed',verification.independent_verification_exposed?'YES':'NO',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Result digest',verification.result_digest||'NOT_AVAILABLE',verification.result_digest?'OBSERVED':'UNKNOWN')}</div></section>${passportEvidenceTimeline({snapshot,grant,consumption,outbox,runtime,verification})}${passportGroup('Integrity',[['Canonical JSON',integrity.canonical_json_validated?'VALIDATED':'UNKNOWN',integrity.canonical_json_validated?'VERIFIED':'UNKNOWN'],['Lineage bindings',integrity.lineage_bindings_validated?'VALIDATED':'UNKNOWN',integrity.lineage_bindings_validated?'VERIFIED':'UNKNOWN'],['Independent verification',integrity.independent_verification_validated?'VALIDATED':'NOT_VALIDATED',integrity.independent_verification_validated?'VERIFIED':'UNKNOWN']])}<details class="passport-raw"><summary>Raw canonical passport</summary><pre id="passport-raw-json"></pre></details>`;$('passport-raw-json').textContent=JSON.stringify(data,null,2)}
let passportSelectionEpoch=0;
function clearOperationPassport(){
  ++passportSelectionEpoch;
  $('passport-raw-json')?.replaceChildren?.();
  $('operation-passport-panel').classList.add('hidden');
  $('operation-passport-content').innerHTML='';
}
async function loadOperationPassport(executionId){const bearer=state.token;if(!bearer)return;const epoch=++passportSelectionEpoch;const panel=$('operation-passport-panel');panel.classList.remove('hidden');$('operation-passport-content').innerHTML='<p class="muted">Načítám canonical Operation Passport…</p>';try{const data=await api(`/operations/${encodeURIComponent(executionId)}/passport`);if(epoch!==passportSelectionEpoch||bearer!==state.token)return;if(data?.schema!=='vone.operation-passport/v1'||data.execution_id!==executionId)throw new Error('Passport neodpovídá vybranému běhu.');renderOperationPassport(data)}catch(err){if(epoch!==passportSelectionEpoch||bearer!==state.token)return;const missing=err.statusCode===404;const title=missing?'Canonical passport není pro tento execution dostupný.':'Canonical passport se nepodařilo bezpečně načíst.';const note=missing?'Runs obsahují i legacy execution záznamy. Absence canonical lineage se zobrazuje explicitně a není nahrazena domněnkou.':'Chyba čtení nebo konflikt canonical lineage se nesmí interpretovat jako prostá absence. Stav zůstává UNKNOWN, dokud není příčina ověřena.';$('operation-passport-content').innerHTML=`<article class="passport-unavailable"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(err.message)}</p><p class="muted">${escapeHtml(note)}</p></article>`}}
$('runs-table').addEventListener('click',event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-passport-execution-id]');if(!button)return;loadOperationPassport(button.dataset.passportExecutionId)})
$('close-passport-button').addEventListener('click',clearOperationPassport)
async function loadPlans(){
  const epoch=++requestContextEpoch;
  clearRequestContext('Načítám aktuální požadavky…');
  try{
  // Both lists are existing authorized GET APIs; an absent/mismatched row is NOT an execution permission.
  const [data,requests,runtime]=await Promise.all([
    api('/control-room',{cache:'no-store'}),api('/change-requests',{cache:'no-store'}),api('/operations/status',{cache:'no-store'}).catch(()=>null)
  ]);
  if(epoch!==requestContextEpoch)return;
  updateRequestCapabilities(data);
  const byId=new Map(requests.map(item=>[item.id,item]));
  $('plans-table').innerHTML=data.plans.items.length?data.plans.items.map(plan=>{
    const request=byId.get(plan.request_id);
    const bound=request && request.status===plan.status && request.environment===plan.environment;
    let action='<span class="muted">UNKNOWN · obnovit</span>';
    if(bound && plan.status==='DRAFT'){
      action=`<button data-change-action="submit" data-request-id="${escapeHtml(plan.request_id)}">Submit</button>`;
    }else if(bound && plan.status==='APPROVED' && request.adapter==='github-read-ref'){
      const approval=canonicalReadApprovalWindow(request,runtime);
      const allowed=canonicalReadReady(runtime)&&['local','development','staging'].includes(plan.environment)
        && canonicalReadPayloadValid(request.payload)&&approval.eligible;
      action=allowed?`<button data-change-action="canonical-read" data-request-id="${escapeHtml(plan.request_id)}">Canonical READ</button><small class="muted">${escapeHtml(approval.label)}</small>`
        :`<span class="muted">${escapeHtml(approval.reason==='EXPIRED'
          ?approval.label:'READ DISABLED · runtime / scope / schválení neověřeno')}</span>`;
    }else if(bound && plan.status==='APPROVED' && plan.environment!=='production'
      && ['echo','write_artifact','run_validation'].includes(request.adapter)){
      action=`<button data-change-action="execute" data-request-id="${escapeHtml(plan.request_id)}">Spustit schválenou operaci</button>`;
    }else if(bound){action='<span class="muted">—</span>'}
    return `<tr><td>${escapeHtml(plan.risk)}</td><td><strong>${escapeHtml(plan.title)}</strong><br><span class="mono muted">${escapeHtml(plan.request_id)}</span><br><small>${escapeHtml(request?.adapter||'UNKNOWN')}</small></td><td>${status(plan.status)}</td><td>${escapeHtml(plan.approval_count)} / ${escapeHtml(plan.approval_required)}</td><td>${escapeHtml(plan.environment)}</td><td class="actions">${action}</td></tr>`;
  }).join(''):'<tr><td colspan="6" class="muted">Žádné plány.</td></tr>';
  await loadApprovals(byId,epoch);
  }catch(err){
    if(epoch===requestContextEpoch)clearRequestContext('UNKNOWN · aktuální kontext požadavků není dostupný.');
    throw err;
  }
}
async function loadRegistry(){const data=await controlRoom();$('registry-summary').innerHTML=[fact('Fail-closed default',String(data.capability_registry.fail_closed_default),data.capability_registry.fail_closed_default?'ENFORCED':'FAIL'),fact('Production effects',data.capability_registry.production_effects_enabled?'ENABLED':'DISABLED',data.capability_registry.production_effects_enabled?'ENABLED':'DISABLED')].join('');$('registry-cards').innerHTML=data.capability_registry.items.map(item=>`<article class="panel"><header class="panel-heading"><strong>${escapeHtml(item.id)}</strong>${status(item.runtime_status)}</header><p>${escapeHtml(item.surface)} · ${escapeHtml(item.effect)}</p><p class="muted">Verification: ${escapeHtml(item.verification)}</p></article>`).join('')}
let timelineRefreshEpoch=0;
async function loadTimeline(){const epoch=++timelineRefreshEpoch;$('timeline-list').textContent='Načítám aktuální důkazy…';try{const data=await api('/control-room',{cache:'no-store'});if(epoch!==timelineRefreshEpoch)return;if(!Array.isArray(data?.evidence_timeline))throw new Error('Neúplná projekce důkazů.');const filter=$('timeline-filter').value;
  const items=data.evidence_timeline.filter(item=>filter==='all'||(filter==='access')===(item.title==='session.issue'));
  $('timeline-list').innerHTML=items.length?items.map(item=>{const canonical=item.source==='OPERATION_PASSPORT';const drilldown=canonical&&item.execution_id?`<button class="secondary compact-button" type="button" data-evidence-passport-execution-id="${escapeHtml(item.execution_id)}">Passport</button>`:'';return `<article class="receipt-card"><header><strong>${escapeHtml(item.kind)} · ${escapeHtml(item.title==='session.issue'?'Vydání přístupové relace':item.title)}</strong>${status(item.status)}</header><p>${escapeHtml(item.detail)}</p><p class="muted">${escapeHtml(item.source||'UNKNOWN_SOURCE')} · ${escapeHtml(item.timestamp && Number.isFinite(Date.parse(item.timestamp)) ? new Date(item.timestamp).toLocaleString('cs-CZ') : 'Čas neuveden')}</p>${drilldown}</article>`}).join(''):'<article class="panel muted">Žádná evidence.</article>'}catch(err){if(epoch!==timelineRefreshEpoch)return;$('timeline-list').textContent='UNKNOWN · aktuální důkazy nejsou dostupné.';throw err}}
$('timeline-filter').addEventListener('change',()=>loadView('evidence'));
async function openEvidencePassport(executionId){if(!canonicalReadRequestPattern.test(executionId||''))return;const loading=loadView('runs');await loadOperationPassport(executionId);await loading}
$('timeline-list').addEventListener('click',async event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-evidence-passport-execution-id]');if(!button)return;await openEvidencePassport(button.dataset.evidencePassportExecutionId)})
for (const view of ['authority','lifecycle','lineage']) {
  $('view-'+view).addEventListener('click',async event=>{
    if (!(event.target instanceof Element)) return;
    const button=event.target.closest('button');
    if (button?.hasAttribute('data-board-policy')) await loadView('policy');
    if (button?.dataset.boardPassport) {
      if(await loadView('runs'))await loadOperationPassport(button.dataset.boardPassport);
    }
  });
}
async function loadPolicy(){const data=await controlRoom();$('policy-gates').innerHTML=Object.entries({truth_invariant:'Pravidla vyhodnocení',runtime:'Provozní omezení',evidence:'Integrita záznamů'}).map(([source,label])=>'<section><h2>'+label+'</h2>'+data.policy_gates.filter(gate=>gate.source===source).map(gate=>fact(gate.name,gate.source,gate.status)).join('')+'</section>').join('')}
let verifierRefreshEpoch=0;
async function loadVerifier(){
  const epoch=++verifierRefreshEpoch;
  $('verifier-list').textContent='Načítám aktuální výsledky ověření…';
  $('verifier-rule').textContent='ExecutionReceipt != VerificationResult';
  try{
    const data=await api('/control-room',{cache:'no-store'});
    if(epoch!==verifierRefreshEpoch)return;
    const center=data?.verifier_center;
    if(!Array.isArray(center?.recent_checks)||center.separation_rule!=='ExecutionReceipt != VerificationResult')
      throw new Error('Neúplná projekce ověření.');
    $('verifier-list').innerHTML=center.recent_checks.length?center.recent_checks.map(check=>{
      const canonical=check.source==='VERIFICATION_RESULT_V1';
      const legacy=check.source==='LEGACY_RECEIPT';
      const bound=canonical&&typeof check.execution_id==='string'&&canonicalReadRequestPattern.test(check.execution_id);
      const reference=canonical?check.result_digest:(check.receipt_id||check.execution_id);
      const evidencePresent=bound&&typeof check.result_digest==='string'&&!!check.result_digest
        &&typeof check.verification_strength==='string'&&!!check.verification_strength
        &&typeof check.checked_at==='string'&&Number.isFinite(Date.parse(check.checked_at));
      const verdict=evidencePresent?(check.verification_status||'UNKNOWN'):'UNKNOWN';
      const provenance=canonical?`Strength ${escapeHtml(check.verification_strength||'UNKNOWN')} · checked ${escapeHtml(check.checked_at||'TIME_NOT_AVAILABLE')}`:
        'No durable independent VerificationResult/v1 is bound to this receipt.';
      const drilldown=bound?`<button class="secondary compact-button" type="button" data-verifier-passport-execution-id="${escapeHtml(check.execution_id)}">Passport</button>`:'';
      return `<article class="receipt-card"><header><strong>${escapeHtml(canonical?'VerificationResult/v1':legacy?'Legacy receipt':'UNKNOWN_SOURCE')} · ${escapeHtml(reference||'NOT_AVAILABLE')}</strong>${status(verdict)}</header><p>Execution ${escapeHtml(check.execution_id)} · ${escapeHtml(check.execution_status)}</p><p class="muted">${provenance}</p>${drilldown}</article>`;
    }).join(''):'<article class="panel muted">Independent verification zatím nemá runtime výsledek.</article>';
  }catch(err){
    if(epoch!==verifierRefreshEpoch)return;
    $('verifier-list').textContent='UNKNOWN · aktuální výsledky ověření nejsou dostupné.';
    throw err;
  }
}
$('verifier-list').addEventListener('click',async event=>{
  if(!(event.target instanceof Element))return;
  const button=event.target.closest('button[data-verifier-passport-execution-id]');
  if(!button)return;
  await openEvidencePassport(button.dataset.verifierPassportExecutionId);
});
// Systém is a read-only diagnostic projection except for the existing,
// server-authorized emergency-stop action. Configuration is not live proof.
function showStopState(active, environment, canActivate=false, canClear=false) {
  $('activate-stop').disabled = !canActivate || active !== false;
  $('clear-stop').disabled = !canClear || active !== true;
  $('activate-stop').hidden = active === true;
  $('clear-stop').hidden = active === false;
  const label = active === true ? 'Aktivní' : active === false ? 'Vypnuto' : 'Stav neověřen';
  $('stop-state').textContent = environment ? label + ' · ' + environment : label;
}
let healthRefreshEpoch=0;
let healthStopAuthority=null;
let healthStopPending=null;
// Local presentation safeguard, not a server-issued authorization or lease.
// Measure from the start of the diagnostic read, including time spent waiting.
const HEALTH_CLEAR_FRESHNESS_MS=30000;
let healthClearExpiryTimer=null;
function healthClock(){
  return {wall:Date.now(),monotonic:typeof performance==='undefined'?NaN:performance.now()};
}
function healthClearRemaining(started){
  const now=healthClock();
  const wall=now.wall-started.wall,mono=now.monotonic-started.monotonic;
  return Number.isFinite(wall)&&Number.isFinite(mono)&&wall>=0&&mono>=0
    ?Math.max(0,HEALTH_CLEAR_FRESHNESS_MS-Math.max(wall,mono)):0;
}
function cancelHealthClearExpiry(){
  if(healthClearExpiryTimer!==null)clearTimeout(healthClearExpiryTimer);
  healthClearExpiryTimer=null;
}
function expireHealthClear(auth){
  if(healthStopAuthority!==auth||auth.bearer!==state.token||auth.epoch!==viewEpoch
    ||auth.generation!==healthRefreshEpoch||!healthViewActive())return;
  cancelHealthClearExpiry();
  healthStopAuthority=null;
  $('clear-stop').disabled=true;
  $('health-action-feedback').textContent='Platnost diagnostiky pro zrušení stop vypršela. Obnov diagnostiku; žádný požadavek nebyl odeslán.';
}
function scheduleHealthClearExpiry(auth){
  const remaining=healthClearRemaining(auth.started);
  if(!remaining){expireHealthClear(auth);return}
  healthClearExpiryTimer=setTimeout(()=>{
    if(healthStopAuthority!==auth)return;
    healthClearExpiryTimer=null;
    scheduleHealthClearExpiry(auth);
  },remaining);
}
function healthViewActive(){
  return $('view-health').classList.contains('active');
}
function clearRuntimeHealthContext({loading=false,clearReason=false}={}){
  ++healthRefreshEpoch;
  cancelHealthClearExpiry();
  healthStopAuthority=null;
  showStopState(null);
  if(clearReason)$('stop-reason').value='';
  $('health-time').textContent=loading?'Načítám aktuální autorizovanou diagnostiku…':'Aktuální stav není ověřen.';
  $('health-overall').textContent='UNKNOWN';
  $('health-overall').className='status UNKNOWN';
  for(const id of ['health-summary','health-perimeter','health-components','health-problems','health-events','health-versions']){
    $(id).textContent=loading?'Načítám…':'Nedostupné · bez aktuální projekce.';
  }
  $('health-json').textContent='';
  $('health-action-feedback').textContent='';
}
const healthRecord=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
const healthIntegrity=value=>value?.valid===true?'PASS':value?.valid===false?'FAIL':'UNKNOWN';
const healthFlag=(value,yes,no)=>value===true?yes:value===false?no:'UNKNOWN';
const healthKnown=(value,allowed)=>allowed.includes(value)?value:'UNKNOWN';
const healthString=value=>typeof value==='string'&&value.trim()?value:'Nedostupné';
function healthCard(title,verdict,detail,source){
  return '<details class="system-component"><summary><strong>'+escapeHtml(title)+'</strong>'+status(verdict)+'</summary>'+
    '<p>'+escapeHtml(detail)+'</p><small>Zdroj: '+escapeHtml(source)+'</small></details>';
}
function renderRuntimeHealth(data,liveness,operations,principal,allowControls=true){
  if(!healthRecord(data)||!healthRecord(data.overview)||!Array.isArray(data.runtime_health))
    throw new Error('Neplatná provozní projekce.');
  const o=data.overview;
  const rows=data.runtime_health.filter(healthRecord);
  const byName=name=>{const matches=rows.filter(item=>item.name===name);return matches.length===1?matches[0]:undefined};
  const probe=healthRecord(liveness)?liveness:{};
  const runtime=healthRecord(operations)&&operations.schema==='vone.canonical-operation-api-status/v1'?operations:{};
  const env=healthString(o.environment);
  const trust=healthKnown(o.trust_state,['HEALTHY','INCIDENT']);
  const receipts=healthIntegrity(o.receipt_integrity),audit=healthIntegrity(o.audit_integrity);
  const integrity=receipts==='FAIL'||audit==='FAIL'?'FAIL':receipts==='PASS'&&audit==='PASS'?'PASS':'UNKNOWN';
  const production=healthFlag(o.production_effects_enabled,'ENABLED','DISABLED');
  const stop=healthFlag(o.emergency_stop,'ACTIVE','INACTIVE');
  const apiState=healthKnown(probe.status,['HEALTHY','EMERGENCY_STOP','UNAVAILABLE']);
  const dbState=healthKnown(probe.database,['HEALTHY','UNAVAILABLE']);
  const conflictingStop=(apiState==='EMERGENCY_STOP'&&stop==='INACTIVE')||(apiState==='HEALTHY'&&stop==='ACTIVE');
  const conflictingDb=dbState!=='UNKNOWN'&&healthKnown(byName('Database')?.status,['HEALTHY','UNAVAILABLE'])!=='UNKNOWN'
    &&dbState!==byName('Database').status;
  const readState=runtime.configured===false&&runtime.read_terminal_configured===false?'DISABLED':
    runtime.configured===true&&runtime.read_terminal_configured===true?'CONFIGURED':'UNKNOWN';
  const writeState=runtime.write_routes_exposed===false&&runtime.provider_write_effects_exposed===false?'DISABLED':'UNKNOWN';
  const projectionConfigured=healthKnown(byName('Canonical runtime')?.status,['ENABLED','DISABLED']);
  const runtimeConflict=(projectionConfigured==='DISABLED'&&runtime.configured===true)||(projectionConfigured==='ENABLED'&&runtime.configured===false);
  const role=healthRecord(principal)?healthString(principal.role):'Nedostupné';
  const uiEligible=['administrator','security_reviewer'].includes(role);
  const primaryApi=healthKnown(byName('API')?.status,['HEALTHY','EMERGENCY_STOP','UNAVAILABLE']);
  const primaryDb=healthKnown(byName('Database')?.status,['HEALTHY','UNAVAILABLE']);
  const conflictingApi=primaryApi!=='UNKNOWN'&&apiState!=='UNKNOWN'&&primaryApi!==apiState;
  const eligible=uiEligible&&!conflictingStop&&!conflictingApi&&env!=='Nedostupné';
  // Activating a protective stop is distinct from removing it. Only the
  // latter requires complete, consistent fresh safety signals. Server
  // authorization remains authoritative; these are presentation safeguards.
  const confirmedStop=(stop==='ACTIVE'&&apiState==='EMERGENCY_STOP'&&primaryApi==='EMERGENCY_STOP')
    ||(stop==='INACTIVE'&&apiState==='HEALTHY'&&primaryApi==='HEALTHY');
  const confirmedDb=dbState==='HEALTHY'&&primaryDb==='HEALTHY'&&!conflictingDb;
  const canActivate=allowControls&&eligible&&stop==='INACTIVE';
  const canClear=allowControls&&eligible&&stop==='ACTIVE'&&trust==='INCIDENT'
    &&confirmedStop&&confirmedDb&&integrity==='PASS'&&!runtimeConflict;
  const observedStop=confirmedStop&&confirmedDb?o.emergency_stop:null;
  const overall=trust==='INCIDENT'||integrity==='FAIL'||stop==='ACTIVE'||apiState==='EMERGENCY_STOP'||apiState==='UNAVAILABLE'||dbState==='UNAVAILABLE'
    ||primaryApi==='EMERGENCY_STOP'||primaryApi==='UNAVAILABLE'||primaryDb==='UNAVAILABLE'?'INCIDENT':
    trust==='HEALTHY'&&integrity==='PASS'&&stop==='INACTIVE'&&confirmedStop&&confirmedDb&&!runtimeConflict?'HEALTHY':'UNKNOWN';
  $('health-overall').textContent=overall;
  $('health-overall').className='status '+overall;
  $('health-time').textContent='Načteno v prohlížeči '+new Date().toLocaleTimeString()+' · '+env.toUpperCase()+' · není trvalý monitoring';
  $('health-summary').innerHTML=[
    fact('Control Room',trust,trust),
    fact('API / liveness',apiState,apiState),
    fact('Databáze / liveness',dbState,dbState),
    fact('Databázový backend',healthString(probe.database_backend),probe.database_backend?'OBSERVED':'UNKNOWN')
  ].join('');
  $('health-perimeter').innerHTML=[
    fact('Nouzové zastavení',conflictingStop?'Rozpor měření':stop,conflictingStop?'UNKNOWN':stop),
    fact('Produkční účinky',production,production),
    fact('Auditní řetězec',audit,audit),
    fact('Receipt řetězec',receipts,receipts),
    fact('Role aktuální relace',role,role==='Nedostupné'?'UNKNOWN':'OBSERVED'),
    fact('Provider WRITE',writeState,writeState)
  ].join('');
  $('health-components').innerHTML=[
    healthCard('Canonical runtime / G8 READ',runtimeConflict?'UNKNOWN':readState,
      runtimeConflict?'Konfigurace se mezi projekcemi rozchází.':readState==='CONFIGURED'?'READ terminál je nakonfigurován. Neprokazuje funkční provider, Runner ani Verifier.':readState==='DISABLED'?'READ runtime není nakonfigurován.':'Přesnou konfiguraci se nepodařilo potvrdit.',
      '/operations/status + /control-room'),
    healthCard('Identita',byName('Identity')?.status?'CONFIGURED':'UNKNOWN',
      healthString(byName('Identity')?.status)+' · konfigurace poskytovatele; není důkaz jeho nezávislé dostupnosti.','/control-room runtime_health'),
    healthCard('CASEBOOK','UNKNOWN','Dostupnost a integritu konkrétní relace ověř v Deníku. Tato obrazovka nemá samostatný health probe.','Diagnostické API nevystaveno'),
    ...['CASER','CASTER-MINAL','Runner','Verifier','MRC','GitHub provider','Nexus'].map(name=>
      healthCard(name,'UNKNOWN','Tato projekce nevystavuje samostatnou živou kontrolu komponenty.','Diagnostické API nevystaveno'))
  ].join('');
  const problems=[];
  if(stop==='ACTIVE'||apiState==='EMERGENCY_STOP')problems.push(['BLOCKED','Nouzové zastavení hlášeno','Prověř aktuální stav; aktivní stop blokuje nové execution operace.']);
  if(integrity==='FAIL')problems.push(['FAIL','Integrita evidence','Audit nebo receipt řetězec je neplatný. Prověř důkazy, nikoli pouze liveness.']);
  if(apiState==='UNAVAILABLE'||dbState==='UNAVAILABLE'||primaryApi==='UNAVAILABLE'||primaryDb==='UNAVAILABLE')problems.push(['UNAVAILABLE','Liveness','API nebo databáze hlásí nedostupnost.']);
  if(conflictingStop||conflictingApi||conflictingDb||runtimeConflict)problems.push(['UNKNOWN','Rozpor mezi čteními','Obnov diagnostiku. Údaje nejsou jedním atomickým snapshotem.']);
  if(trust==='INCIDENT'&&!problems.length)problems.push(['INCIDENT','Control Room hlásí incident','Příčina nebyla v projekci potvrzena.']);
  if(trust==='UNKNOWN'||integrity==='UNKNOWN'||stop==='UNKNOWN'||apiState==='UNKNOWN'||dbState==='UNKNOWN'||primaryApi==='UNKNOWN'||primaryDb==='UNKNOWN')
    problems.push(['UNKNOWN','Neúplná diagnostika','Chybí platné měření nebo stav některého povinného signálu.']);
  if(readState==='UNKNOWN'||runtimeConflict||writeState==='UNKNOWN')
    problems.push(['UNKNOWN','Neověřená konfigurace canonical runtime','Chybí konzistentní výsledek /operations/status.']);
  $('health-problems').innerHTML=problems.length?problems.map(([verdict,title,detail])=>
    '<div class="system-problem">'+status(verdict)+'<strong>'+escapeHtml(title)+'</strong><p>'+escapeHtml(detail)+'</p></div>').join(''):
    '<p class="muted">V načtených základních signálech není potvrzená porucha. Neověřené komponenty nejsou zahrnuty.</p>';
  const events=Array.isArray(data.evidence_timeline)?data.evidence_timeline.filter(item=>healthRecord(item)&&item.kind==='AUDIT_EVENT'&&item.source==='AUDIT_LEDGER').slice(0,5):null;
  $('health-events').innerHTML=events?.length?events.map(item=>
    '<div class="lc-event">'+status(healthKnown(item.status,['RECORDED']))+'<div><strong>'+escapeHtml(healthString(item.title))+'</strong><small>'+escapeHtml(healthString(item.timestamp))+' · AUDIT_LEDGER</small></div></div>').join(''):
    '<p class="muted">'+(events?'V načteném omezeném výřezu nejsou auditní události.':'Auditní výřez nebyl vystaven.')+'</p>';
  const schema=Number.isSafeInteger(probe.schema_version)&&probe.schema_version>=0?String(probe.schema_version):'Nedostupné';
  $('health-versions').innerHTML=[
    fact('Databázové schéma',schema,schema==='Nedostupné'?'UNKNOWN':'OBSERVED'),
    fact('Čas serveru / operations',healthString(runtime.server_time_utc),runtime.server_time_utc?'OBSERVED':'UNKNOWN'),
    fact('Běžící commit','API nevystavuje','NOT_EXPOSED'),
    fact('Poslední ověřená obnova','API nevystavuje','NOT_EXPOSED'),
    fact('Latence / vytížení','Bez měření','NOT_EXPOSED')
  ].join('');
  $('health-json').textContent=JSON.stringify({runtime_health:rows,liveness:probe,operations_status:runtime},null,2);
  showStopState(conflictingStop||conflictingApi?null:o.emergency_stop,env==='Nedostupné'?undefined:env,canActivate,canClear);
  if(!allowControls)$('health-action-feedback').textContent='Čtení začalo během předchozího požadavku. Ovládání zůstává blokováno; po jeho dokončení obnov diagnostiku.';
  else if(stop==='ACTIVE'&&!canClear)$('health-action-feedback').textContent='Zrušení stop není nyní způsobilé: vyžaduje oprávněnou relaci, konzistentní stop, dostupnou databázi a platnou integritu.';
  return {active:o.emergency_stop,environment:env,canActivate,canClear,observedStop};
}
async function loadRuntimeHealth(){
  const bearer=state.token,epoch=viewEpoch;
  if(!bearer||!healthViewActive())return;
  clearRuntimeHealthContext({loading:true});
  const generation=healthRefreshEpoch;
  const started=healthClock();
  // A read begun during a mutation is never a fresh action authority, even
  // if it completes after the POST. A new explicit refresh is required.
  const pendingAtStart=healthStopPending?.bearer===bearer;
  const current=()=>bearer===state.token&&epoch===viewEpoch&&generation===healthRefreshEpoch&&healthViewActive();
  try{
    // Only the authenticated Control Room projection owns presentation.
    // Supplemental reads never manufacture positive health or permission.
    const [primary,live,ops,me]=await Promise.allSettled([
      api('/control-room',{cache:'no-store'}),api('/health',{cache:'no-store'}),
      api('/operations/status',{cache:'no-store'}),api('/me',{cache:'no-store'})
    ]);
    if(!current())return;
    if(primary.status!=='fulfilled')throw primary.reason;
    if(me.status==='rejected'&&[401,403].includes(me.reason?.statusCode))throw me.reason;
    if(ops.status==='rejected'&&ops.reason?.statusCode===401)throw ops.reason;
    const liveness=live.status==='fulfilled'?live.value:
      live.reason?.statusCode===503?{status:'UNAVAILABLE'}:null;
    const observation=renderRuntimeHealth(primary.value,liveness,ops.status==='fulfilled'?ops.value:null,me.status==='fulfilled'?me.value:null,
      !pendingAtStart&&healthStopPending?.bearer!==bearer);
    healthStopAuthority=observation.canActivate||observation.canClear?{...observation,bearer,epoch,generation,started}:null;
    if(healthStopAuthority?.canClear)scheduleHealthClearExpiry(healthStopAuthority);
    return healthClearRemaining(started)>0?observation.observedStop:null;
  }catch(error){
    if(!current())return;
    clearRuntimeHealthContext();
    throw error;
  }
}
async function setStop(active){
  const auth=healthStopAuthority,bearer=state.token;
  if(typeof active!=='boolean'||!auth||!bearer||auth.bearer!==bearer||auth.epoch!==viewEpoch
    ||auth.generation!==healthRefreshEpoch||!healthViewActive()||auth.active===active
    ||(active?!auth.canActivate:!auth.canClear)||healthStopPending?.bearer===bearer)return;
  if(!active&&!healthClearRemaining(auth.started)){expireHealthClear(auth);return}
  const reason=$('stop-reason').value.trim();
  if(reason.length<3){toast('Vyplň důvod',true);return}
  const epoch=viewEpoch;
  const pending={bearer};
  healthStopPending=pending;
  clearRuntimeHealthContext({loading:true});
  const generation=healthRefreshEpoch;
  $('health-action-feedback').textContent='Odesílám jediný požadavek. Čekám na potvrzení serveru.';
  let accepted=false;
  try{
    await api('/system/emergency-stop',{method:'POST',body:JSON.stringify({active,reason})});
    accepted=true;
  }catch{
    // Do not retry a potentially applied mutation. Read back instead.
  }finally{
    if(healthStopPending===pending)healthStopPending=null;
  }
  // Do not let an older mutation erase input, refresh, or report its
  // outcome in a newer view or refresh generation of the same session.
  if(bearer!==state.token||epoch!==viewEpoch||generation!==healthRefreshEpoch||!healthViewActive())return;
  if($('stop-reason').value.trim()===reason)$('stop-reason').value='';
  const expectedGeneration=generation+1;
  let readback;
  try{readback=await loadRuntimeHealth()}catch{return}
  if(bearer!==state.token||epoch!==viewEpoch||expectedGeneration!==healthRefreshEpoch||!healthViewActive())return;
  $('health-action-feedback').textContent=accepted&&readback===active
    ?'Server potvrdil požadavek a stav byl znovu načten.'
    :'Výsledek požadavku není potvrzen. Nepokračuj automatickým opakováním; zkontroluj aktuální stav a audit.';
}
async function loadLearning(){const data=await controlRoom();$('learning-signals').innerHTML=data.learning_intelligence.signals.map(item=>fact(item.name === 'Execution success rate' ? 'Úspěšnost dokončených běhů (n = '+String(data.learning_intelligence.completed_sample ?? 'neuvedeno')+')' : item.name,item.value,item.status)).join('');$('learning-router').textContent=data.learning_intelligence.scoring_router}
async function loadProjectMap(){
  const banner=$('projectmap-status');
  $('projectmap-details').hidden=true;
  banner.textContent='Načítám SHA-256 ověřený snapshot. Nejedná se o živé Git údaje.';
  $('projectmap-projects').textContent='';
  $('projectmap-relations').textContent='';
  $('projectmap-gaps').textContent='';
  try{
    const data=await api('/project-control-map');
    if(data?.schema!=='ProjectControlMapProjection/v1'||data.mode!=='READ_ONLY'
      ||data.authority_effect!=='NONE'||!Array.isArray(data.projects)
      ||!Array.isArray(data.relationships)||!Array.isArray(data.known_gaps))
      throw new Error('Neověřená struktura mapy');
    const digest=String(data.snapshot_sha256||'');
    if(!/^[0-9a-f]{64}$/.test(digest))throw new Error('Neověřený hash snapshotu');
    const summary=document.createElement('p');
    summary.className='projectmap-summary';
    summary.textContent=`Stav zaznamenaný ve snapshotu ${data.observed_at_utc} · ${data.freshness} · FinishGate podle snapshotu: ${data.active_delivery} (${data.focus_status}). Žádné schvalování ani změny.`;
    const details=document.createElement('details');
    details.className='projectmap-digest';
    const label=document.createElement('summary');
    label.textContent=`SHA-256 ${digest.slice(0,12)}… (zobrazit celý otisk)`;
    const full=document.createElement('code');
    full.textContent=digest;
    details.append(label,full);
    banner.replaceChildren(summary,details);
    $('projectmap-projects').innerHTML=data.projects.map(p=>{
      const parts=String(p.repo||'').split('/');
      const link=parts.length===2 && parts.every(x=>/^[A-Za-z0-9_.-]+$/.test(x))
        ? `https://github.com/${encodeURIComponent(parts[0])}/${encodeURIComponent(parts[1])}`:null;
      const label=link?`<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(p.name)}</a>`:escapeHtml(p.name);
      return `<article class="panel projectmap-card">
        <header class="panel-heading"><h2>${label}</h2>${status(p.freshness)}</header>
        <p class="muted">${escapeHtml(p.kind)} · ${escapeHtml(p.status)}</p>
        <p><strong>Git:</strong> <span class="mono">${escapeHtml(p.branch)}</span></p>
        <p><strong>Lokální / GitHub:</strong> <span class="mono">${escapeHtml(p.local_head)} / ${escapeHtml(p.hosted_head)}</span></p>
        <p><strong>Porovnání:</strong> ${status(p.head_comparison)} · <strong>Working tree:</strong> ${escapeHtml(p.worktree)}</p>
      </article>`;
    }).join('');
    $('projectmap-details').hidden=false;
    $('projectmap-relations').innerHTML=data.relationships.map(r=>
      `<li><strong>${escapeHtml(r.from)}</strong> → <strong>${escapeHtml(r.to)}</strong>
      <span class="muted">${escapeHtml(r.kind)} · ${escapeHtml(r.status)}</span></li>`).join('');
    $('projectmap-gaps').innerHTML=data.known_gaps.map(g=>`<li>${escapeHtml(g)}</li>`).join('');
  }catch(error){
    banner.textContent=error.message==='project control map snapshot not configured'?'UNAVAILABLE / UNVERIFIED — chybí konfigurace ověřeného snímku.':error.statusCode===403?'Pro tuto mapu chybí oprávnění.':'UNAVAILABLE / UNVERIFIED — mapový snapshot není nakonfigurován, je neplatný nebo se nepodařilo načtení. Žádné údaje nebyly považovány za aktuální.';
    $('projectmap-projects').textContent='';
    $('projectmap-relations').textContent='';
    $('projectmap-gaps').textContent='';
  }
}
async function loadGovernance(){
  const bearer=state.token,epoch=viewEpoch;
  if(!bearer||!settingsViewActive())return;
  clearSettingsContext({loading:true});
  const generation=settingsRefreshEpoch;
  const current=()=>bearer===state.token&&epoch===viewEpoch&&generation===settingsRefreshEpoch&&settingsViewActive();
  try{
    const [primary,identity,operations]=await Promise.allSettled([
      api('/control-room',{cache:'no-store'}),api('/me',{cache:'no-store'}),
      api('/operations/status',{cache:'no-store'})
    ]);
    if(!current())return;
    if(primary.status!=='fulfilled')throw primary.reason;
    if(identity.status==='rejected'&&[401,403].includes(identity.reason?.statusCode))throw identity.reason;
    if(operations.status==='rejected'&&operations.reason?.statusCode===401)throw operations.reason;
    const data=primary.value;
    if(!healthRecord(data)||!healthRecord(data.governance))throw new Error('Neplatná konfigurace prostředí.');
    const config=data.governance;
    const me=identity.status==='fulfilled'&&healthRecord(identity.value)?identity.value:{};
    const op=operations.status==='fulfilled'&&operations.value?.schema==='vone.canonical-operation-api-status/v1'?operations.value:{};
    const env=healthString(config.environment);
    const environmentConsistent=env!=='Nedostupné'&&data.overview?.environment===env;
    const production=typeof config.production_effects_enabled==='boolean'&&config.production_effects_enabled===data.overview?.production_effects_enabled
      ?healthFlag(config.production_effects_enabled,'ENABLED','DISABLED'):'UNKNOWN';
    const compatibility=healthFlag(config.approval_policy_compatibility_enabled,'ENABLED','DISABLED');
    const configured=healthFlag(op.configured,'CONFIGURED','DISABLED');
    const readTerminal=op.configured===false&&op.read_terminal_configured===true?'UNKNOWN':healthFlag(op.read_terminal_configured,'CONFIGURED','DISABLED');
    const writes=op.write_routes_exposed===false&&op.provider_write_effects_exposed===false?'DISABLED':'UNKNOWN';
    const account=healthString(me.username),role=healthString(me.role),provider=healthString(config.identity_provider);
    $('settings-identity').innerHTML=[
      fact('Přihlášený účet',account,account==='Nedostupné'?'UNKNOWN':'OBSERVED'),
      fact('Role relace',role,role==='Nedostupné'?'UNKNOWN':'OBSERVED'),
      fact('Poskytovatel identity',provider,provider==='Nedostupné'?'UNKNOWN':'CONFIGURED')
    ].join('');
    $('governance-grid').innerHTML=[
      fact('Aktuální prostředí',environmentConsistent?env.toUpperCase():'Neověřeno',environmentConsistent?'OBSERVED':'UNKNOWN'),
      fact('Produkční účinky',production,production),
      fact('Kompatibilita schvalovací politiky',compatibility,compatibility)
    ].join('');
    $('settings-network').innerHTML=settingsList('Důvěryhodné hosty',config.trusted_hosts)+settingsList('Povolené CORS origins',config.cors_origins);
    $('settings-integrations').innerHTML=[
      fact('Canonical runtime',configured,configured),
      fact('READ terminál',readTerminal,readTerminal),
      fact('Provider WRITE',writes,writes),
      fact('Ostatní integrace','API neposkytuje konfigurační detail','NOT_EXPOSED')
    ].join('');
    $('governance-time').textContent='Načteno v prohlížeči '+new Date().toLocaleTimeString('cs-CZ')+' · pouze pro čtení';
    $('settings-configuration-state').textContent=environmentConsistent&&production!=='UNKNOWN'&&compatibility!=='UNKNOWN'?'OBSERVED':'UNKNOWN';
    $('settings-configuration-state').className='status '+$('settings-configuration-state').textContent;
  }catch(error){
    if(!current())return;
    clearSettingsContext();
    throw error;
  }
}
let settingsRefreshEpoch=0;
let settingsReducedMotion=false;
function settingsViewActive(){return $('view-governance').classList.contains('active')}
function applySettingsMotion(value){
  settingsReducedMotion=value===true;
  $('app-shell').classList.toggle('settings-reduced-motion',settingsReducedMotion);
  $('settings-reduced-motion').checked=settingsReducedMotion;
  $('settings-motion-state').textContent=settingsReducedMotion?'Omezení animací v této relaci aktivní.':'Používá se výchozí nastavení a preference operačního systému.';
}
function clearSettingsContext({loading=false,resetPreference=false}={}){
  ++settingsRefreshEpoch;
  for(const id of ['settings-identity','governance-grid','settings-network','settings-integrations'])
    $(id).textContent=loading?'Načítám…':'Nedostupné · konfigurace nebyla ověřena.';
  $('settings-configuration-state').textContent='UNKNOWN';
  $('settings-configuration-state').className='status UNKNOWN';
  $('governance-time').textContent=loading?'Načítám aktuální konfiguraci…':'Aktuální konfigurace nebyla ověřena.';
  if(resetPreference)applySettingsMotion(false);
}
function settingsList(label,items){
  const valid=Array.isArray(items)&&items.every(item=>typeof item==='string'&&item.trim());
  const content=!valid?'<p>Nedostupné</p>':items.length?'<ul>'+items.map(item=>'<li><code>'+escapeHtml(item)+'</code></li>').join('')+'</ul>':'<p>Žádné položky v konfiguraci.</p>';
  return '<article class="settings-network-list"><h3>'+escapeHtml(label)+'</h3>'+status(valid?'CONFIGURED':'UNKNOWN')+content+'</article>';
}
$('settings-reduced-motion').addEventListener('change',()=>{
  if(!state.token||!settingsViewActive()){applySettingsMotion(settingsReducedMotion);return}
  applySettingsMotion($('settings-reduced-motion').checked===true);
});
async function loadCommand(){const data=await api('/command-center');$('environment-badge').textContent=data.environment.toUpperCase();$('health-badge').textContent=data.trust_state;$('health-badge').className=`status ${data.trust_state}`;const kpis=[['Trust state',data.trust_state],['Active executions',data.executions.RUNNING||0],['Pending approvals',data.pending_approvals],['Production effects',data.production_effects_enabled?'ENABLED':'DISABLED']];$('command-kpis').innerHTML=kpis.map(x=>`<div class="kpi"><span>${escapeHtml(x[0])}</span><strong>${escapeHtml(x[1])}</strong></div>`).join('');$('risk-overview').innerHTML=['R0','R1','R2','R3','R4'].map(r=>`<p><strong>${r}</strong> · ${escapeHtml(data.risk[r]||0)}</p>`).join('');$('integrity-overview').innerHTML=`<p>Receipts: ${status(data.receipt_integrity.valid?'PASS':'FAIL')}</p><p>Audit: ${status(data.audit_integrity.valid?'PASS':'FAIL')}</p><p>Emergency stop: ${status(data.emergency_stop?'ACTIVE':'INACTIVE')}</p>`;const evidenceState=data.receipt_integrity.valid&&data.audit_integrity.valid?'PASS':'FAIL';const policyFacts=[fact('Environment',String(data.environment||'UNKNOWN').toUpperCase(),String(data.environment||'UNKNOWN').toUpperCase()),fact('Production effects',data.production_effects_enabled?'ENABLED':'DISABLED',data.production_effects_enabled?'ENABLED':'DISABLED'),fact('Emergency stop',data.emergency_stop?'ACTIVE':'INACTIVE',data.emergency_stop?'ACTIVE':'INACTIVE'),fact('Evidence integrity',evidenceState,evidenceState),fact('Approval policy metadata','NOT EXPOSED','UNKNOWN'),fact('Execution-plane isolation','NOT EXPOSED','UNKNOWN')];$('policy-overview').innerHTML=policyFacts.join('');$('policy-summary-status').textContent=data.trust_state;$('policy-summary-status').className=`status ${data.trust_state}`}
$('new-change-button').addEventListener('click',()=>{$('change-form-panel').classList.remove('hidden');invalidateChangeReview()})
$('cancel-change-button').addEventListener('click',()=>{$('change-form-panel').classList.add('hidden');invalidateChangeReview()})
$('change-workspace').addEventListener('change',syncChangeEnvironment)
$('change-adapter').addEventListener('change',syncChangeAdapter)
$('change-form').addEventListener('input',invalidateChangeReview)
$('change-form').addEventListener('change',invalidateChangeReview)
$('change-review-button').addEventListener('click',async()=>{
  invalidateChangeReview();
  try{await refreshRequestCapabilities();renderChangeReview(changeDraft())}
  catch(err){invalidateChangeReview();$('change-review').classList.remove('hidden');$('change-review-state').textContent='BLOKOVÁNO';$('change-review-state').className='status DENIED';$('change-review-note').textContent=err.message;toast(err.message,true)}
})
$('change-form').addEventListener('submit',async e=>{
  e.preventDefault();
  if(changeSubmitting)return;
  changeSubmitting=true;
  $('change-create-button').disabled=true;
  try{
    if(!reviewedChangeFingerprint)throw new Error('Nejdřív zkontrolujte aktuální dopad požadavku.');
    await refreshRequestCapabilities();
    const draft=changeDraft();
    if(reviewedChangeFingerprint!==changeFingerprint(draft))throw new Error('Nejdřív zkontrolujte aktuální dopad požadavku.');
    await api('/change-requests',{method:'POST',body:JSON.stringify({
      workspace_id:draft.workspace_id,title:draft.title,description:draft.description,
      risk:draft.risk,environment:draft.environment,adapter:draft.adapter,payload:draft.payload
    })});
    $('change-form-panel').classList.add('hidden');
    invalidateChangeReview();
    toast('Požadavek vytvořen · schválení je stále samostatné');
    try{await loadPlans()}catch{toast('Požadavek vytvořen · aktuální přehled není dostupný.',true)}
  }catch(err){invalidateChangeReview();toast(err.message,true)}
  finally{changeSubmitting=false}
})
$('plans-table').addEventListener('click',async event=>{
  if(!(event.target instanceof Element))return;
  const button=event.target.closest('button[data-change-action]');
  if(!button)return;
  const id=button.dataset.requestId;
  if(button.dataset.changeAction==='canonical-read'){
    await runCanonicalRead(id,button);
    return;
  }
  try{
    if(button.dataset.changeAction==='submit'){
      await api(`/change-requests/${encodeURIComponent(id)}/submit`,{method:'POST'});
      toast('Požadavek odeslán ke schválení');
    }else if(button.dataset.changeAction==='execute'){
      const result=await api(`/change-requests/${encodeURIComponent(id)}/execute`,{
        method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()}
      });
      toast(`Legacy execution ${result.status}`);
    }
    await loadPlans();
  }catch(err){toast(err.message,true)}
})
async function loadApprovals(requestsById=new Map(),epoch=requestContextEpoch){
  $('approvals-list').innerHTML='<article class="panel">Načítám rozhodovací kontext…</article>';
  let rows;
  try{
    rows=await api('/approvals?pending_only=true',{cache:'no-store'});
    if(epoch!==requestContextEpoch)return;
  }
  catch(err){
    if(epoch!==requestContextEpoch)return;
    if(err.statusCode===403){
      $('approvals-list').innerHTML='<article class="panel"><strong>Rozhodování není pro tuto relaci dostupné.</strong><p class="muted">Požadavky můžete dále vytvářet a sledovat. Schválení vyžaduje roli s oprávněním approval.review.</p></article>';
      return;
    }
    clearRequestContext('UNKNOWN · aktuální kontext schvalování není dostupný.');
    throw err;
  }
  $('approvals-list').innerHTML=rows.length?rows.map(row=>{
    const approved=Number(row.approved_count||0);
    const required=Number(row.required_count||0);
    const remaining=Math.max(required-approved,0);
    const request=requestsById.get(row.request_id);
    const capability=request?capabilityForAdapter(request.adapter):null;
    const exactContext=request&&capability&&request.status==='REVIEW_REQUIRED'
      &&request.title===row.title&&request.risk===row.risk&&request.environment===row.environment;
    const decisionActions=exactContext
      ?`<div class="actions"><button data-decision="APPROVED" data-request-id="${escapeHtml(row.request_id)}">Schválit jednou</button><button class="danger" data-decision="DENIED" data-request-id="${escapeHtml(row.request_id)}">Zamítnout</button></div>`
      :'<p class="error">Přesný požadavek nebo účinek není dostupný. Rozhodnutí je v tomto pohledu zablokováno.</p>';
    const facts=[
      ['Schváleno',`${approved} / ${required}`],
      ['Zbývá',remaining],
      ['Prostředí',String(row.environment||request?.environment||'UNKNOWN').toUpperCase()],
      ['Schopnost',capability?.id||request?.adapter||'UNKNOWN'],
      ['Účinek',capability?.effect||'UNKNOWN'],
      ['Ověření',capability?.verification||'UNKNOWN'],
      ['Cíl',request?requestTargetSummary(request.adapter,request.payload||{}):'UNKNOWN'],
    ];
    return `<article class="approval-card"><header><div><strong>${escapeHtml(row.title)}</strong><div class="mono muted">${escapeHtml(row.request_id)}</div></div>${status(row.risk)}</header><div class="approval-facts">${facts.map(([label,value])=>`<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')}</div><p class="muted">Rozhodnutí platí pouze pro zobrazený požadavek. Policy version a identita žadatele zatím nejsou v API vystavené.</p>${decisionActions}</article>`;
  }).join(''):'<article class="panel">Žádné požadavky nečekají na rozhodnutí.</article>';
}
$('approvals-list').addEventListener('click',async event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-decision]');if(!button)return;const reason=prompt('Důvod rozhodnutí:');if(!reason)return;try{await api(`/change-requests/${button.dataset.requestId}/decision`,{method:'POST',body:JSON.stringify({decision:button.dataset.decision,reason})});toast(`Rozhodnutí ${button.dataset.decision}`);await loadPlans()}catch(err){toast(err.message,true)}})
$('activate-stop').addEventListener('click',()=>setStop(true));$('clear-stop').addEventListener('click',()=>setStop(false));showApp();
