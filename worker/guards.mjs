export const patches = r => Array.isArray(r.edit) ? r.edit : r.edit ? [r.edit] : [];
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const protectedTokens=s=>[s.match(/<math\b[\s\S]*?<\/math>|<img\b[^>]*>/gi)||[],s.replace(/<[^>]*>/g,'').match(/\d+(?:\.\d+)?|[=+*/^<>±−×÷√πμρεϕθ]/g)||[]];
export function applyPatch(question,result){
 const q=structuredClone(question),old=q.questionType,d=q[old];
 for(const p of patches(result)){if(p.field==='questionType')q.questionType=p.replace;else if(p.field==='answer')d.answer=p.replace;else d[p.field]=d[p.field].replace(p.find,p.replace)}
 if(old!==q.questionType){q[q.questionType]=d;delete q[old]}return q;
}
export function validate(question,r,taxonomy,automatic=false){
 if(!Object.hasOwn(taxonomy.verdicts,r.verdict))throw Error('Unknown verdict');
 if(typeof r.confidence!=='number'||!Number.isFinite(r.confidence)||r.confidence<0||r.confidence>1)throw Error('Invalid confidence');
 if(!['auto_apply','faculty_review','no_change'].includes(r.route))throw Error('Unknown route');
 const edits=patches(r);
 if(r.verdict!=='defect'){if(r.repair||edits.length||r.route!=='no_change')throw Error('Non-defect cannot mutate content');return}
 const rule=taxonomy.repairs[r.repair];if(!rule)throw Error('Unknown repair');
 if(!rule.auto&&(edits.length||r.route!=='faculty_review'))throw Error('Faculty authoring required');
 if(r.route==='auto_apply'&&!edits.length)throw Error('No patch to apply');
 if(automatic&&(!rule.auto||r.route!=='auto_apply'||r.confidence<.97))throw Error('Automatic threshold not met');
 if(automatic&&r.repair==='answer_key'&&new Set((r.checks||[]).filter(x=>typeof x==='string'&&x.trim().length>=10).map(x=>x.trim())).size<2)throw Error('Two distinct substantive checks required');
 const d=question[question.questionType],seen=new Set();
 for(const p of edits){
  const f=p.field;if(!rule.fields.includes(f))throw Error('Field outside repair scope');if(seen.has(f))throw Error('Duplicate field');seen.add(f);
  const old=f==='questionType'?question.questionType:d[f];if(equal(old,p.replace))throw Error('Empty change');
  if(['answer','questionType'].includes(f)){
   if(!equal(old,p.find))throw Error('Stale record');
   if(f==='questionType'&&!['scq','mcq','integerQuestion'].includes(p.replace))throw Error('Unknown question type');
  }else{
   if(typeof p.find!=='string'||!p.find||typeof old!=='string'||old.split(p.find).length!==2)throw Error('Patch must match exactly once');
   if(typeof p.replace!=='string')throw Error('Text replacement required');
   if(r.repair==='spelling'&&!equal(protectedTokens(p.find),protectedTokens(p.replace)))throw Error('Spelling repair cannot change mathematics');
   if(r.repair==='answer_form'&&!p.replace.includes(p.find))throw Error('Answer form must be additive');
   if(r.repair==='option_repair'){
    if(old.indexOf(p.find)<old.indexOf('(A)')||!old.includes('(A)'))throw Error('Option repair cannot change stem');
    if(!equal(p.find.match(/\([ABCD]\)/g)||[],p.replace.match(/\([ABCD]\)/g)||[]))throw Error('Option labels must be preserved');
   }
   if(/<\s*(script|iframe|object)|\bon\w+\s*=|javascript:/i.test(p.replace))throw Error('Unsafe markup');
  }
 }
 if(edits.length){const q=applyPatch(question,r),type=q.questionType,a=q[type].answer;
 if(type==='scq'&&(typeof a!=='string'||! /^[ABCD]$/.test(a)))throw Error('SCQ key invalid');
 if(type==='mcq'&&(!Array.isArray(a)||!a.length||new Set(a).size!==a.length||a.some(x=>!['A','B','C','D'].includes(x))))throw Error('MCQ key invalid');
 if(type==='integerQuestion'&&!/^-?\d+$/.test(String(a)))throw Error('Integer key invalid');}
}
