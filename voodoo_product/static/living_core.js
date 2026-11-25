'use strict';

(function installLivingCore(){
  const nativeControlRoom=window.controlRoom;
  if(typeof nativeControlRoom!=='function')return;
  let lastProjection=null;

  const $=id=>document.getElementById(id);
  const html=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const list=value=>Array.isArray(value)?value:[];
  const count=value=>Number.isSafeInteger(value)&&value>=0?String(value):'Nedostupné';
  const currentView=()=>document.getElementById('view-overview')?.classList.contains('active');

  function stateName(value){
    const candidate=String(value??'UNKNOWN').toUpperCase();
    return /^[A-Z][A-Z0-9_]{0,31}$/.test(candidate)?candidate:'UNKNOWN';
  }

  function setStage(name,state,detail,source){
    const node=document.querySelector('.lc-stage[data-stage="'+name+'"]');
    if(!node)return;
    const badge=node.querySelector('.lc-stage-state');
    if(badge){const safe=stateName(state);badge.textContent=safe;badge.className='lc-stage-state status '+safe}
    const body=node.querySelector('.lc-stage-detail');
    if(body)body.textContent=String(detail??'Nedostupné');
    const origin=node.querySelector('.lc-stage-source');
    if(origin)origin.textContent=String(source??'API projekce');
    node.dataset.state=stateName(state);
  }

  function card(label,value,state){
    const safe=stateName(state??value);
    return '<div class="lc-metric"><span>'+html(label)+'</span><strong>'+html(value)+'</strong><small class="status '+safe+'">'+html(safe)+'</small></div>';
  }

  // Operator focus is a *summary of independent records*, not one execution passport.
  // A route never grants authority: all consequential actions remain in their native views.
  function setFocus(state,title,summary,source,route,label){
    const badge=$('lc-focus-state');
    if(badge){const safe=stateName(state);badge.textContent=safe;badge.className='status '+safe}
    const heading=$('lc-focus-title');
    if(heading)heading.textContent=String(title);
    const detail=$('lc-focus-summary');
    if(detail)detail.textContent=String(summary);
    const origin=$('lc-focus-source');
    if(origin)origin.textContent=String(source);
    const action=$('lc-focus-open');
    if(action){
      action.dataset.refresh=route||'';
      action.disabled=!route;
      action.setAttribute('aria-disabled',route?'false':'true');
      action.textContent=label||'Otevřít související modul';
    }
  }

  function renderFocus(plans,runs,checks){
    const pending=Number.isSafeInteger(plans.pending_approvals)&&plans.pending_approvals>=0?plans.pending_approvals:null;
    const active=Number.isSafeInteger(runs.active_count)&&runs.active_count>=0?runs.active_count:null;
    const failures=Number.isSafeInteger(runs.failed_count)&&runs.failed_count>=0?runs.failed_count:null;
    const latest=list(checks)[0];
    const verdict=latest?stateName(latest.verification_status):'UNKNOWN';
    if(pending!==null&&pending>0){
      setFocus('REVIEW_REQUIRED','Rozhodnutí čekají na člověka',
        pending+' čekajících schválení v aktuální projekci. Oprávnění a platnost musí ověřit server.',
        'Zdroj: Plans / pending_approvals','plans','Otevřít Approvals');
    }else if(active!==null&&active>0){
      setFocus('RUNNING','Probíhá vykonávání',
        active+' aktivních běhů. Stav není důkazem úspěchu ani nezávislého ověření.',
        'Zdroj: Runs / active_count','runs','Otevřít Runs');
    }else if(failures!==null&&failures>0){
      setFocus('FAILED','V historii jsou neúspěšné běhy',
        failures+' neúspěšných běhů podle souhrnné projekce. Je potřeba otevřít detail.',
        'Zdroj: Runs / failed_count','runs','Prověřit Runs');
    }else if(['FAILED','DENIED','REJECTED','INCONCLUSIVE'].includes(verdict)){
      setFocus(verdict,'Poslední kontrola vyžaduje pozornost',
        'Zobrazený verdict patří pouze poslednímu zaznamenanému verifier checku.',
        'Zdroj: Verifier Center / recent_checks','verifier','Otevřít Verifier');
    }else if(pending===0&&active===0){
      setFocus('NO_PENDING','V přehledu není aktivní požadavek',
        'Projekce hlásí 0 čekajících schválení a 0 aktivních běhů. To není potvrzení globálního zdraví systému.',
        'Zdroj: Plans + Runs / agregované počty','plans','Prohlédnout Plans');
    }else{
      setFocus('UNKNOWN','Nelze určit aktuální fokus',
        'Control Room nevystavil úplné počty potřebné pro bezpečné určení priority.',
        'Zdroj: Control Room / neúplná projekce',null,null);
    }
  }

  function renderProjection(data){
    if(!data||typeof data!=='object')return;
    const overview=data.overview&&typeof data.overview==='object'?data.overview:{};
    const plans=data.plans&&typeof data.plans==='object'?data.plans:{};
    const runs=data.runs&&typeof data.runs==='object'?data.runs:{};
    const verifier=data.verifier_center&&typeof data.verifier_center==='object'?data.verifier_center:{};
    const planItems=list(plans.items);
    const runItems=list(runs.recent);
    const checks=list(verifier.recent_checks);
    const evidence=list(data.evidence_timeline);

    const latestIntent=evidence.find(item=>/INTENT|REQUEST_CREATED/i.test(String(item.kind||'')));
    setStage('intent',latestIntent?stateName(latestIntent.status||'OBSERVED'):'UNKNOWN',
      latestIntent?((latestIntent.title||latestIntent.kind||'Záměr zachycen')+' · '+stateName(latestIntent.status||'OBSERVED')):'Nedostupné · samostatná událost záměru v projekci chybí',
      'Evidence Timeline');
    const pending=Number.isSafeInteger(plans.pending_approvals)?plans.pending_approvals:null;
    setStage('approval',pending===null?'UNKNOWN':pending?'REVIEW_REQUIRED':'NO_PENDING',
      pending===null?'Nedostupné':pending+' čekajících',
      'Plans');

    setStage('jit','UNKNOWN','Nedostupné · API tento stav nevystavuje',
      'API');

    const active=Number.isSafeInteger(runs.active_count)?runs.active_count:null;
    setStage('execution',active===null?'UNKNOWN':active?'RUNNING':'IDLE',
      active===null?'Nedostupné':active+' běžících · '+count(runs.queue_depth)+' ve frontě · '+count(runs.completed_count)+' dokončených · '+count(runs.failed_count)+' selhalo',
      'Runs');

    const latestCheck=checks[0];
    setStage('verification',latestCheck?stateName(latestCheck.verification_status):'UNKNOWN',
      latestCheck?('Execution '+(latestCheck.execution_id||'Nedostupné')+' · '+stateName(latestCheck.verification_status)):'Nedostupné · verifier zatím nemá záznam',
      latestCheck?'Verifier Center':'Verifier Center');
    const latestEvidence=evidence[0];
    setStage('evidence',latestEvidence?stateName(latestEvidence.status):'UNKNOWN',
      latestEvidence?((latestEvidence.kind||'Záznam')+' · '+stateName(latestEvidence.status)):'Nedostupné · timeline je prázdná',
      'Evidence Timeline');

    const observed=$('lc-observed-at');
    if(observed)observed.textContent='Projekce načtena · '+new Date().toLocaleTimeString();

    const activeRun=runItems.find(item=>['RUNNING','ACTIVE'].includes(item.status));
    const latestRun=activeRun||runItems[0];
    const delivery=$('lc-delivery-content');
    if(delivery)delivery.innerHTML=latestRun
      ?'<div class="lc-record"><strong>'+html(activeRun?'Aktivní běh · '+(latestRun.title||latestRun.id||'Execution'):'Poslední běh · '+(latestRun.title||latestRun.id||'Execution'))+'</strong><span class="status '+stateName(latestRun.status)+'">'+html(stateName(latestRun.status))+'</span><small>'+html(latestRun.id||'ID nedostupné')+' · '+html(latestRun.environment||'environment nedostupné')+' · '+html(latestRun.adapter||'adapter nedostupný')+'</small></div><div class="lc-count-row"><span>Aktivní</span><strong>'+html(count(runs.active_count))+'</strong><span>Fronta</span><strong>'+html(count(runs.queue_depth))+'</strong></div>'
      :'<p class="lc-empty">V aktuální projekci není žádný execution běh.</p>';

    const approvals=$('lc-approvals-content');
    if(approvals){
      const waiting=planItems.filter(item=>item.status==='REVIEW_REQUIRED').slice(0,3);
      approvals.innerHTML='<div class="lc-count-row"><span>Čekající rozhodnutí</span><strong>'+html(count(plans.pending_approvals))+'</strong></div>'+
        (waiting.length?waiting.map(item=>'<div class="lc-record"><strong>'+html(item.title||item.request_id||'Požadavek')+'</strong><span class="status REVIEW_REQUIRED">REVIEW_REQUIRED</span><small>'+html(item.risk||'Riziko nedostupné')+' · '+html(item.environment||'environment nedostupné')+' · '+html(item.request_id||'ID nedostupné')+'</small></div>').join(''):'<p class="lc-empty">V aktuální projekci není zobrazen žádný čekající požadavek.</p>');
    }

    const verification=$('lc-verification-content');
    if(verification)verification.innerHTML=checks.length?checks.slice(0,3).map(item=>'<div class="lc-record"><strong>'+html(item.source==='VERIFICATION_RESULT_V1'?'VerificationResult/v1':'Kontrola')+' · '+html(item.execution_id||'Execution nedostupné')+'</strong><span class="status '+stateName(item.verification_status)+'">'+html(stateName(item.verification_status))+'</span><small>'+html(item.verification_strength||'Síla ověření nedostupná')+' · '+html(item.checked_at||'Čas nedostupný')+'</small></div>').join(''):'<p class="lc-empty">Nedostupné · verifier zatím nevystavil výsledek.</p>';

    const eventList=$('lc-evidence-content');
    if(eventList)eventList.innerHTML=evidence.length?evidence.slice(0,4).map(item=>'<div class="lc-event"><span class="status '+stateName(item.status)+'">'+html(stateName(item.status))+'</span><div><strong>'+html(item.kind||'Záznam')+' · '+html(item.title||'Bez názvu')+'</strong><small>'+html(item.source||'Zdroj nedostupný')+' · '+html(item.timestamp||'Čas nedostupný')+'</small></div></div>').join(''):'<p class="lc-empty">Nedostupné · timeline neobsahuje záznamy.</p>';

    renderFocus(plans,runs,checks);

    const metrics=$('lc-metrics-content');
    if(metrics){
      const integrity=overview.receipt_integrity?.valid===true&&overview.audit_integrity?.valid===true?'PASS':
        overview.receipt_integrity?.valid===false||overview.audit_integrity?.valid===false?'FAIL':'UNKNOWN';
      metrics.innerHTML=[
        card('Trust state',overview.trust_state||'Nedostupné',overview.trust_state||'UNKNOWN'),
        card('Agents','Nedostupné','UNKNOWN'),
        card('Latency','Nedostupné','UNKNOWN'),
        card('Throughput','Nedostupné','UNKNOWN'),
        card('Evidence integrity',integrity,integrity),
        card('Success rate','Nedostupné','UNKNOWN')
      ].join('');
    }
  }

  function renderUnavailable(){
    setFocus('UNKNOWN','Projekce nedostupná','Nepodařilo se ověřit aktuální stav. Dříve zobrazená priorita není platná.','Zdroj: Control Room / chyba',null,null);
    setStage('intent','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('approval','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('jit','UNKNOWN','Nedostupné · JIT není vystaven v přehledu','API');
    setStage('execution','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('verification','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('evidence','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    for(const id of ['lc-delivery-content','lc-approvals-content','lc-verification-content','lc-evidence-content','lc-metrics-content']){
      const target=$(id);if(target)target.textContent='Nedostupné · nepodařilo se načíst ověřenou projekci.';
    }
    const health=$('health-badge');
    if(health){health.textContent='UNKNOWN';health.className='status UNKNOWN'}
    const environment=$('environment-badge');
    if(environment)environment.textContent='Nedostupné';
    const kpis=$('overview-kpis');
    if(kpis)kpis.innerHTML=[
      ['Trust state','Nedostupné'],['Active runs','Nedostupné'],
      ['Pending approvals','Nedostupné'],['Evidence integrity','UNKNOWN']
    ].map(([label,value])=>'<div class="kpi"><span>'+label+'</span><strong>'+value+'</strong></div>').join('');
    const observed=$('lc-observed-at');if(observed)observed.textContent='Projekce nedostupná';
  }

  const casebookForm=$('lc-casebook-form');
  if(casebookForm)casebookForm.addEventListener('submit',async event=>{
    event.preventDefault();
    const sessionId=String($('lc-casebook-id')?.value||'').trim();
    const hint=$('lc-casebook-hint');
    if(!/^[A-Za-z0-9_-]{5,128}$/.test(sessionId)){
      if(hint)hint.textContent='Neplatné ID relace. Nebyl proveden žádný požadavek.';
      return;
    }
    if(typeof window.loadView!=='function'||typeof window.loadCasebookTask!=='function'){
      if(hint)hint.textContent='CASEBOOK pohled není dostupný; nebyl proveden žádný požadavek.';
      return;
    }
    // Reuse the native scoped CASEBOOK reader and its validation, authorization and truth rules.
    await window.loadView('casebook');
    const target=$('casebook-session-id');
    if(!target){if(hint)hint.textContent='CASEBOOK formulář není dostupný.';return}
    target.value=sessionId;
    if(typeof target.focus==='function')target.focus();
    await window.loadCasebookTask(sessionId);
  });
  const logout=$('logout-button');
  if(logout)logout.addEventListener('click',()=>{
    const field=$('lc-casebook-id');
    if(field)field.value='';
    const hint=$('lc-casebook-hint');
    if(hint)hint.textContent='Pouze autentizované čtení; bez spuštění operace nebo zápisu.';
  });

  window.voodooLivingCore=Object.freeze({renderProjection,renderUnavailable});
  window.controlRoom=async function(){
    try{
      const data=await nativeControlRoom();
      lastProjection=data;
      if(currentView())renderProjection(data);
      return data;
    }catch(error){
      if(currentView())renderUnavailable();
      throw error;
    }
  };

  const nativeLoadOverview=window.loadOverview;
  if(typeof nativeLoadOverview==='function'){
    window.loadOverview=async function(...args){
      const result=await nativeLoadOverview.apply(this,args);
      if(currentView()&&lastProjection)renderProjection(lastProjection);
      return result;
    };
  }
})();