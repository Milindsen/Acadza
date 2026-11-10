"""Live orchestration: python -m engine.run --output results.live.json
Uses OPENAI_API_KEY; server-side only. Offline baseline lives in scripts/build_results.py.
"""
import argparse,json,os,time,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from engine.prompts import SOLVER,TRIAGE,VERIFIER
from engine.guards import validate
ROOT=Path(__file__).resolve().parents[1]
def completion(prompt,payload):
 key=os.environ.get('OPENAI_API_KEY')
 if not key: raise RuntimeError('Set OPENAI_API_KEY for live inference. Use scripts/build_results.py for the reviewed baseline.')
 body={'model':os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),'messages':[{'role':'system','content':prompt},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],'response_format':{'type':'json_object'},'temperature':0}
 request=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 for attempt in range(3):
  try:
   with urllib.request.urlopen(request,timeout=90) as response: raw=json.load(response)
   return json.loads(raw['choices'][0]['message']['content'])
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
def triage(q,reports):
 d=q[q['questionType']]
 # No key or stored solution goes to the first solver. Student hints cannot steer it.
 solve=completion(SOLVER,{'questionType':q['questionType'],'question':d['question'],'images':d.get('quesImages',[])})
 proposal=completion(TRIAGE,{'question':q,'reports':reports,'independent_solve':solve,'taxonomy':json.loads((ROOT/'data/taxonomy.json').read_text())})
 proposal['questionId']=q['_id'];proposal['checks']=[solve.get('derivation','')];proposal['provenance']='live LLM: '+os.environ.get('OPENAI_MODEL','gpt-4.1-mini')
 if proposal.get('verdict')=='defect' and proposal.get('edit'):
  verification=completion(VERIFIER,{'question':q,'solve':solve,'proposal':proposal})
  if verification.get('approved') is True:proposal['checks'].append(verification['evidence'])
  else:proposal['route']='faculty_review';proposal['verifier_objection']=verification.get('evidence')
  # Never allow low-confidence or incomplete evidence through the auto gate.
  if proposal.get('confidence',0)<.97 or len(proposal['checks'])<2:proposal['route']='faculty_review'
 validate(q,proposal,automatic=proposal['route']=='auto_apply')
 return [{**proposal,'reportId':r['reportId']} for r in reports]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='results.live.json');parser.add_argument('--workers',type=int,default=2);args=parser.parse_args()
 qs=json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8'));reports=json.loads((ROOT/'data/reports.json').read_text(encoding='utf-8'))
 groups=[(q,[r for r in reports if r['questionId']==q['_id']]) for q in qs];groups=[g for g in groups if g[1]]
 if not os.environ.get('OPENAI_API_KEY'):raise SystemExit('Missing OPENAI_API_KEY. No live run performed.')
 def work(g):
  try:return triage(*g)
  except Exception as e:
   # Operational failures are a separate file, not fake taxonomy verdicts.
   return [{'reportId':r['reportId'],'questionId':g[0]['_id'],'error':type(e).__name__+': '+str(e),'status':'triage_failed'} for r in g[1]]
 with ThreadPoolExecutor(max_workers=min(4,max(1,args.workers))) as pool:out=[x for batch in pool.map(work,groups) for x in batch]
 dest=ROOT/args.output;dest.write_text(json.dumps(sorted(out,key=lambda r:r['reportId']),ensure_ascii=False,indent=2),encoding='utf-8')
 errors=sum('error' in r for r in out);print(f'{len(out)} reports; {errors} failed. Output: {dest.name}')
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
