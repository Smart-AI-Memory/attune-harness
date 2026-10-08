/* Exercise persistent descriptions and the real partial-save/recovery path. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {Element}=require('./gui_forms_intake.cjs');
async function flush(){for(let i=0;i<60;i++)await Promise.resolve();}
async function setup(){
 const doc={createElement(tag){return new Element(tag,this);}};
 const root=new Element('main',doc);
 for(const id of ['form-panel','tasks','decisions']){const el=new Element('div',doc);el.id=id;root.append(el);}
 doc.querySelector=s=>root.querySelector(s);doc.querySelectorAll=s=>root.querySelectorAll(s);
 const queue=[{editable:true,tasks:[]}],calls=[],status=new Element('p',doc);
 const context=vm.createContext({document:doc,status,token:'test',console,Map,JSON,Error,Object,
  refresh:async()=>true,clearTimeout(){},fetch:async(path,opts)=>{
   calls.push({path,opts});assert(queue.length,`Unexpected request ${path}`);const next=queue.shift();
   if(next instanceof Error)throw next;
   return {ok:next.ok!==false,text:async()=>next.error||'409 conflict',json:async()=>next};
  }});
 vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);await flush();
 return {root,doc,queue,calls,status,panel:doc.querySelector('#form-panel'),run:s=>vm.runInContext(s,context)};
}
const fields=[
 {id:'answer_0',text:'Which exact files are in scope? Enter one item per line.',type:'text_input',required:true},
 {id:'answer_1',text:'Which approach?',type:'single_select',required:true,options:['One','Two']},
 {id:'optional',text:'Optional context <script> stays literal',type:'text_input',required:false},
 {id:'unknown',text:'No requiredness supplied',type:'text_input'},
];
const shown={task:'A',checkpoint:'current-cp',decision:'single-use',display:{kind:'questions',
 title:'Clarify the work',markdown:'Owner record',definition:{fields}}};
function verify(h){
 const form=h.panel.querySelector('form'),instructions=h.panel.querySelector('#answer-instructions');
 assert(instructions);assert(h.panel.children.indexOf(instructions)<h.panel.children.indexOf(form));
 assert.match(instructions.textContent,/You can save partial answers/);
 const controls=form.querySelectorAll('textarea,select'),labels=form.querySelectorAll('label');
 assert.equal(controls.length,fields.length);assert.equal(labels.length,fields.length);
 for(let i=0;i<controls.length;i++){
  const input=controls[i],field=fields[i];assert.equal(input.name,field.id);
  assert.equal(labels[i].htmlFor,input.id);assert.equal(labels[i].textContent,field.text);
  const descriptions=input.getAttribute('aria-describedby').split(' ');
  assert.equal(descriptions.length,2);assert.equal(descriptions[0],instructions.id);
  const hint=h.panel.querySelector('#'+descriptions[1]);assert(hint);assert.equal(hint.hidden,false);
  assert.match(hint.textContent,/You can leave this blank when saving partial answers/);
  assert.equal(hint.textContent.includes('Required before intent acceptance.'),field.required===true);
  assert(!input.required);assert.equal(input.getAttribute('aria-required'),null);
  assert.equal(input.getAttribute('placeholder'),null);assert.equal(input.value,'');
 }
 const ids=h.panel.querySelectorAll('p,small,textarea,select').map(e=>e.id).filter(Boolean);
 assert.equal(new Set(ids).size,ids.length,'description references must not resolve ambiguously');
 assert(!h.panel.querySelector('script'),'untrusted label stays literal');
 return {form,instructions,controls};
}
(async()=>{
 const h=await setup();h.run(`renderDecision(${JSON.stringify(shown)})`);
 const {form,instructions,controls}=verify(h),count=h.calls.length;
 controls[0].value=' \n ';form.onsubmit({preventDefault(){}});await flush();
 assert.equal(h.calls.length,count,'blank submission makes no request');
 assert.equal(h.status.textContent,'Enter at least one answer to save.');assert(!form.querySelector('button').disabled);
 const text='src/first.py\nsrc/second.py';controls[0].value=text;controls[0].focus();
 assert.equal(h.panel.querySelector('#answer-instructions'),instructions,'instructions survive typing');
 assert.equal(controls[0].getAttribute('aria-describedby'),'answer-instructions field-answer_0-hint');
 h.queue.push({ok:false,error:'409 changed'});form.onsubmit({preventDefault(){}});await flush();
 const submits=h.calls.filter(c=>c.path==='/decision/submit');assert.equal(submits.length,1);
 assert.deepEqual(JSON.parse(submits[0].opts.body),{task:'A',checkpoint:'current-cp',decision:'single-use',response:{answers:{answer_0:text}}});
 assert.equal(h.panel.querySelector('textarea'),controls[0]);assert.equal(controls[0].value,text);assert(controls[0].readOnly);
 assert.equal(h.panel.querySelector('#answer-instructions'),instructions);assert(h.panel.querySelector('#field-answer_0-hint'));
 assert.match(h.panel.querySelector('.retained-answers').textContent,/src\/first.py\nsrc\/second.py/);
 const after=h.calls.length;form.onsubmit({preventDefault(){}});await flush();assert.equal(h.calls.length,after,'expired form never replays');
 const current={...shown,checkpoint:'fresh-cp',decision:'fresh-decision'};h.run(`renderDecision(${JSON.stringify(current)})`);verify(h);
 assert(h.calls.every(c=>['/workspace','/decision/submit'].includes(c.path)),'guidance never grants execution');
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
