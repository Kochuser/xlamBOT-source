import test from 'node:test';
import assert from 'node:assert/strict';
import {channelAdmin} from '../src/channel-admin.mjs';

const env={PLUS_BRIDGE_SECRET:'bridge',TELEGRAM_BOT_TOKEN:'SECRET_TOKEN'};
const request=(body,secret='bridge')=>new Request('https://receiver.test/internal/channel-admin',
 {method:'POST',headers:{'Content-Type':'application/json','X-Plus-Bridge-Secret':secret},body:JSON.stringify(body)});
const read=r=>r.json();
function gateway(rights={status:'administrator',can_change_info:true,can_post_messages:true,can_edit_messages:true}){
 const calls=[];
 const send=async(url,options)=>{
  const method=url.split('/').at(-1),payload=options.body instanceof FormData?options.body:JSON.parse(options.body);
  calls.push({method,payload});
  const result=method==='getMe'?{id:123,username:'xlambottt_bot'}:method==='getChatMember'?rights:method==='getChat'?{id:-1001,username:'xlamModz',title:'xlamBOT'}:{message_id:102};
  return Response.json({ok:true,result});
 };
 return {calls,send};
}
test('unauthorized or missing-secret requests never reach Telegram',async()=>{
 const g=gateway();
 assert.equal((await channelAdmin(request({action:'snapshot'},'bad'),env,read,g.send)).status,401);
 assert.equal((await channelAdmin(request({action:'snapshot'}),{},read,g.send)).status,401);
 assert.equal(g.calls.length,0);
});
test('arbitrary methods, other channels, malformed messages and unsafe buttons are rejected',async()=>{
 const g=gateway();
 for(const body of [{action:'setWebhook'},{action:'snapshot',chat_id:'@other'},{action:'photo'},
  {action:'pin',message_id:-1},{action:'profile',title:'x',description:'x'.repeat(256)},
  {action:'edit',message_id:1,text:'x',reply_markup:{inline_keyboard:[[{text:'bad',url:'https://evil.invalid'}]]}}])
  assert.equal((await channelAdmin(request(body),env,read,g.send)).status,400);
 assert.equal(g.calls.length,0);
});
test('snapshot is scoped to the owned channel and returns no token or administrator identity',async()=>{
 const g=gateway();const response=await channelAdmin(request({action:'snapshot'}),env,read,g.send);
 assert.equal(response.status,200);const text=await response.text();assert.ok(!text.includes('SECRET_TOKEN'));
 assert.equal(JSON.parse(text).result.chat.username,'xlamModz');
 assert.equal(g.calls.find(x=>x.method==='getChat').payload.chat_id,'@xlamModz');
});
test('profile edits require the actual channel permission and preserve fixed scope',async()=>{
 const g=gateway({status:'administrator',can_post_messages:true});
 const body={action:'profile',title:'xlamBOT',description:'Updated'};
 assert.equal((await channelAdmin(request(body),env,read,g.send)).status,403);
 assert.ok(!g.calls.some(x=>x.method.startsWith('setChat')));
 const allowed=gateway();assert.equal((await channelAdmin(request(body),env,read,allowed.send)).status,200);
 for(const call of allowed.calls.filter(x=>x.method.startsWith('setChat')))assert.equal(call.payload.chat_id,'@xlamModz');
});
test('editing and pinning only address the configured channel; pinning is silent',async()=>{
 const g=gateway();
 assert.equal((await channelAdmin(request({action:'edit',message_id:86,text:'Archive'}),env,read,g.send)).status,200);
 assert.equal((await channelAdmin(request({action:'pin',message_id:102}),env,read,g.send)).status,200);
 const edit=g.calls.find(x=>x.method==='editMessageText');assert.equal(edit.payload.message_id,86);assert.equal(edit.payload.chat_id,'@xlamModz');
 assert.deepEqual(g.calls.find(x=>x.method==='pinChatMessage').payload,{chat_id:'@xlamModz',message_id:102,disable_notification:true});
});
test('a cover uploads the provided image as multipart, with safe navigation and no alert',async()=>{
 const form=new FormData();form.append('photo',new Blob([new Uint8Array([137,80,78,71,13,10,26,10,0])],{type:'image/png'}),'start.png');
 form.append('caption','Start here');form.append('reply_markup',JSON.stringify({inline_keyboard:[[{text:'Start',url:'https://t.me/xlambottt_bot?start=plus'}]]}));
 const req=new Request('https://receiver.test/internal/channel-admin?action=cover',{method:'POST',headers:{'X-Plus-Bridge-Secret':'bridge'},body:form});
 const g=gateway();assert.equal((await channelAdmin(req,env,read,g.send)).status,200);
 const post=g.calls.find(x=>x.method==='sendPhoto').payload;
 assert.equal(post.get('chat_id'),'@xlamModz');assert.equal(post.get('disable_notification'),'true');assert.ok(post.get('photo') instanceof Blob);
});
test('multipart bytes are bounded even without Content-Length',async()=>{
 const req=new Request('https://receiver.test/internal/channel-admin?action=photo',{method:'POST',headers:{'X-Plus-Bridge-Secret':'bridge','Content-Type':'multipart/form-data; boundary=x'},body:new Uint8Array(600001)});
 const g=gateway();assert.equal((await channelAdmin(req,env,read,g.send)).status,413);assert.equal(g.calls.length,0);
});
