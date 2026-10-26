const json=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store'}});
export function equal(a,b){if(typeof a!=='string'||typeof b!=='string'||!b||a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0;}
export function plusUpdate(update){
  if(update?.pre_checkout_query)return true;
  const m=update?.message;
  if(m?.successful_payment?.invoice_payload?.startsWith('plus_')||m?.refunded_payment?.invoice_payload?.startsWith('plus_'))return true;
  if(typeof update?.callback_query?.data==='string'&&update.callback_query.data.startsWith('plus:'))return true;
  return /^\/(?:plus(?:_history|_device|_admin|_test|_refund|_compensate|_support)?|terms|paysupport)(?:@[A-Za-z0-9_]+)?(?:\s|$)/.test(m?.text||'')||/^\/start(?:@[A-Za-z0-9_]+)?\s+plus(?:_|$)/.test(m?.text||'');
}
export async function forwardPlus(update,env){
  if(!env.PLUS||!env.PLUS_BRIDGE_SECRET)return json({error:'plus_unavailable'},503);
  try{
    const r=await env.PLUS.fetch('https://plus.internal/internal/telegram',{method:'POST',headers:{'Content-Type':'application/json','X-Plus-Bridge-Secret':env.PLUS_BRIDGE_SECRET},body:JSON.stringify({update,admin_id:env.ADMIN_TELEGRAM_USER_ID||''}),signal:AbortSignal.timeout(8500)});
    return json({ok:r.ok},r.ok?200:503);
  }catch{return json({error:'plus_unavailable'},503);}
}
const methods=new Set(['sendMessage','sendInvoice','createInvoiceLink','answerPreCheckoutQuery','answerCallbackQuery','refundStarPayment','getStarTransactions','getChatMember']);

export async function miniappPlus(action,body,user,env){
  if(!['status','terms','beta','invoice','unlink','support'].includes(action))return json({error:'not_found'},404);
  if(!env.PLUS||!env.PLUS_BRIDGE_SECRET)return json({error:'plus_unavailable'},503);
  try{
    const response=await env.PLUS.fetch('https://plus.internal/internal/miniapp/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Plus-Bridge-Secret':env.PLUS_BRIDGE_SECRET},body:JSON.stringify({...body,user_id:Number(user),admin_id:env.ADMIN_TELEGRAM_USER_ID||''}),signal:AbortSignal.timeout(8500)});
    const data=await response.json();
    return json(data,response.status);
  }catch{return json({error:'plus_unavailable'},503);}
}
export async function configurePlusWebhook(request,env,send=fetch){
  if(request.method!=='POST')return json({error:'not_found'},404);
  if(!equal(request.headers.get('X-Plus-Bridge-Secret'),env.PLUS_BRIDGE_SECRET))return json({error:'unauthorized'},401);
  if(!env.TELEGRAM_BOT_TOKEN||!env.TELEGRAM_WEBHOOK_SECRET)return json({error:'unavailable'},503);
  const expected='https://xlambot-error-receiver.olegu621.workers.dev/telegram';
  const call=async(method,payload={})=>{
    const r=await send('https://api.telegram.org/bot'+env.TELEGRAM_BOT_TOKEN+'/'+method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),redirect:'manual',signal:AbortSignal.timeout(5000)});
    const data=await r.json();if(!r.ok||!data.ok)throw Error('telegram_failed');return data.result;
  };
  try{
    const me=await call('getMe');
    if(me.username?.toLowerCase()!==(env.TELEGRAM_BOT_USERNAME||'xlambottt_bot').toLowerCase())return json({error:'wrong_bot'},409);
    const info=await call('getWebhookInfo');
    if(info.url!==expected)return json({error:'unexpected_webhook'},409);
    const updates=Array.isArray(info.allowed_updates)&&info.allowed_updates.length?[...new Set([...info.allowed_updates,'message','callback_query','pre_checkout_query'])]:[];
    await call('setWebhook',{url:expected,secret_token:env.TELEGRAM_WEBHOOK_SECRET,allowed_updates:updates,drop_pending_updates:false,max_connections:info.max_connections||40});
    const verified=await call('getWebhookInfo');
    if(verified.url!==expected||verified.allowed_updates?.length&&['message','callback_query','pre_checkout_query'].some(k=>!verified.allowed_updates.includes(k)))throw Error('verification_failed');
    return json({ok:true,bot_username:me.username,updates:verified.allowed_updates||[],webhook_verified:true,pending_updates:verified.pending_update_count||0});
  }catch{return json({error:'configuration_failed'},503);}
}
export async function telegramGateway(request,env,readBody,send=fetch){
  if(request.method!=='POST')return json({error:'not_found'},404);
  if(!equal(request.headers.get('X-Plus-Bridge-Secret'),env.PLUS_BRIDGE_SECRET))return json({error:'unauthorized'},401);
  const body=await readBody(request);
  if(!methods.has(body.method)||!body.payload||Array.isArray(body.payload)||typeof body.payload!=='object')return json({error:'invalid'},400);
  if(!env.TELEGRAM_BOT_TOKEN)return json({error:'unavailable'},503);
  try{
    const r=await send('https://api.telegram.org/bot'+env.TELEGRAM_BOT_TOKEN+'/'+body.method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body.payload),redirect:'manual',signal:AbortSignal.timeout(5000)});
    const data=await r.json();
    return json(data.ok?{ok:true,result:data.result}:{ok:false,description:String(data.description||'telegram_failed').slice(0,250)},r.ok?200:502);
  }catch{return json({error:'gateway_unavailable'},503);}
}
