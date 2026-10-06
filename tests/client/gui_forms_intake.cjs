/* Executes the production script with deterministic DOM, fetch and timer seams.
 * This is a behavioral client check; actual browser rendering remains a host check. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag,doc){this.tagName=tag.toUpperCase();this.doc=doc;this.children=[];this._text='';this.value='';this.disabled=false;this.hidden=false;this.scrollTop=0;}
 set textContent(v){this._text=String(v);this.children=[];this.firstChild={parentNode:this,textContent:this._text};}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 append(...els){for(const el of els){el.parentNode=this;this.children.push(el);}}
 replaceChildren(...els){for(const c of this.children)c.parentNode=null;this.children=[];this._text='';this.append(...els);}
 querySelectorAll(selector){return this.children.flatMap(c=>[...(match(c,selector)?[c]:[]),...c.querySelectorAll(selector)]);}
 querySelector(s){return this.querySelectorAll(s)[0]||null;}
 focus(){this.doc.activeElement=this;}
 setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b;}
 setAttribute(k,v){this[k]=String(v);}
 getAttribute(k){return this[k]??null;}
 contains(el){return this===el||el?.parentNode===this||this.children.some(c=>c.contains(el));}
 remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(c=>c!==this);}
}
function match(el,s){if(s.includes(','))return s.split(',').some(x=>match(el,x.trim()));if(s==='button')return el.tagName==='BUTTON';if(s==='textarea')return el.tagName==='TEXTAREA';if(s==='select')return el.tagName==='SELECT';if(s==='form')return el.tagName==='FORM';if(s==='pre')return el.tagName==='PRE';if(s.startsWith('#'))return el.id===s.slice(1);if(s.startsWith('.'))return (el.className||'').split(/\s+/).includes(s.slice(1));return el.tagName===s.toUpperCase();}
async function setup(){
 const doc={activeElement:null,createElement(tag){return new Element(tag,this);}};
 const root=new Element('main',doc);for(const id of ['form-panel','tasks','decisions']){const el=new Element('div',doc);el.id=id;root.append(el);}
 doc.querySelector=s=>root.querySelector(s);doc.querySelectorAll=s=>root.querySelectorAll(s);
 let queue=[],calls=[],timers=new Map(),seq=0;const snapshot={fresh:true};
 const status=new Element('p',doc);
 const selection={anchorNode:null,focusNode:null,setBaseAndExtent(a,ao,f,fo){this.anchorNode=a;this.anchorOffset=ao;this.focusNode=f;this.focusOffset=fo;}};const window={scrollX:0,scrollY:0,getSelection:()=>selection,scrollTo(x,y){this.scrollX=x;this.scrollY=y;}};
 const context=vm.createContext({window,document:doc,status,token:'test',console,Map,JSON,Error,Object,setTimeout(fn){const id=++seq;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},refresh:async()=>snapshot.fresh,fetch:async(path,opts)=>{calls.push({path,opts});assert(queue.length,`Unexpected request ${path}`);const next=queue.shift();if(next instanceof Error)throw next;if(typeof next==='function')return next();return {ok:next.ok!==false,text:async()=>next.error||'409 conflict',json:async()=>next};}});
 queue.push({editable:true,tasks:[]});vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);await flush();
 return {doc,root,status,selection,window,snapshot,queue,calls,timers,run:s=>vm.runInContext(s,context),panel:doc.querySelector('#form-panel')};
}
async function flush(){for(let i=0;i<60;i++)await Promise.resolve();}
const shown={task:'A',checkpoint:'checkpoint-old',decision:'single-use',display:{kind:'questions',title:'Intake',markdown:'Owner',definition:{fields:[{id:'answer_0',type:'text_input',text:'Goal'},{id:'answer_1',type:'single_select',text:'Choice',options:['One','Two']}]}}};
function build(running=true,evidence={receipt:'one'}){return {note:'Inspect saved state',running,view:{summary:'Recorded',next_action:'review',completed:['one'],evidence},reviews:[]};}
function workspace(task='A',data=build()){return {editable:true,tasks:[{task,label:task,status:'accepted',checkpoint:'cp',build:data}]};}
(async()=>{
 for(const failure of [{ok:false,error:'409 conflict'},new Error('network lost')]){
  const h=await setup();h.run(`renderDecision(${JSON.stringify(shown)})`);const input=h.panel.querySelector('textarea');input.value='Recover this answer';const select=h.panel.querySelector('select');select.value='Two';input.focus();input.setSelectionRange(2,7);
  h.queue.push(failure);h.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
  assert.equal(h.panel.querySelector('textarea'),input,'failure must retain original input node');assert.equal(input.value,'Recover this answer');assert.equal(h.panel.querySelector('select'),select);assert.equal(select.value,'Two');assert(select.disabled);const recovery=h.panel.querySelector('.retained-answers');assert(recovery,'expired fields need copyable recovery text');assert(recovery.textContent.includes(shown.display.definition.fields[0].text+': Recover this answer'));assert(recovery.textContent.includes(shown.display.definition.fields[1].text+': Two'));assert(!recovery.textContent.includes('answer_0:'));assert(!recovery.textContent.includes('answer_1:'));assert.equal(recovery.getAttribute('aria-label'),'Retained answers for copying');assert.equal(h.panel.querySelectorAll('.retained-answers').length,1);assert.equal(h.panel.querySelectorAll('.expired-notice').length,1);h.run('expirePanel()');assert.equal(h.panel.querySelectorAll('.retained-answers').length,1,'repeated expiry must not duplicate recovery');assert.equal(h.panel.querySelectorAll('.expired-notice').length,1,'repeated expiry must not duplicate notice');assert.equal(h.doc.activeElement,input);assert.equal(input.selectionStart,2);assert.equal(input.selectionEnd,7);assert(h.panel.querySelector('button').disabled,'expired submission must stay disabled');
  const count=h.calls.length;h.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();assert.equal(h.calls.length,count,'expired form must never replay');
 }
 const h=await setup();h.run(`renderDecision(${JSON.stringify(shown)})`);const input=h.panel.querySelector('textarea');input.value='Unsaved';h.queue.push(new Error('refresh lost'));await h.run('refreshWorkspace()');assert.equal(h.panel.querySelector('textarea'),input);assert.equal(input.value,'Unsaved');assert(h.panel.querySelector('button').disabled);
 const f=await setup();f.run(`renderDecision(${JSON.stringify(shown)})`);const savedInput=f.panel.querySelector('textarea');savedInput.value='Saved or uncertain';f.snapshot.fresh=false;f.queue.push({message:'Saved'},new Error('workspace unavailable'));f.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();assert.equal(f.panel.querySelector('textarea'),savedInput,'failed post-submit refresh must retain recoverable input');assert.equal(savedInput.value,'Saved or uncertain');assert(savedInput.readOnly,'expired answer remains readable and copyable');assert(f.panel.querySelector('button').disabled);assert.equal(f.calls.filter(c=>c.path==='/decision/submit').length,1);
 // An offline owner-state sequence proves that acceptance never grants execution.
 const j=await setup(),button=text=>j.root.querySelectorAll('button').find(b=>b.textContent===text);
 const current={...shown,checkpoint:'current-cp',decision:'current-decision',display:{...shown.display,definition:{fields:[{id:'answer_0',type:'text_input',text:'Remaining question after partial intake'}]}}};
 const intakeState={editable:true,tasks:[{task:'A',label:'A',status:'intake',note:'Questions remain',checkpoint:'current-cp',available:true}]};
 j.queue.push(intakeState);await j.run('loadTasks()');j.queue.push(current);button('Open current form').onclick();await flush();
 assert.equal(j.panel.querySelector('textarea').value,'','current reopen must never remap retained positional answers');
 j.panel.querySelector('textarea').value='Local goal';j.queue.push({message:'Saved'},intakeState);j.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(JSON.parse(j.calls.find(c=>c.path==='/decision/submit').opts.body).response.answers.answer_0,'Local goal');
 const remaining={...current,decision:'remaining-decision',checkpoint:'remaining-cp',display:{...current.display,definition:{fields:[{id:'answer_0',type:'text_input',text:'Only the unanswered question'}]}}};j.queue.push(remaining);button('Open current form').onclick();await flush();assert.equal(j.panel.querySelector('textarea').value,'','partial answer must not remap answer_0 into a newly issued remaining question');assert.equal(j.panel.querySelector('button').disabled,false,'only deliberate current reopen restores submission');
 const acceptance={task:'A',checkpoint:'accept-cp',decision:'accept-decision',display:{kind:'review',title:'Review',markdown:'Local intent',actions:[{id:'approve_task',label:'Accept'}]}};
 j.queue.push(acceptance);button('Open current form').onclick();await flush();
 const ready={editable:true,tasks:[{task:'A',label:'A',status:'accepted',note:'Intent accepted',available:false}]};j.queue.push({message:'Accepted'},ready);button('Accept this intent').onclick();await flush();
 assert.equal(j.calls.filter(c=>c.path==='/build/start').length,0,'intent acceptance must never start build');

 assert(!j.root.querySelectorAll('button').some(b=>/build|resume|grant/i.test(b.textContent)),'release must not render execution controls');
 assert(j.calls.every(c=>['/workspace','/decision/open','/decision/submit'].includes(c.path)),'release must only call forms routes');
 const r=await setup();r.queue.push({editable:false,tasks:[{task:'A',label:'Read-only draft',status:'draft',note:'Inspect intent',available:true}]});await r.run('loadTasks()');assert.match(r.root.textContent,/Read-only draft/);assert.equal(r.doc.querySelector('#decisions').hidden,false);assert.equal(r.root.querySelectorAll('button').length,0,'read-only draft has no decision controls');
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
