import asyncio,json,pathlib,sys,os
sys.path.insert(0,str(pathlib.Path(os.environ.get('TEMP','.'))/'waijing-tts'))
import edge_tts
ROOT=pathlib.Path(__file__).resolve().parent.parent
async def main():
 sem=asyncio.Semaphore(3)
 async def one(i,row):
  async with sem:
   voice='zh-CN-YunxiNeural' if i not in (2,3) else 'zh-CN-YunjianNeural'
   await edge_tts.Communicate(row[2],voice,rate='+3%').save(str(ROOT/'音频'/f'v2_{i:02d}.mp3'))
   print(f'voice {i:02d} ready',flush=True)
 await asyncio.gather(*(one(i,r) for i,r in enumerate(json.loads((ROOT/'源文件'/'旁白_v2.json').read_text(encoding='utf8')))))
asyncio.run(main())
