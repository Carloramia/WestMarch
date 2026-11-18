"""Local deployment sandbox. Run: python server.py; open http://127.0.0.1:8877/"""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json,time,secrets,threading
from simulate import Battle,validate_scenario
from campaign import catalog,prepare,player_frame,player_summary
from settlement import Settlement
ROOT=Path(__file__).resolve().parent
SESSIONS={}
RETRIES={}
SETTLEMENTS={}
LOCK=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def do_GET(self):
  if self.path=='/api/campaign':self.reply(200,catalog());return
  if self.path=='/':self.path='/'+__import__('urllib.parse',fromlist=['quote']).quote('村庄布防回放.html')
  super().do_GET()
 def do_POST(self):
  if self.path not in ('/api/simulate','/api/start','/api/tick','/api/stop','/api/order','/api/settlement'):self.send_error(404);return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=65536:raise ValueError('请求过大或为空')
   payload=json.loads(self.rfile.read(size))
   if self.path=='/api/settlement':
    with LOCK:
     action=payload.get('action');key=payload.get('key')
     if action=='new':
      settlement=Settlement(payload.get('level'),secrets.randbits(64));key=secrets.token_urlsafe(18)
      if len(SETTLEMENTS)>=24:SETTLEMENTS.pop(next(iter(SETTLEMENTS)))
      SETTLEMENTS[key]=settlement
      result={}
     else:
      settlement=SETTLEMENTS.get(key)
      if not settlement:raise ValueError('经营会话已失效，请重新进入关卡')
      result={}
      if action=='queue':settlement.queue(payload.get('target'),payload.get('kind'))
      elif action=='advance':
       count=payload.get('steps',1)
       if type(count) is not int or count not in (1,3):raise ValueError('每次可推进 1 或 3 步')
       initial_jobs=len(settlement.jobs)
       was_safe=settlement.clock<settlement.safe_until
       for _ in range(count):
        encounter=settlement.advance(payload.get('units'))
        if encounter or len(settlement.jobs)<initial_jobs or (was_safe and settlement.clock>=settlement.safe_until):
         break
       if encounter:
        b,limit=encounter;session=secrets.token_urlsafe(18)
        save_session(session,b,limit,settlement)
        result={'session':session,'summary':player_summary(b),'frames':[player_frame(b.history[0])]}
      else:raise ValueError('经营操作无效')
     self.reply(200,{**result,'key':key,'settlement':settlement.public()})
    return
   if self.path in ('/api/tick','/api/stop','/api/order'):
    with LOCK:
     key=payload.get('session');session=SESSIONS.get(key)
     if not session:raise ValueError('战斗已结束或会话失效，请返回布防重新开始')
     if self.path=='/api/stop':SESSIONS.pop(key);self.reply(200,{'stopped':True});return
     b,limit,_,settlement=session
     if self.path=='/api/order':
      receipt=b.issue_field_order(payload.get('gate'));self.reply(200,receipt);return
     frame=settlement.step(b,limit) if settlement else b.step(limit)
     SESSIONS[key]=(b,limit,time.monotonic(),settlement)
     campaign=b.profile=='campaign'
     result={'frame':player_frame(frame) if campaign else frame,'summary':player_summary(b) if campaign else b.summary(),'done':bool(b.result)}
     if settlement:result['settlement']=settlement.public()
    self.reply(200,result);return
   campaign=self.path=='/api/start' and 'level' in payload
   if campaign:
    previous=payload.get('retry')
    seed=None
    if previous:
     with LOCK:
      retry=RETRIES.get(previous)
      if not retry or retry[0]!=payload['level'] or time.monotonic()-retry[2]>3600:
       raise ValueError('上场敌情已失效，请关闭同敌情重试后开战')
      seed=retry[1]
    b,limit=prepare(payload,seed)
   else:
    validate_scenario(payload)
    seed=payload.get('seed',7);limit=payload.get('limit',72)
    if type(seed)!=int or not 0<=seed<=999999 or type(limit)!=int or not 1<=limit<=144:raise ValueError('种子须为0至999999，轮次须为1至144')
    b=Battle('custom',seed,payload)
   if self.path=='/api/start':
    b.snapshot();key=secrets.token_urlsafe(18)
    with LOCK:
     save_session(key,b,limit)
     if campaign:
      for old in list(RETRIES):
       if time.monotonic()-RETRIES[old][2]>3600:RETRIES.pop(old)
      if len(RETRIES)>=128:RETRIES.pop(next(iter(RETRIES)))
      RETRIES[key]=(payload['level'],b.seed,time.monotonic())
    result={'session':key,'summary':player_summary(b) if campaign else b.summary(),'frames':[player_frame(b.history[0])] if campaign else b.history,'done':False}
   else:result={'summary':b.run(limit),'frames':b.history}
   self.reply(200,result)
  except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:self.reply(400,{'error':str(e)})
 def reply(self,status,value):
  raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf8')
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

def save_session(key,battle,limit,settlement=None):
 for old in list(SESSIONS):
  if time.monotonic()-SESSIONS[old][2]>3600:SESSIONS.pop(old)
 if len(SESSIONS)>=32:SESSIONS.pop(next(iter(SESSIONS)))
 SESSIONS[key]=(battle,limit,time.monotonic(),settlement)

if __name__=='__main__':
 print('Village sandbox: http://127.0.0.1:8877/',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8877),Handler).serve_forever()
