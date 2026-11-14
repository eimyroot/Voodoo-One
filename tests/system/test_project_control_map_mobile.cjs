'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const root=path.resolve(__dirname,'../..');
const js=fs.readFileSync(path.join(root,'voodoo_product/static/control_room.js'),'utf8');
const css=fs.readFileSync(path.join(root,'voodoo_product/static/styles.css'),'utf8');
const navFragment=js.split('function revealActiveNavOnCompactViewport(name){',2)[1]?.split('async function loadView(name){',1)[0];
assert.ok(navFragment,'missing mobile navigation helper');
const nodes=[
  {dataset:{view:'overview'},scrollIntoView(){throw Error('wrong navigation button')}},
  {dataset:{view:'projectmap'},scrollIntoView(options){this.lastOptions=options}},
];
const ctx=vm.createContext({window:{matchMedia:()=>({matches:true})},document:{querySelectorAll:()=>nodes}});
vm.runInContext('function revealActiveNavOnCompactViewport(name){'+navFragment,ctx);
vm.runInContext("revealActiveNavOnCompactViewport('projectmap')",ctx);
assert.equal(nodes[1].lastOptions.inline,'center');
assert.equal(nodes[1].lastOptions.block,'nearest');
nodes[1].lastOptions=undefined;
ctx.window.matchMedia=()=>({matches:false});
vm.runInContext("revealActiveNavOnCompactViewport('projectmap')",ctx);
assert.equal(nodes[1].lastOptions,undefined,'desktop must not scroll sidebar');
assert.match(js,/revealActiveNavOnCompactViewport\(name\);const view=/);

const mapFragment=js.split('async function loadProjectMap(){',2)[1]?.split('async function loadGovernance(){',1)[0];
assert.ok(mapFragment,'missing isolated project map view loader');
class Element {
  constructor(tag='div'){this.tagName=tag;this.innerHTML='';this.textContent='';this.className='';this.children=[];}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
}
const elements=new Map();
const el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)};
let mapData={
  schema:'ProjectControlMapProjection/v1',mode:'READ_ONLY',authority_effect:'NONE',
  observed_at_utc:'2026-11-13T11:44:28Z',freshness:'CURRENT_SNAPSHOT',
  active_delivery:'PROJECT-CONTROL-MAP-R1',focus_status:'IN_PROGRESS',
  snapshot_sha256:'a'.repeat(64),projects:[],relationships:[],known_gaps:[],
};
const mapContext=vm.createContext({
  $:el,
  document:{createElement:(tag)=>new Element(tag)},
  api:async()=>mapData,
  escapeHtml:v=>String(v).replaceAll('<','&lt;').replaceAll('>','&gt;'),
  status:v=>'['+v+']',
});
vm.runInContext('async function loadProjectMap(){'+mapFragment,mapContext);
(async()=>{
  await vm.runInContext('loadProjectMap()',mapContext);
  const banner=el('projectmap-status');
  assert.equal(banner.children.length,2);
  assert.match(banner.children[0].textContent,/snapshotu/);
  const details=banner.children[1];
  assert.equal(details.tagName,'details');
  assert.equal(details.children[1].textContent,'a'.repeat(64));
  assert.match(details.children[0].textContent,/SHA-256 a{12}…/);
  assert.doesNotMatch(banner.children[0].textContent,/a{64}/);
  assert.match(css,/#projectmap-status \.projectmap-digest code\{/);
  mapData={...mapData,snapshot_sha256:'<not-a-valid-digest>'};
  await vm.runInContext('loadProjectMap()',mapContext);
  assert.match(banner.textContent,/UNAVAILABLE \/ UNVERIFIED/);
  assert.equal(el('projectmap-projects').innerHTML,'');
  console.log('PASS: mobile selected tab visibility; compact auditable SHA; invalid digest fails closed');
})().catch(error=>{console.error(error);process.exitCode=1});
