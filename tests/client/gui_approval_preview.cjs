/* Check readable authoritative answers, hidden protocol, visible owner blockers. */
const assert=require('node:assert/strict');
const {setup,flush}=require('./gui_intake_summary.cjs');
const owner='## Retained decision\nActions: approve_task\n```json\n{"__elicitation_response__":true,"action":"approve_task"}\n```';
const intent={goal:'Accurate <script> text stays literal',acceptance:['Every control works','Claims have receipts'],scope:['source.py'],constraints:['Keep saved work'],context:['Use evidence'],
 questions:[{question:'Who uses this?',answer:'CLI users',material:true},{question:'Anything else?',answer:null,material:false}]};
const summary={intent,choices:[{question:'Which format?',selected:'jsonl',options:[{id:'jsonl',proposal:'JSON lines',rationale:'Streams results',counter_case:'Different shape'}]}],
 authoring:{tier:'bounded'},effects:{writes:[{path:'source.py',action:'modify'}],checks:[{control:{id:'unit-tests'}}]},blocking_reasons:[]};
const shown={task:'A',checkpoint:'exact-cp',decision:'one-use',summary,display:{kind:'spec',title:'Owner gate',markdown:owner,
 actions:[{id:'approve_task',label:'Accept',consequence:'Record intent'},{id:'redo_task',label:'Reconsider',consequence:'Keep draft'}]}};
const render=(h,value=shown)=>h.run(`renderDecision(${JSON.stringify(value)})`);
const outside=(panel,details)=>panel.children.filter(c=>c!==details).map(c=>c.textContent).join('\n');
(async()=>{
 const h=await setup();render(h);
 const answers=h.panel.querySelector('.approval-answers'),details=h.panel.querySelector('details');
 assert(answers,'approval must show authoritative questions and answers');
 assert.equal(answers.getAttribute('aria-label'),'Questions and answers');
 assert.deepEqual(answers.querySelectorAll('h3').map(e=>e.textContent),['What should this work accomplish?','What observable result establishes success?','Which exact files are in scope?','What constraints should guide this work?','What context should inform this work?','Who uses this?','Anything else?','Which format?']);
 assert.equal(answers.querySelector('p').textContent,intent.goal);assert(!answers.querySelector('script'));
 assert.deepEqual(answers.querySelectorAll('li').map(e=>e.textContent),[...intent.acceptance,...intent.scope,...intent.constraints,...intent.context]);
 assert.match(answers.textContent,/CLI users/);assert.match(answers.textContent,/Not answered/);assert.match(answers.textContent,/JSON lines/);
 assert.equal(details.open,false);assert.equal(details.querySelector('summary').textContent,'Technical details');
 assert.equal(details.querySelector('.owner-record').textContent,owner,'full owner record remains unchanged');
 assert.equal(details.querySelectorAll('pre')[1].textContent,JSON.stringify(summary.effects,null,2));
 const visible=outside(h.panel,details);
 for(const technical of ['__elicitation_response__','approve_task','Authoring format:','Bound to checkpoint','unit-tests','"writes"'])assert(!visible.includes(technical),technical+' leaked outside disclosure');
 assert(details.textContent.includes('Authoring format: bounded'));assert(details.textContent.includes('Bound to checkpoint exact-cp'));
 assert(h.panel.children.indexOf(details)>h.panel.children.indexOf(answers));
 assert.deepEqual(h.panel.querySelectorAll('button').map(e=>e.textContent),['Approve this work request','Keep as draft']);
 const choices=h.panel.querySelectorAll('.action-row');
 assert.match(visible,/Neither option starts the work/);
 assert.match(choices[0].querySelector('p').textContent,/work request shown in this review.*goal, success criteria, scope, context, constraints, and recorded choices.*records your approval only.*does not start the work/);
 assert.match(choices[1].querySelector('p').textContent,/unapproved draft.*reconsider.*does not start the work/);
 assert.notEqual(choices[0].querySelector('p').textContent,choices[1].querySelector('p').textContent,'each choice explains its own consequence');
 assert(!visible.includes('Record this response'),'known intent choices must not use the generic owner fallback');
 assert.equal(h.panel.querySelector('.approval-blockers'),null,'raw Markdown must not invent structured blockers');
 const first=h.panel.querySelector('button');h.queue.push({ok:false,error:'409 changed'});first.onclick();await flush();
 assert(first.disabled);assert.equal(h.panel.querySelector('.approval-answers'),answers,'uncertain response keeps readable answers');
 assert.equal(details.open,false);assert.equal(h.calls.filter(c=>c.path==='/decision/submit').length,1);
 assert.deepEqual(JSON.parse(h.calls.find(c=>c.path==='/decision/submit').opts.body),{task:'A',checkpoint:'exact-cp',decision:'one-use',response:{action:'approve_task',confirmed:true}});
 first.onclick();await flush();assert.equal(h.calls.filter(c=>c.path==='/decision/submit').length,1,'expired approval never replays');
 const kept=await setup();render(kept);kept.queue.push({message:'Kept as draft'},{editable:true,tasks:[]});
 kept.panel.querySelectorAll('button')[1].onclick();await flush();
 assert.deepEqual(JSON.parse(kept.calls.find(c=>c.path==='/decision/submit').opts.body),{task:'A',checkpoint:'exact-cp',decision:'one-use',response:{action:'redo_task',confirmed:true}},'keeping a draft retains the owner action and current decision binding');
 for(const reason of ['A planner assignment is required','Unavailable required control: tests','Acknowledge <script> this receipt']){
  const blocked=await setup();render(blocked,{...shown,summary:{...summary,blocking_reasons:[reason]},display:{...shown.display,actions:[]}});
  const technical=blocked.panel.querySelector('details'),reasons=blocked.panel.querySelector('.approval-blockers');
  assert.equal(reasons.getAttribute('aria-label'),'Approval blocked');assert.equal(reasons.querySelector('li').textContent,reason);assert(!reasons.querySelector('script'));
  assert(blocked.panel.children.indexOf(reasons)<blocked.panel.children.indexOf(technical));assert.equal(technical.open,false);
  assert(!technical.querySelector('summary').textContent.includes('optional'));assert.equal(blocked.panel.querySelectorAll('button').length,0);
  assert(outside(blocked.panel,technical).includes(reason),'readiness reason must remain visible while protocol is collapsed');
  assert.equal(blocked.calls.filter(c=>c.opts.method==='POST').length,0);
 }
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
