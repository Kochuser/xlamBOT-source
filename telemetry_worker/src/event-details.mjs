const choices={state:new Set(['match','menu','loading','unknown','-','brawler_selection','select_brawler','idle_disconnect','connection_lost','lobby','paused','stopped','results']),capture:new Set(['accessibility','projection','none']),backend:new Set(['cpu','gpu','nnapi','auto'])};
const ranges={frame_age_ms:86400000,frame_sequence:Number.MAX_SAFE_INTEGER,heap_mb:32768,native_heap_mb:32768,sdk:100,display_width:16384,display_height:16384,inference_ms:60000,exit_reason:32};
export function cleanDiagnostics(value){
 if(!value||Array.isArray(value)||typeof value!=='object')return {};
 const out={};
 for(const [key,allowed] of Object.entries(choices))if(allowed.has(value[key]))out[key]=value[key];
 for(const [key,max] of Object.entries(ranges))if(Number.isSafeInteger(value[key])&&value[key]>=0&&value[key]<=max&&(key!=='sdk'||value[key]>=26))out[key]=value[key];
 return out;
}
export async function saveEventDetails(env,item,received){
 const diagnostics=JSON.stringify(cleanDiagnostics(item.diagnostics));
 await env.DB.prepare(`INSERT INTO event_details(installation,id,first_seen,last_seen,first_received,received_at,diagnostics)
 SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM events WHERE installation=? AND id=? AND fingerprint=?)
 ON CONFLICT(installation,id) DO UPDATE SET first_seen=MIN(first_seen,excluded.first_seen),
 last_seen=MAX(last_seen,excluded.last_seen),received_at=MAX(received_at,excluded.received_at),
 diagnostics=CASE WHEN excluded.last_seen>=last_seen THEN excluded.diagnostics ELSE diagnostics END`)
 .bind(item.installation,item.id,item.first_seen,item.last_seen,received,received,diagnostics,item.installation,item.id,item.fingerprint).run();
}
