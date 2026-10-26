const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('D:\\Projects\\CCWBot\\reports\\event-alert-review-20261016\\telegram_review\\CCWBot_REVIEW_A_vs_GPT6_66.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements=new Map(),callbacks={},local={};
const el=id=>{
 if(!elements.has(id))elements.set(id,{
  id, style:{}, textContent:'', value:'', innerHTML:'', disabled:false,
  addEventListener:(event,fn)=>{callbacks[id+':'+event]=fn},
  querySelector:()=>({textContent:'',style:{}}),
  querySelectorAll:()=>[],
  click:()=>{},setAttribute:()=>{},append:()=>{},appendChild:()=>{},remove:()=>{}
 });
 return elements.get(id);
};
const ctx=vm.createContext({
 document:{getElementById:el,createElement:()=>({value:'',textContent:'',click:()=>{},remove:()=>{}}),body:{append:()=>{}}},
 window:{scrollTo:()=>{}},
 localStorage:{getItem:k=>local[k]||null,setItem:(k,v)=>{local[k]=v}},
 Blob:class{},URL:{createObjectURL:()=> 'fake',revokeObjectURL:()=>{}},
 setTimeout:()=>{},alert:msg=>{throw Error(msg)},confirm:()=>true,
 console,Intl,Number,Math,Date,JSON,Array,Set,Map,Symbol,String,parseInt,parseFloat
});
vm.runInContext(js,ctx,{timeout:15000});
assert.equal(el('counter').textContent,'Ситуация 1 из 66');
assert.equal(el('done-count').textContent,'Оценено всего: 0/66');
assert.equal(el('pair-filter').value,'');
assert.match(el('questions').innerHTML,/Reviewer A/);
assert.match(el('questions').innerHTML,/Reviewer C/);
assert.match(el('questions').innerHTML,/Какое решение вы считаете правильным сейчас/);
assert.equal(vm.runInContext('ALL_ITEMS.length',ctx),66);
const initialId=vm.runInContext('ITEMS[0].id',ctx);
vm.runInContext('answer("warrant","no_alert")',ctx);
assert.equal(el('done-count').textContent,'Оценено всего: 1/66');
assert.equal(vm.runInContext('get(0).warrant',ctx),'no_alert');
const storageKey=Object.keys(local).find(x=>x.includes('-AC-1'));
assert(storageKey,'dedicated AC localStorage key');
assert.equal(JSON.parse(local[storageKey])[initialId].warrant,'no_alert');
vm.runInContext('goto(1)',ctx);
assert.equal(el('counter').textContent,'Ситуация 2 из 66');
el('pair-filter').value='alert|no_alert';
callbacks['pair-filter:change']();
assert.equal(vm.runInContext('ITEMS.length',ctx),17);
assert.equal(el('counter').textContent,'Ситуация 1 из 17');
assert.equal(el('done-count').textContent,'Оценено всего: 1/66');
el('coin-filter').value='BTC';
callbacks['coin-filter:change']();
assert(vm.runInContext('ITEMS.every(x=>x.symbol==="BTC")',ctx));
el('pair-filter').value='';
el('coin-filter').value='';
callbacks['coin-filter:change']();
assert.equal(vm.runInContext('ITEMS.length',ctx),66);
assert.equal(el('done-count').textContent,'Оценено всего: 1/66');
console.log('PASS: browser-script VM render, A/C side-by-side labels, explanations, 66 cases, answer saving, next/prev navigation, pair and coin filters, globally retained progress.');
