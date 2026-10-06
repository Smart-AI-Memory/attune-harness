/* Dependency-free handoff regressions; trusted gestures are also exercised in real Chromium. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {Element}=require('./gui_forms_intake.cjs');
const script=fs.readFileSync(process.argv[2],'utf8');
async function flush(){for(let i=0;i<60;i++)await Promise.resolve();}
async function setup({authorized=true,editable=true}={}){
 const doc={createElement(tag){return new Element(tag,this);}},root=new Element('main',doc);
 for(const id of ['refresh','browser-open','browser-tip','status','decisions','tasks','form-panel']){
  const el=new Element(['refresh','browser-open'].includes(id)?'button':'div',doc);el.id=id;
  el.disabled=id==='browser-open';el.hidden=['browser-tip','decisions'].includes(id);
  el.addEventListener=function(name,listener){(this.listeners??={})[name]=listener;};root.append(el);
 }
 doc.querySelector=s=>root.querySelector(s);doc.querySelectorAll=s=>root.querySelectorAll(s);
 const media={matches:false,addEventListener(name,fn){assert.equal(name,'change');this.changed=fn;}};
 const queue=[],calls=[];
 const globals={document:doc,location:{hash:'#private-fixture-token',pathname:'/'},history:{replaceState(){}},
  sessionStorage:{setItem(){}},window:{matchMedia(query){assert.equal(query,'(max-width:600px)');return media;}},
  fetch:async(path,opts)=>{calls.push({path,opts});assert(queue.length,'Unexpected request '+path);const next=queue.shift();
   if(next instanceof Error)throw next;if(typeof next==='function')return next();
   return {ok:next.ok!==false,text:async()=>next.error||'403 refused',json:async()=>next};}};
 queue.push(authorized?{editable,tasks:[]}:{ok:false,error:'Open this workspace using its local launcher link'});
 const context=vm.createContext(globals);vm.runInContext(script,context);await flush();
 return {doc,root,queue,calls,media,run:s=>vm.runInContext(s,context)};
}
(async()=>{
 for(const editable of [true,false]){
  const h=await setup({editable}),button=h.doc.querySelector('#browser-open'),tip=h.doc.querySelector('#browser-tip');
  assert(!button.disabled);assert(tip.hidden);assert.equal(h.calls.length,1);
  h.media.matches=true;h.media.changed();assert(!tip.hidden);assert.equal(h.calls.length,1,'resize must never launch browser');
  h.media.matches=false;h.media.changed();assert(tip.hidden);
  button.listeners.click({isTrusted:false});await flush();assert.equal(h.calls.length,1,'synthetic click must not launch browser');
  let deliver;
  h.queue.push(()=>new Promise(resolve=>deliver=resolve));button.listeners.click({isTrusted:true});
  button.listeners.click({isTrusted:true});await flush();assert(button.disabled);
  assert.equal(h.calls.filter(c=>c.path==='/browser/open').length,1,'pending repeated click must not duplicate launch');
  const sent=h.calls.at(-1);assert.deepEqual(JSON.parse(sent.opts.body),{confirmed:true});assert.equal(sent.opts.headers['X-Attune-Session'],'private-fixture-token');
  deliver({ok:true,json:async()=>({requested:true,message:'Browser opening requested.'})});await flush();
  assert(!button.disabled);assert.match(h.doc.querySelector('#status').textContent,/Browser opening requested/);
  assert(h.calls.every(c=>['/workspace','/browser/open'].includes(c.path)),'handoff must not submit a decision');
 }
 const missing=await setup({authorized:false}),blocked=missing.doc.querySelector('#browser-open');
 assert(blocked.disabled);blocked.listeners.click({isTrusted:true});await flush();assert.equal(missing.calls.length,1);
 missing.queue.push({editable:true,tasks:[]});missing.doc.querySelector('#refresh').listeners.click();await flush();assert(!blocked.disabled,'successful Refresh restores browser control');
 const h=await setup();
 const shown={task:'A',checkpoint:'cp',decision:'decision',display:{kind:'questions',title:'Intake',markdown:'Owner',definition:{fields:[{id:'answer_0',type:'text_input',text:'Goal'}]}}};
 h.run('renderDecision('+JSON.stringify(shown)+')');const input=h.doc.querySelector('textarea');input.value='Keep this unsaved answer';
 h.queue.push(new Error('network unavailable'));h.doc.querySelector('#browser-open').listeners.click({isTrusted:true});await flush();
 assert(input.readOnly);assert.equal(input.value,'Keep this unsaved answer');assert.match(h.doc.querySelector('.retained-answers').textContent,/Keep this unsaved answer/);
 assert(h.doc.querySelector('#form-panel').querySelector('button').disabled);assert(!h.doc.querySelector('#browser-open').disabled);
 assert.match(h.doc.querySelector('#status').textContent,/could not be confirmed.*Terminal/);
 const count=h.calls.length;h.doc.querySelector('form').onsubmit({preventDefault(){}});await flush();assert.equal(h.calls.length,count,'handoff expires prior form without replay');
 assert(!h.doc.querySelector('#status').textContent.includes('private-fixture-token'));
 console.log('client regressions passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
