const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const base=path.join('D:','Projects','CCWBot','reports','event-alert-review-20261016','telegram_review');
for(const reviewer of ['A','B'])for(const phase of [1,2]){
  const html=fs.readFileSync(path.join(base,'CCWBot_Reviewer_'+reviewer+'_PHASE'+phase+'.html'),'utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const elem=new Map(),callbacks={};const local={};
  const el=(id)=>{if(!elem.has(id))elem.set(id,{
      id,style:{},textContent:'',value:'',innerHTML:'',disabled:false,
      addEventListener:(type,fn)=>{callbacks[id+':'+type]=fn},
      querySelector:()=>({textContent:'',style:{}}),
      querySelectorAll:()=>[],
      click:()=>{},setAttribute:()=>{},append:()=>{},remove:()=>{}
  });return elem.get(id)};
  const ctx=vm.createContext({document:{getElementById:el,createElement:()=>({click:()=>{},remove:()=>{}}),body:{append:()=>{}}},
    window:{scrollTo:()=>{}},localStorage:{getItem:x=>local[x]||null,setItem:(x,v)=>local[x]=v},
    Blob:class{},URL:{createObjectURL:()=>'fake',revokeObjectURL:()=>{}},
    setTimeout:()=>{},alert:()=>{},confirm:()=>true,
    console,Intl,Number,Math,Date,JSON,Array,Set,Map,Symbol,String});
  vm.runInContext(js,ctx,{timeout:6000});
  assert.equal(el('counter').textContent,'Ситуация 1 из '+(phase===1?200:72));
  assert.equal(el('done-count').textContent,'Оценено: 0/'+(phase===1?200:72));
  if(phase===1){
      vm.runInContext('answer("warrant","alert")',ctx);
  }else{
      vm.runInContext('answer("useful",true)',ctx);
      assert.equal(vm.runInContext('done(0)',ctx),true);
      assert.equal(vm.runInContext('get(0).factual',ctx),undefined);
  }
  assert.equal(el('done-count').textContent,'Оценено: 1/'+(phase===1?200:72));
  vm.runInContext('goto(1)',ctx);
  assert.equal(el('counter').textContent,'Ситуация 2 из '+(phase===1?200:72));
  console.log(reviewer,phase,'INTERACTIVE_RENDER=OK','ANSWER_SAVE=OK','NAVIGATION=OK');
}
