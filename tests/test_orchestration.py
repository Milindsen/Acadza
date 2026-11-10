import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from engine.run import triage
from engine.guards import validate
ROOT=Path(__file__).resolve().parents[1]
qs=json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8'));reports=json.loads((ROOT/'data/reports.json').read_text(encoding='utf-8'));results=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
class OrchestrationTests(unittest.TestCase):
 def scenario(self,n=1):
  r=copy.deepcopy(next(r for r in results if r['reportId']==f'R{n:03}'));q=next(q for q in qs if q['_id']==r['questionId']);rs=[x for x in reports if x['questionId']==q['_id']];return q,rs,r
 def test_solver_is_blind_to_key_solution_and_student_comment(self):
  q,rs,r=self.scenario();solver={'derivation':'Independent phasor computation gives 50 volts','answer':'A','answerable':True,'assumptions':[]};verifier={'approved':True,'evidence':'Independent arithmetic and option match confirmed'}
  with patch('engine.run.completion',side_effect=[solver,r,verifier]) as call:
   out=triage(q,rs);payload=call.call_args_list[0].args[1];self.assertNotIn('answer',payload);self.assertNotIn('solution',payload);self.assertNotIn('reports',payload);self.assertEqual(len(out),3);self.assertEqual({x['reportId'] for x in out},{'R001','R002','R003'})
 def test_verifier_disagreement_routes_to_human(self):
  q,rs,r=self.scenario()
  with patch('engine.run.completion',side_effect=[{'derivation':'Independent solve concludes A','answer':'A','answerable':True,'assumptions':[]},r,{'approved':False,'evidence':'Insufficient verification'}]):self.assertTrue(all(x['route']=='faculty_review' for x in triage(q,rs)))
 def test_unanswerable_solver_cannot_auto_apply(self):
  q,rs,r=self.scenario()
  with patch('engine.run.completion',side_effect=[{'derivation':'Essential data might be absent','answer':'A','answerable':False,'assumptions':[]},r,{'approved':True,'evidence':'Verifier asserted support despite missing data'}]):self.assertEqual(triage(q,rs)[0]['route'],'faculty_review')
 def test_solver_key_disagreement_cannot_auto_apply(self):
  q,rs,r=self.scenario()
  with patch('engine.run.completion',side_effect=[{'derivation':'Independent solve proposes B','answer':'B','answerable':True,'assumptions':[]},r,{'approved':True,'evidence':'Verifier agrees with the proposed edit'}]):self.assertEqual(triage(q,rs)[0]['route'],'faculty_review')
 def test_spelling_numeric_injection_is_rejected(self):
  q,rs,r=self.scenario(12);r['edit']['replace']+=' 2'
  with self.assertRaises(ValueError):validate(q,r)
 def test_duplicate_checks_not_independent(self):
  q,rs,r=self.scenario();r['checks']=[r['checks'][0],r['checks'][0]]
  with self.assertRaises(ValueError):validate(q,r,automatic=True)
