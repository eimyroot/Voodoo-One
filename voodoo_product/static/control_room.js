const state={token:sessionStorage.getItem('voodoo_token')||'',me:null,workspaces:[]};
const $=id=>document.getElementById(id);
function toast(message,error=false){const el=$('toast');el.textContent=message;el.classList.toggle('toast-error',error);el.classList.remove('hidden');setTimeout(()=>el.classList.add('hidden'),3500)}
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(state.token)headers.Authorization=`Bearer ${state.token}`;const response=await fetch(`/api/v1${path}`,{...options,headers});let body={};try{body=await response.json()}catch{}if(!response.ok){const error=new Error(body.detail||`HTTP ${response.status}`);error.statusCode=response.status;throw error}return body}
function status(value){const text=String(value??'UNKNOWN');const className=/^[A-Z][A-Z0-9_]{0,31}$/.test(text)?text:'UNKNOWN';return `<span class="status ${className}">${escapeHtml(text)}</span>`}
function escapeHtml(value){return String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]))}
async function authReady(){if(!state.token)return false;try{state.me=await api('/me');$('current-user').textContent=`${state.me.username} · ${state.me.role}`;return true}catch{sessionStorage.removeItem('voodoo_token');state.token='';return false}}
async function showApp(){if(!(await authReady())){showAuth();return}$('auth-screen').classList.add('hidden');$('app-shell').classList.remove('hidden');await loadWorkspaces();await loadView('overview')}
function showAuth(){$('app-shell').classList.add('hidden');$('auth-screen').classList.remove('hidden');api('/bootstrap/status').then(x=>$('bootstrap-panel').open=x.required).catch(()=>{})}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify({username:$('login-username').value,password:$('login-password').value})});state.token=result.token;sessionStorage.setItem('voodoo_token',result.token);$('auth-error').textContent='';await showApp()}catch(err){$('auth-error').textContent=err.message}})
$('bootstrap-form').addEventListener('submit',async e=>{e.preventDefault();try{const result=await api('/auth/bootstrap',{method:'POST',body:JSON.stringify({username:$('bootstrap-username').value,password:$('bootstrap-password').value,bootstrap_token:$('bootstrap-token').value})});state.token=result.token;sessionStorage.setItem('voodoo_token',result.token);await showApp()}catch(err){$('auth-error').textContent=err.message}})
$('logout-button').addEventListener('click',async()=>{let warning='';try{await api('/auth/logout', { method: 'POST' })}catch(err){console.warn('Server-side logout failed; clearing local session',err);warning='Serverové odvolání relace se nepodařilo potvrdit. Lokální token byl odstraněn.'}finally{state.token='';sessionStorage.removeItem('voodoo_token');showAuth();$('auth-error').textContent=warning}})
document.querySelectorAll('.nav').forEach(button=>button.addEventListener('click',()=>loadView(button.dataset.view)))
document.querySelectorAll('[data-refresh]').forEach(button=>button.addEventListener('click',()=>loadView(button.dataset.refresh)))
async function loadView(name){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));document.querySelectorAll('.nav').forEach(v=>v.classList.toggle('active',v.dataset.view===name));const view=$(`view-${name}`);if(!view){toast(`Neznámý pohled: ${name}`,true);return}view.classList.add('active');const loaders={ecosystem:loadEcosystemBoard,lifecycle:loadLifecycleBoard,authority:loadAuthorityBoard,lineage:loadLineageBoard,overlays:loadOverlaysBoard,projectmap:loadProjectMap,overview:loadOverview,runs:loadRuns,plans:loadPlans,registry:loadRegistry,evidence:loadTimeline,policy:loadPolicy,verifier:loadVerifier,health:loadRuntimeHealth,learning:loadLearning,governance:loadGovernance};try{await loaders[name]()}catch(err){toast(err.message,true)}}
function canonicalReadReady(runtime){
  return runtime?.configured===true && runtime.read_terminal_configured===true
    && runtime.write_routes_exposed===false && runtime.provider_write_effects_exposed===false;
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
function canonicalReadFeedback(message,error=false){
  const el=$('canonical-read-feedback');
  el.textContent=message;
  el.classList.toggle('error',error);
  el.classList.remove('hidden');
}
async function runCanonicalRead(requestId,button){
  if(!canonicalReadRequestPattern.test(requestId)||canonicalReadPending.has(requestId))return;
  canonicalReadPending.add(requestId);
  button.disabled=true;
  $('canonical-read-result').textContent='';
  $('canonical-read-result').classList.add('hidden');
  canonicalReadFeedback('Ověřuji oprávnění a aktuální schválení. Kanonický READ ještě nebyl spuštěn.');
  try{
    const [runtime,request]=await Promise.all([
      api('/operations/status'),
      api(`/change-requests/${encodeURIComponent(requestId)}`)
    ]);
    if(!canonicalReadReady(runtime))throw new Error('Kanonický READ runtime není dostupný. Nic nebylo spuštěno.');
    if(request?.id!==requestId||request.adapter!=='github-read-ref'||request.status!=='APPROVED'
      ||!['local','development','staging'].includes(request.environment)
      ||!canonicalReadPayloadValid(request.payload)){
      throw new Error('Požadavek nebo schválení nejsou platné pro kanonický GitHub READ.');
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
    if(result?.schema!=='vone.canonical-operation-read/v1'||result.operation?.request_id!==requestId
      ||!canonicalReadRequestPattern.test(result.operation?.execution_id||'')
      ||result.execution?.status!=='SUCCEEDED'||result.verification?.verdict!=='VERIFIED'
      ||result.verification?.strength_class!=='INDEPENDENT_PROVIDER_READBACK'
      ||typeof result.verification?.result_digest!=='string'||!result.verification.result_digest){
      throw new Error('Kanonický READ nemá ověřený výsledek. Stav UNKNOWN; neopakovat automaticky.');
    }
    const executionId=result.operation.execution_id;
    canonicalReadFeedback('Kanonický READ: nezávislý VERIFIER odpověděl VERIFIED. Otevírám Passport.');
    await loadView('runs');
    const receipt=$('canonical-read-result');
    receipt.textContent=`READ API: VERIFIED · ${executionId} · ${result.verification.strength_class} · digest ${result.verification.result_digest}. Passport uvádí pouze vlastní dostupnou durable evidenci.`;
    receipt.classList.remove('hidden');
    await loadOperationPassport(executionId);
  }catch(err){
    canonicalReadFeedback(`Kanonický READ: UNKNOWN / NEOVĚŘENO — ${err.message}. Bez automatického opakování; ověř stav a Passport podle request ID ${requestId}.`,true);
  }finally{
    canonicalReadPending.delete(requestId);
    button.disabled=false;
  }
}
function syncChangeAdapter(){
  if($('change-adapter').value==='github-read-ref'){
    $('change-payload').value='{"repository":"","ref":"refs/heads/main"}';
  }else if($('change-payload').value==='{"repository":"","ref":"refs/heads/main"}'){
    $('change-payload').value='{"message":"VOODOO One ready"}';
  }
}
function syncChangeEnvironment(){const workspace=state.workspaces.find(w=>w.id===$('change-workspace').value);$('change-environment').value=workspace?.environment||''}
async function loadWorkspaces(){state.workspaces=await api('/workspaces');$('change-workspace').innerHTML=state.workspaces.map(w=>`<option value="${escapeHtml(w.id)}">${escapeHtml(w.name)} · ${escapeHtml(w.environment)}</option>`).join('');syncChangeEnvironment()}
function fact(label,value,stateValue=value){return `<div class="fact"><span>${escapeHtml(label)}</span>${status(stateValue)}<strong>${escapeHtml(value)}</strong></div>`}
async function controlRoom(){return api('/control-room')}
function renderTable(target,rows,columns){$(target).innerHTML=rows.length?rows.map(row=>`<tr>${columns.map(column=>`<td>${column.status?status(row[column.key]):escapeHtml(row[column.key]??'—')}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${columns.length}" class="muted">Žádná data.</td></tr>`}
function renderArchitectureFlow(flow){const nodes=flow.nodes.map((node,index)=>`<div class="architecture-node">${status(node.status)}<strong>${escapeHtml(node.label)}</strong><span>${escapeHtml(node.source)}</span>${node.note?`<small>${escapeHtml(node.note)}</small>`:''}</div>${index<flow.nodes.length-1?'<span class="graph-link">→</span>':''}`).join('');return `<article class="panel architecture-flow"><div class="panel-heading"><div><h2>${escapeHtml(flow.label)}</h2><p>${escapeHtml(flow.id)}</p></div>${status(flow.status)}</div><div class="architecture-path">${nodes}</div></article>`}
async function loadOverview(){const data=await controlRoom();const overview=data.overview;$('environment-badge').textContent=overview.environment.toUpperCase();$('health-badge').textContent=overview.trust_state;$('health-badge').className=`status ${overview.trust_state}`;const kpis=[['Trust state',overview.trust_state],['Active runs',data.runs.active_count],['Pending approvals',data.plans.pending_approvals],['Evidence integrity',overview.receipt_integrity.valid&&overview.audit_integrity.valid?'PASS':'FAIL']];$('overview-kpis').innerHTML=kpis.map(([label,value])=>`<div class="kpi"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('');$('risk-overview').innerHTML=['R0','R1','R2','R3','R4'].map(risk=>`<p><strong>${risk}</strong> · ${escapeHtml(overview.risk[risk]||0)}</p>`).join('');$('integrity-overview').innerHTML=`<p>Receipts: ${status(overview.receipt_integrity.valid?'PASS':'FAIL')}</p><p>Audit: ${status(overview.audit_integrity.valid?'PASS':'FAIL')}</p><p>Emergency stop: ${status(overview.emergency_stop?'ACTIVE':'INACTIVE')}</p>`;$('orchestration-graph').innerHTML=data.architecture.flows.map(renderArchitectureFlow).join('')}
async function loadRuns(){const data=await controlRoom();$('runs-kpis').innerHTML=[['Queue',data.runs.queue_depth],['Active',data.runs.active_count],['Succeeded',data.runs.completed_count],['Failed',data.runs.failed_count]].map(([label,value])=>`<div class="kpi"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join('');$('runs-table').innerHTML=data.runs.recent.length?data.runs.recent.map(run=>`<tr><td>${status(run.status)}</td><td><strong>${escapeHtml(run.id)}</strong><br><span class="muted">${escapeHtml(run.title)}</span></td><td>${escapeHtml(run.title)}</td><td>${escapeHtml(run.risk)}</td><td>${escapeHtml(run.environment)}</td><td>${escapeHtml(run.adapter)}</td><td>${escapeHtml(run.receipt_id??'—')}</td><td><button class="secondary compact-button" type="button" data-passport-execution-id="${escapeHtml(run.id)}">Passport</button></td></tr>`).join(''):'<tr><td colspan="8" class="muted">Žádné běhy.</td></tr>'}
function passportFact(label,value,stateValue='OBSERVED'){return `<div class="fact"><span>${escapeHtml(label)}</span>${status(stateValue)}<strong>${escapeHtml(value??'—')}</strong></div>`}
function passportGroup(title,entries){return `<section class="passport-group"><h3>${escapeHtml(title)}</h3><div class="fact-grid">${entries.map(entry=>passportFact(entry[0],entry[1],entry[2]??'OBSERVED')).join('')}</div></section>`}
function passportTimelineEvent(label,timestamp,reference,stateValue='OBSERVED'){return `<article class="timeline-item"><div class="timeline-marker">${status(stateValue)}</div><div class="timeline-body"><header><strong>${escapeHtml(label)}</strong><span class="mono muted">${escapeHtml(reference||'NO_REFERENCE')}</span></header><time>${escapeHtml(timestamp||'TIME_NOT_AVAILABLE')}</time></div></article>`}
function passportEvidenceTimeline({snapshot,grant,consumption,outbox,runtime,verification}){const events=[];if(snapshot.authorized_at)events.push(passportTimelineEvent('Authorization snapshot',snapshot.authorized_at,snapshot.snapshot_digest));if(grant.issued_at)events.push(passportTimelineEvent('Execution grant issued',grant.issued_at,grant.grant_digest));if(consumption.consumed_at)events.push(passportTimelineEvent('Execution grant consumed',consumption.consumed_at,consumption.consumption_digest));if(outbox.created_at)events.push(passportTimelineEvent('Dispatch outbox recorded',outbox.created_at,outbox.entry_digest));if(runtime.completed_at||runtime.updated_at)events.push(passportTimelineEvent('Runtime state',runtime.completed_at||runtime.updated_at,runtime.completion_digest||runtime.execution_capsule_digest,runtime.status||'UNKNOWN'));if(verification.independent_verification_exposed)events.push(passportTimelineEvent('Independent verification',verification.checked_at,verification.result_digest,verification.verdict||'UNKNOWN'));else events.push(passportTimelineEvent('Independent verification',null,'NOT_PERSISTED','UNKNOWN'));return `<section class="passport-group"><h3>Canonical evidence timeline</h3><p class="muted">Derived only from validated Operation Passport facts. Missing evidence remains explicit.</p><div class="timeline passport-evidence-timeline">${events.join('')}</div></section>`}
function renderOperationPassport(data){const operation=data.operation||{};const authority=data.authority||{};const snapshot=authority.snapshot||{};const grant=authority.grant||{};const consumption=authority.consumption||{};const dispatch=data.dispatch||{};const outbox=dispatch.outbox||{};const inbox=dispatch.inbox||{};const runtime=data.runtime||{};const lease=runtime.current_lease||{};const verification=data.verification||{};const integrity=data.integrity||{};const verificationState=verification.verdict||'UNKNOWN';$('operation-passport-content').innerHTML=`<div class="passport-hero"><div><span class="mono muted">${escapeHtml(data.execution_id)}</span><h3>${escapeHtml(operation.capability||'Canonical operation')}</h3></div>${status(data.lifecycle_stage)}</div>${passportGroup('Intent & target',[['Request',operation.request_id],['Actor',operation.actor_id],['Workspace',operation.workspace_id],['Environment',operation.environment,String(operation.environment||'UNKNOWN').toUpperCase()],['Target kind',operation.target_kind],['Target digest',operation.target_digest],['Reviewed content SHA-256',operation.review_content_sha256]])}${passportGroup('Bounded authority',[['Snapshot',snapshot.snapshot_digest],['Policy version',snapshot.policy_version],['Authorized at',snapshot.authorized_at],['Approval valid until',snapshot.approval_valid_until],['Grant',grant.grant_digest||'NOT_ISSUED',grant.grant_digest?'OBSERVED':'UNKNOWN'],['Grant use',grant.use_semantics||'NOT_ISSUED',grant.use_semantics?'OBSERVED':'UNKNOWN'],['Grant expiry',grant.expires_at||'NOT_ISSUED',grant.expires_at?'OBSERVED':'UNKNOWN'],['Consumed at',consumption.consumed_at||'NOT_CONSUMED',consumption.consumed_at?'OBSERVED':'UNKNOWN']])}${passportGroup('Dispatch & runtime',[['Outbox',outbox.entry_digest||'NOT_ENQUEUED',outbox.entry_digest?'OBSERVED':'UNKNOWN'],['Inbox',inbox.admission_digest||'NOT_ADMITTED',inbox.admission_digest?'OBSERVED':'UNKNOWN'],['Runtime',runtime.status||'UNKNOWN',runtime.status||'UNKNOWN'],['Execution epoch',runtime.execution_epoch],['Runner class',runtime.runner_class],['Capsule digest',runtime.execution_capsule_digest],['Lease expiry',lease.expires_at||'NO_ACTIVE_LEASE',lease.expires_at?'OBSERVED':'UNKNOWN'],['Completed at',runtime.completed_at||'NOT_COMPLETED',runtime.completed_at?'OBSERVED':'UNKNOWN']])}<section class="passport-group verification-block"><div class="panel-heading"><div><h3>Independent verification</h3><p>${escapeHtml(verification.reason||'No verification explanation is available.')}</p></div>${status(verificationState)}</div><div class="fact-grid">${passportFact('Persistence status',verification.status||'UNKNOWN',verification.status||'UNKNOWN')}${passportFact('Verdict',verification.verdict||'UNKNOWN',verificationState)}${passportFact('Verification strength',verification.verification_strength_class||'NOT_AVAILABLE',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Checked at',verification.checked_at||'NOT_AVAILABLE',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Independent result exposed',verification.independent_verification_exposed?'YES':'NO',verification.independent_verification_exposed?'VERIFIED':'UNKNOWN')}${passportFact('Result digest',verification.result_digest||'NOT_AVAILABLE',verification.result_digest?'OBSERVED':'UNKNOWN')}</div></section>${passportEvidenceTimeline({snapshot,grant,consumption,outbox,runtime,verification})}${passportGroup('Integrity',[['Canonical JSON',integrity.canonical_json_validated?'VALIDATED':'UNKNOWN',integrity.canonical_json_validated?'VERIFIED':'UNKNOWN'],['Lineage bindings',integrity.lineage_bindings_validated?'VALIDATED':'UNKNOWN',integrity.lineage_bindings_validated?'VERIFIED':'UNKNOWN'],['Independent verification',integrity.independent_verification_validated?'VALIDATED':'NOT_VALIDATED',integrity.independent_verification_validated?'VERIFIED':'UNKNOWN']])}<details class="passport-raw"><summary>Raw canonical passport</summary><pre id="passport-raw-json"></pre></details>`;$('passport-raw-json').textContent=JSON.stringify(data,null,2)}
async function loadOperationPassport(executionId){const panel=$('operation-passport-panel');panel.classList.remove('hidden');$('operation-passport-content').innerHTML='<p class="muted">Načítám canonical Operation Passport…</p>';try{const data=await api(`/operations/${encodeURIComponent(executionId)}/passport`);renderOperationPassport(data)}catch(err){const missing=err.statusCode===404;const title=missing?'Canonical passport není pro tento execution dostupný.':'Canonical passport se nepodařilo bezpečně načíst.';const note=missing?'Runs obsahují i legacy execution záznamy. Absence canonical lineage se zobrazuje explicitně a není nahrazena domněnkou.':'Chyba čtení nebo konflikt canonical lineage se nesmí interpretovat jako prostá absence. Stav zůstává UNKNOWN, dokud není příčina ověřena.';$('operation-passport-content').innerHTML=`<article class="passport-unavailable"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(err.message)}</p><p class="muted">${escapeHtml(note)}</p></article>`}}
$('runs-table').addEventListener('click',event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-passport-execution-id]');if(!button)return;loadOperationPassport(button.dataset.passportExecutionId)})
$('close-passport-button').addEventListener('click',()=>$('operation-passport-panel').classList.add('hidden'))
async function loadPlans(){
  // Both lists are existing authorized GET APIs; an absent/mismatched row is NOT an execution permission.
  const [data,requests,runtime]=await Promise.all([
    controlRoom(),api('/change-requests'),api('/operations/status').catch(()=>null)
  ]);
  const byId=new Map(requests.map(item=>[item.id,item]));
  $('plans-table').innerHTML=data.plans.items.length?data.plans.items.map(plan=>{
    const request=byId.get(plan.request_id);
    const bound=request && request.status===plan.status && request.environment===plan.environment;
    let action='<span class="muted">UNKNOWN · obnovit</span>';
    if(bound && plan.status==='DRAFT'){
      action=`<button data-change-action="submit" data-request-id="${escapeHtml(plan.request_id)}">Submit</button>`;
    }else if(bound && plan.status==='APPROVED' && request.adapter==='github-read-ref'){
      const allowed=canonicalReadReady(runtime)&&['local','development','staging'].includes(plan.environment)
        && canonicalReadPayloadValid(request.payload);
      action=allowed?`<button data-change-action="canonical-read" data-request-id="${escapeHtml(plan.request_id)}">Canonical READ</button>`
        :'<span class="muted">READ DISABLED · runtime / scope</span>';
    }else if(bound && plan.status==='APPROVED' && plan.environment!=='production'
      && ['echo','write_artifact','run_validation'].includes(request.adapter)){
      action=`<button data-change-action="execute" data-request-id="${escapeHtml(plan.request_id)}">Execute (legacy)</button>`;
    }else if(bound){action='<span class="muted">—</span>'}
    return `<tr><td>${escapeHtml(plan.risk)}</td><td><strong>${escapeHtml(plan.title)}</strong><br><span class="mono muted">${escapeHtml(plan.request_id)}</span><br><small>${escapeHtml(request?.adapter||'UNKNOWN')}</small></td><td>${status(plan.status)}</td><td>${escapeHtml(plan.approval_count)} / ${escapeHtml(plan.approval_required)}</td><td>${escapeHtml(plan.environment)}</td><td class="actions">${action}</td></tr>`;
  }).join(''):'<tr><td colspan="6" class="muted">Žádné plány.</td></tr>';
  await loadApprovals();
}
async function loadRegistry(){const data=await controlRoom();$('registry-summary').innerHTML=[fact('Fail-closed default',String(data.capability_registry.fail_closed_default),data.capability_registry.fail_closed_default?'ENFORCED':'FAIL'),fact('Production effects',data.capability_registry.production_effects_enabled?'ENABLED':'DISABLED',data.capability_registry.production_effects_enabled?'ENABLED':'DISABLED')].join('');$('registry-cards').innerHTML=data.capability_registry.items.map(item=>`<article class="panel"><header class="panel-heading"><strong>${escapeHtml(item.id)}</strong>${status(item.runtime_status)}</header><p>${escapeHtml(item.surface)} · ${escapeHtml(item.effect)}</p><p class="muted">Verification: ${escapeHtml(item.verification)}</p></article>`).join('')}
async function loadTimeline(){const data=await controlRoom();$('timeline-list').innerHTML=data.evidence_timeline.length?data.evidence_timeline.map(item=>{const canonical=item.source==='OPERATION_PASSPORT';const drilldown=canonical&&item.execution_id?`<button class="secondary compact-button" type="button" data-evidence-passport-execution-id="${escapeHtml(item.execution_id)}">Passport</button>`:'';return `<article class="receipt-card"><header><strong>${escapeHtml(item.kind)} · ${escapeHtml(item.title)}</strong>${status(item.status)}</header><p>${escapeHtml(item.detail)}</p><p class="muted">${escapeHtml(item.source||'UNKNOWN_SOURCE')} · ${escapeHtml(item.timestamp)}</p>${drilldown}</article>`}).join(''):'<article class="panel muted">Žádná evidence.</article>'}
$('timeline-list').addEventListener('click',async event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-evidence-passport-execution-id]');if(!button)return;await loadView('runs');await loadOperationPassport(button.dataset.evidencePassportExecutionId)})
async function loadPolicy(){const data=await controlRoom();$('policy-gates').innerHTML=data.policy_gates.map(gate=>fact(gate.name,gate.source,gate.status)).join('')}
async function loadVerifier(){const data=await controlRoom();$('verifier-rule').textContent=data.verifier_center.separation_rule;$('verifier-list').innerHTML=data.verifier_center.recent_checks.length?data.verifier_center.recent_checks.map(check=>{const canonical=check.source==='VERIFICATION_RESULT_V1';const reference=canonical?check.result_digest:(check.receipt_id||check.execution_id);const provenance=canonical?`Strength ${escapeHtml(check.verification_strength||'UNKNOWN')} · checked ${escapeHtml(check.checked_at||'TIME_NOT_AVAILABLE')}`:'No durable independent VerificationResult/v1 is bound to this receipt.';return `<article class="receipt-card"><header><strong>${escapeHtml(canonical?'VerificationResult/v1':'Legacy receipt')} · ${escapeHtml(reference)}</strong>${status(check.verification_status)}</header><p>Execution ${escapeHtml(check.execution_id)} · ${escapeHtml(check.execution_status)}</p><p class="muted">${provenance}</p></article>`}).join(''):'<article class="panel muted">Independent verification zatím nemá runtime výsledek.</article>'}
async function loadRuntimeHealth(){const data=await controlRoom();$('health-summary').innerHTML=data.runtime_health.map(item=>fact(item.name,item.detail,item.status)).join('');$('health-json').textContent=JSON.stringify(data.runtime_health,null,2)}
async function loadLearning(){const data=await controlRoom();$('learning-signals').innerHTML=data.learning_intelligence.signals.map(item=>fact(item.name,item.value,item.status)).join('');$('learning-router').textContent=data.learning_intelligence.scoring_router}
async function loadProjectMap(){
  const banner=$('projectmap-status');
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
    banner.textContent=`Zdroj: snapshot ${data.observed_at_utc} · ${data.freshness} · FinishGate: ${data.active_delivery} (${data.focus_status}). SHA-256 ${data.snapshot_sha256}. Žádné schvalování ani změny.`;
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
    $('projectmap-relations').innerHTML=data.relationships.map(r=>
      `<li><strong>${escapeHtml(r.from)}</strong> → <strong>${escapeHtml(r.to)}</strong>
      <span class="muted">${escapeHtml(r.kind)} · ${escapeHtml(r.status)}</span></li>`).join('');
    $('projectmap-gaps').innerHTML=data.known_gaps.map(g=>`<li>${escapeHtml(g)}</li>`).join('');
  }catch(error){
    banner.textContent='UNAVAILABLE / UNVERIFIED — mapový snapshot není nakonfigurován, je neplatný nebo se nepodařilo načtení. Žádné údaje nebyly považovány za aktuální.';
    $('projectmap-projects').textContent='';
    $('projectmap-relations').textContent='';
    $('projectmap-gaps').textContent='';
  }
}
async function loadGovernance(){const data=await controlRoom();$('governance-grid').innerHTML=Object.entries(data.governance).map(([key,value])=>fact(key.replaceAll('_',' '),Array.isArray(value)?value.join(', ')||'NONE':String(value),typeof value==='boolean'?(value?'ENABLED':'DISABLED'):'OBSERVED')).join('')}
async function loadCommand(){const data=await api('/command-center');$('environment-badge').textContent=data.environment.toUpperCase();$('health-badge').textContent=data.trust_state;$('health-badge').className=`status ${data.trust_state}`;const kpis=[['Trust state',data.trust_state],['Active executions',data.executions.RUNNING||0],['Pending approvals',data.pending_approvals],['Production effects',data.production_effects_enabled?'ENABLED':'DISABLED']];$('command-kpis').innerHTML=kpis.map(x=>`<div class="kpi"><span>${escapeHtml(x[0])}</span><strong>${escapeHtml(x[1])}</strong></div>`).join('');$('risk-overview').innerHTML=['R0','R1','R2','R3','R4'].map(r=>`<p><strong>${r}</strong> · ${escapeHtml(data.risk[r]||0)}</p>`).join('');$('integrity-overview').innerHTML=`<p>Receipts: ${status(data.receipt_integrity.valid?'PASS':'FAIL')}</p><p>Audit: ${status(data.audit_integrity.valid?'PASS':'FAIL')}</p><p>Emergency stop: ${status(data.emergency_stop?'ACTIVE':'INACTIVE')}</p>`;const evidenceState=data.receipt_integrity.valid&&data.audit_integrity.valid?'PASS':'FAIL';const policyFacts=[fact('Environment',String(data.environment||'UNKNOWN').toUpperCase(),String(data.environment||'UNKNOWN').toUpperCase()),fact('Production effects',data.production_effects_enabled?'ENABLED':'DISABLED',data.production_effects_enabled?'ENABLED':'DISABLED'),fact('Emergency stop',data.emergency_stop?'ACTIVE':'INACTIVE',data.emergency_stop?'ACTIVE':'INACTIVE'),fact('Evidence integrity',evidenceState,evidenceState),fact('Approval policy metadata','NOT EXPOSED','UNKNOWN'),fact('Execution-plane isolation','NOT EXPOSED','UNKNOWN')];$('policy-overview').innerHTML=policyFacts.join('');$('policy-summary-status').textContent=data.trust_state;$('policy-summary-status').className=`status ${data.trust_state}`}
$('new-change-button').addEventListener('click',()=>$('change-form-panel').classList.remove('hidden'))
$('cancel-change-button').addEventListener('click',()=>$('change-form-panel').classList.add('hidden'))
$('change-workspace').addEventListener('change',syncChangeEnvironment)
$('change-adapter').addEventListener('change',syncChangeAdapter)
$('change-form').addEventListener('submit',async e=>{
  e.preventDefault();
  try{
    const adapter=$('change-adapter').value;
    const payload=JSON.parse($('change-payload').value||'{}');
    if(adapter==='github-read-ref'){
      if(!['local','development','staging'].includes($('change-environment').value)
        ||!canonicalReadPayloadValid(payload))
        throw new Error('GitHub READ vyžaduje neprodukční workspace a přesný repository/ref.');
    }
    await api('/change-requests',{method:'POST',body:JSON.stringify({
      workspace_id:$('change-workspace').value,title:$('change-title').value,
      description:$('change-description').value,risk:$('change-risk').value,
      environment:$('change-environment').value,adapter,payload
    })});
    $('change-form-panel').classList.add('hidden');
    toast('Change request vytvořen · schválení je stále samostatné');
    await loadPlans();
  }catch(err){toast(err.message,true)}
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
async function loadApprovals(){const rows=await api('/approvals?pending_only=true');$('approvals-list').innerHTML=rows.length?rows.map(r=>{const approved=Number(r.approved_count||0);const required=Number(r.required_count||0);const remaining=Math.max(required-approved,0);return `<article class="approval-card"><header><div><strong>${escapeHtml(r.title)}</strong><div class="mono muted">${escapeHtml(r.request_id)}</div></div>${status(r.risk)}</header><div class="approval-progress"><div><span>Approved</span><strong>${escapeHtml(approved)} / ${escapeHtml(required)}</strong></div><div><span>Remaining</span><strong>${escapeHtml(remaining)}</strong></div><div><span>Environment</span><strong>${escapeHtml(String(r.environment||'UNKNOWN').toUpperCase())}</strong></div></div><p class="muted">The API exposes the effective threshold for this request. Policy version and requester identity are not yet exposed.</p><div class="actions"><button data-decision="APPROVED" data-request-id="${escapeHtml(r.request_id)}">Approve once</button><button class="danger" data-decision="DENIED" data-request-id="${escapeHtml(r.request_id)}">Deny</button></div></article>`}).join(''):'<article class="panel">Žádná čekající schválení.</article>'}
$('approvals-list').addEventListener('click',async event=>{if(!(event.target instanceof Element))return;const button=event.target.closest('button[data-decision]');if(!button)return;const reason=prompt('Důvod rozhodnutí:');if(!reason)return;try{await api(`/change-requests/${button.dataset.requestId}/decision`,{method:'POST',body:JSON.stringify({decision:button.dataset.decision,reason})});toast(`Rozhodnutí ${button.dataset.decision}`);await loadPlans()}catch(err){toast(err.message,true)}})
async function setStop(active){const reason=$('stop-reason').value.trim();if(reason.length<3){toast('Vyplň důvod',true);return}try{await api('/system/emergency-stop',{method:'POST',body:JSON.stringify({active,reason})});toast(active?'Emergency stop aktivován':'Emergency stop zrušen');await loadHealth()}catch(err){toast(err.message,true)}}
$('activate-stop').addEventListener('click',()=>setStop(true));$('clear-stop').addEventListener('click',()=>setStop(false));showApp();
