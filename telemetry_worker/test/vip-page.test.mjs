import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {plusScript} from '../src/plus-page.mjs';

test('VIP storefront shows indefinite membership and disables payment while ordinary Plus can renew',()=>{
 new vm.Script(plusScript);
 const elements=new Map(),element=()=>({textContent:'',hidden:false,disabled:false,replaceChildren(){},append(){}});
 const context=vm.createContext({window:{},document:{querySelectorAll(){return [];},getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},createElement:element},Intl,Date});
 vm.runInContext(plusScript.slice(0,plusScript.indexOf("$('refresh').addEventListener")),context);
 vm.runInContext("state={account:{plan:'plus',vip:true,until:253402300799,username:'tester'},device:{label:'Phone'},linked:true,price:50,sales_enabled:true,promo_active:true,promo_until:1792684800,beta_enabled:true,beta_used:false,features:[],history:[]};render();",context);
 assert.match(elements.get('plan-badge').textContent,/VIP/);
 assert.match(elements.get('account-plan').textContent,/бессрочный/);
 assert.equal(elements.get('buy').disabled,true);
 assert.equal(elements.get('beta').disabled,true);
 assert.equal(elements.get('promo').hidden,true);
 assert.doesNotMatch(elements.get('plan-until').textContent,/9999/);
 vm.runInContext('state.account.vip=false;state.account.until=1800000000;render();',context);
 assert.equal(elements.get('buy').disabled,false);
 assert.match(elements.get('buy').textContent,/Продлить/);
});

test('1.2 storefront presents referral reward without a trial promise',()=>{
 const elements=new Map(),element=()=>({textContent:'',hidden:false,disabled:false,replaceChildren(){},append(){},querySelector(key){return this[key]??(this[key]=element());}});
 const context=vm.createContext({window:{},document:{querySelectorAll(){return [];},getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},createElement:element},Intl,Date});
 vm.runInContext(plusScript.slice(0,plusScript.indexOf("$('refresh').addEventListener")),context);
 vm.runInContext("state={promo_until:0,trials_removed:true,referrals:{qualified:8,progress:3,link:'https://t.me/xlambottt_bot?start=ref_test'},account:{plan:'free'},price:50,sales_enabled:true,beta_enabled:false,features:[],history:[]};render();",context);
 assert.equal(elements.get('referral-offer').querySelector('h3').textContent,'5 друзей = 10 дней');
 assert.match(elements.get('trial-hint').textContent,/3 из 5/);assert.doesNotMatch(elements.get('trial-hint').textContent,/3 часа/);
 assert.equal(elements.get('beta').disabled,false);assert.match(elements.get('beta').textContent,/приглашением/);
});
