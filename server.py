"""Zero-dependency local faculty API with durable SQLite and atomic audit writes."""
import hashlib,json,os,secrets,sqlite3,threading
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from contextlib import contextmanager
from engine.guards import validate,apply
ROOT=Path(__file__).resolve().parent
QUESTIONS=json.loads((ROOT/'data/questions.json').read_text(encoding='utf-8'))
REPORTS=json.loads((ROOT/'data/reports.json').read_text(encoding='utf-8'))
RESULTS=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
DB=Path(os.environ.get('ACADZA_DB',str(ROOT/'work/review.sqlite3')));DB.parent.mkdir(parents=True,exist_ok=True)
TOKEN=os.environ.get('REVIEW_TOKEN',secrets.token_urlsafe(24))
@contextmanager
def db():
 c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row
 try:
  with c:yield c
 finally:c.close()
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, content TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT "pending"); CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, questionId TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL, note TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL, proposal TEXT, version INTEGER NOT NULL);')
  for q in QUESTIONS:c.execute('INSERT OR IGNORE INTO records(id,content) VALUES (?,?)',(q['_id'],json.dumps(q)))
def snapshot():
 with db() as c:
  records=c.execute('SELECT * FROM records').fetchall();audit=c.execute('SELECT * FROM audit ORDER BY at DESC').fetchall()
 return {'questions':[json.loads(r['content']) for r in records],'reports':REPORTS,'results':RESULTS,'states':{r['id']:{'version':r['version'],'status':r['status']} for r in records},'audit':[{**dict(a),'before':json.loads(a['before']),'after':json.loads(a['after']),'proposal':json.loads(a['proposal']) if a['proposal'] else None} for a in audit],'mode':'server','baseline':'Assistant-reviewed precomputed results; live inference available separately'}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
 def send_json(self,value,status=200):
  data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/api/state':return self.send_json(snapshot())
  if self.path=='/api/health':return self.send_json({'ok':True,'storage':'sqlite','inference':'precomputed'})
  if self.path=='/api/results':return self.send_json(RESULTS)
  if self.path=='/api/export':return self.send_json(snapshot())
  return super().do_GET()
 def do_POST(self):
  if self.path!='/api/action':return self.send_json({'error':'Not found'},404)
  if self.headers.get('Authorization')!='Bearer '+TOKEN:return self.send_json({'error':'Enter the reviewer token printed when the server started.'},401)
  if int(self.headers.get('Content-Length',0))>65536:return self.send_json({'error':'Request too large'},413)
  try:
   b=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
   with db() as c:
    c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM records WHERE id=?',(b['questionId'],)).fetchone()
    if not r:raise ValueError('Unknown question')
    if b.get('version')!=r['version']:return self.send_json({'error':'This case changed. Refresh before acting.'},409)
    if r['status']!='pending':raise ValueError('Case already resolved')
    before=json.loads(r['content']);after=before;action=b['action'];proposal=next(x for x in RESULTS if x['questionId']==b['questionId'])
    if action in ('approve','edit'):
     if action=='edit':proposal={**proposal,'edit':b.get('edit'),'route':'faculty_review'}
     validate(before,proposal)
     if not proposal.get('edit'):raise ValueError('No grounded edit exists. Use Escalate for faculty authoring.')
     after=apply(before,proposal);status='approved'
    elif action=='reject':status='rejected'
    elif action=='close':
     if proposal['verdict']=='defect':raise ValueError('Defects need approval, rejection or escalation')
     status='closed'
    elif action=='escalate':status='escalated'
    else:raise ValueError('Invalid action')
    if action in ('reject','escalate','edit') and not str(b.get('note','')).strip():raise ValueError('Add a short review reason')
    actor=str(b.get('actor','')).strip()[:80]
    if not actor:raise ValueError('Reviewer name required')
    c.execute('UPDATE records SET content=?,version=version+1,status=? WHERE id=?',(json.dumps(after),status,b['questionId']))
    c.execute('INSERT INTO audit VALUES (?,?,?,?,?,?,?,?,?,?)',(secrets.token_hex(12),b['questionId'],action,actor,datetime.now(timezone.utc).isoformat(),str(b.get('note',''))[:2000],json.dumps(before),json.dumps(after),json.dumps(proposal),r['version']+1))
   return self.send_json({'ok':True,'status':status,'version':r['version']+1})
  except (ValueError,KeyError,StopIteration,TypeError) as e:return self.send_json({'error':str(e)},400)
  except Exception:return self.send_json({'error':'Storage operation failed; no changes committed'},500)
if __name__=='__main__':
 init();port=int(os.environ.get('PORT','8765'));print(f'Acadza Review: http://127.0.0.1:{port}\nReviewer token: {TOKEN}',flush=True)
 ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),port),Handler).serve_forever()
