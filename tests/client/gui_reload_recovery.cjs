/* Run the shipped reload path with the existing DOM seam and shared lock model. */
const assert=require('node:assert/strict');
const {setup,flush}=require('./gui_intake_summary.cjs');
const held=new Map();let serial=0;
function browser(type,storage=new Map(),{locks=true,readDenied=false}={}){
 const listeners={},state={writeDenied:false};
 const globals={
  performance:{getEntriesByType(kind){assert.equal(kind,'navigation');return [{type}];}},
  crypto:{randomUUID:()=>`view-${String(++serial).padStart(32,'0')}`},
  window:{addEventListener(name,fn){listeners[name]=fn;}},
  sessionStorage:{getItem(key){if(readDenied)throw Error('Storage unavailable');return storage.get(key)||null;},
   setItem(key,value){if(state.writeDenied)throw Error('Storage unavailable');storage.set(key,value);}},
  navigator:locks?{locks:{request(name,options,fn){
   assert.deepEqual(JSON.parse(JSON.stringify(options)),{ifAvailable:true});
   if(held.has(name))return Promise.resolve(fn(null));
   held.set(name,true);
   return Promise.resolve(fn({name})).finally(()=>held.delete(name));
  }}}:{}
 };
 return {globals,storage,state,leave:async()=>{listeners.pagehide?.();await flush();}};
}
const intent={goal:null,acceptance:[],scope:['source.py'],constraints:['No execution'],context:[],questions:[]};
const goal='My Capitalized goal\nwith a second line';
function workspace(checkpoint,savedGoal=null){return {editable:true,tasks:[{
 task:'A',checkpoint,status:'draft',heading:'Draft saved',available:true,action_label:'Continue form',note:'Saved state',
 saved_request:{task_id:'owner',revision:1,checkpoint,intent:{...intent,goal:savedGoal},choices:[],authoring:{tier:'prompt'},fresh:true,accepted:false}
}]};}
function form(checkpoint,fields,savedGoal=null){return {
 task:'A',checkpoint,decision:'decision-'+checkpoint,
 summary:{intent:{...intent,goal:savedGoal},choices:[],authoring:{tier:'prompt'}},
 display:{kind:'questions',title:'Clarify the work',markdown:'Owner record',definition:{fields:fields.map((text,i)=>({id:'answer_'+i,text,type:'text_input'}))}}
};}
const initial=form('cp-1',['What should this work accomplish?','What observable result establishes success?']);
const remaining=form('cp-2',['What observable result establishes success?'],goal);
const payload=call=>JSON.parse(call.opts.body);
const recovery=b=>JSON.parse(b.storage.get('attune-gui-form'));
(async()=>{
 const first=browser('navigate');
 const h=await setup({globals:first.globals,responses:[workspace('cp-1'),initial]});
 const firstView=recovery(first).view;
 assert.equal(payload(h.calls.at(-1)).replace,false);
 assert.equal(payload(h.calls.at(-1)).view,firstView);
 h.panel.querySelector('textarea').value=goal;
 h.queue.push({message:'Answers saved'},workspace('cp-2',goal),remaining);
 h.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(h.panel.querySelector('.saved-answers').querySelector('p').textContent,goal);
 assert.deepEqual(recovery(first).recovery,{task:'A',checkpoint:'cp-2',decision:'decision-cp-2'});
 assert.equal(recovery(first).blocked,false);
 assert(!JSON.stringify(recovery(first)).includes(goal),'recovery metadata never stores answer text');
 await first.leave();
 assert(h.panel.querySelector('textarea').readOnly,'leaving expires the old page controls');

 const same=browser('reload',first.storage);
 const resumed=await setup({globals:same.globals,responses:[workspace('cp-2',goal),remaining]});
 assert.deepEqual(resumed.calls.map(c=>c.path),['/workspace','/decision/restore']);
 assert.deepEqual(payload(resumed.calls[1]),{task:'A',checkpoint:'cp-2',decision:'decision-cp-2',view:firstView});
 assert.equal(resumed.panel.querySelector('textarea').value,'','reload never remaps a saved positional answer');
 assert.equal(resumed.panel.querySelector('label').textContent,'What observable result establishes success?');
 assert.equal(resumed.panel.querySelector('.saved-answers').querySelector('p').textContent,goal);
 assert.equal(resumed.root.querySelectorAll('button').find(b=>b.textContent==='Continue form').hidden,true);
 assert.equal(resumed.calls.filter(c=>c.path==='/decision/submit').length,0,'restoration never saves, approves or executes');

 // A duplicated tab inherits storage, but its navigation creates a new view.
 const copied=browser('navigate',new Map(same.storage));
 const duplicate=await setup({globals:copied.globals,responses:[workspace('cp-2',goal),{ok:false,error:'A form is already open'}]});
 assert.notEqual(recovery(copied).view,firstView);
 assert.deepEqual(duplicate.calls.map(c=>c.path),['/workspace','/decision/open']);
 assert.equal(payload(duplicate.calls[1]).replace,false);
 assert.equal(duplicate.panel.children.length,0);
 await copied.leave();

 // Even copied storage marked as reload cannot share an active page's lock.
 const copiedReload=browser('reload',new Map(same.storage));
 const locked=await setup({globals:copiedReload.globals,responses:[workspace('cp-2',goal),{ok:false,error:'A form is already open'}]});
 assert.deepEqual(locked.calls.map(c=>c.path),['/workspace','/decision/open']);
 assert.equal(payload(locked.calls[1]).view,undefined);
 assert.equal(payload(locked.calls[1]).replace,false);
 assert.equal(locked.panel.children.length,0);
 assert(!resumed.panel.querySelector('textarea').readOnly,'another view never expires the genuine form');

 // A stale recovery refuses; it cannot silently issue a replacement collector.
 await same.leave();
 const stale=browser('reload',same.storage);
 const changed=await setup({globals:stale.globals,responses:[workspace('cp-3',goal)]});
 assert.deepEqual(changed.calls.map(c=>c.path),['/workspace']);
 assert.match(changed.status.textContent,/recovery changed.*deliberately reopen/);
 await stale.leave();
 const expired=browser('reload',same.storage);
 const refused=await setup({globals:expired.globals,responses:[workspace('cp-2',goal),{ok:false,error:'Decision expired'}]});
 assert.deepEqual(refused.calls.map(c=>c.path),['/workspace','/decision/restore']);
 assert.equal(refused.panel.children.length,0);
 await expired.leave();

 // A lost submission reply persists a barrier before reload, and never replays.
 const uncertain=browser('reload',same.storage);
 const sending=await setup({globals:uncertain.globals,responses:[workspace('cp-2',goal),remaining]});
 sending.panel.querySelector('textarea').value='Unconfirmed result';
 sending.queue.push(new Error('Reply lost'));
 sending.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(recovery(uncertain).blocked,true);assert.equal(recovery(uncertain).recovery,null);
 assert(sending.panel.querySelector('textarea').readOnly);
 await uncertain.leave();
 const afterLoss=browser('reload',uncertain.storage);
 const inspected=await setup({globals:afterLoss.globals,responses:[workspace('cp-2',goal)]});
 assert.deepEqual(inspected.calls.map(c=>c.path),['/workspace']);
 assert.match(inspected.status.textContent,/previous form was submitted or left.*deliberately reopen/);
 const lostSupport=browser('reload',new Map(uncertain.storage),{locks:false});
 const stillBlocked=await setup({globals:lostSupport.globals,responses:[workspace('cp-2',goal)]});
 assert.deepEqual(stillBlocked.calls.map(c=>c.path),['/workspace'],'an unconfirmed submission stays blocked if lock support disappears');
 inspected.queue.push({...remaining,decision:'deliberately-opened'});
 inspected.root.querySelector('button').onclick();await flush();
 assert.equal(inspected.calls.at(-1).path,'/decision/open');
 assert.equal(payload(inspected.calls.at(-1)).replace,undefined,'replacement requires the deliberate button');
 assert.equal(inspected.panel.querySelector('textarea').value,'');
 assert.equal(recovery(afterLoss).blocked,false);
 await afterLoss.leave();

 // Unsupported or denied ownership primitives preserve the older safe fallback.
 for(const options of [{locks:false},{readDenied:true}]){
  const unavailable=browser('reload',new Map(first.storage),options);
  const fallback=await setup({globals:unavailable.globals,responses:[workspace('cp-2',goal),{ok:false,error:'A form is already open'}]});
  assert.deepEqual(fallback.calls.map(c=>c.path),['/workspace','/decision/open']);
  assert.equal(payload(fallback.calls[1]).view,undefined);assert.equal(payload(fallback.calls[1]).replace,false);
  assert.equal(fallback.panel.children.length,0);
 }
 const storageLoss=browser('navigate');
 const blocked=await setup({globals:storageLoss.globals,responses:[workspace('cp-1'),initial]});
 blocked.panel.querySelector('textarea').value='Preserve this typing';
 storageLoss.state.writeDenied=true;
 const before=blocked.calls.length;
 blocked.panel.querySelector('form').onsubmit({preventDefault(){}});await flush();
 assert.equal(blocked.calls.length,before,'a failed no-replay barrier prevents sending the response');
 assert.equal(blocked.panel.querySelector('textarea').value,'Preserve this typing');
 assert(blocked.panel.querySelector('textarea').readOnly);
 await storageLoss.leave();
 console.log('client regressions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
