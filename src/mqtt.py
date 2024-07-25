import asyncio
import json
from elastic_queue import Queue
from mqtt_as import MQTTClient, config

MQTTClient.DEBUG = True
_client = None
_device_config = None
_main_msg_queue = None
_mqtt_state_queue = None
_broadcast_queue = Queue(8)

_initial_connection_establed = False
_connect_task = None
_mqtt_up_task = None
_mqtt_down_task = None
_mqtt_messages_task = None

async def register_device():
    global _client
    payload = json.dumps({
        "request": "registration",
        "requestTopic": _device_config["topics"]["subscription"]["device"],
        "responseTopic": _device_config["topics"]["publish"]["device"],
        "state": {
            "id": _device_config["id"],
            "name": _device_config["name"],
            "features": _device_config["features"]
        }
    })
    print("Registering device", _device_config["topics"]["publish"]["manager"], payload)
    await _client.publish(_device_config["topics"]["publish"]["manager"], payload, qos = 0)
    print("Registered device")
    
def broadcast(feature_id, state):
    _broadcast_queue.put_nowait(json.dumps({
        'deviceId': _device_config["id"],
        'featureId': feature_id,
        'state': state
    }))
    print("Broadcasting", feature_id, state)

async def mqtt_up(client):
    global _initial_connection_establed, _client
    
    while True:
        print("Waiting for connection...")
        await client.up.wait()
        client.up.clear()
        print("Connection (re-)established")
        _client = client
        
        _mqtt_state_queue.put_nowait("up")
        
        if not _initial_connection_establed:
            _initial_connection_establed = True
            
        for k,v in _device_config["topics"]["subscription"].items():
            print(f"Subscribing to {v}")
            await client.subscribe(v, 1)
            
        await register_device()

async def mqtt_down(client):
    while True:
        print("Waiting for connection to be down")
        await client.down.wait()
        client.down.clear()
        _mqtt_state_queue.put_nowait("down")
        print("Connection is down")

async def mqtt_message(client):
    async for item in client.queue:
        topic = item[0]
        msg = item[1]
        
        if topic == _device_config["topics"]["subscription"]["manager"]:
            await register_device()
            continue
        
        if topic == _device_config["topics"]["subscription"]["device"] or topic == _device_config["topics"]["subscription"]["lighting"]:
            try:
                msg = json.loads(msg)
                _main_msg_queue.put_nowait(msg)
            except Exception as e:
                print("Failed to parse json message", e)

async def process_broadcast_queue():
    while True:
        msg = await _broadcast_queue.get()
        if _client is None:
            continue    

        await _client.publish(_device_config["topics"]["publish"]["device"], msg, qos = 0)
        print("Broadcasted", msg)

async def init(device_config, main_msg_queue, mqtt_state_queue):
    global _client, \
           _device_config, \
           _main_msg_queue, \
           _mqtt_state_queue, \
           _connect_task
           
    _device_config = device_config
    _main_msg_queue = main_msg_queue
    _mqtt_state_queue = mqtt_state_queue
    
    config["ssid"] = device_config["ssid"]
    config["wifi_pw"] = device_config["password"]
    config["server"] = device_config["server"]
    config["queue_len"] = 8
    
    while not _initial_connection_establed:
        client = MQTTClient(config)
        _connect_task = asyncio.create_task(client.connect())
        try:
            print(f"Connecting to {config['server']}...")
            _mqtt_state_queue.put_nowait("connecting")
            await _connect_task

            if _mqtt_up_task is not None:
                _mqtt_up_task.cancel()
            if _mqtt_down_task is not None:
                _mqtt_down_task.cancel()
            if _mqtt_messages_task is not None:
                _mqtt_messages_task.cancel()

            for coroutine in (mqtt_up, mqtt_down, mqtt_message):
                asyncio.create_task(coroutine(client))

            # Wait for tasks to start
            await asyncio.sleep_ms(250)

            print(f"Initial connection status is: {_initial_connection_establed}")
            
            if _initial_connection_establed:
                asyncio.create_task(process_broadcast_queue())
        except BaseException as e:
            print("Connection error:", e)

    print("MQTT initialized")


    