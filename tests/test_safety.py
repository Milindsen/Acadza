import copy,json,sys,unittest,tempfile,threading,urllib.request,urllib.error,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.guards import validate,apply
Q=json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8'));R=json.loads((ROOT/'results.json').read_text(encoding='utf-8'));qs={q['_id']:q for q in Q}
def result(n):return copy.deepcopy(next(r for r in R if r['reportId']==f'R{n:03}'))
class GuardTests(unittest.TestCase):
 def test_every_report_and_taxonomy(self):
  self.assertEqual(len(R),44);self.assertEqual(len({r['reportId'] for r in R}),44)
  for r in R:validate(qs[r['questionId']],r,automatic=r['route']=='auto_apply')
 def test_scope_escalates(self):
  r=result(12);r['edit']['field']='answer'
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r)
 def test_faculty_only_cannot_write(self):
  r=result(25);r['edit']={'field':'question','find':'figure','replace':'picture'}
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r)
 def test_stale_anchor_rejected(self):
  r=result(12);q=copy.deepcopy(qs[r['questionId']]);q['scq']['question']=q['scq']['question'].replace('Epithellial tisue','Epithelial tissue')
  with self.assertRaises(ValueError):apply(q,r)
 def test_duplicate_anchor_rejected(self):
  r=result(12);q=copy.deepcopy(qs[r['questionId']]);q['scq']['question']+='Epithellial tisue'
  with self.assertRaises(ValueError):apply(q,r)
 def test_low_confidence_rejected_for_auto(self):
  r=result(1);r['confidence']=.96
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r,automatic=True)
 def test_key_requires_two_checks(self):
  r=result(1);r['checks']=[]
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r,automatic=True)
 def test_injection_no_mutation(self):
  r=result(27);self.assertEqual(r['verdict'],'no_error');self.assertIsNone(r['edit']);self.assertEqual(apply(qs[r['questionId']],r),qs[r['questionId']])
 def test_atomic_type_migration(self):
  r=result(21);q=apply(qs[r['questionId']],r);self.assertEqual(q['questionType'],'scq');self.assertEqual(q['scq']['answer'],'B');self.assertNotIn('mcq',q)
 def test_unknown_question_type_rejected(self):
  r=result(21);r['edit'][0]['replace']='invented_type'
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r)
 def test_mcq_normalized(self):
  r=result(20);q=apply(qs[r['questionId']],r);self.assertEqual(q['mcq']['answer'],['A','B','D'])
 def test_student_wrong_but_key_broken(self):self.assertEqual(result(4)['edit']['replace'],'D')
 def test_missing_distractor_abstains(self):self.assertIsNone(result(9)['edit']);self.assertEqual(result(9)['route'],'faculty_review')
 def test_correct_key_wrong_solution(self):
  r=result(16);q=apply(qs[r['questionId']],r);self.assertEqual(q['integerQuestion']['answer'],'20');self.assertIn('20',q['integerQuestion']['solution'])
 def test_unsafe_markup_rejected(self):
  r=result(12);r['edit']['replace']='<img src=x onerror=alert(1)>'
  with self.assertRaises(ValueError):validate(qs[r['questionId']],r)
 def test_immutable_source(self):
  before=copy.deepcopy(Q)
  for r in R:apply(qs[r['questionId']],r)
  self.assertEqual(Q,before)
class APITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  (ROOT/'work').mkdir(exist_ok=True)
  cls.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');os.environ['ACADZA_DB']=str(Path(cls.tmp.name)/'test.sqlite');os.environ['REVIEW_TOKEN']='test-reviewer-token'
  import server
  cls.mod=server;server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.url=f'http://127.0.0.1:{cls.http.server_port}';cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
 def request(self,payload,token='test-reviewer-token'):
  req=urllib.request.Request(self.url+'/api/action',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_auth_atomic_approval_and_conflict(self):
  r=result(1);p={'questionId':r['questionId'],'version':0,'actor':'Test reviewer','action':'approve'}
  self.assertEqual(self.request(p,'bad')[0],401);self.assertEqual(self.request(p)[0],200);self.assertEqual(self.request(p)[0],409)
  with urllib.request.urlopen(self.url+'/api/state') as resp:s=json.load(resp)
  a=next(x for x in s['audit'] if x['questionId']==r['questionId']);self.assertEqual(a['before']['scq']['answer'],'C');self.assertEqual(a['after']['scq']['answer'],'A')
 def test_edit_reject_escalate_close(self):
  for n,action in [(12,'edit'),(15,'reject'),(25,'escalate'),(27,'close')]:
   r=result(n);payload={'questionId':r['questionId'],'version':0,'actor':'Test reviewer','action':action,'note':'Faculty checked this case'}
   if action=='edit':payload['edit']=r['edit']
   self.assertEqual(self.request(payload)[0],200,action)
 def test_invalid_patch_rolls_back(self):
  r=result(22);bad=copy.deepcopy(r['edit']);bad['find']='not present';p={'questionId':r['questionId'],'version':0,'actor':'Reviewer','action':'edit','note':'test','edit':bad}
  self.assertEqual(self.request(p)[0],400)
  with urllib.request.urlopen(self.url+'/api/state') as resp:s=json.load(resp)
  self.assertEqual(s['states'][r['questionId']]['version'],0);self.assertFalse(any(a['questionId']==r['questionId'] for a in s['audit']))
if __name__=='__main__':unittest.main()
