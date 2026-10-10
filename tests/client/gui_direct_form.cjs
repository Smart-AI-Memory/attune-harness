/* Execute the shipped single-task journey, including recovery and approval. */
const assert=require('node:assert/strict');
const {setup,flush}=require('./gui_intake_summary.cjs');
const intent={goal:null,acceptance:[],scope:['source.py'],constraints:['No execution'],context:[],questions:[]};
function task(checkpoint,goal=null,acceptance=[],accepted=false){return {
 task:'A',checkpoint,status:accepted?'accepted':'draft',heading:accepted?'Intent accepted':'Draft saved',
 label:goal||'Unfinished draft',note:'Saved state',available:!accepted,action_label:acceptance.length?'Review your answers':'Continue form',
 saved_request:{task_id:'owner-id',revision:1,checkpoint,intent:{...intent,goal,acceptance},choices:[],authoring:{tier:'prompt'},fresh:true,accepted}
};}
function questions(checkpoint,fields,goal=null){return {
 task:'A',checkpoint,decision:'decision-'+checkpoint,summary:{intent:{...intent,goal},choices:[],authoring:{tier:'prompt'}},
 display:{kind:'questions',title:'Clarify the work',markdown:'Literal owner record',definition:{fields:fields.map((text,index)=>({id:'answer_'+index,text,type:'text_input',required:true}))}}
};}
const initial=questions('cp-1',['What should this work accomplish?','What observable result establishes success?']);
const goal='My Capitalized goal\nwith a second line';
const workspace=item=>({editable:true,tasks:[item]});
(async()=>{
 const h=await setup();
 h.queue.push(workspace(task('cp-1')),initial);await h.run('loadTasks()');
 assert(h.panel.querySelector('form'),'single draft displays its form without a navigation click');
 assert.equal(h.root.querySelectorAll('button').find(b=>b.textContent==='Continue form').hidden,true,'Continue form is not an extra step');
 assert.equal(h.calls.filter(c=>c.path==='/decision/submit').length,0,'display never submits a response');
 assert.deepEqual(JSON.parse(h.calls.at(-1).opts.body),{task:'A',checkpoint:'cp-1',replace:false});
 h.panel.querySelector('textarea').value=goal;
 h.queue.push({message:'Answers saved'},workspace(task('cp-2',goal)),questions('cp-2',['What observable result establishes success?'],goal));
 h.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(h.panel.querySelector('.saved-answers').querySelector('h4').textContent,'Saved goal');
 assert.equal(h.panel.querySelector('.saved-answers').querySelector('p').textContent,goal);
 assert.equal(h.panel.querySelector('textarea').value,'','saved answer_0 is never remapped into the next question');
 assert.equal(h.panel.querySelector('button').disabled,false,'confirmed save advances to the remaining form');
 const acceptedIntent={...intent,goal,acceptance:['The result is visible']};
 const review={task:'A',checkpoint:'cp-3',decision:'review-id',summary:{intent:acceptedIntent,choices:[],authoring:{tier:'prompt'}},
  display:{kind:'spec',markdown:'Intent only',actions:[{id:'approve_task',label:'Accept',consequence:'Record intent only'}]}};
 h.panel.querySelector('textarea').value='The result is visible';
 h.queue.push({message:'Answers saved'},workspace(task('cp-3',goal,acceptedIntent.acceptance)),review);
 h.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(h.panel.querySelector('h2').textContent,'Review your answers');
 assert.equal(h.panel.querySelector('.technical-input').textContent,'source.py','scope paths use technical presentation without rewriting');
 assert.equal(h.calls.filter(c=>c.path==='/decision/submit').length,2);
 assert(h.calls.filter(c=>c.path==='/decision/submit').every(c=>JSON.parse(c.opts.body).response.answers),'review is shown without accepting');
 h.queue.push({message:'Intent accepted',heading:'Intent accepted'},workspace(task('cp-4',goal,acceptedIntent.acceptance,true)));
 h.panel.querySelector('button').onclick();await flush();
 const accepted=h.root.querySelector('.saved-request');assert.equal(accepted.open,true);
 assert.equal(accepted.querySelector('summary').textContent,'View accepted request');
 assert.equal(h.panel.children.length,0,'accepted view has no leftover editing or approval controls');
 assert.equal(h.root.querySelectorAll('button').length,0,'no Edit button is introduced');
 assert.equal(h.calls.filter(c=>c.path==='/decision/open').length,3,'accepted inspection opens no collector');
 assert(h.calls.every(c=>['/workspace','/decision/open','/decision/submit'].includes(c.path)),'the journey has no execution route');

 // Refresh and uncertain saves preserve typing and never reopen or replay it.
 for(const failure of [false,true]){
  const r=await setup();r.queue.push(workspace(task('cp-1')),initial);await r.run('loadTasks()');
  const input=r.panel.querySelector('textarea');input.value='Keep this unsaved answer';
  const opens=r.calls.filter(c=>c.path==='/decision/open').length;
  if(failure){r.queue.push({ok:false,error:'Uncertain save'});r.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();}
  r.queue.push(workspace(task('cp-1')));await r.run('refreshWorkspace()');
  assert.equal(r.panel.querySelector('textarea'),input);assert.equal(input.value,'Keep this unsaved answer');assert(input.readOnly);
  assert.equal(r.calls.filter(c=>c.path==='/decision/open').length,opens,'refresh never replaces a recoverable form');
  const calls=r.calls.length;r.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();assert.equal(r.calls.length,calls);
 }
 const conflict=await setup();conflict.queue.push(workspace(task('cp-1')),{ok:false,error:'A form is already open'});
 await conflict.run('refreshWorkspace()');
 assert.equal(conflict.panel.children.length,0);assert.match(conflict.status.textContent,/already open/);
 assert.equal(conflict.root.querySelector('button').disabled,false,'deliberate recovery remains available');
 assert.deepEqual(conflict.root.querySelector('p').parentNode.querySelectorAll('b').map(x=>x.textContent),['Saved goal: ','Next: ','Continue form']);
 const multiple=await setup();multiple.queue.push({editable:true,tasks:[task('cp-1'),{...task('cp-2'),task:'B'}]});await multiple.run('loadTasks()');
 assert.equal(multiple.calls.filter(c=>c.path==='/decision/open').length,0,'never choose a task for the user');
 const readonly=await setup();readonly.queue.push({editable:false,tasks:[task('cp-1')]});await readonly.run('loadTasks()');
 assert.equal(readonly.calls.filter(c=>c.path==='/decision/open').length,0,'read-only mode never opens a decision');
 const stale=await setup();stale.queue.push(workspace({...task('cp-1'),available:false,saved_request:{...task('cp-1').saved_request,fresh:false,freshness_note:'Changed inputs'}}));await stale.run('loadTasks()');
 assert.equal(stale.calls.filter(c=>c.path==='/decision/open').length,0,'stale input remains inspection only');
 const paths=await setup();const scope=questions('scope-cp',['Which exact files are in scope?']);scope.display.field_map={answer_0:'scope'};
 paths.run(`renderDecision(${JSON.stringify(scope)})`);
 assert.equal(paths.panel.querySelector('textarea').className,'technical-input','only owner-identified technical fields use monospace');
 assert.equal(paths.panel.querySelector('textarea').value,'');
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
