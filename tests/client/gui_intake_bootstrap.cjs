/* Runs the complete shipped startup script, including private-link handling.
 * DOM/fetch seams qualify behavior; real browser rendering remains a host check. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {Element}=require('./gui_forms_intake.cjs');
const script=fs.readFileSync(process.argv[2],'utf8'),mode=process.argv[3];
async function flush(){for(let i=0;i<60;i++)await Promise.resolve();}
(async()=>{
 const doc={createElement(tag){return new Element(tag,this);}},root=new Element('main',doc);
 for(const id of ['refresh','status','decisions','tasks','form-panel']){
  const el=new Element(id==='refresh'?'button':'div',doc);el.id=id;
  if(id==='status')el.textContent='Connecting…';if(id==='decisions')el.hidden=true;
  el.addEventListener=function(name,listener){(this.listeners??={})[name]=listener;};root.append(el);
 }
 doc.querySelector=s=>root.querySelector(s);doc.querySelectorAll=s=>root.querySelectorAll(s);
 const hasFragment=['fragment','write-denied','write-property-denied','first-fetch-fails'].includes(mode);
 const location={hash:hasFragment?'#private-fixture-token':'',pathname:'/'};
 let stored=mode==='stored'?'private-fixture-token':null,reads=0,writes=0,historyCalls=0;
 const storage={getItem(key){if(key==='attune-gui-form')return null;reads++;assert.equal(key,'attune-gui-token');
  if(mode==='read-denied')throw Error('SecurityError: storage denied');return stored;},
 setItem(key,value){writes++;assert.equal(key,'attune-gui-token');
  if(mode==='write-denied')throw Error('SecurityError: storage denied');stored=value;}};
 const calls=[];
 const globals={document:doc,location,history:{replaceState(state,title,path){
  assert.equal(path,'/');location.hash='';historyCalls++;}},
  fetch:async(path,opts)=>{calls.push({path,opts});assert.equal(path,'/workspace');assert.equal(opts.method,'GET');
   if(mode==='first-fetch-fails'&&calls.length===1)throw Error('injected network failure');
   if(opts.headers['X-Attune-Session']!=='private-fixture-token')return{ok:false,text:async()=>'Open this workspace using its local launcher link'};
   return{ok:true,json:async()=>({editable:true,tasks:[{task:'A',heading:'Draft saved — more answers needed',label:'Local fixture',note:'Questions remain',available:true}]})};}};
 Object.defineProperty(globals,'sessionStorage',{get(){
  if(mode.endsWith('property-denied'))throw Error('SecurityError: storage access denied');return storage;}});
 const context=vm.createContext(globals);
 vm.runInContext(script,context);await flush();
 const status=doc.querySelector('#status'),refresh=doc.querySelector('#refresh');
 assert.equal(typeof refresh.listeners?.click,'function','storage refusal must leave Refresh active');
 assert.equal(calls.length,1,'startup must make exactly one read-only request');
 assert.equal(historyCalls,hasFragment?1:0);
 if(hasFragment){assert.equal(location.hash,'','private fragment must still be removed');assert.equal(reads,0);}
 if(mode==='fragment'){assert.equal(writes,1);assert.equal(stored,'private-fixture-token');}
 const authorized=hasFragment||mode==='stored';
 if(!authorized){
  assert.equal(doc.querySelector('#decisions').hidden,true,'missing capability must never reveal workspace data');
  assert.match(status.textContent,/Open this workspace using its local launcher link/);
  assert.equal(calls[0].opts.headers['X-Attune-Session'],'');
 }else if(mode==='first-fetch-fails'){
  assert.equal(doc.querySelector('#decisions').hidden,true);assert.match(status.textContent,/injected network failure/);
 }else{assert.equal(doc.querySelector('#tasks').children.length,1);assert.equal(doc.querySelector('#decisions').hidden,false);}
 refresh.listeners.click();await flush();
 assert.equal(calls.length,2,'Refresh must issue a read without submitting a decision');
 assert.equal(refresh.disabled,false);
 if(authorized){
  assert.equal(doc.querySelector('#tasks').children.length,1);assert.equal(doc.querySelector('#decisions').hidden,false);
  assert.equal(calls[1].opts.headers['X-Attune-Session'],'private-fixture-token','Refresh retains the in-memory capability');
  assert.match(status.textContent,/Forms refreshed/);
 }else{assert.equal(doc.querySelector('#decisions').hidden,true);assert.match(status.textContent,/local launcher link/);}
 assert(!status.textContent.includes('private-fixture-token'),'status must not expose the capability');
 console.log('client regressions passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
