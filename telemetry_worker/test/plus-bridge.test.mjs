import {test} from 'node:test';
import assert from 'node:assert/strict';
import {plusUpdate,forwardPlus,telegramGateway} from '../src/plus-bridge.mjs';
import {telegramCommand} from '../src/statistics.mjs';
test('only Plus-related updates are forwarded; old commands remain owned by original handler',()=>{
  for(const text of ['/plus','/plus_admin','/plus_test','/plus_refund abc','/plus_support S-1 answer','/paysupport help','/terms','/start plus_abc','/plus@xlambottt_bot'])assert.equal(plusUpdate({message:{text}}),true,text);
  for(const text of ['/start','/help','/online','/panel','/admin','/plus_malicious'])assert.equal(plusUpdate({message:{text}}),false,text);
  assert.equal(plusUpdate({pre_checkout_query:{}}),true);assert.equal(plusUpdate({callback_query:{data:'plus:home'}}),true);
});
test('webhook authenticates before forwarding and propagates failures for Telegram retry',async()=>{
  let calls=0;const env={TELEGRAM_WEBHOOK_SECRET:'telegram-secret',PLUS_BRIDGE_SECRET:'bridge',ADMIN_TELEGRAM_USER_ID:'123',PLUS:{async fetch(url,r){calls++;const e=JSON.parse(r.body);assert.equal(e.admin_id,'123');assert.equal(r.headers['X-Plus-Bridge-Secret'],'bridge');return new Response('',{status:503});}}};
  const update={update_id:1,message:{text:'/plus'}};
  const req=secret=>new Request('https://receiver.test/telegram',{method:'POST',headers:secret?{'X-Telegram-Bot-Api-Secret-Token':secret}:{},body:JSON.stringify(update)});
  assert.equal((await telegramCommand(req('bad'),env,r=>r.json())).status,401);assert.equal(calls,0);assert.equal((await telegramCommand(req('telegram-secret'),env,r=>r.json())).status,503);assert.equal(calls,1);
  assert.equal((await forwardPlus(update,{})).status,503);
});
test('private gateway cannot set webhook, leak token or proxy arbitrary methods',async()=>{
  const env={PLUS_BRIDGE_SECRET:'bridge',TELEGRAM_BOT_TOKEN:'token-for-local-test'};let calls=0;
  const req=(method,secret='bridge')=>new Request('https://receiver.test/internal/plus/telegram-api',{method:'POST',headers:{'X-Plus-Bridge-Secret':secret},body:JSON.stringify({method,payload:{user_id:123,telegram_payment_charge_id:'id'}})});
  const send=async(url)=>{calls++;assert.equal(url,'https://api.telegram.org/bottoken-for-local-test/refundStarPayment');return Response.json({ok:true,result:true});};
  assert.equal((await telegramGateway(req('refundStarPayment','wrong'),env,r=>r.json(),send)).status,401);
  for(const m of ['setWebhook','getUpdates','logOut','deleteWebhook','getMe','https://evil.invalid'])assert.equal((await telegramGateway(req(m),env,r=>r.json(),send)).status,400);
  assert.equal(calls,0);const r=await telegramGateway(req('refundStarPayment'),env,r=>r.json(),send);assert.equal(r.status,200);assert.equal(calls,1);assert.equal((await r.text()).includes('token-for-local-test'),false);
});
