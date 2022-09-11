import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from asyncio_mqtt import Client, MqttError
import random
import json
from cc_live import CC
from bilibili_live import BiliBili
import os

host = '192.168.1.8'
mqtt_port = 1883
keepalive = 60
server_topic = '/live/cc/server'
client_topic = '/live/cc/client/'
will_topic = '/live/cc/will'
client_id = f'livecc-server-{random.randint(0, 1000)}'
username = 'livecc'
password = '203039'
cids = []

async def post_to_topic(client, topic, message):
    print(f'[send] topic = "{topic}"\nmsg = {message}')
    await client.publish(topic, message, qos=0)

async def run_mqtt():
    async with AsyncExitStack() as stack:
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)
        client = Client(hostname=host, port=mqtt_port, keepalive=keepalive,
            client_id=client_id, username=username, password=password)
        await stack.enter_async_context(client)
        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(log_messages(client, messages, cids))
        tasks.add(task)
        await client.subscribe(server_topic)
        await client.subscribe(will_topic)
        task = asyncio.create_task(get_danmu(client, cids))
        tasks.add(task)
        await asyncio.gather(*tasks)

async def get_danmu(client, cids):
    last_danmu = {}
    while True:
        for cid in cids:
            danmu = os.popen(f'tail -n 1 temp/{cid}.danmu').read()
            if danmu != '':
                new_danmu = json.loads(danmu)
                if last_danmu != {}:
                    if last_danmu["time"] != new_danmu["time"]:
                        last_danmu = new_danmu
                        print(last_danmu)
                        msg = {
                            'code': 0,
                            'type': 'resp_get_danmu',
                            'data': {
                                'url': {},
                                'danmu': last_danmu["danmu"]
                            }
                        }
                        await post_to_topic(client, client_topic + cid, json.dumps(msg))
                else:
                    last_danmu = new_danmu
        await asyncio.sleep(0.1)

async def log_messages(client, messages, cids):
    async for message in messages:
        print(f'[recv] topic = "{message.topic}"\nmsg = {message.payload.decode()}')
        if message.topic == server_topic:
            data = json.loads(message.payload.decode())
            if data["code"] == 0:
                if data["type"] == 'req_get_url':
                    url = ''
                    try:
                        if data["node"] == 'cc':
                            cc = CC(data["data"]["rid"])
                            url = cc.get_real_url()
                        elif data["node"] == 'bilibili':
                            bilibili = BiliBili(data["data"]["rid"])
                            url = bilibili.get_real_url()["\u7ebf\u8def1"]
                    except:
                        url = 'none'
                    msg = {
                        'code': 0,
                        'type': 'resp_get_url',
                        'data': {
                            'url': url,
                            'danmu': {
                                'name': '',
                                'content': ''
                            }
                        }
                    }
                    await post_to_topic(client, client_topic + data["data"]["cid"], json.dumps(msg))
                if data["type"] == 'req_get_danmu':
                    if data["node"] == 'cc':
                        url = f'https://cc.163.com/{data["data"]["rid"]}/'
                    elif data["node"] == 'bilibili':
                        url = f'https://live.bilibili.com/{data["data"]["rid"]}'
                    os.system(f'touch temp/{data["data"]["cid"]}.sock temp/{data["data"]["cid"]}.danmu')
                    await asyncio.sleep(1)
                    os.system(f'python3 danmu.py -u {url} -c {data["data"]["cid"]} &')
                    cids.append(data["data"]["cid"])
        if message.topic == will_topic:
            cid = message.payload.decode()
            for c in cids:
                if c == cid:
                    cids.remove(cid)
                    os.system(f'rm -rf temp/{cid}.sock')
                    await asyncio.sleep(1)
                    os.system(f'rm -rf temp/{cid}.danmu')

async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

async def main():
    reconnect_interval = 3
    while True:
        try:
            await run_mqtt()
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)

if __name__ == '__main__':
    print('livecc server is started.')
    asyncio.run(main())
