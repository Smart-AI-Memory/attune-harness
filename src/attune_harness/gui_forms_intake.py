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
fieldset{border:0;margin:0;padding:0}label{display:block;margin:16px 0 6px;font-weight:600}
textarea,select{box-sizing:border-box;width:100%;padding:10px;border:1px solid #869a8a;border-radius:6px;font:inherit;background:white;color:#263c30}
textarea{min-height:86px;resize:vertical}select{white-space:normal}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.55 system-ui;background:#f5f6f2;padding:16px;border-radius:6px}
.action-row{border-top:1px solid #dce4da;margin-top:16px;padding-top:16px}.action-row p{margin-bottom:8px}
button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #c18529;outline-offset:3px}
#form-panel button{margin-top:12px}#form-panel small{display:block;margin:8px 0;color:#4b6353}
@media(max-width:600px){#decisions{padding:16px}#form-panel:not(:empty){padding:16px}header{padding:12px 16px}}
"""

INTAKE_SCRIPT = r"""
const panel=document.querySelector('#form-panel'),tasks=document.querySelector('#tasks');
let busy=false,expired=false;
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
 try{const data=await api('/workspace');tasks.replaceChildren();document.querySelector('#decisions').hidden=false;
 for(const task of data.tasks){
  const card=node('article',undefined,tasks);card.className='task-card';node('h2',task.heading||task.status,card);node('p',task.label,card);node('p',task.note,card);
  if(data.editable&&task.available){const open=node('button','Open current form',card);open.type='button';open.onclick=()=>act(async()=>{
   const shown=await api('/decision/open',{task:task.task,checkpoint:task.checkpoint});renderDecision(shown);
   status.textContent='Current decision retained. Review before responding.';
  });}
 }
 return true;
 }catch(e){status.textContent='Decision inspection failed. '+e.message;return false;}
}
async function act(operation){
 if(busy)return;busy=true;const disabled=new Map(Array.from(document.querySelectorAll('button'),b=>[b,b.disabled]));disabled.forEach((_,b)=>b.disabled=true);
 try{await operation();}catch(e){expirePanel('Action not confirmed. Keep these answers and inspect saved state before continuing; this response will not be replayed.');status.textContent='Action not confirmed. '+e.message+' Refresh saved state before continuing.';}
 finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=(expired&&panel.contains(b))||disabled.get(b)||false);}
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
function renderDecision(shown){
 expired=false;
 panel.replaceChildren();const display=shown.display;
 const title=node('h2',display.kind==='spec'?'Review draft intent':display.title,panel);title.tabIndex=-1;title.focus();
 node('small','Bound to checkpoint '+shown.checkpoint.slice(0,12)+'. Opening another form or restarting expires this decision.',panel);
 if(display.kind==='spec'){
  const summary=shown.summary,intent=summary.intent;
  node('h3','Goal',panel);node('p',intent.goal,panel);
  for(const [key,label] of [['scope','Files in scope'],['acceptance','Done when'],['constraints','Constraints'],['context','Context']]){
   if(intent[key].length){node('h3',label,panel);const list=node('ul',undefined,panel);for(const item of intent[key])node('li',item,list);}
  }
  for(const question of intent.questions){
   node('h3',question.question,panel);
   node('small',question.material?'Required for acceptance':'Optional question',panel);
   node('p',question.answer===null?'Not answered':question.answer,panel);
  }
  for(const choice of summary.choices){
   node('h3',choice.question,panel);const option=choice.options.find(o=>o.id===choice.selected);
   node('p',option?option.proposal:'Undecided',panel);
   if(option){node('p','Rationale: '+option.rationale+' Counter-case: '+option.counter_case,panel);}
  }
  node('small','Authoring format: '+summary.authoring.tier,panel);
  if(summary.effects){const effects=node('details',undefined,panel);node('summary','Configured file effects and checks',effects);node('pre',JSON.stringify(summary.effects,null,2),effects);}
 }
 const details=node('details',undefined,panel);node('summary','Read retained owner decision',details);node('pre',display.markdown,details);
 if(display.kind==='questions'){
  const form=node('form',undefined,panel),inputs=[];
  node('p','Answer what you know. You can save partial answers; Harness will ask only what remains.',form);
  for(const field of display.definition.fields){
   const id='field-'+field.id;const label=node('label',field.text,form);label.htmlFor=id;
   let input;
   if(field.type==='single_select'){input=node('select',undefined,form);node('option','Choose an option…',input).value='';
    for(const text of field.options){node('option',text,input).value=text;}
   }else if(field.type==='text_input'){input=node('textarea',undefined,form);}
   else{node('p','This field requires the CLI collector.',form);return;}
   input.id=id;input.name=field.id;input.setAttribute('data-recovery-label',field.text);inputs.push([field.id,input]);
  }
  const save=node('button','Save answers',form);save.type='submit';
  form.onsubmit=e=>{e.preventDefault();if(expired)return;const answers=Object.fromEntries(inputs.filter(([,input])=>input.value.trim()).map(([key,input])=>[key,input.value]));
   if(!Object.keys(answers).length){status.textContent='Enter at least one answer to save.';return;}
   act(()=>submit(shown,{answers}));};
 }else{
  // Owner markdown contains the actual intent, readiness and review evidence.
  details.open=display.actions.length===0;
  node('p','Choose explicitly. These controls record an intent decision only; execution remains a separate step.',panel);
  for(const action of display.actions){
   const row=node('div',undefined,panel);row.className='action-row';
   node('p',action.consequence||'Record this response to the current decision.',row);
   const labels={approve_task:'Accept this intent',redo_task:'Keep draft for reconsideration'};
   const choose=node('button',labels[action.id]||action.label,row);choose.type='button';
   choose.onclick=()=>act(()=>submit(shown,{action:action.id,confirmed:true}));
  }
  if(!display.actions.length)node('p','The owner has no available action. Inspect the blocking evidence above.',panel);
 }
}

refreshWorkspace();
"""
