import {validate,applyPatch} from './guards.mjs';

export function createApp({dataset,taxonomy,assets={}}){
 const questionMap=new Map(dataset.questions.map(q=>[q._id,q]));
 const resultMap=new Map(dataset.results.map(r=>[r.questionId,r]));
 const isUUID=s=>/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(s||'');
 const pagesOrigin='https://milindsen.github.io';
 function workspace(req){const bearer=req.headers.get('Authorization')?.replace(/^Bearer /,'');if(req.headers.get('Origin')===pagesOrigin&&isUUID(bearer))return {id:bearer,fresh:false};const raw=(req.headers.get('Cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('acadza_workspace='))?.slice(17);return isUUID(raw)?{id:raw,fresh:false}:{id:crypto.randomUUID(),fresh:true}}
 const json=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 async function state(db,space){
  const [rr,aa]=await db.batch([db.prepare('SELECT * FROM review_records WHERE workspace=?').bind(space),db.prepare('SELECT * FROM review_audit WHERE workspace=? ORDER BY at DESC').bind(space)]);
  const map=new Map(rr.results.map(r=>[r.id,r]));
  return {...dataset,questions:dataset.questions.map(q=>map.has(q._id)?JSON.parse(map.get(q._id).content):q),states:Object.fromEntries(rr.results.map(r=>[r.id,{version:r.version,status:r.status}])),audit:aa.results.map(a=>({...a,before:JSON.parse(a.before),after:JSON.parse(a.after),proposal:JSON.parse(a.proposal)})),mode:'server',storage:'d1',reviewToken:space,baseline:'Precomputed assistant-reviewed results; live inference is a separate optional run'};
 }
 async function action(req,db,space){
  const origin=req.headers.get('Origin');if(origin&&origin!==new URL(req.url).origin&&origin!==pagesOrigin)return json({error:'Cross-origin write rejected'},403);
  if(req.headers.get('Authorization')!=='Bearer '+space)return json({error:'Refresh this workspace before reviewing.'},401);
  const raw=await req.text();if(new TextEncoder().encode(raw).length>65536)return json({error:'Request too large'},413);
  let b;try{b=JSON.parse(raw)}catch{return json({error:'Invalid JSON'},400)}
  try{
   const original=questionMap.get(b.questionId),baseline=resultMap.get(b.questionId);if(!original||!baseline)throw Error('Unknown question case');
   if(!Number.isInteger(b.version)||b.version<0)throw Error('Revision required');
   const current=await db.prepare('SELECT * FROM review_records WHERE workspace=? AND id=?').bind(space,b.questionId).first();
   if(current&&(current.version!==b.version||current.status!=='pending'))return json({error:'This case changed. Refresh before acting.'},409);
   if(!current&&b.version!==0)return json({error:'Stale revision'},409);
   const before=current?JSON.parse(current.content):original;let after=before,proposal=structuredClone(baseline),status;
   if(['approve','edit'].includes(b.action)){
    if(b.action==='edit')proposal={...proposal,edit:b.edit,route:'faculty_review'};
    validate(before,proposal,taxonomy);if(!proposal.edit)throw Error('No grounded edit exists. Send this case to faculty.');
    after=applyPatch(before,proposal);status='approved';
   }else if(b.action==='reject')status='rejected';
   else if(b.action==='escalate')status='escalated';
   else if(b.action==='close'){if(proposal.verdict==='defect')throw Error('Defects cannot be closed as no change');status='closed'}
   else throw Error('Invalid action');
   const actor=typeof b.actor==='string'?b.actor.trim().slice(0,80):'';if(!actor)throw Error('Reviewer name required');
   const note=typeof b.note==='string'?b.note.trim().slice(0,2000):'';
   if(['edit','reject','escalate'].includes(b.action)&&!note)throw Error('Add a short review reason');
   const nonce=crypto.randomUUID(),event=crypto.randomUUID(),at=new Date().toISOString();
   const batch=await db.batch([
    db.prepare('INSERT OR IGNORE INTO review_records(workspace,id,content,version,status) VALUES(?,?,?,0,?)').bind(space,b.questionId,JSON.stringify(before),'pending'),
    db.prepare('UPDATE review_records SET content=?,version=version+1,status=?,nonce=? WHERE workspace=? AND id=? AND version=? AND status=?').bind(JSON.stringify(after),status,nonce,space,b.questionId,b.version,'pending'),
    db.prepare('INSERT INTO review_audit(id,workspace,questionId,action,actor,at,note,before,after,proposal,version) SELECT ?,?,?,?,?,?,?,?,?,?,version FROM review_records WHERE workspace=? AND id=? AND nonce=?').bind(event,space,b.questionId,b.action,actor,at,note,JSON.stringify(before),JSON.stringify(after),JSON.stringify(proposal),space,b.questionId,nonce)
   ]);
   if(batch[1].meta.changes!==1)return json({error:'This case changed. Refresh before acting.'},409);
   return json({ok:true,status,version:b.version+1});
  }catch(e){return json({error:e.message||'Review failed; no changes applied'},400)}
 }
 function asset(req,path){
  const file=assets[path];if(!file)return new Response('Not found',{status:404});
  const bytes=file.base64?Uint8Array.from(atob(file.body),c=>c.charCodeAt(0)):new TextEncoder().encode(file.body);
  const headers={'Content-Type':file.type,'X-Content-Type-Options':'nosniff','Accept-Ranges':'bytes','Cache-Control':'public, max-age=300'};
  let start=0,end=bytes.length-1,status=200;const range=req.headers.get('Range');
  if(range){const match=/^bytes=(\d*)-(\d*)$/.exec(range);if(!match||(!match[1]&&!match[2]))return new Response(null,{status:416,headers:{'Content-Range':`bytes */${bytes.length}`}});
   if(!match[1])start=Math.max(0,bytes.length-Number(match[2]));else{start=Number(match[1]);if(match[2])end=Math.min(end,Number(match[2]))}
   if(start>end||start>=bytes.length)return new Response(null,{status:416,headers:{'Content-Range':`bytes */${bytes.length}`}});
   status=206;headers['Content-Range']=`bytes ${start}-${end}/${bytes.length}`;
  }headers['Content-Length']=String(end-start+1);return new Response(req.method==='HEAD'?null:bytes.slice(start,end+1),{status,headers});
 }
 return {async fetch(req,env){
  const path=new URL(req.url).pathname;
  if(!path.startsWith('/api/'))return asset(req,path==='/walkthrough'?'/walkthrough.html':path==='/'?'/index.html':path);
  const cors=req.headers.get('Origin')===pagesOrigin;
  if(req.method==='OPTIONS')return new Response(null,{status:cors?204:403,headers:cors?{'Access-Control-Allow-Origin':pagesOrigin,'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type','Access-Control-Max-Age':'600','Vary':'Origin'}:{}});
  const space=workspace(req);let response;
  try{
   if(!env.DB)response=json({error:'Cloud database binding is unavailable'},503);
   else if(req.method==='GET'&&path==='/api/health'){await env.DB.prepare('SELECT 1 AS ok').first();response=json({ok:true,storage:'d1',inference:'precomputed',questions:dataset.questions.length,reports:dataset.reports.length})}
   else if(req.method==='GET'&&['/api/state','/api/export'].includes(path))response=json(await state(env.DB,space.id));
   else if(req.method==='GET'&&path==='/api/results')response=json(dataset.results);
   else if(req.method==='POST'&&path==='/api/action')response=await action(req,env.DB,space.id);
   else response=json({error:'Not found'},404);
  }catch{response=json({error:'Database unavailable. Please retry; no local fallback writes are made.'},503)}
  if(space.fresh)response.headers.append('Set-Cookie',`acadza_workspace=${space.id}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`);
  if(cors){response.headers.set('Access-Control-Allow-Origin',pagesOrigin);response.headers.set('Vary','Origin');}
  return response;
 }};
}
