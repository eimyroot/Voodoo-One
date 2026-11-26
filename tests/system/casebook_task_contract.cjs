/* Node-only contract test of the actual CASEBOOK browser pane.
 * Backward-compatible live API payloads must render, while any VERIFIED
 * authority claim is refused. No external node packages are needed.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.resolve(
  __dirname, "../../voodoo_product/static/control_room.js",
), "utf8");
const start = source.indexOf("const casebookSessionIdPattern=");
const end = source.indexOf("function canonicalReadReady(", start);
assert.ok(start >= 0 && end > start, "casebook rendering code exists");
const pane = source.slice(start, end);
const session = "caser-demo-task-20261123";
const fakeTimeline = [
  {seq: 1, event_id: "e1", type: "GOAL", timestamp: "2026-11-23T17:00:00Z",
    source_claim: "user", status_claim: "OPEN",
    summary: "<img src=x onerror=alert(1)>", event_hash: "a".repeat(64)},
];
const base = {
  schema: "voodoo-casebook/task-view/v1", session_id: session,
  workspace_id: "local-demo-workspace", project: "synthetic/CyberCaser",
  goal: "Synthetic status only",
  display_state: "RESULT_RECORDED_UNVERIFIED",
  journal_integrity: "LOCAL_HASH_CHAIN_VERIFIED_ONLY",
  native_approval: "NOT_ATTESTED",
  isolated_runner_execution: "NOT_ATTESTED",
  independent_verifier: "NOT_ATTESTED",
  handoff: "NOT_ESTABLISHED", result: "RECORDED_UNVERIFIED",
  next_action: "VERIFY_NATIVE_APPROVAL_EXECUTION_AND_INDEPENDENT_RESULT",
  timeline: fakeTimeline,
};

async function render(payload) {
  const els = new Map();
  const $ = (id) => {
    if (!els.has(id)) {
      const classes = new Set(["hidden"]);
      els.set(id, {
        textContent: "", innerHTML: "", value: "",
        classList: {
          add: (c) => classes.add(c),
          remove: (c) => classes.delete(c),
          contains: (c) => classes.has(c),
        },
        replaceChildren() { this.innerHTML = ""; },
        addEventListener() {},
      });
    }
    return els.get(id);
  };
  const ctx = vm.createContext({
    $, state: {token: "test-only"},
    api: async (_path,options) => { assert.equal(options.cache,'no-store'); return payload; },
    status: (value) => "<span>"+String(value)+"</span>",
    escapeHtml: (value) => String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;",
      '"': "&quot;", "'": "&#39;",
    }[char])),
  });
  vm.runInContext(pane, ctx, {filename: "casebook/control_room.js"});
  await vm.runInContext("loadCasebookTask("+JSON.stringify(session)+")", ctx);
  return {
    visible: !$("casebook-task-detail").classList.contains("hidden"),
    feedback: $("casebook-task-feedback").textContent,
    details: $("casebook-task-state").innerHTML,
    timeline: $("casebook-task-timeline").innerHTML,
    goal: $("casebook-task-goal").textContent,
    meta: $("casebook-task-meta").textContent,
    next: $("casebook-task-next").textContent,
    signals: $("casebook-task-signals").innerHTML,
  };
}

(async function run() {
  const legacy = await render({...base});
  assert.equal(legacy.visible, true, "legacy API without flags is displayable");
  assert.match(legacy.feedback, /lokální integrita journalu ověřena/);
  assert.match(legacy.details, /NOT_ATTESTED/);
  assert.equal(legacy.goal, base.goal);
  assert.ok(!legacy.timeline.includes("<img"), "untrusted text is escaped");
  assert.match(legacy.timeline, /&lt;img/);

  const current = await render({
    ...base, execution_verified_by_this_view: false,
    execution_authorized_by_this_view: false,
  });
  assert.equal(current.visible, true, "explicit false flags are displayable");

  const spoof = await render({
    ...base, execution_verified_by_this_view: true,
  });
  assert.equal(spoof.visible, false, "verified execution must never be spoofed");
  assert.match(spoof.feedback, /NEDOSTUPNÉ \/ NEOVĚŘENO/);

  const spoofAuthorized = await render({
    ...base, execution_authorized_by_this_view: true,
  });
  assert.equal(spoofAuthorized.visible, false, "unattested authorization must not be claimed");

  const spoofString = await render({
    ...base, execution_verified_by_this_view: "false",
  });
  assert.equal(spoofString.visible, false, "string false is not a boolean proof");

  const spoofNull = await render({
    ...base, execution_verified_by_this_view: null,
  });
  assert.equal(spoofNull.visible, false, "null is not an acceptable missing claim");

  const spoofVerifier = await render({
    ...base, independent_verifier: "VERIFIED",
  });
  assert.equal(spoofVerifier.visible, false, "independent verification is not a journal claim");
  assert.match(spoofVerifier.feedback, /NEDOSTUPNÉ \/ NEOVĚŘENO/);
  const story = await render({...base, timeline:[
    ...fakeTimeline,
    {...fakeTimeline[0],seq:2,type:'DECISION',summary:'Chosen approach'},
    {...fakeTimeline[0],seq:3,type:'BLOCKER',summary:'<script>unsafe</script>',status_claim:'OPEN'},
    {...fakeTimeline[0],seq:4,type:'BLOCKER',summary:'resolved earlier',status_claim:'RESOLVED'},
    {...fakeTimeline[0],seq:5,type:'LEARNING',summary:'Lesson recorded'},
  ]});
  assert.match(story.meta,/synthetic\/CyberCaser/);
  assert.match(story.next,/Doložit nativní schválení/);
  assert.match(story.signals,/Chosen approach/);
  assert.match(story.signals,/Lesson recorded/);
  assert.match(story.signals,/&lt;script&gt;unsafe/);
  assert.doesNotMatch(story.signals,/resolved earlier|<script>/);
  assert.match(story.timeline,/Původ zápisu/);
  const unknownNext=await render({...base,next_action:'UNREVIEWED_MUTATION'});
  assert.equal(unknownNext.next,'Další krok není doložen.');
  process.stdout.write("CASEBOOK_JS_CONTRACT_PASS 7/7 + JOURNAL_STORY_PASS\n");

  const els=new Map(), requests=[];
  const $=id=>{
    if(!els.has(id))els.set(id,{textContent:'',innerHTML:'',value:'',disabled:true,listeners:{},
      classList:{add(){},remove(){}},replaceChildren(){this.innerHTML='';},addEventListener(n,fn){this.listeners[n]=fn;}});
    return els.get(id);
  };
  const ctx=vm.createContext({$,state:{token:'synthetic'},
    api:(url,opts)=>{assert.equal(opts.cache,'no-store');return new Promise((resolve,reject)=>requests.push({url,resolve,reject}));},
    escapeHtml:value=>String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])),
    status:value=>String(value)});
  vm.runInContext(pane,ctx);
  const evaluate=expression=>vm.runInContext(expression,ctx);
  const payload=id=>({schema:'voodoo-casebook/bound-task-index/v1',journal_integrity:'NOT_CHECKED_BY_INDEX',has_more:false,
    items:[{session_id:id,project:'<synthetic>',workspace_id:'wrk-1',environment:'local'}]});
  const a=evaluate('loadCasebookTasks()'),b=evaluate('loadCasebookTasks()');
  assert.equal(requests[0].url,'/casebook/tasks');
  requests[1].resolve(payload(session));await b;
  requests[0].resolve(payload('caser-stale'));await a;
  assert.match($('casebook-bound-session').innerHTML,/caser-demo-task/);
  assert.match($('casebook-bound-session').innerHTML,/&lt;synthetic&gt;/);
  assert.doesNotMatch($('casebook-bound-session').innerHTML,/caser-stale/);
  assert.equal($('casebook-bound-open').disabled,false);
  $('casebook-bound-session').value=session;
  $('casebook-bound-form').listeners.submit({preventDefault(){}});
  assert.equal(requests[2].url,'/casebook/tasks/'+session);
  requests[2].resolve(base);await Promise.resolve();await Promise.resolve();
  const c=evaluate('loadCasebookTasks()');
  assert.equal($('casebook-bound-open').disabled,true);
  requests[3].reject(Error('offline'));await c;
  assert.match($('casebook-index-feedback').textContent,/UNKNOWN/);
  assert.equal($('casebook-bound-session').innerHTML,'');
  const d=evaluate('loadCasebookTasks()');
  ctx.state.token='';
  evaluate('clearCasebookIndex()');
  requests[4].resolve(payload(session));await d;
  assert.equal($('casebook-bound-session').innerHTML,'');
  assert.equal($('casebook-bound-open').disabled,true);
  console.log('CASEBOOK_BOUND_INDEX_PASS selection, stale response, outage, logout, escaping');

  if (process.argv[2] === "--live") {
    const root = process.argv[3];
    assert.ok(root && root.startsWith("/Users/eimyna/0_EVIDENCE/Voodoo-One/CASEBOOK_FUNCTIONAL_UI_"), "synthetic demo root");
    const settings = JSON.parse(fs.readFileSync(path.join(root, ".private_preview_settings.json"), "utf8"));
    assert.equal(settings.marker, "CASEBOOK_LOCAL_PREVIEW_ONLY");
    const endpoint = "http://127.0.0.1:10003";
    const login = await fetch(endpoint+"/api/v1/auth/login", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username: "casebook-demo", password: settings.demo_password}),
    });
    assert.equal(login.status, 200, "live login");
    const auth = (await login.json()).token;
    const headers = {Authorization: "Bearer "+auth};
    try {
      const response = await fetch(endpoint+"/api/v1/casebook/tasks/"+session, {headers});
      assert.equal(response.status, 200, "live CASEBOOK API");
      const payload = await response.json();
      const visual = await render(payload);
      assert.equal(visual.visible, true, "live API payload renders in actual pane");
      assert.match(visual.details, /NOT_ATTESTED/);
      assert.match(visual.feedback, /lokální integrita journalu ověřena/);
      assert.match(visual.goal, /DEMO/);
      process.stdout.write("CASEBOOK_LIVE_JS_RENDER_PASS 1/1\n");
    } finally {
      const logout = await fetch(endpoint+"/api/v1/auth/logout", {method: "POST", headers});
      assert.equal(logout.status, 204, "live logout");
    }
  }
})().catch(err => {
  process.stderr.write(String(err)+"\n");
  process.exitCode = 1;
});
