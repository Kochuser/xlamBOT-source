const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
export async function gateCommunity(env,actor,{text='',updateId=null,callbackId=null,force=false}={}){
 if(env.PLUS_COMMUNITY_ENABLED!=='true')return {allowed:true};
 if(!env.PLUS||!env.PLUS_BRIDGE_SECRET)throw Error('community_unavailable');
 const known=await env.DB.prepare('SELECT installation FROM remote_links WHERE user_id=? LIMIT 1').bind(String(actor.id)).first();
 const r=await env.PLUS.fetch('https://plus.internal/internal/community/gate',{method:'POST',headers:{'Content-Type':'application/json','X-Plus-Bridge-Secret':env.PLUS_BRIDGE_SECRET},body:JSON.stringify({actor:{id:actor.id,is_bot:actor.is_bot===true},text,known_existing:!!known,update_id:updateId,callback_id:callbackId,force_check:force}),signal:AbortSignal.timeout(8500)});
 if(!r.ok)throw Error('community_unavailable');return r.json();
}
export async function miniCommunity(env,user){
 try {const gate=await gateCommunity(env,{id:Number(user)});return gate.allowed?null:json({error:'channel_subscription_required',...gate},403);}
 catch{return json({error:'community_unavailable'},503);}
}
