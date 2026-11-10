"""Dependency-free Worker bundle; the generated file embeds the public demo assets."""
import base64,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data={k:json.loads((root/p).read_text(encoding='utf-8')) for k,p in [('questions','data/questions.json'),('reports','data/reports.json'),('results','results.json')]}
taxonomy=json.loads((root/'data/taxonomy.json').read_text(encoding='utf-8'))
assets={}
for name,mime in [('index.html','text/html; charset=utf-8'),('app.js','application/javascript; charset=utf-8'),('style.css','text/css; charset=utf-8'),('walkthrough.html','text/html; charset=utf-8')]:
 assets['/'+name]={'type':mime,'body':(root/'web'/name).read_text(encoding='utf-8')}
video=root/'dist/walkthrough.mp4'
if video.exists():assets['/walkthrough.mp4']={'type':'video/mp4','base64':True,'body':base64.b64encode(video.read_bytes()).decode()}
guards=(root/'worker/guards.mjs').read_text(encoding='utf-8').replace('export ','')
app=(root/'worker/app.mjs').read_text(encoding='utf-8').replace("import {validate,applyPatch} from './guards.mjs';",'').replace('export ','')
bundle=guards+'\n'+app+'\nconst dataset='+json.dumps(data,ensure_ascii=False)+';\nconst taxonomy='+json.dumps(taxonomy,ensure_ascii=False)+';\nconst assets='+json.dumps(assets,ensure_ascii=False)+';\nexport default createApp({dataset,taxonomy,assets});\n'
out=root/'dist/server';out.mkdir(parents=True,exist_ok=True);(out/'index.js').write_text(bundle,encoding='utf-8')
manifest=json.loads((root/'.openai/hosting.json').read_text(encoding='utf-8'));manifest.pop('static',None);manifest.update(d1='DB',r2=None)
(root/'.openai/hosting.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(root/'dist/.openai').mkdir(exist_ok=True);(root/'dist/.openai/hosting.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Bundled Worker with durable database binding and',len(assets),'assets.')
