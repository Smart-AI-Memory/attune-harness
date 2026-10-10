"""Browser controls for owner-selected forms; all untrusted text uses textContent."""

INTAKE_PAGE = ('<section id="decisions" hidden aria-labelledby="decision-heading">'
             '<div><p class="eyebrow">DRAFT INTAKE · INTENT APPROVAL</p>'
             '<h1 id="decision-heading">Saved work</h1>'
             '<p>Harness chooses the form from saved work. Saving answers keeps a draft. '
             'Approving the work request records your decision only; it does not start the work.</p></div>'
             '<p>Your answers help shape a clear work request for the AI: what to accomplish, '
             'what context matters, and how to judge success.</p>'
             '<details><summary>How this becomes a prompt</summary>'
             '<p>A well-prepared prompt separates the goal, context, constraints, and success criteria. '
             'XML tags can label these sections so they are easier to identify and review. '
             'Clear content still matters: tags cannot supply missing facts or resolve an unclear goal.</p>'
             '<p>Harness distinguishes plain prompts, XML-enhanced prompts, and fuller specifications '
             'according to the work’s requirements. You can answer in ordinary language.</p>'
             '<p>Illustrative XML format:</p><pre class="technical-input">&lt;goal&gt;Group saved work by the decision it needs&lt;/goal&gt;\n'
             '&lt;success&gt;Each saved task shows its next decision&lt;/success&gt;</pre>'
             '<p>This example explains structure; it is not a submitted answer or an execution grant.</p></details>'
             '<div id="tasks"></div><div id="form-panel"></div></section>')

FORM_STYLE = """
#decisions{padding:24px;max-width:1040px;margin:auto}
h1{font-size:28px;margin:8px 0}h2{font-size:20px}.eyebrow{font-size:11px;letter-spacing:.09em}
#tasks{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}
.task-card{background:white;border:1px solid #dce4da;border-radius:10px;padding:16px;flex:1;min-width:220px}
.task-card p{margin:8px 0;overflow-wrap:anywhere}.task-card h2{margin:0;overflow-wrap:anywhere}
#form-panel:not(:empty){background:white;border:1px solid #b8cdbb;border-radius:12px;padding:24px}
.saved-answers{overflow-wrap:anywhere}
.approval-answers,.approval-blockers{overflow-wrap:anywhere}
.saved-answers p,.saved-answers li,.approval-answers p,.approval-answers li,.saved-goal{white-space:pre-wrap}
.technical-input,.owner-record{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
fieldset{border:0;margin:0;padding:0}label{display:block;margin:16px 0 6px;font-weight:600}
textarea,select{box-sizing:border-box;width:100%;padding:10px;border:1px solid #869a8a;border-radius:6px;font:inherit;background:white;color:#263c30}
textarea{min-height:86px;resize:vertical}select{white-space:normal}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.55 system-ui;background:#f5f6f2;padding:16px;border-radius:6px}
.action-row{border-top:1px solid #dce4da;margin-top:16px;padding-top:16px}.action-row p{margin-bottom:8px}
button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #c18529;outline-offset:3px}
#form-panel button{margin-top:12px}#form-panel small{display:block;margin:8px 0;color:#4b6353}
#browser-tip:not([hidden]){flex-basis:100%;padding:10px 12px;background:#e7efe5;border-radius:7px}
@media(max-width:600px){#decisions{padding:16px}#form-panel:not(:empty){padding:16px}header{padding:12px 16px}}
"""

