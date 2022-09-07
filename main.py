import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from asyncio_mqtt import Client, MqttError
import random
import json
from cc_live import CC
import danmaku
import requests
import os
import sys

host = '192.168.1.8'
mqtt_port = 1883
http_port = 18083
keepalive = 60          
server_topic = '/live/cc/server'
client_topic = '/live/cc/client/#'
client_id = f'live-cc-server-{random.randint(0, 1000)}'
username = 'livecc'
password = '203039'

async def post_to_topic(client, topic, message):
    print(f'[topic="{topic}"] Publishing message={message}')
    await client.publish(topic, message, qos=0)

async def get_danmu(client, cid, q):
    while True:
        m = await q.get()
        if m["msg_type"] == 'danmaku':
            print(f'Danmaku | {m["name"]}：{m["content"]}')
            msg = {
                'code': 0,
                'type': 'resp_get_danmu',
                'data': {
                    'url': {},
                    'danmu': {
                        'name': m["name"],
                        'content': m["content"]
                    }
                }
            }
            await post_to_topic(client, server_topic, json.dumps(msg))
            offline = True
            url = f'http://{host}:{http_port}/api/v5/clients'
            headers = { 'Authorization': 'Basic Mjg4MDdmNDAyMTJiOTY5YzpldFlPMnNDSW9UOUM2RkRvamtUOUFReDlDZEtWeFM1ckRaNUVocjJ6SnFDMmNE' }
            response = requests.request("GET", url, headers=headers)
            data = json.loads(response.text)
            for d in data["data"]:
                if d["clientid"] == cid and d["connected"] == True:
                    offline = False
            if offline == True:
                print('client is offline.')
                p = sys.executable
                os.execl(p, p, *sys.argv)

async def log_messages(client, messages, template):
    async for message in messages:
        print(template.format(message.payload.decode()))
        data = json.loads(message.payload.decode())
        if data["code"] == 0:
            if data["type"] == 'req_get_url':
                url = ""
                try:
                    cc = CC(data["data"]["rid"])
                    url = cc.get_real_url()
                except:
                    url = "none"
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
                await post_to_topic(client, server_topic, json.dumps(msg))
            if data["type"] == 'req_get_danmu':
                url = f'https://cc.163.com/{data["data"]["rid"]}/'
                q = asyncio.Queue()
                dmc = danmaku.DanmakuClient(url, q)
                asyncio.create_task(get_danmu(client, data["data"]["cid"], q))
                await dmc.start()

async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

async def run_mqtt(tasks):
    async with AsyncExitStack() as stack:
        stack.push_async_callback(cancel_tasks, tasks)

        client = Client(hostname=host, port=mqtt_port, keepalive=keepalive,
            client_id=client_id, username=username, password=password)
        await stack.enter_async_context(client)
        print('server is started.')

        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(log_messages(client, messages, "[message] {}"))
        tasks.add(task)
        await client.subscribe(client_topic)
        await asyncio.gather(*tasks)

async def main():
    tasks = set()
    reconnect_interval = 3
    while True:
        try:
            await run_mqtt(tasks)
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)

if __name__ == '__main__':
    asyncio.run(main())
