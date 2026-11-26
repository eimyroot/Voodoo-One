'use strict';

(function installLivingCore(){

  const $=id=>document.getElementById(id);
  const html=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const list=value=>Array.isArray(value)?value.filter(item=>item&&typeof item==='object'&&!Array.isArray(item)):[];
  const nonnegative=value=>Number.isSafeInteger(value)&&value>=0?value:null;
  const count=value=>nonnegative(value)===null?'Nedostupné':String(value);
  const integrityState=value=>value?.valid===true?'PASS':value?.valid===false?'FAIL':'UNKNOWN';
  const combinedIntegrity=overview=>{
    const a=integrityState(overview.receipt_integrity),b=integrityState(overview.audit_integrity);
    return a==='FAIL'||b==='FAIL'?'FAIL':a==='PASS'&&b==='PASS'?'PASS':'UNKNOWN';
  };
  const stopState=value=>value===true?'ACTIVE':value===false?'INACTIVE':'UNKNOWN';
  const trustState=overview=>['HEALTHY','INCIDENT'].includes(overview.trust_state)?overview.trust_state:'UNKNOWN';

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

  function renderFocus(overview,plans,runs,checks){
    const pending=nonnegative(plans.pending_approvals);
    const active=nonnegative(runs.active_count);
    const queued=nonnegative(runs.queue_depth);
    const failures=nonnegative(runs.failed_count);
    // Only actual canonical verdicts can drive a verification-specific priority.
    const latest=list(checks).find(item=>item.source==='VERIFICATION_RESULT_V1');
    const verdict=latest?stateName(latest.verification_status):'UNKNOWN';
    const integrity=combinedIntegrity(overview);
    if(overview.emergency_stop===true){
      setFocus('BLOCKED','Nouzové zastavení je aktivní',
        'Nejdříve prověř stav systému. Přehled nic nespouští ani nemění oprávnění.',
        'Zdroj: Control Room / emergency_stop','health','Otevřít Stav systému');
    }else if(integrity==='FAIL'){
      setFocus('BLOCKED','Integrita evidence vyžaduje kontrolu',
        'Audit nebo receipt ledger hlásí neplatnou integritu. Nejde o ověření výsledku operace.',
        'Zdroj: Control Room / receipt_integrity + audit_integrity','evidence','Prověřit důkazy');
    }else if(trustState(overview)==='INCIDENT'){
      setFocus('BLOCKED','Systém hlásí incident',
        'Nejdříve prověř aktuální provozní stav.',
        'Zdroj: Control Room / trust_state','health','Otevřít Stav systému');
    }else if(trustState(overview)!=='HEALTHY'||integrity!=='PASS'||overview.emergency_stop!==false){
      setFocus('UNKNOWN','Bezpečnostní stav není úplný',
        'Chybí potvrzení provozního stavu, integrity nebo nouzového zastavení. Prioritu nelze bezpečně určit.',
        'Zdroj: Control Room / neúplná projekce','health','Prověřit Stav systému');
    }else if(pending!==null&&pending>0){
      setFocus('REVIEW_REQUIRED','Rozhodnutí čekají na člověka',
        pending+' čekajících schválení v aktuální projekci. Oprávnění a platnost musí ověřit server.',
        'Zdroj: Plans / pending_approvals','plans','Otevřít požadavky');
    }else if(pending===null){
      setFocus('UNKNOWN','Schvalovací fronta není ověřena',
        'Chybí platný počet čekajících schválení. Nelze bezpečně vybrat další prioritu.',
        'Zdroj: Plans / neúplná projekce',null,null);
    }else if(active!==null&&active>0){
      setFocus('RUNNING','Probíhá vykonávání',
        active+' aktivních běhů v načteném výřezu. Stav není důkazem úspěchu ani nezávislého ověření.',
        'Zdroj: Runs / active_count','runs','Otevřít běhy');
    }else if(active===null){
      setFocus('UNKNOWN','Stav aktivních běhů není ověřen',
        'Chybí platný počet aktivních běhů.',
        'Zdroj: Runs / neúplná projekce',null,null);
    }else if(['FAILED','DENIED','REJECTED','INCONCLUSIVE'].includes(verdict)){
      setFocus(verdict,'Poslední kanonická kontrola vyžaduje pozornost',
        'Verdikt patří poslednímu kanonickému výsledku v načteném výřezu, nikoli všem běhům.',
        'Zdroj: Verifier Center / recent_checks','verifier','Otevřít ověření');
    }else if(queued!==null&&queued>0){
      setFocus('REVIEW_REQUIRED','Požadavky čekají na zpracování',
        queued+' rozpracovaných nebo k posouzení v načteném výřezu. Nejde o povolení ke spuštění.',
        'Zdroj: Runs / queue_depth','plans','Otevřít požadavky');
    }else if(failures!==null&&failures>0){
      setFocus('FAILED','V historii jsou neúspěšné běhy',
        failures+' neúspěšných běhů v načteném výřezu. Nejde o potvrzení aktuálního blockeru.',
        'Zdroj: Runs / failed_count','runs','Prověřit běhy');
    }else if(pending===0&&active===0&&queued===0&&failures===0&&Array.isArray(checks)){
      setFocus('NO_PENDING','V načteném výřezu není aktivní práce',
        'Projekce hlásí 0 čekajících schválení, aktivních běhů a požadavků ve frontě. Kontext úkolů zůstává v Deníku.',
        'Zdroj: Plans + Runs / omezený výřez','casebook','Otevřít Deník');
    }else{
      setFocus('UNKNOWN','Nelze určit aktuální fokus',
        'Control Room nevystavil úplné počty potřebné pro bezpečné určení priority.',
        'Zdroj: Control Room / neúplná projekce',null,null);
    }
  }

  function renderSystemSummary(overview,plans,runs,verifier){
    const trust=trustState(overview),integrity=combinedIntegrity(overview);
    const header=$('health-badge');
    if(header){header.textContent=trust;header.className='status '+trust}
    const environment=$('environment-badge');
    if(environment)environment.textContent=typeof overview.environment==='string'&&overview.environment
      ?overview.environment.toUpperCase():'Nedostupné';
    const kpis=$('overview-kpis');
    if(kpis)kpis.innerHTML=[
      ['Provozní stav',trust],['Aktivní běhy (výřez)',count(runs.active_count)],
      ['Čekající schválení',count(plans.pending_approvals)],['Integrita evidence',integrity]
    ].map(([label,value])=>'<div class="kpi"><span>'+html(label)+'</span><strong>'+html(value)+'</strong></div>').join('');
    const risk=$('risk-overview');
    if(risk)risk.innerHTML=['R0','R1','R2','R3','R4'].map(name=>
      '<p><strong>'+name+'</strong> · '+html(overview.risk&&typeof overview.risk==='object'
        ?count(Object.hasOwn(overview.risk,name)?overview.risk[name]:0):'Nedostupné')+'</p>').join('');
    const detail=$('integrity-overview');
    if(detail)detail.innerHTML=[
      ['Receipts',integrityState(overview.receipt_integrity)],
      ['Audit',integrityState(overview.audit_integrity)],
      ['Emergency stop',stopState(overview.emergency_stop)]
    ].map(([label,value])=>'<p>'+html(label)+': <span class="status '+value+'">'+value+'</span></p>').join('');
    const metrics=$('lc-metrics-content');
    if(metrics){
      const stop=stopState(overview.emergency_stop);
      const canonical=nonnegative(verifier.canonical_result_count);
      metrics.innerHTML=[
        card('Nouzové zastavení',stop,stop),
        card('Integrita evidence',integrity,integrity),
        card('Kanonické výsledky (výřez)',canonical===null?'Nedostupné':String(canonical),canonical===null?'UNKNOWN':'OBSERVED')
      ].join('');
    }
  }

  function renderProjection(data){
    if(!data||typeof data!=='object'||Array.isArray(data))throw new Error('Neplatná projekce Přehledu.');
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
    const pending=nonnegative(plans.pending_approvals);
    setStage('approval',pending===null?'UNKNOWN':pending?'REVIEW_REQUIRED':'NO_PENDING',
      pending===null?'Nedostupné':pending+' čekajících',
      'Plans');

    setStage('jit','UNKNOWN','Nedostupné · API tento stav nevystavuje',
      'API');

    const active=nonnegative(runs.active_count);
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
       :'<p class="lc-empty">'+(Array.isArray(runs.recent)?'V načteném výřezu není žádný běh.':'Nedostupné · seznam běhů chybí.')+'</p>';

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

    renderFocus(overview,plans,runs,verifier.recent_checks);

    renderSystemSummary(overview,plans,runs,verifier);
    const graph=$('orchestration-graph');
    if(graph)graph.innerHTML=typeof window.renderArchitectureFlow==='function'
      ?list(data.architecture?.flows).filter(flow=>Array.isArray(flow.nodes)).map(window.renderArchitectureFlow).join('')
      :'';

  }

  function renderUnavailable({loading=false,clearHeader=true}={}){
    setFocus('UNKNOWN',loading?'Načítám aktuální stav':'Projekce nedostupná',
      loading?'Čekám na novou autorizovanou projekci.':'Aktuální stav nebyl ověřen. Dříve zobrazená priorita není platná.',
      'Zdroj: Control Room / '+(loading?'načítání':'nedoručeno'),null,null);
    setStage('intent','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('approval','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('jit','UNKNOWN','Nedostupné · JIT není vystaven v přehledu','API');
    setStage('execution','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('verification','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    setStage('evidence','UNKNOWN','Nedostupné · Control Room projekce se nepodařila načíst','API');
    for(const id of ['lc-delivery-content','lc-approvals-content','lc-verification-content','lc-evidence-content','lc-metrics-content','risk-overview','integrity-overview','orchestration-graph']){
      const target=$(id);if(target)target.textContent=loading?'Načítám aktuální projekci…':'Nedostupné · aktuální projekce nebyla ověřena.';
    }
    const health=$('health-badge');
    if(clearHeader&&health){health.textContent='UNKNOWN';health.className='status UNKNOWN'}
    const environment=$('environment-badge');
    if(clearHeader&&environment)environment.textContent='Nedostupné';
    const kpis=$('overview-kpis');
    if(kpis)kpis.innerHTML=[
      ['Provozní stav','Nedostupné'],['Aktivní běhy (výřez)','Nedostupné'],
      ['Čekající schválení','Nedostupné'],['Integrita evidence','UNKNOWN']
    ].map(([label,value])=>'<div class="kpi"><span>'+label+'</span><strong>'+value+'</strong></div>').join('');
    const observed=$('lc-observed-at');if(observed)observed.textContent=loading?'Načítám aktuální projekci…':'Projekce nedostupná';
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
    if(!(await window.loadView('casebook')))return;
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
})();
