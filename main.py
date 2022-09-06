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

broker = 'pkrs.cc'
port = 1883
keepalive = 60          
server_topic = '/live/cc/server'
client_topic = '/live/cc/client/#'
client_id = f'live-cc-server-{random.randint(0, 1000)}'
username = 'admin'
password = 'password'

async def post_to_topic(client, topic, message):
    print(f'[topic="{topic}"] Publishing message={message}')
    await client.publish(topic, message, qos=0)

async def get_danmu(client, cid, q, dmc):
    while True:
        m = await q.get()
        if m['msg_type'] == 'danmaku':
            print(f'Danmaku | {m["name"]}：{m["content"]}')
            msg = {
                'code': 0,
                'type': 'resp_get_danmu',
                'danmu': {
                    'name': m["name"],
                    'content': m["content"]
                }
            }
            await post_to_topic(client, server_topic, json.dumps(msg))
            url = f'http://pkrs.cc:8081/api/v4/clients/{cid}'
            headers = { 'Authorization': 'Basic YWRtaW46cHVibGlj' }
            response = requests.request("GET", url, headers=headers)
            data = json.loads(response.text)
            if data["data"] == []:
                print('client is offline.')
                p = sys.executable
                os.execl(p, p, *sys.argv)
                sys.exit()

async def log_messages(client, messages, template):
    async for message in messages:
        print(template.format(message.payload.decode()))
        data = json.loads(message.payload.decode())
        if data["code"] == 0:
            if data['type'] == 'req_get_url':
                cc = CC(data['rid'])
                msg = {
                    'code': 0,
                    'type': 'resp_get_url',
                    'url': cc.get_real_url()
                }
                await post_to_topic(client, server_topic, json.dumps(msg))
            if data['type'] == 'req_get_danmu':
                url = f'https://cc.163.com/{data["rid"]}/'
                q = asyncio.Queue()
                dmc = danmaku.DanmakuClient(url, q)
                asyncio.create_task(get_danmu(client, data["cid"], q, dmc))
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

        client = Client(hostname=broker, port=port, keepalive=keepalive,
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
