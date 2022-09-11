import asyncio
from operator import imod
import danmaku
import os, sys, getopt
import json
import time

async def printer(cid, q, dmc):
    while True:
        m = await q.get()
        if m['msg_type'] == 'danmaku':
            data = {
                'time': int(time.time()),
                'danmu': {
                    'name': m["name"],
                    'content': m["content"]
                }
            }
            with open(f'temp/{cid}.danmu', 'a') as f:
                f.write(json.dumps(data) + '\n')
        sock = os.popen(f'find temp -name {cid}.sock').read()
        if sock == '':
            await dmc.stop()

async def main(url, cid):
    q = asyncio.Queue()
    dmc = danmaku.DanmakuClient(url, q)
    asyncio.create_task(printer(cid, q, dmc))
    await dmc.start()

def start_get_danmu(argv):
    url = ''
    cid = ''
    try:
        opts, args = getopt.getopt(argv,"hu:c:",["url=","cid="])
    except getopt.GetoptError:
        print ('danmu.py -u <url> -c <cid>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('danmu.py -u <url> -c <cid>')
            sys.exit()
        elif opt in ("-u", "--url"):
            url = arg
        elif opt in ("-c", "--cid"):
            cid = arg
    print(f'url: {url}\ncid: {cid}')
    asyncio.run(main(url, cid))

if __name__ == '__main__':
    try:
        start_get_danmu(sys.argv[1:])
    except RuntimeError:
        print('danmu exit')
