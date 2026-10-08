/* Saved disclosures inspect owner data without creating a decision or replaying input. */
const assert=require('node:assert/strict');
const {setup,flush}=require('./gui_intake_summary.cjs');
const intent={goal:'Literal <script> text',acceptance:['Each saved task shows its next decision'],scope:['source.py'],constraints:['No implementation or model calls'],context:['Training example'],questions:[]};
const saved={task_id:'owner-id',revision:2,checkpoint:'saved-cp',intent,choices:[],authoring:{tier:'prompt'},fresh:true,freshness_note:'',accepted:true};
(async()=>{
 const h=await setup();
 h.queue.push({editable:false,tasks:[{task:'A',heading:'Intent accepted',label:intent.goal,note:'Execution remains separate.',available:false,saved_request:saved}]});
 await h.run('loadTasks()');
 const view=h.root.querySelector('.saved-request');assert(view);assert.equal(view.open,false);
 assert.equal(view.querySelector('summary').textContent,'View accepted request');
 assert.match(view.textContent,/source.py/);assert.match(view.textContent,/No implementation or model calls/);assert.match(view.textContent,/Saved revision 2/);
 assert(view.textContent.includes(intent.goal));assert(!view.querySelector('script'));
 assert(!view.querySelector('button'));assert.equal(h.calls.filter(c=>c.opts.method==='POST').length,0);
 const details=view.querySelector('details');assert.equal(details.open,false);assert.match(details.textContent,/owner-id.*saved-cp/s);
 h.queue.push({editable:true,tasks:[{task:'A',heading:'Accepted intent — inputs changed',label:intent.goal,note:'Historical acceptance.',available:false,saved_request:{...saved,fresh:false,freshness_note:'<script> changed input'}}]});
 await h.run('loadTasks()');
 const card=h.root.querySelector('article'),warning=card.children.find(e=>e.getAttribute('role')==='status');
 assert(warning);assert(card.children.indexOf(warning)<card.children.indexOf(card.querySelector('.saved-request')),'staleness must remain visible outside the collapsed summary');
 assert.match(card.textContent,/Saved inputs have changed/);assert(!card.querySelector('script'));
 assert(!card.querySelector('button'));assert.equal(h.calls.filter(c=>c.opts.method==='POST').length,0);
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
