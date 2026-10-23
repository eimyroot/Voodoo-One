/* Read-only UX projections over the existing authenticated VOODOO One API.
 * Visual topology is an explicitly marked design model, never runtime evidence.
 */
const boardSafe = value => escapeHtml(value ?? 'UNKNOWN');
const boardArray = value => Array.isArray(value) ? value : [];
const boardNumber = value => Number.isFinite(value) ? value : 'UNKNOWN';
const boardBoolean = (value, whenTrue, whenFalse) => value === true ? whenTrue : value === false ? whenFalse : 'UNKNOWN';
const boardTruth = value => status(String(value ?? 'UNKNOWN').toUpperCase());
const boardBadge = (text, kind = 'info') =>
  '<span class="wb-chip wb-' + kind + '">' + boardSafe(text) + '</span>';
const boardTile = (title, caption, symbol = '◇', kind = '') =>
  '<article class="wb-node ' + kind + '"><span class="wb-symbol" aria-hidden="true">' +
  boardSafe(symbol) + '</span><div><h3>' + boardSafe(title) +
  '</h3><p>' + boardSafe(caption) + '</p></div></article>';
const boardEmpty = (message, detail = '') =>
  '<div class="wb-empty"><strong>' + boardSafe(message) + '</strong><p>' +
  boardSafe(detail) + '</p></div>';
const boardStats = items =>
  '<div class="wb-stats">' + items.map(([label, value, hint]) =>
  '<div class="wb-stat"><span>' + boardSafe(label) + '</span><strong>' +
  boardSafe(value) + '</strong><small>' + boardSafe(hint || '') + '</small></div>').join('') + '</div>';
const boardModelSections = new Set(["VOODOO Workflow","Task lifecycle · referenční model","Rozhodovací hranice","Trust boundaries","Hard stop","Evidence lineage · referenční proces","Shared workflow","Referenční projekty"]);
const boardLiveSections = new Set(["Skutečné architektonické projekce","Aktuální běhy","Runtime policy gates","Safety kernel","Evidence timeline","Independent verification","Připojené workspaces"]);
const boardPanel = (title, subtitle, content, extra = '') => {
  const kind = boardModelSections.has(title) ? 'model' : boardLiveSections.has(title) ? 'live' : '';
  const provenance = kind === 'model'
    ? '<p class="wb-provenance wb-provenance-model">REFERENČNÍ MODEL · NEJDE O RUNTIME STAV</p>'
    : kind === 'live'
      ? '<p class="wb-provenance wb-provenance-live">DATA Z AUTORIZOVANÉHO API</p>' : '';
  return '<section class="wb-panel ' + extra + (kind ? ' wb-panel-' + kind : '') + '">' +
    provenance + '<header><div><h2>' + boardSafe(title) +
    '</h2><p>' + boardSafe(subtitle) + '</p></div></header>' + content + '</section>';
};
const boardHead = (title, intro, source, connection = 'LIVE') =>
  '<div class="wb-head"><div><p class="wb-eyebrow">VOODOO · WORKFLOW INTELLIGENCE / READ-ONLY</p>' +
  '<h1>' + boardSafe(title) + '</h1><p>' + boardSafe(intro) + '</p></div><div class="wb-head-meta">' +
  boardBadge(connection === 'LIVE' ? 'LIVE API DATA' : connection === 'LOADING' ? 'LOADING' : 'API UNAVAILABLE', connection === 'LIVE' ? 'good' : connection === 'LOADING' ? 'warn' : 'danger') + boardBadge('DESIGN MODEL ≠ RUNTIME', 'warn') +
  '<small>Zdroj: ' + boardSafe(source) + '</small></div></div>';
const boardStep = (index, title, detail) =>
  '<div class="wb-step"><span class="wb-step-number">' +
  String(index).padStart(2, '0') + '</span><h3>' + boardSafe(title) +
  '</h3><p>' + boardSafe(detail) + '</p></div>';
const boardNotice = text => '<p class="wb-notice">ⓘ ' + boardSafe(text) + '</p>';

