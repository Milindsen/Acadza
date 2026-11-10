"""GitHub Pages frontend using the existing durable API, with a per-browser workspace token."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];out=root/'docs';out.mkdir(exist_ok=True)
backend='https://acadza-question-care-milind.magnetichymn1.chatgpt.site'
html=(root/'web/index.html').read_text(encoding='utf-8').replace('href="/"','href="./"').replace('href="/style.css"','href="./style.css"').replace('src="/app.js"','src="./app.js"')
(out/'index.html').write_text(html,encoding='utf-8')
s=(root/'web/app.js').read_text(encoding='utf-8')
prefix="""const backend=BACKEND;
function cloudFetch(path,options={}){let id=localStorage.getItem('acadza-cloud-workspace');if(!id){id=crypto.randomUUID();localStorage.setItem('acadza-cloud-workspace',id)}const headers={...(options.headers||{}),Authorization:'Bearer '+id};return fetch(backend+path,{...options,headers,credentials:'omit'})}
""".replace('BACKEND',json.dumps(backend))
s=prefix+s.replace("fetch('/api/","cloudFetch('/api/").replace("fetch('/dataset.json')","fetch('./dataset.json')")
(out/'app.js').write_text(s,encoding='utf-8');(out/'style.css').write_text((root/'web/style.css').read_text(encoding='utf-8'),encoding='utf-8')
video=(root/'web/walkthrough.html').read_text(encoding='utf-8').replace('href="/"','href="./"').replace('src="/walkthrough.mp4"','src="'+backend+'/walkthrough.mp4"').replace('href="/walkthrough.mp4"','href="'+backend+'/walkthrough.mp4"')
(out/'walkthrough.html').write_text(video,encoding='utf-8');(out/'.nojekyll').write_text('')
print('GitHub Pages frontend prepared in docs/. Cloud API retains durable decisions.')
