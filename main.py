#!/usr/bin/env python
#coding:utf-8

import time
import json
import random
from paho.mqtt import client as mqtt_client

broker = 'pkrs.cc'
port = 1883
keepalive = 60          
topic = "/live/cc/server"
client_id = f'live-cc-server-{random.randint(0, 1000)}'
username = 'admin'
password = 'password'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT OK!")
        else:
            print("Failed to connect, return code %d\n", rc)
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port, keepalive)
    return client

def subscribe(client, topic):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    client.subscribe(topic)
    client.on_message = on_message

def publish(client, topic, msg):
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        print(f"Send `{msg}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")

def run():
    client = connect_mqtt()
    client.loop_start()

if __name__ == '__main__':
    run()