async function boardLoad(view, build) {
  const root = document.getElementById('view-' + view);
  if (!root) return;
  root.innerHTML = boardHead('Načítám údaje', 'Pouze autorizované read-only API.', '/api/v1/control-room', 'LOADING');
  try {
    const data = await controlRoom();
    root.innerHTML = build(data);
  } catch (error) {
    root.innerHTML = boardHead('Data nejsou dostupná', 'Bez ověřeného API nezobrazujeme domnělé výsledky.', '/api/v1/control-room', 'UNAVAILABLE') +
      boardPanel('Stav připojení', 'Fail-closed zobrazení', boardEmpty('UNKNOWN / NOT CONNECTED', error.message));
  }
}
function loadEcosystemBoard() {
  return boardLoad('ecosystem', data => {
    const flows = boardArray(data.architecture?.flows);
    const flowHtml = flows.length ? flows.map(flow =>
      '<div class="wb-flow"><div class="wb-flow-name"><strong>' +
      boardSafe(flow.label) + '</strong>' + boardTruth(flow.status) + '</div><div class="wb-flow-nodes" tabindex="0" role="region" aria-label="Architektonická projekce z API; lze vodorovně posouvat">' +
      boardArray(flow.nodes).map(node =>
        '<div><strong>' + boardSafe(node.label) + '</strong><small>' +
        boardSafe(node.source) + '</small>' + boardTruth(node.status) + '</div>').join('<span aria-hidden="true">→</span>') +
      '</div></div>').join('') : boardEmpty('Žádné doložené architektonické toky', 'Neznamená to, že vazby neexistují.');
    const html = '<div class="wb-layout"><div class="wb-main">' +
      boardPanel('VOODOO Workflow', 'Logická mapa odpovědností · model, nikoliv detekce běžících služeb',
        '<div class="wb-map"><div class="wb-map-pair">' +
        boardTile('Rook / Orchestration', 'Koordinace agentů a úkolů', '⌘') +
        boardTile('Relore / Memory', 'Znalosti, vyhledávání, kontext', '▤') +
        '</div><div class="wb-map-core">' +
        boardTile('Architecture Lab', 'Experimentální návrhy, žádná production authority', '⚗', 'wb-lab') +
        boardTile('VOODOO One', 'Řízení policy, approvals, evidence a auditu', '◈', 'wb-primary') +
        boardTile('Eval Fabric', 'Oddělené měření a ověřování', '✓', 'wb-eval') +
        '</div><div class="wb-map-pair">' +
        boardTile('Context Layer / SKILLS', 'Načítání projektových pravidel a schopností', '▱') +
        boardTile('Evidence Layer', 'Trace, artefakty, verifikace, původ', '▣') +
        '</div><div class="wb-project-strip">' +
        ['Pansofie', 'WEBFORGE', 'ODKAZERO', 'MRC'].map(x =>
          '<div>' + boardSafe(x) + '<small>REFERENCE · INTEGRATION UNKNOWN</small></div>').join('') +
        '</div></div>') +
      boardPanel('Skutečné architektonické projekce', 'Výstup přímo z V-One control-room API', flowHtml) + '</div>' +
      '<aside class="wb-aside">' +
      boardStats([['Trust state', data.overview?.trust_state ?? 'UNKNOWN', 'API projection'],
        ['Active runs', boardNumber(data.runs?.active_count), 'API projection'],
        ['Pending approvals', boardNumber(data.plans?.pending_approvals), 'API projection']]) +
      boardPanel('Legenda', 'Návrhové a runtime hranice',
        '<div class="wb-legend"><p>' + boardBadge('MODEL', 'warn') + ' logické umístění komponent</p><p>' +
        boardBadge('RUNTIME', 'good') + ' jen ověřené API hodnoty</p><p>' +
        boardBadge('UNKNOWN', 'neutral') + ' žádné falešné health indikátory</p></div>') +
      '</aside></div>';
    return boardHead('VOODOO Ecosystem Map', 'Kdo je kdo a jak spolu vrstvy souvisí.', '/api/v1/control-room · architecture') +
      html + boardNotice('Rook, Relore a další propojení jsou vizuální referenční model. Jejich stav není tímto API potvrzen.');
  });
}
function loadLifecycleBoard() {
  return boardLoad('lifecycle', data => {
    const stages = [
      ['Goal', 'Uživatelský záměr a scope'],
      ['Resolve', 'Určit projekt, policy a oprávnění'],
      ['Context', 'Bootstrap, zdroje a SKILLS'],
      ['Plan', 'Povolené kroky a omezení'],
      ['Execute', 'Úkony v povolené hranici'],
      ['Verify', 'Oddělené ověření skutečnosti'],
      ['Evidence', 'Původ, traces, důkazy'],
      ['Decision', 'Retry, stop či eskalace'],
      ['Closure', 'Archivace nebo zvlášť řízená promotion']
    ];
    const recent = boardArray(data.runs?.recent);
    const runs = recent.length ? recent.slice(0, 9).map(run =>
      '<article class="wb-item"><div><strong>' + boardSafe(run.title || run.id) +
      '</strong><small>' + boardSafe(run.id) + ' · ' + boardSafe(run.environment) +
      ' · ' + boardSafe(run.adapter) + '</small></div>' + boardTruth(run.status) + '</article>').join('') :
      boardEmpty('Nebyly vráceny žádné nedávné běhy', 'Toto je skutečný prázdný stav API.');
    return boardHead('VOODOO Task Lifecycle', 'Od cíle po důkaz. Horní pipeline představuje procesní model.', '/api/v1/control-room · runs') +
      boardStats([['Active', boardNumber(data.runs?.active_count), 'live API'],
        ['Queued', boardNumber(data.runs?.queue_depth), 'live API'],
        ['Succeeded', boardNumber(data.runs?.completed_count), 'live API'],
        ['Failed', boardNumber(data.runs?.failed_count), 'live API']]) +
      boardPanel('Task lifecycle · referenční model', 'Jednotlivé fáze samy o sobě netvrdí, že jimi konkrétní běh prošel',
        '<p class="wb-scroll-hint">← Diagram lze posouvat vodorovně →</p><div class="wb-steps" tabindex="0" role="region" aria-label="Devět kroků referenčního životního cyklu; lze vodorovně posouvat">' + stages.map(([a,b],i)=>boardStep(i+1,a,b)).join('') + '</div>' +
        '<div class="wb-branch"><span>Verification failed → bounded retry</span><span>Policy denied → STOP</span><span>Approval needed → HUMAN</span></div>') +
      '<div class="wb-columns">' +
      boardPanel('Aktuální běhy', 'Reálné záznamy z ProductService', '<div class="wb-items">'+runs+'</div>') +
      boardPanel('Rozhodovací hranice', 'Žádné automatické udělení authority',
        '<div class="wb-item"><strong>Worker → independent verification</strong>' + boardBadge('REQUIRED', 'info') + '</div>' +
        '<div class="wb-item"><strong>Experiment → production</strong>' + boardBadge('BLOCKED BY DESIGN', 'danger') + '</div>' +
        '<div class="wb-item"><strong>Release / deploy</strong>' + boardBadge('SEPARATE GATE', 'warn') + '</div>') + '</div>' +
      boardNotice('Stav běhu neznamená výsledek nezávislé verifikace. Detail skutečné operace otevřeš v existující sekci Runs → Passport.');
  });
}
function loadAuthorityBoard() {
  return boardLoad('authority', data => {
    const gates = boardArray(data.policy_gates);
    const cards = gates.length ? gates.map(gate =>
      '<article class="wb-gate"><div><strong>' + boardSafe(gate.name) +
      '</strong><small>' + boardSafe(gate.source) + '</small></div>' +
      boardTruth(gate.status) + '</article>').join('') :
      boardEmpty('Žádná dostupná policy metadata', 'Stav oprávnění je UNKNOWN.');
    return boardHead('Authority & Safety Boundaries', 'Kdo co smí a kde systém musí zastavit.', '/api/v1/control-room · policy_gates') +
      '<div class="wb-layout"><div class="wb-main">' +
      boardPanel('Trust boundaries', 'Návrhový model rolí; faktická oprávnění určuje server',
        '<div class="wb-trust"><div class="wb-trust-core"><span>◈</span><strong>VOODOO One</strong><small>CONTROL PLANE</small></div>' +
        '<div class="wb-trust-ring wb-ring-1">Orchestration</div><div class="wb-trust-ring wb-ring-2">Verification</div>' +
        '<div class="wb-trust-ring wb-ring-3">Execution</div><div class="wb-trust-ring wb-ring-4">Experimentation</div></div>' +
        '<div class="wb-role-row">' +
        boardTile('Worker Agents','Omezené provádění · žádná implicitní production authority','⌁') +
        boardTile('Independent Verifier','Výstup ≠ potvrzený důkaz','✓') +
        boardTile('Human Operator','Schválení významných a produkčních účinků','♙') + '</div>') +
      boardPanel('Runtime policy gates', 'Živé stavy ze serverové projekce',
        '<div class="wb-gates">'+cards+'</div>') + '</div>' +
      '<aside class="wb-aside">' + boardPanel('Safety kernel', 'Aktuální hodnoty',
        '<div class="wb-kernel">' +
        '<div><span>Fail-closed default</span>' + boardTruth(boardBoolean(data.capability_registry?.fail_closed_default, 'ENFORCED', 'NOT_ENFORCED')) + '</div>' +
        '<div><span>Production effects</span>' + boardTruth(boardBoolean(data.capability_registry?.production_effects_enabled, 'ENABLED', 'DISABLED')) + '</div>' +
        '<div><span>Emergency stop</span>' + boardTruth(boardBoolean(data.overview?.emergency_stop, 'ACTIVE', 'INACTIVE')) + '</div></div>') +
      boardPanel('Hard stop', 'Přechody vyžadují reálnou autoritu',
        '<p class="wb-blocked">⊘ No production authority for experiments</p><p class="muted">Žádný interaktivní prvek této obrazovky neprovádí změnu policy.</p>') +
      '</aside></div>' + boardNotice('Zobrazené policy hodnoty jsou read-only; schvalování zůstává v existujících autoritativních API a rolích.');
  });
}
function loadLineageBoard() {
  return boardLoad('lineage', data => {
    const items = boardArray(data.evidence_timeline);
    const checks = boardArray(data.verifier_center?.recent_checks);
    const timeline = items.length ? items.slice(0,12).map(item =>
      '<article class="wb-item"><div><strong>' + boardSafe(item.kind) +
      ' · ' + boardSafe(item.title) + '</strong><small>' + boardSafe(item.timestamp) +
      ' · ' + boardSafe(item.source || 'UNKNOWN_SOURCE') + '</small><p>' +
      boardSafe(item.detail || '') + '</p></div>' + boardTruth(item.status) + '</article>').join('') :
      boardEmpty('Evidence timeline je prázdná', 'Absence pozorovaného důkazu není důkazem absence skutečnosti.');
    const results = checks.length ? checks.slice(0,8).map(item =>
      '<article class="wb-item"><div><strong>' + boardSafe(item.source || 'UNKNOWN_SOURCE') +
      '</strong><small>' + boardSafe(item.result_digest || item.receipt_id || item.execution_id) +
      '</small></div>' + boardTruth(item.verification_status) + '</article>').join('') :
      boardEmpty('Bez doložené nezávislé verifikace', 'Žádná zelená značka se nedopočítává z execution statusu.');
    return boardHead('Evidence & Verification Chain', 'Od tvrzení přes vykonanou práci k ověřitelnému výsledku.', '/api/v1/control-room · evidence_timeline + verifier_center') +
      boardPanel('Evidence lineage · referenční proces', 'Model fází, nikoliv skutečná trace jednoho běhu',
        '<p class="wb-scroll-hint">← Diagram lze posouvat vodorovně →</p><div class="wb-steps wb-steps-evidence" tabindex="0" role="region" aria-label="Osm kroků referenční evidence; lze vodorovně posouvat">' +
        [['Claim', 'Co tvrdíme'], ['Context', 'Odkud informace pochází'],
        ['Action', 'Co se vykonalo'], ['Artifact', 'Co vzniklo'],
        ['Verify', 'Nezávislý verdikt'], ['Uncertainty', 'Co zůstává UNKNOWN'],
        ['Store', 'Původ a vazby'], ['Closure', 'Auditní uzavření']].map(([x,y],i)=>boardStep(i+1,x,y)).join('') +
        '</div>') +
      boardStats([['Evidence items', items.length, 'počet vrácených záznamů'],
        ['Verifier checks', checks.length, 'počet vrácených záznamů'],
        ['Independent exposed', boardBoolean(data.verifier_center?.independent_verification_exposed, 'YES', 'NO'), 'API truth']]) +
      '<div class="wb-columns">' + boardPanel('Evidence timeline', 'Skutečné položky z autorizovaného API', '<div class="wb-items">'+timeline+'</div>') +
      boardPanel('Independent verification', 'Receipt není důkaz ověřeného post-state',
        '<div class="wb-items">'+results+'</div>') + '</div>' +
      boardNotice('Výsledek modelu, receipt, integrity check a VerificationResult/v1 jsou rozdílné věci. Stav UNKNOWN zůstává explicitní.');
  });
}
function loadOverlaysBoard() {
  return boardLoad('overlays', data => {
    const workspaces = boardArray(state.workspaces);
    const owned = workspaces.length ? workspaces.map(ws =>
      '<article class="wb-profile wb-connected"><div class="wb-profile-title"><span class="wb-symbol" aria-hidden="true">▤</span><div><h3>' +
      boardSafe(ws.name) + '</h3><small>' + boardSafe(ws.id) + '</small></div></div>' +
      boardBadge('CONNECTED WORKSPACE','good') +
      '<div class="wb-profile-facts"><p><span>Environment</span><strong>' + boardSafe(ws.environment) +
      '</strong></p><p><span>Tools</span><strong>NOT EXPOSED</strong></p><p><span>Project profile</span><strong>UNKNOWN</strong></p>' +
      '<p><span>Approval path</span><strong>SERVER POLICY</strong></p></div></article>').join('') :
      boardEmpty('Žádné workspaces ve vašem účtu', 'Projekty se z tohoto stavu automaticky nepovažují za připojené.');
    const references = ['Pansofie','WEBFORGE','ODKAZERO','MRC'].map((name,i)=>
      '<article class="wb-profile wb-reference"><div class="wb-profile-title"><span class="wb-symbol" aria-hidden="true">' +
      ['✳','⬡','◎','⌘'][i] + '</span><div><h3>' + name + '</h3><small>Reference project</small></div></div>' +
      boardBadge('REFERENCE ONLY','neutral') +
      '<div class="wb-profile-facts"><p><span>Context source</span><strong>UNKNOWN</strong></p>' +
      '<p><span>Allowed tools</span><strong>UNKNOWN</strong></p>' +
      '<p><span>Verification mode</span><strong>UNKNOWN</strong></p>' +
      '<p><span>Evidence focus</span><strong>NOT MAPPED</strong></p></div></article>').join('');
    return boardHead('Project-Specific Overlays', 'Jednotné workflow a oddělené projektové hranice.', '/api/v1/workspaces + /api/v1/control-room') +
      boardPanel('Shared workflow', 'Projektové profily nesmějí přepisovat canonical authority',
        '<p class="wb-scroll-hint">← Diagram lze posouvat vodorovně →</p><div class="wb-steps wb-shared" tabindex="0" role="region" aria-label="Pět kroků referenčního workflow; lze vodorovně posouvat">' + [['Research','Kontext'],['Orchestrate','Oprávnění'],
        ['Execute','Scoped work'],['Evaluate','Verifier'],['Evidence','Audit']].map(([x,y],i)=>boardStep(i+1,x,y)).join('') + '</div>') +
      boardPanel('Připojené workspaces', 'Autorizovaný seznam z existujícího produktu',
        '<div class="wb-profiles">'+owned+'</div>') +
      boardPanel('Referenční projekty', 'Návrhové profily; žádné smyšlené integrace nebo živé stavy',
        '<div class="wb-profiles">'+references+'</div>') +
      boardNotice('Projektový overlay není authority owner. Skutečné konfigurace a identity budou napojeny až po nezávislém kontraktačním ověření.');
  });
}
