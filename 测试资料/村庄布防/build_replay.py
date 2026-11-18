import json
from simulate import SKILLS
from pathlib import Path
root=Path(__file__).resolve().parent
template=(root/'replay.template.html').read_text(encoding='utf8')
payload=json.loads((root/'replays.json').read_text(encoding='utf8'))
payload['skills']=SKILLS
data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
(root/'村庄布防回放.html').write_text(template.replace('__SIMULATION_DATA__',data),encoding='utf8')
print('Replay built')
