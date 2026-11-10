"""Bundle a transparent offline evaluation demo for any static host."""
import json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];dist=root/'dist';dist.mkdir(exist_ok=True)
for f in (root/'web').iterdir():shutil.copy2(f,dist/f.name)
data={k:json.loads((root/p).read_text(encoding='utf-8')) for k,p in [('questions','data/questions.json'),('reports','data/reports.json'),('results','results.json')]}
data.update(states={},audit=[],mode='demo')
(dist/'dataset.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
print('Static demo built: dist/')
