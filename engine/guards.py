"""Pure validation and optimistic, atomic application. No model can bypass this module."""
import copy, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = json.loads((ROOT/'data/taxonomy.json').read_text(encoding='utf-8'))

def patches(result):
    e = result.get('edit')
    return e if isinstance(e,list) else [e] if e else []

def validate(q, result, automatic=False):
    if result.get('verdict') not in TAXONOMY['verdicts']: raise ValueError('Unknown verdict')
    if not isinstance(result.get('confidence'),(float,int)) or not 0 <= result['confidence'] <= 1: raise ValueError('Invalid confidence')
    if result.get('route') not in ('auto_apply','faculty_review','no_change'): raise ValueError('Unknown route')
    repair = result.get('repair')
    if result['verdict'] != 'defect':
        if repair or patches(result) or result['route'] != 'no_change': raise ValueError('Non-defect cannot mutate content')
        return
    if repair not in TAXONOMY['repairs']: raise ValueError('Unknown repair')
    rule=TAXONOMY['repairs'][repair]
    if not rule['auto'] and (patches(result) or result['route']!='faculty_review'): raise ValueError('Faculty authoring required')
    if result['route']=='auto_apply' and not patches(result): raise ValueError('No patch to apply')
    if automatic and (not rule['auto'] or result['route']!='auto_apply' or result['confidence'] < .97): raise ValueError('Automatic threshold not met')
    if automatic and repair=='answer_key' and len(result.get('checks',[])) < 2: raise ValueError('Two checks required')
    data=q[q['questionType']]
    seen=set()
    for p in patches(result):
        f=p.get('field')
        if f not in rule['fields']: raise ValueError('Field outside repair scope')
        if f in seen: raise ValueError('Use one surgical edit per field')
        seen.add(f)
        old=q['questionType'] if f=='questionType' else data.get(f)
        if old==p.get('replace'): raise ValueError('Empty change')
        if f in ('answer','questionType'):
            if old!=p.get('find'): raise ValueError('Stale record')
            if f=='questionType' and p.get('replace') not in ('scq','mcq','integerQuestion'): raise ValueError('Unknown question type')
        else:
            if not isinstance(p.get('find'),str) or not p['find'] or old.count(p['find'])!=1: raise ValueError('Patch must match exactly once')
            if not isinstance(p.get('replace'),str): raise ValueError('Text replacement required')
            if repair=='answer_form' and p['find'] not in p['replace']: raise ValueError('Answer form must be additive')
            if repair=='option_repair':
                pos=old.index(p['find']); start=re.search(r'\(A\)',old)
                if not start or pos < start.start(): raise ValueError('Option repair cannot change stem')
            if re.search(r'<\s*(script|iframe|object)|\bon\w+\s*=|javascript:',p['replace'],re.I): raise ValueError('Unsafe markup')
    if patches(result):
        candidate=apply(q,result,check=False)
        typ=candidate['questionType']; ans=candidate[typ]['answer']
        if typ=='scq' and (not isinstance(ans,str) or ans not in 'ABCD' or len(ans)!=1): raise ValueError('SCQ key invalid')
        if typ=='mcq' and (not isinstance(ans,list) or not ans or any(x not in ['A','B','C','D'] for x in ans) or len(set(ans))!=len(ans)): raise ValueError('MCQ key invalid')
        if typ=='integerQuestion' and not re.fullmatch(r'-?\d+',str(ans)): raise ValueError('Integer key invalid')

def apply(q,result,check=True):
    if check: validate(q,result)
    new=copy.deepcopy(q); oldtype=q['questionType']; data=new[oldtype]
    for p in patches(result):
        f=p['field']
        if f=='questionType': new['questionType']=p['replace']
        elif f=='answer': data[f]=p['replace']
        else: data[f]=data[f].replace(p['find'],p['replace'],1)
    if new['questionType']!=oldtype: new[new['questionType']]=new.pop(oldtype)
    return new
