"""Browser controls for owner-selected forms; all untrusted text uses textContent."""

INTAKE_PAGE = ('<section id="decisions" hidden aria-labelledby="decision-heading">'
             '<div><p class="eyebrow">DRAFT INTAKE · INTENT APPROVAL</p>'
             '<h1 id="decision-heading">Saved work</h1>'
             '<p>Harness chooses the form from saved work. Saving answers does not approve the plan. '
             'Accepting intent does not run a model or build.</p></div>'
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
let busy=false,expired=false;
const browserButton=document.querySelector('#browser-open'),browserTip=document.querySelector('#browser-tip');
let workspaceReady=false;
function syncBrowserButton(){if(browserButton)browserButton.disabled=busy||!workspaceReady;}
if(browserButton){
 const narrow=window.matchMedia('(max-width:600px)');
 const recommend=()=>{if(browserTip)browserTip.hidden=!narrow.matches;};
 recommend();narrow.addEventListener('change',recommend);
 browserButton.addEventListener('click',event=>{
  if(!event.isTrusted||busy||!workspaceReady)return;
  act(async()=>{
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
 const res=await fetch(path,{method:payload?'POST':'GET',headers:{'X-Attune-Session':token||'',...(payload?{'Content-Type':'application/json'}:{})},...(payload?{body:JSON.stringify(payload)}:{}),cache:'no-store'});
 if(!res.ok)throw Error(await res.text());return await res.json();
}
async function loadTasks(){
 try{const data=await api('/workspace');workspaceReady=true;syncBrowserButton();tasks.replaceChildren();document.querySelector('#decisions').hidden=false;
 for(const task of data.tasks){
  const card=node('article',undefined,tasks);card.className='task-card';node('h2',task.heading||task.status,card);node('p',task.label,card);node('p',task.note,card);
  if(data.editable&&task.available){const tip=node('p',undefined,card);node('strong','Tip: ',tip);node('span',task.action_tip||'Open the current form to continue.',tip);const open=node('button',task.action_label||'Open current form',card);open.type='button';open.onclick=()=>act(async()=>{
   const shown=await api('/decision/open',{task:task.task,checkpoint:task.checkpoint});renderDecision(shown);
   status.textContent='Current decision retained. Review before responding.';
  });}
 }
 return true;
 }catch(e){workspaceReady=false;syncBrowserButton();status.textContent='Decision inspection failed. '+e.message;return false;}
}
async function act(operation){
 if(busy)return;busy=true;const disabled=new Map(Array.from(document.querySelectorAll('button'),b=>[b,b.disabled]));disabled.forEach((_,b)=>b.disabled=true);
 try{await operation();}catch(e){expirePanel('Action not confirmed. Keep these answers and inspect saved state before continuing; this response will not be replayed.');status.textContent='Action not confirmed. '+e.message+' Refresh saved state before continuing.';}
 finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=(expired&&panel.contains(b))||disabled.get(b)||false);syncBrowserButton();}
}
async function submit(shown,response){
 if(expired)return;
 expirePanel('Submitting this response. This form is now read-only; answers remain available for copying.');
 const result=await api('/decision/submit',{task:shown.task,checkpoint:shown.checkpoint,decision:shown.decision,response});
 const title=panel.querySelector('h2');if(title&&typeof result.heading==='string')title.textContent=result.heading;
 expirePanel(result.message+' This previous form is now read-only.');
 await refreshWorkspace(result.message);
}
async function refreshWorkspace(message=''){
 expirePanel();
 const loaded=await loadTasks();
 if(loaded)status.textContent=message||'Forms refreshed. Inspection makes no decisions or model calls.';
}
function renderSavedAnswers(summary){
 const intent=summary?.intent;if(!intent)return;
 const entries=[];
 if(typeof intent.goal==='string'&&intent.goal.trim())entries.push(['Goal',[intent.goal]]);
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
function renderDecision(shown){
 expired=false;
 panel.replaceChildren();const display=shown.display;
 const title=node('h2',display.kind==='spec'?'Review your answers':display.title,panel);title.tabIndex=-1;title.focus();
 const checkpoint=node('small','Bound to checkpoint '+shown.checkpoint.slice(0,12)+'. Opening another form or restarting expires this decision.',display.kind==='questions'?panel:undefined);
 if(display.kind==='spec'){
  const summary=shown.summary,intent=summary.intent;
  const answers=node('section',undefined,panel);answers.className='approval-answers';answers.setAttribute('aria-label','Questions and answers');
  node('h3','What should this work accomplish?',answers);node('p',intent.goal,answers);
  for(const [key,label] of [['acceptance','What observable result establishes success?'],['scope','Which exact files are in scope?'],['constraints','What constraints should guide this work?'],['context','What context should inform this work?']]){
   if(intent[key].length){node('h3',label,answers);const list=node('ul',undefined,answers);for(const item of intent[key])node('li',item,list);}
  }
  for(const question of intent.questions){
   node('h3',question.question,answers);
   node('small',question.material?'Required for acceptance':'Optional question',answers);
   node('p',question.answer===null?'Not answered':question.answer,answers);
  }
  for(const choice of summary.choices){
   node('h3',choice.question,answers);const option=choice.options.find(o=>o.id===choice.selected);
   node('p',option?option.proposal:'Undecided',answers);
   if(option){node('p','Rationale: '+option.rationale+' Counter-case: '+option.counter_case,answers);}
  }
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
   if(shown.summary.effects){node('h3','Configured file effects and checks',details);node('pre',JSON.stringify(shown.summary.effects,null,2),details);}
  }
 }
 if(display.kind==='questions'){
  renderSavedAnswers(shown.summary);
  const instructions=node('p','Answer what you know. You can save partial answers; Harness will ask only what remains. After saving, use the next-step button in Saved work to continue.',panel);instructions.id='answer-instructions';
  const form=node('form',undefined,panel),inputs=[];
  details.querySelector('summary').textContent='Technical details (optional)';details.open=false;panel.append(details);
  for(const field of display.definition.fields){
   const id='field-'+field.id;const label=node('label',field.text,form);label.htmlFor=id;
   let input;
   if(field.type==='single_select'){input=node('select',undefined,form);node('option','Choose an option…',input).value='';
    for(const text of field.options){node('option',text,input).value=text;}
   }else if(field.type==='text_input'){input=node('textarea',undefined,form);}
   else{node('p','This field requires the CLI collector.',form);return;}
   input.id=id;input.name=field.id;input.setAttribute('data-recovery-label',field.text);inputs.push([field.id,input]);
   const hint=node('small',(field.required===true?'Required before intent acceptance. ':'')+'You can leave this blank when saving partial answers.',form);hint.id=id+'-hint';
   input.setAttribute('aria-describedby',instructions.id+' '+hint.id);
  }
  const save=node('button','Save answers',form);save.type='submit';
  form.onsubmit=e=>{e.preventDefault();if(expired)return;const answers=Object.fromEntries(inputs.filter(([,input])=>input.value.trim()).map(([key,input])=>[key,input.value]));
   if(!Object.keys(answers).length){status.textContent='Enter at least one answer to save.';return;}
   act(()=>submit(shown,{answers}));};
 }else{
  node('p','Choose explicitly. These controls record an intent decision only; execution remains a separate step.',panel);
  for(const action of display.actions){
   const row=node('div',undefined,panel);row.className='action-row';
   node('p',action.consequence||'Record this response to the current decision.',row);
   const labels={approve_task:'Accept this intent',redo_task:'Keep draft for reconsideration'};
   const choose=node('button',labels[action.id]||action.label,row);choose.type='button';
   choose.onclick=()=>act(()=>submit(shown,{action:action.id,confirmed:true}));
  }
  if(!display.actions.length)node('p','No approval action is available in this view. Resolve the blocking reasons or inspect the full decision in Technical details before continuing.',panel);
 }
}

refreshWorkspace();
"""