INTAKE_SCRIPT = r"""
const panel=document.querySelector('#form-panel'),tasks=document.querySelector('#tasks');
let busy=false,expired=false,automaticOpenNotice='';
let formView=null,formRecovery=null,reloadRecovery=false,recoveryBlocked=false,releaseView=null,viewGone=false;
const recoveryKey='attune-gui-form';
function rememberForm(shown,blocked=false){
 if(viewGone)return;
 formRecovery=shown?{task:shown.task,checkpoint:shown.checkpoint,decision:shown.decision}:null;
 recoveryBlocked=blocked;
 if(!formView)return;
 // Write the no-replay barrier before submitting. If storage becomes unavailable,
 // refuse that submission rather than leave an old recovery identity behind.
 sessionStorage.setItem(recoveryKey,JSON.stringify({session:token,view:formView,recovery:formRecovery,blocked}));
}
async function claimFormView(){
 try{
  if(typeof sessionStorage==='undefined')return;
  const stored=JSON.parse(sessionStorage.getItem(recoveryKey)||'null');
  recoveryBlocked=stored?.session===token&&stored?.blocked===true;
  reloadRecovery=recoveryBlocked;
  if(typeof navigator==='undefined'||!navigator.locks||typeof crypto==='undefined'||!crypto.randomUUID||typeof performance==='undefined')return;
  // New tabs may inherit sessionStorage. Only a reload can reuse its identity;
  // an exclusive live-page lock also refuses a copied identity in another tab.
  const reload=performance.getEntriesByType('navigation')[0]?.type==='reload';
  const saved=reload&&stored?.session===token&&typeof stored.view==='string'&&/^[A-Za-z0-9_-]{32,128}$/.test(stored.view)?stored:null;
  const candidate=saved?.view||crypto.randomUUID();
  const held=await new Promise(resolve=>{
   navigator.locks.request('attune-form-view-'+candidate,{ifAvailable:true},lock=>{
    if(!lock||viewGone){resolve(false);return;}
    return new Promise(release=>{releaseView=release;resolve(true);});
   }).catch(()=>resolve(false));
  });
  if(viewGone){if(releaseView)releaseView();return;}
  if(!held){
   recoveryBlocked=true;reloadRecovery=true;
   // A rejected copied identity must not become usable when its owner leaves.
   sessionStorage.setItem(recoveryKey,JSON.stringify({session:token,view:crypto.randomUUID(),recovery:null,blocked:true}));
   return;
  }
  formView=candidate;formRecovery=saved?.recovery||null;recoveryBlocked=saved?.blocked===true;
  reloadRecovery=!!formRecovery||recoveryBlocked;
  sessionStorage.setItem(recoveryKey,JSON.stringify({session:token,view:formView,recovery:formRecovery,blocked:recoveryBlocked}));
 }catch(e){formView=null;formRecovery=null;reloadRecovery=recoveryBlocked;if(releaseView)releaseView();}
}
if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('pagehide',()=>{
 viewGone=true;
 expirePanel('This view is no longer active. Reload the page to continue. Unsaved answers are not restored.');
 document.querySelectorAll('button').forEach(b=>b.disabled=true);
 formView=null;formRecovery=null;reloadRecovery=false;if(releaseView)releaseView();
},{once:true});
function openPayload(task,automatic=false){
 return {task:task.task,checkpoint:task.checkpoint,...(automatic?{replace:false}:{}),...(formView?{view:formView}:{})};
}
const browserButton=document.querySelector('#browser-open'),browserTip=document.querySelector('#browser-tip');
let workspaceReady=false;
function syncBrowserButton(){if(browserButton)browserButton.disabled=busy||viewGone||!workspaceReady;}
if(browserButton){
 const narrow=window.matchMedia('(max-width:600px)');
 const recommend=()=>{if(browserTip)browserTip.hidden=!narrow.matches;};
 recommend();narrow.addEventListener('change',recommend);
 browserButton.addEventListener('click',event=>{
  if(!event.isTrusted||busy||!workspaceReady)return;
  act(async()=>{
   rememberForm(null,true);
   expirePanel('Opening another view. This form is now read-only; unsaved answers remain here for copying. Open the current form in the new view to continue.');
   try{const result=await api('/browser/open',{confirmed:true});status.textContent=result.message;}
   catch(e){status.textContent='Browser opening could not be confirmed. Copy the private launcher link from Terminal into your browser. Unsaved answers stay here for copying.';}
  });
 });
}
function expirePanel(message){
 expired=true;
 if(!panel.children.length)return;
 for(const input of panel.querySelectorAll('textarea'))input.readOnly=true;
 for(const control of panel.querySelectorAll('button,select'))control.disabled=true;
 const answers=Array.from(panel.querySelectorAll('textarea,select')).filter(input=>input.value).map(input=>(input.getAttribute('data-recovery-label')||input.name)+': '+input.value);
 if(answers.length&&!panel.querySelector('.retained-answers')){const recovery=node('pre',answers.join('\n\n'),panel);recovery.className='retained-answers';recovery.setAttribute('aria-label','Retained answers for copying');}
 let notice=panel.querySelector('.expired-notice');
 if(!notice){notice=node('p','This previous form is now read-only. Answers remain available for copying. Deliberately open the current form or preview to continue; answers are never replayed.',panel);notice.className='expired-notice';notice.setAttribute('role','status');}
 if(message)notice.textContent=message;
}
function node(tag,text,parent){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(parent)parent.append(el);return el;}
async function api(path,payload){
 if(viewGone)throw Error('This view is no longer active. Reload the page to continue.');
 const res=await fetch(path,{method:payload?'POST':'GET',headers:{'X-Attune-Session':token||'',...(payload?{'Content-Type':'application/json'}:{})},...(payload?{body:JSON.stringify(payload)}:{}),cache:'no-store'});
 if(!res.ok)throw Error(await res.text());const value=await res.json();
 if(viewGone)throw Error('This view is no longer active. Reload the page to continue.');return value;
}
async function loadTasks({advance=false}={}){
 automaticOpenNotice='';
 try{const data=await api('/workspace');workspaceReady=true;syncBrowserButton();tasks.replaceChildren();document.querySelector('#decisions').hidden=false;
 const presentations=new Map();
 for(const task of data.tasks){
  const card=node('article',undefined,tasks);card.className='task-card';node('h2',task.heading||task.status,card);
  const goal=node('p',undefined,card);goal.className='saved-goal';
  if(task.saved_request){node('b','Saved goal: ',goal);node('span',task.saved_request.intent.goal||'Not answered',goal);}else goal.textContent=task.label;
  const note=node('p',task.note,card);
  if(task.saved_request){
   const saved=task.saved_request;
   if(!saved.fresh){const warning=node('p','Saved inputs have changed. '+saved.freshness_note,card);warning.setAttribute('role','status');}
   const view=node('details',undefined,card);view.className='saved-request';
   node('summary',saved.accepted?'View accepted request':'View saved request',view);view.open=saved.accepted;
   node('p','Saved revision '+saved.revision+'. Refresh saved state to inspect the latest record.',view);
   renderIntent(saved,view);
   node('p',saved.accepted?'Intent accepted. Implementation and paid dispatch are not authorized by this decision.':'Saving answers does not accept intent. Review the current form before deciding.',view);
   const identity=node('details',undefined,view);node('summary','Technical details',identity);identity.open=false;
   node('pre','Task '+saved.task_id+'\nCheckpoint '+saved.checkpoint+'\nAuthoring format: '+saved.authoring.tier,identity).className='technical-input';
  }
  if(data.editable&&task.available){const tip=node('p',undefined,card);node('b','Next: ',tip);node('span','Click ',tip);node('b',task.action_label||'Open current form',tip);node('span','. '+(task.action_tip||'Review the current form before responding.'),tip);const open=node('button',task.action_label||'Open current form',card);open.type='button';open.onclick=()=>act(async()=>{
   const shown=await api('/decision/open',openPayload(task));renderDecision(shown);
   open.hidden=true;tip.hidden=true;
   note.textContent='The current form is ready. Viewing it does not accept intent or authorize execution.';
   status.textContent='Current form displayed. Review before responding.';
  });presentations.set(task.task,{tip,open,note});}
 }
 // A single eligible draft can show its form directly. Never choose among
 // tasks, replace another view's collector, or discard unconfirmed typing.
 const task=data.tasks.length===1?data.tasks[0]:null;
 if(advance&&task?.saved_request?.accepted)panel.replaceChildren();
 if(data.editable&&task?.available&&task.status==='draft'&&task.saved_request&&(advance||!panel.children.length)){
  const controls=presentations.get(task.task);controls.open.disabled=true;
  try{
   let shown;
   if(recoveryBlocked)throw Error('A previous form was submitted or left. Inspect saved answers, then deliberately reopen the current form.');
   if(reloadRecovery){
    if(formRecovery.task!==task.task||formRecovery.checkpoint!==task.checkpoint)throw Error('Saved form recovery changed; deliberately reopen the current form.');
    shown=await api('/decision/restore',{...formRecovery,view:formView});
   }else shown=await api('/decision/open',openPayload(task,true));
   renderDecision(shown);controls.open.hidden=true;controls.tip.hidden=true;
   controls.note.textContent='The current form is ready. Viewing it does not accept intent or authorize execution.';
  }catch(e){
   recoveryBlocked=true;try{rememberForm(null,true);}catch(storageError){}
   automaticOpenNotice='The current form was not opened. '+e.message;
  }finally{reloadRecovery=false;controls.open.disabled=false;}
 }
 return true;
 }catch(e){workspaceReady=false;syncBrowserButton();status.textContent='Decision inspection failed. '+e.message;return false;}
}
async function act(operation){
 if(busy||viewGone)return;busy=true;const disabled=new Map(Array.from(document.querySelectorAll('button'),b=>[b,b.disabled]));disabled.forEach((_,b)=>b.disabled=true);
 try{await operation();}catch(e){expirePanel('Action not confirmed. Keep these answers and inspect saved state before continuing; this response will not be replayed.');status.textContent='Action not confirmed. '+e.message+' Refresh saved state before continuing.';}
 finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=viewGone||(expired&&panel.contains(b))||disabled.get(b)||false);syncBrowserButton();}
}
async function submit(shown,response){
 if(expired)return;
 rememberForm(null,true);
 expirePanel('Submitting this response. This form is now read-only; answers remain available for copying.');
 const result=await api('/decision/submit',{task:shown.task,checkpoint:shown.checkpoint,decision:shown.decision,response});
 rememberForm(null);
 const title=panel.querySelector('h2');if(title&&typeof result.heading==='string')title.textContent=result.heading;
 expirePanel(result.message+' This previous form is now read-only.');
 await refreshWorkspace(result.message,{advance:true});
}
async function refreshWorkspace(message='',options={}){
 expirePanel();
 const loaded=await loadTasks(options);
 if(loaded)status.textContent=(message||'Forms refreshed. Viewing does not accept intent or authorize execution.')+(automaticOpenNotice?' '+automaticOpenNotice:'');
}
function renderSavedAnswers(summary){
 const intent=summary?.intent;if(!intent)return;
 const entries=[];
 if(typeof intent.goal==='string'&&intent.goal.trim())entries.push(['Saved goal',[intent.goal]]);
 if(intent.acceptance?.length)entries.push(['Done when',intent.acceptance]);
 for(const question of intent.questions||[]){
  if(typeof question.answer==='string'&&question.answer.trim())entries.push([question.question,[question.answer]]);
 }
 for(const choice of summary.choices||[]){
  const option=choice.options.find(o=>o.id===choice.selected);
  if(option)entries.push([choice.question,[option.proposal]]);
 }
 if(!entries.length)return;
 const saved=node('section',undefined,panel);saved.className='saved-answers';saved.setAttribute('aria-label','Saved answers');
 node('h3','Saved answers',saved);
 for(const [label,answers] of entries){
  node('h4',label,saved);
  if(label==='Done when'){const list=node('ul',undefined,saved);for(const answer of answers)node('li',answer,list);}
  else node('p',answers[0],saved);
 }
}
function renderIntent(summary,parent){
 const intent=summary.intent;
 const answers=node('section',undefined,parent);answers.className='approval-answers';answers.setAttribute('aria-label','Questions and answers');
 node('h3','What should this work accomplish?',answers);node('p',intent.goal||'Not answered',answers);
 for(const [key,label] of [['acceptance','What observable result establishes success?'],['scope','Which exact files are in scope?'],['constraints','What constraints should guide this work?'],['context','What context should inform this work?']]){
  if(intent[key].length){node('h3',label,answers);const list=node('ul',undefined,answers);for(const item of intent[key]){const value=node('li',item,list);if(key==='scope')value.className='technical-input';}}
 }
 for(const question of intent.questions){
  node('h3',question.question,answers);node('small',question.material?'Required for acceptance':'Optional question',answers);
  node('p',question.answer===null?'Not answered':question.answer,answers);
 }
 for(const choice of summary.choices){
  node('h3',choice.question,answers);const option=choice.options.find(o=>o.id===choice.selected);
  node('p',option?option.proposal:'Undecided',answers);
  if(option)node('p','Rationale: '+option.rationale+' Counter-case: '+option.counter_case,answers);
 }
}
function renderDecision(shown){
 if(viewGone)return;
 rememberForm(shown);
 expired=false;
 panel.replaceChildren();const display=shown.display;
 const title=node('h2',display.kind==='spec'?'Review your answers':display.title,panel);title.tabIndex=-1;title.focus();
 const checkpoint=node('small','Bound to checkpoint '+shown.checkpoint.slice(0,12)+'. Opening another form or restarting expires this decision.',display.kind==='questions'?panel:undefined);
 if(display.kind==='spec'){
  const summary=shown.summary;
  renderIntent(summary,panel);
  if(summary.blocking_reasons?.length){
   const blocked=node('section',undefined,panel);blocked.className='approval-blockers';blocked.setAttribute('aria-label','Approval blocked');
   node('h3','Approval is blocked',blocked);const reasons=node('ul',undefined,blocked);for(const reason of summary.blocking_reasons)node('li',reason,reasons);
  }
 }
 const details=node('details',undefined,panel);node('summary','Technical details',details);details.open=false;
 const owner=node('pre',display.markdown,details);owner.className='owner-record';
 if(display.kind!=='questions'){
  details.append(checkpoint);
  if(display.kind==='spec'){
   node('small','Authoring format: '+shown.summary.authoring.tier,details);
   if(shown.summary.effects){node('h3','Configured file effects and checks',details);node('pre',JSON.stringify(shown.summary.effects,null,2),details).className='technical-input';}
  }
 }
 if(display.kind==='questions'){
  renderSavedAnswers(shown.summary);
  const instructions=node('p','Answer what you know. You can save partial answers. Harness will ask only what remains. After saving, continue with the remaining questions or review your answers.',panel);instructions.id='answer-instructions';
  const form=node('form',undefined,panel),inputs=[];
  details.querySelector('summary').textContent='Technical details (optional)';details.open=false;panel.append(details);
  for(const field of display.definition.fields){
   const id='field-'+field.id;const label=node('label',field.text,form);label.htmlFor=id;
   let input;
   if(field.type==='single_select'){input=node('select',undefined,form);node('option','Choose an option…',input).value='';
    for(const text of field.options){node('option',text,input).value=text;}
   }else if(field.type==='text_input'){input=node('textarea',undefined,form);}
   else{node('p','This field requires the CLI collector.',form);return;}
   if(display.field_map?.[field.id]==='scope')input.className='technical-input';
   input.id=id;input.name=field.id;input.setAttribute('data-recovery-label',field.text);inputs.push([field.id,input]);
   const hint=node('small',(field.required===true?'Required before intent acceptance. ':'')+'You can leave this blank when saving partial answers.',form);hint.id=id+'-hint';
   input.setAttribute('aria-describedby',instructions.id+' '+hint.id);
  }
  const save=node('button','Save answers',form);save.type='submit';
  form.onsubmit=e=>{e.preventDefault();if(expired)return;const answers=Object.fromEntries(inputs.filter(([,input])=>input.value.trim()).map(([key,input])=>[key,input.value]));
   if(!Object.keys(answers).length){status.textContent='Enter at least one answer to save.';return;}
   act(()=>submit(shown,{answers}));};
 }else{
  node('p','Review this work request, then choose whether to approve it or keep it as a draft. Neither option starts the work.',panel);
  for(const action of display.actions){
   const row=node('div',undefined,panel);row.className='action-row';
   const consequences={approve_task:'Approve the work request shown in this review, including its goal, success criteria, scope, context, constraints, and recorded choices. This records your approval only. It does not start the work.',redo_task:'Keep this work request as an unapproved draft so you can reconsider it. This does not start the work.'};
   node('p',consequences[action.id]||action.consequence||'Record this response to the current decision.',row);
   const labels={approve_task:'Approve this work request',redo_task:'Keep as draft'};
   const choose=node('button',labels[action.id]||action.label,row);choose.type='button';
   choose.onclick=()=>act(()=>submit(shown,{action:action.id,confirmed:true}));
  }
  if(!display.actions.length){const guidance=node('p','No approval action is available in this view. Resolve the blocking reasons or expand ',panel);node('b','Technical details',guidance);node('span',' to inspect the full decision before continuing.',guidance);}
 }
}

act(async()=>{await claimFormView();await refreshWorkspace();});
"""
