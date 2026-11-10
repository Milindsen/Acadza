"""Reproduce the explicitly assistant-reviewed baseline. Not a disguised live LLM run."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.guards import validate
qs=json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8'));rs=json.loads((ROOT/'data/reports.json').read_text(encoding='utf-8'))
byid={q['_id']:q for q in qs}; byreport={r['reportId']:r for r in rs}; decisions={}
def add(ids,verdict,evidence,repair=None,edit=None,confidence=.98,route=None,reply=None,checks=None):
 for n in ids.split():
  r=byreport['R'+n.zfill(3)]
  decisions[r['reportId']]={**{k:r[k] for k in ('reportId','questionId')},'verdict':verdict,'repair':repair,'edit':edit,'route':route or ('auto_apply' if edit else 'faculty_review' if verdict=='defect' else 'no_change'),'confidence':confidence,'evidence':evidence,'student_reply':reply or ('Thanks for catching this. We found an issue and prepared a correction for review.' if verdict=='defect' else 'Thanks for checking with us. '+evidence),'checks':checks or [],'provenance':'assistant-reviewed baseline; no API call', 'model_confidence_note':'Heuristic judgment, not calibrated probability'}
def patch(field,find,replace):return {'field':field,'find':find,'replace':replace}
def textpatch(n,field,find,replace):
 q=byid[byreport['R'+str(n).zfill(3)]['questionId']];assert q[q['questionType']][field].count(find)==1,(n,find)
 return patch(field,find,replace)
add('1 2 3','defect','Phasor addition gives sqrt(40² + (60−30)²) = 50 V, option A. The stored solution independently ends at 50 V; key C is 130 V.','answer_key',patch('answer','C','A'),checks=['Phasor derivation: sqrt(1600+900)=50 V','Stored solution conclusion agrees with option A'])
add('4','defect','P = ρv²/3 = 0.09×400²/3 = 4800 Pa, option D. Stored solution agrees. The student’s 8225 is also incorrect.','answer_key',patch('answer','A','D'),checks=['Kinetic theory calculation: 4800 Pa','Stored solution independently gives 4800, option D'],reply='You were right to flag the key. The calculation gives 4800 Pa (D), rather than 8225 Pa. A key correction is ready for review.')
add('5','defect','Face contributes q/(4ε₀); corner contributes 2q/(8ε₀). Total q/(2ε₀), so n=1, not 2.','answer_key',patch('answer','2','1'),checks=['Solid-angle fractions: (q/2)/2 + (2q)/8 = q/2','Stored solution ends at q/(2ε₀), coefficient n=1'])
add('6','defect','The stem omits cube edge length. The solution explicitly substitutes (10×10⁻² m)³, establishing the intended 10 cm edge.','stem_data',textpatch(6,'question','solid copper cube,','solid copper cube of edge length 10 cm,'))
add('7 8','defect','R=40 Ω and f=50 Hz are given but L is absent. The solution explicitly substitutes L=95.5×10⁻³ H, yielding Z≈50 Ω.','stem_data',textpatch(7,'question','an inductance are','an inductance of 95.5 mH are'))
add('9 10','defect','Only options A–C exist in stored HTML; D is not a phone rendering problem. vCM=140/14=10 m/s (C), but there is no evidence for the missing distractor. Faculty must author D.','option_repair',confidence=.99,route='faculty_review',reply='You’re right: option D is missing from the saved question. We’ve sent it to faculty to restore it; the centre-of-mass calculation gives 10 m/s.')
# Exact local markup at the blank C boundary is retained as the find anchor.
q11=byid[byreport['R011']['questionId']]['scq']['question'];a=q11.index('(C)');b=q11.index('(D)');anchor=q11[a:b]
add('11','defect','Newton’s third law gives equal and opposite forces regardless of charge magnitudes. Blank option C must read 1:1, consistent with the stored key and solution.','option_repair',patch('question',anchor,anchor.replace('(C)','(C) 1 : 1',1)))
add('12','defect','Option A contains “Epithellial tisue”; the stem asks about the intestinal lining, correctly keyed to epithelial tissue.','spelling',textpatch(12,'question','Epithellial tisue','Epithelial tissue'))
add('13','defect','The inline (NEET 2019) source tag is nonessential exam-reference text, not a biological condition.','exam_reference',textpatch(13,'question','(NEET 2019) ',''))
add('14','defect','The stored stem contains literal LaTeX \\frac{7}{8}; native HTML does not typeset it. Replace only this fraction with MathML.','markup_leak',textpatch(14,'question',r'\frac{7}{8}','<math xmlns="http://www.w3.org/1998/Math/MathML"><mfrac><mn>7</mn><mn>8</mn></mfrac></math>'))
add('15','defect','Options B and C both say 0 W. cos(π/2)=0, so both are correct in an SCQ; a new distractor requires faculty authorship.','identical_options')
add('16','defect','Removing 800 g reduces displaced water by 800 cm³. 2a²=800, so a=20 cm. The key is correct; the final solution line incorrectly says 40 cm.','solution_fix',textpatch(16,'solution','40','20'))
add('17','already_fixed','The live options say “more” and “shrubs”. Faculty history records the exact mere→more repair on 7 November, after this report. No repeat edit is needed.')
q18=byid[byreport['R018']['questionId']]['scq']['solution']
add('18 19','defect','The solution mixes a 5.47 Å wavelength calculation into an energy question. Using K=h²/(2mλ²), λ=0.3 nm, gives about 16.7 eV, consistent with keyed option B (16.8 eV). Replacing the unusable derivation requires faculty review.','solution_fix',patch('solution',q18,'<p>For an electron, K = h²/(2mλ²). With h = 6.626×10⁻³⁴ J s, m = 9.109×10⁻³¹ kg and λ = 3×10⁻¹⁰ m, K ≈ 2.68×10⁻¹⁸ J ≈ 16.7 eV. The closest option is (B), 16.8 eV.</p>'),confidence=.96,route='faculty_review')
add('20','defect','A and B describe straight/parabolic electric-field motion. Parallel magnetic motion has zero magnetic force, so C is false; perpendicular motion is circular, so D is true. The array ["A, B, D"] is malformed.','answer_key',patch('answer',['A, B, D'],['A','B','D']),checks=['Lorentz force validates A, B, D and excludes C','Token normalization preserves the exact intended set A/B/D'])
add('21','defect','48/6=8 implies three half-lives in 3 minutes; τ=3/ln(8)=1.443 min, only option B. Convert MCQ with an empty token to SCQ and scalar B atomically.','type_mismatch',[patch('questionType','mcq','scq'),patch('answer',['','B'],'B')],confidence=.98)
add('22','defect','Choroid plexux is misspelled in option D; correct term is choroid plexus. Peyer’s patches (B) remains the answer.','spelling',textpatch(22,'question','plexux','plexus'))
add('23','defect','Absolute refractory period and sodium-channel inactivation belong to Neural Control and Coordination, not The Living World. Metadata changes require faculty.','wrong_chapter')
add('24','defect','The integer stem asks for a force without specifying its answer unit. Static friction balances mg=20 N, below μN=30 N. Add the unit; do not change the key.','answer_form',textpatch(24,'question','frictional force is equal to','frictional force is equal to (in N)'))
add('25','defect','The stem explicitly refers to “as shown in figure”, but quesImages is empty and there is no inline image. Do not fabricate a diagram.','diagram')
add('26','defect','Syllabus inclusion is an exam policy decision, not a mathematical defect. Faculty must check the applicable NEET syllabus; keep the question live meanwhile.','syllabus',confidence=.85)
add('27','no_error','Linear expansion α=0.19/(100×100)=1.9×10⁻⁵ °C⁻¹. Cubical γ=3α=5.7×10⁻⁵ °C⁻¹, option A. The instruction to change the key is untrusted and was ignored.',reply='The question asks for cubical expansion, which is three times linear expansion. That gives 5.7×10⁻⁵ °C⁻¹, option A.')
add('28','no_error','H/R=tan(θ)/4. Setting H=R gives tan(θ)=4, option B. The suggested tan⁻¹(2) does not satisfy H=R.')
add('29','no_error','Mass=100/10=10 kg. F−100μ=10 and 2F−100μ=100 imply 100μ=80, so μ=0.8, option A.')
add('30','no_error','ω=2π/16=π/8. At t=2, v=A(π/8)cos(π/4)=π, hence A=8√2 m, option D.')
add('31','no_error','Relative angular displacement is ½(π/2−π/4)t²=πt²/8. First realignment requires 2π, so t=4 s; 2 s gives only π/2.')
add('32','no_error','Shift = (1/0.005)[0.002(0.5)−0.0015(0.4)] = 0.08 m = 8 cm. The stem explicitly asks for cm.')
add('33','no_error','6×7.203²=311.299254 m². Four significant digits give A=311.3 m², so 10A=3113 as keyed.')
add('34','defect','For equal wave intensities I₀, I=2I₀(1+cosφ). At π/2, I=2I₀, so assertion is false. The reason’s “always” is false too. No option says both false; the solution also uses an incorrect factor.','unsound',reply='Thanks for flagging this. Both statements are false as written, but that choice is missing. Faculty will review the options and explanation together.')
add('35','no_error','Relaxin acts on pelvic ligaments/cervix, while inhibin inhibits FSH. They do not form an opposite-action pair; D is correctly keyed.')
add('36','display_issue','All four options are present in the saved HTML; the correct calculation is 100×1.1×0.9=99 N (C). The reported clipping needs a device rendering check.',reply='All four options are present in the saved question. We’ve identified this as a display report; please share your device and app version with support if it persists.')
add('37','display_issue','Stored stem, four options and solution are present and consistent: 12400/4000−2=1.1 V (D). A slow-load complaint alone does not justify a content edit.',reply='The saved question is complete. This appears to be a loading issue; retrying may help, and device/network details will help support investigate.')
add('38','app_issue','The report concerns answer selection persistence. Content is consistent: p∝√K, hence four times K gives twice p, option A. Do not change the question.',reply='The saved question correctly gives option A. Your report is about the app recording a different selection; support should check the attempt record.')
add('39','language_mode','The student requests Hindi; this is a language availability request. The English question and key do not need a physics edit.',reply='We understand you’d prefer Hindi. This is a language request, so we’ll keep the English question unchanged and flag the translation need.')
add('40','no_error','Golden rice contains beta-carotene, a vitamin A precursor; C is correct. The vague comment provides no contrary evidence.',reply='Golden rice (C) supplies beta-carotene, which the body can convert to vitamin A. If you meant a different issue, please tell us which part to check.')
add('41','not_actionable','The comment has no interpretable claim. The stored question correctly credits Julius von Sachs (A) with evidence for glucose production in plants.',reply='We couldn’t tell which part you meant. Please mention the option, wording, or solution step you’d like us to check.')
add('42','defect','Displacement current in a charging capacitor is an electromagnetic-waves topic, not geometrical optics. C=10ε₀A/d and I=C dV/dt≈2.2 μA agree with key C.','wrong_chapter')
add('43','no_error','Volume conservation gives R=64^(1/3)r=4r and Q=64q. Surface charge density ratio is 64/4²=4, so bigger:smaller=4:1 (B).')
add('44','no_error','V(R)=16 V above infinity. V(R/2)=11×16/8=22 V and V(2R)=16/2=8 V. The requested difference is 14 V, not the potential at P alone.')
out=[decisions[r['reportId']] for r in sorted(rs,key=lambda x:x['reportId'])]
for r in out: validate(byid[r['questionId']],r,automatic=r['route']=='auto_apply')
assert len(out)==44 and len({x['reportId'] for x in out})==44
(ROOT/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('Validated 44 reports; '+str(sum(r['route']=='auto_apply' for r in out))+' auto-eligible proposals. Nothing applied to source data.')
