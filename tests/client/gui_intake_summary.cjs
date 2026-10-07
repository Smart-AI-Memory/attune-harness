/* Exercise the shipped intake presentation and retained-decision boundaries. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {Element}=require('./gui_forms_intake.cjs');
async function flush(){for(let i=0;i<60;i++)await Promise.resolve();}
async function setup(){
 const doc={createElement(tag){return new Element(tag,this);}};
 const root=new Element('main',doc);
 for(const id of ['form-panel','tasks','decisions']){const el=new Element('div',doc);el.id=id;root.append(el);}
 doc.querySelector=s=>root.querySelector(s);doc.querySelectorAll=s=>root.querySelectorAll(s);
 const queue=[{editable:true,tasks:[]}],calls=[],status=new Element('p',doc);
 const context=vm.createContext({document:doc,status,token:'test',console,Map,JSON,Error,Object,fetch:async(path,opts)=>{
  calls.push({path,opts});assert(queue.length,`Unexpected request ${path}`);const next=queue.shift();
  if(next instanceof Error)throw next;
  return {ok:next.ok!==false,text:async()=>next.error||'409 conflict',json:async()=>next};
 }});
 vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);await flush();
 return {root,doc,queue,calls,status,panel:doc.querySelector('#form-panel'),run:s=>vm.runInContext(s,context)};
}
const original='## Owner record\nUse field_id: value.\n```json\n{"__elicitation_response__": {"answer_0": null}}\n```';
const intent={goal:'The saved goal <script> is literal',acceptance:[],questions:[],scope:['fixed.py'],constraints:[],context:[]};
const decision={task:'A',checkpoint:'remaining-cp',decision:'single-use',summary:{intent,choices:[],authoring:{tier:'bounded'}},
 display:{kind:'questions',title:'Clarify the work',markdown:original,definition:{fields:[{id:'answer_0',type:'text_input',text:'What observable result establishes success?'}]}}};
function render(h,shown=decision){h.run(`renderDecision(${JSON.stringify(shown)})`);}
module.exports={setup,flush};
if(require.main===module)(async()=>{
 const h=await setup();render(h);
 const saved=h.panel.querySelector('.saved-answers'),form=h.panel.querySelector('form'),details=h.panel.querySelector('details');
 assert(saved,'retained answers must be immediately visible');assert.equal(saved.getAttribute('aria-label'),'Saved answers');
 assert.equal(saved.querySelector('p').textContent,intent.goal);assert(!saved.querySelector('script'),'untrusted saved text must stay literal');
 assert(h.panel.children.indexOf(saved)<h.panel.children.indexOf(form),'saved answers precede the remaining question');
 assert(h.panel.children.indexOf(form)<h.panel.children.indexOf(details),'technical record follows the form');
 assert.equal(details.querySelector('summary').textContent,'Technical details (optional)');assert.equal(details.open,false);
 assert.equal(details.querySelector('pre').textContent,original,'portable owner record must remain byte-for-byte intact');
 const input=form.querySelector('textarea');assert.equal(input.value,'','saved positional answer_0 must not prefill the newly issued answer_0');
 assert.equal(input.name,'answer_0');assert.equal(form.querySelector('label').textContent,decision.display.definition.fields[0].text);
 input.value='A real observable result';h.queue.push({ok:false,error:'409 changed'});form.onsubmit({preventDefault(){}});await flush();
 assert.equal(h.panel.querySelector('.saved-answers'),saved,'uncertain submission retains the visible saved state');
 assert(input.readOnly);assert(form.querySelector('button').disabled);assert.equal(input.value,'A real observable result');
 assert.match(h.panel.querySelector('.retained-answers').textContent,/A real observable result/);
 const submitted=JSON.parse(h.calls.find(c=>c.path==='/decision/submit').opts.body);
 assert.deepEqual(submitted,{task:'A',checkpoint:'remaining-cp',decision:'single-use',response:{answers:{answer_0:'A real observable result'}}});
 const count=h.calls.length;form.onsubmit({preventDefault(){}});await flush();assert.equal(h.calls.length,count,'read-only form never replays answers');
 h.queue.push(new Error('refresh unavailable'));await h.run('refreshWorkspace()');assert.equal(h.panel.querySelector('.saved-answers'),saved);assert(input.readOnly);

 const answered=await setup();render(answered,{...decision,summary:{...decision.summary,intent:{...intent,goal:null,
  acceptance:['Receipt exists','Checks pass'],questions:[{question:'Required decision',answer:'Known answer'},{question:'Pending',answer:null}]},
  choices:[{question:'Format',selected:'jsonl',options:[{id:'jsonl',proposal:'Stream JSON lines'}]},{question:'Undecided',selected:null,options:[]}]}});
 assert.deepEqual(answered.panel.querySelector('.saved-answers').querySelectorAll('h4').map(e=>e.textContent),['Done when','Required decision','Format']);
 assert.deepEqual(answered.panel.querySelector('.saved-answers').querySelectorAll('li').map(e=>e.textContent),['Receipt exists','Checks pass']);
 assert(!answered.panel.querySelector('.saved-answers').textContent.includes('Pending'));assert(!answered.panel.querySelector('.saved-answers').textContent.includes('Undecided'));
 for(const summary of [undefined,{...decision.summary,intent:{...intent,goal:null}}]){
  const fresh=await setup();render(fresh,{...decision,summary});assert.equal(fresh.panel.querySelector('.saved-answers'),null,'fresh intake never invents saved answers');
  assert.equal(fresh.panel.querySelector('pre').textContent,original);assert.equal(fresh.panel.querySelector('textarea').value,'');
 }
 const unsupported=await setup();render(unsupported,{...decision,display:{...decision.display,definition:{fields:[{id:'other',type:'unknown',text:'Other'}]}}});
 assert.equal(unsupported.panel.querySelector('pre').textContent,original,'CLI-only fields retain their full fallback record');
 assert(unsupported.panel.children.indexOf(unsupported.panel.querySelector('form'))<unsupported.panel.children.indexOf(unsupported.panel.querySelector('details')));
 assert.equal(unsupported.panel.querySelector('button'),null);

 for(const actions of [[],[{id:'approve_task',label:'Accept',consequence:'Record intent'}]]){
  const preview=await setup();render(preview,{...decision,display:{kind:'spec',title:'Review',markdown:original,actions}});
  assert.equal(preview.panel.querySelector('.saved-answers'),null,'approval renders its own question-and-answer preview');
  assert.equal(preview.panel.querySelector('h2').textContent,'Review your answers');assert.equal(preview.panel.querySelector('h3').textContent,'What should this work accomplish?');
  assert.equal(preview.panel.querySelector('details').querySelector('summary').textContent,'Technical details');
  assert.equal(preview.panel.querySelector('details').open,false,'raw protocol stays collapsed in approval views');
  assert.equal(preview.panel.querySelectorAll('button').length,actions.length);assert.equal(preview.panel.querySelector('pre').textContent,original);
 }
 const readonly=await setup();readonly.queue.push({editable:false,tasks:[{task:'A',label:'Saved goal',status:'draft',available:true}]});await readonly.run('loadTasks()');
 assert.equal(readonly.root.querySelectorAll('button').length,0);assert.equal(readonly.panel.children.length,0);
 assert(h.calls.every(c=>['/workspace','/decision/submit'].includes(c.path)),'presentation never enables model or build routes');
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
