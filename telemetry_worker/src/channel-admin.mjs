import {equal} from './plus-bridge.mjs';

const CHANNEL='@xlamModz';
const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
const text=(value,max)=>typeof value==='string'&&value.length>0&&value.length<=max;
const messageID=value=>Number.isSafeInteger(value)&&value>0;
const linkAllowed=value=>{
  try {
    const url=new URL(value);
    if(url.protocol!=='https:'||url.username||url.password||url.port)return false;
    return (url.hostname==='olegu621.github.io'&&url.pathname.startsWith('/xlamBOT-Android--Brawl-Stars--/'))||
      (url.hostname==='github.com'&&url.pathname.startsWith('/Olegu621/'))||
      (url.hostname==='t.me'&&/^\/(?:xlamModz(?:\/\d+)?|xlambottt_bot)\/?$/.test(url.pathname));
  }catch{return false;}
};
function keyboard(value){
  if(!value||!Array.isArray(value.inline_keyboard)||value.inline_keyboard.length>8)return false;
  return value.inline_keyboard.every(row=>Array.isArray(row)&&row.length>0&&row.length<=3&&
    row.every(button=>button&&Object.keys(button).every(key=>['text','url'].includes(key))&&text(button.text,64)&&linkAllowed(button.url)));
}

/** Owner tooling for this one channel; independent of payments and the restricted Plus gateway. */
export async function channelAdmin(request,env,readBody,send=fetch){
  if(request.method!=='POST')return json({error:'not_found'},404);
  if(!equal(request.headers.get('X-Plus-Bridge-Secret'),env.PLUS_BRIDGE_SECRET))return json({error:'unauthorized'},401);
  if(!env.TELEGRAM_BOT_TOKEN)return json({error:'unavailable'},503);
  let body,photo;
  const uploadAction=new URL(request.url).searchParams.get('action');
  try {
    if(['photo','cover'].includes(uploadAction)){
      if(Number(request.headers.get('Content-Length')||0)>600000)return json({error:'too_large'},413);
      const reader=request.body?.getReader(),chunks=[];let size=0;
      if(!reader)return json({error:'invalid_photo'},400);
      while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>600000){await reader.cancel();return json({error:'too_large'},413);}chunks.push(value);}
      const form=await new Response(new Blob(chunks),{headers:{'Content-Type':request.headers.get('Content-Type')||''}}).formData();photo=form.get('photo');
      if(!photo||typeof photo.arrayBuffer!=='function'||photo.size<8||photo.size>512000)return json({error:'invalid_photo'},400);
      const bytes=new Uint8Array(await photo.arrayBuffer());
      const png=bytes.slice(0,8).every((v,i)=>v===[137,80,78,71,13,10,26,10][i]);
      const jpeg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
      if((photo.type!=='image/png'||!png)&&(photo.type!=='image/jpeg'||!jpeg))return json({error:'invalid_photo'},400);
      body={action:uploadAction,caption:form.get('caption')};
      if(form.has('reply_markup'))body.reply_markup=JSON.parse(form.get('reply_markup'));
    }else body=await readBody(request);
  }catch{return json({error:'invalid'},400);}
  const action=body?.action;
  if(!['snapshot','profile','photo','photo_backup','cover','edit','pin'].includes(action)||
    (body.chat_id!==undefined&&body.chat_id!==CHANNEL))return json({error:'invalid'},400);
  if(['photo','cover'].includes(action)&&!photo)return json({error:'invalid_photo'},400);
  if(action==='profile'&&(!text(body.title,128)||typeof body.description!=='string'||body.description.length>255))return json({error:'invalid_profile'},400);
  if(['edit','pin'].includes(action)&&!messageID(body.message_id))return json({error:'invalid_message'},400);
  if(action==='edit'&&(!text(body.text,body.caption?1024:4096)||body.reply_markup&&!keyboard(body.reply_markup)))return json({error:'invalid_message'},400);
  if(action==='cover'&&(!text(body.caption,1024)||!keyboard(body.reply_markup)))return json({error:'invalid_cover'},400);

  const call=async(method,payload,form=false)=>{
    const response=await send('https://api.telegram.org/bot'+env.TELEGRAM_BOT_TOKEN+'/'+method,
      {method:'POST',...(form?{}:{headers:{'Content-Type':'application/json'}}),body:form?payload:JSON.stringify(payload),redirect:'manual',signal:AbortSignal.timeout(10000)});
    const data=await response.json();
    if(!response.ok||!data.ok){
      if(/(?:message is not modified|chat_not_modified)/i.test(String(data.description))&&['setChatTitle','setChatDescription','editMessageText','editMessageCaption'].includes(method))return true;
      const error=Error('telegram_failed');error.detail=String(data.description||'telegram_failed').slice(0,180);throw error;
    }
    return data.result;
  };
  try {
    const me=await call('getMe',{});
    if(me.username!=='xlambottt_bot')return json({error:'wrong_bot'},409);
    const rights=await call('getChatMember',{chat_id:CHANNEL,user_id:me.id});
    if(action==='snapshot'){
      const {user,...permissions}=rights;
      return json({ok:true,result:{bot_username:me.username,chat:await call('getChat',{chat_id:CHANNEL}),rights:permissions}});
    }
    const required=action==='cover'?'can_post_messages':['edit','pin'].includes(action)?'can_edit_messages':'can_change_info';
    if(rights.status!=='creator'&&(rights.status!=='administrator'||rights[required]!==true))return json({error:'missing_channel_right',required},403);
    let result;
    if(action==='profile'){
      await call('setChatTitle',{chat_id:CHANNEL,title:body.title});
      await call('setChatDescription',{chat_id:CHANNEL,description:body.description});
      result=await call('getChat',{chat_id:CHANNEL});
    }else if(action==='photo'||action==='cover'){
      const form=new FormData();form.append('chat_id',CHANNEL);form.append('photo',photo,action+'.png');
      if(action==='cover'){
        form.append('caption',body.caption);form.append('parse_mode','HTML');form.append('disable_notification','true');
        form.append('reply_markup',JSON.stringify(body.reply_markup));
      }
      result=await call(action==='photo'?'setChatPhoto':'sendPhoto',form,true);
    }else if(action==='photo_backup'){
      const chat=await call('getChat',{chat_id:CHANNEL});
      if(!chat.photo)return json({error:'no_photo'},404);
      const file=await call('getFile',{file_id:chat.photo.big_file_id});
      if(!/^[\w./-]+$/.test(file.file_path)||file.file_path.includes('..'))return json({error:'invalid_file'},502);
      const response=await send('https://api.telegram.org/file/bot'+env.TELEGRAM_BOT_TOKEN+'/'+file.file_path,{redirect:'manual',signal:AbortSignal.timeout(10000)});
      if(!response.ok)throw Error('photo_unavailable');
      return new Response(await response.arrayBuffer(),{headers:{'Content-Type':'image/jpeg','Cache-Control':'no-store'}});
    }else if(action==='edit'){
      const payload={chat_id:CHANNEL,message_id:body.message_id,parse_mode:'HTML',...(body.reply_markup?{reply_markup:body.reply_markup}:{})};
      payload[body.caption?'caption':'text']=body.text;
      if(!body.caption)payload.link_preview_options={is_disabled:true};
      result=await call(body.caption?'editMessageCaption':'editMessageText',payload);
    }else result=await call('pinChatMessage',{chat_id:CHANNEL,message_id:body.message_id,disable_notification:true});
    return json({ok:true,result});
  }catch(error){return json({error:'channel_operation_failed',detail:error.detail||'telegram_unavailable'},502);}
}
