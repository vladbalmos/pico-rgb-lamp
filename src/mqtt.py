import uasyncio as asyncio
import json
from elastic_queue import Queue
from mqtt_as import MQTTClient, config
from utils import log

_broadcast_queue = Queue(8)

_state = {
    "client": None,
    "device_config": None,
    "main_msg_queue": None,
    "mqtt_state_queue": None,
    "broadcast_queue": None,
    "initial_connection_establed": False,
    "connect_task": None,
    "mqtt_up_task": None,
    "mqtt_down_task": None,
    "mqtt_messages_task": None
}

async def register_device():
    payload = json.dumps({
        "request": "registration",
        "requestTopic": _state["device_config"]["topics"]["subscription"]["device"],
        "responseTopic": _state["device_config"]["topics"]["publish"]["device"],
        "state": {
            "id": _state["device_config"]["id"],
            "name": _state["device_config"]["name"],
            "features": _state["device_config"]["features"]
        }
    })
    log("Registering device", _state["device_config"]["id"], _state["device_config"]["topics"]["publish"]["manager"])
    await _state["client"].publish(_state["device_config"]["topics"]["publish"]["manager"], payload, qos = 0)
    log("Registered device")
    
def broadcast(feature_id, state):
    _broadcast_queue.put_nowait(json.dumps({
        'deviceId': _state["device_config"]["id"],
        'featureId': feature_id,
        'state': state
    }))
    # log("Broadcasting", feature_id, state)

async def mqtt_up(client):
    while True:
        log("Waiting for connection...")
        await client.up.wait()
        client.up.clear()
        log("Connection (re-)established")
        _state["client"] = client
        
        _state["mqtt_state_queue"].put_nowait("up")
        
        if not _state["initial_connection_establed"]:
            _state["initial_connection_establed"] = True
            
        for k,v in _state["device_config"]["topics"]["subscription"].items():
            log(f"Subscribing to {v}")
            await client.subscribe(v, 0)
            
        await register_device()

async def mqtt_down(client):
    while True:
        log("Waiting for connection to be down")
        await client.down.wait()
        client.down.clear()
        _state["mqtt_state_queue"].put_nowait("down")
        log("Connection is down")

async def mqtt_message(client):
    async for item in client.queue:
        topic = item[0]
        msg = item[1]
        
        if topic == _state["device_config"]["topics"]["subscription"]["manager"]:
            await register_device()
            continue
        
        if topic == _state["device_config"]["topics"]["subscription"]["device"] or topic == _state["device_config"]["topics"]["subscription"]["lighting"]:
            try:
                msg = json.loads(msg)
                _state["main_msg_queue"].put_nowait(msg)
            except Exception as e:
                log("Failed to parse json message", e)

async def process_broadcast_queue():
    while True:
        msg = await _broadcast_queue.get()
        if _state["client"] is None:
            continue    

        await _state["client"].publish(_state["device_config"]["topics"]["publish"]["device"], msg, qos = 0)
        # log("Broadcasted", msg)
        
def disconnect():
    if _state["client"]:
        _state["client"].close()

async def init(device_config, main_msg_queue, mqtt_state_queue):
    _state["device_config"] = device_config
    _state["main_msg_queue"] = main_msg_queue
    _state["mqtt_state_queue"] = mqtt_state_queue
    
    config["ssid"] = device_config["ssid"]
    config["wifi_pw"] = device_config["password"]
    config["server"] = device_config["server"]
    config["queue_len"] = 8
    
    while not _state["initial_connection_establed"]:
        client = MQTTClient(config)
        _state["connect_task"] = asyncio.create_task(client.connect())
        try:
            log(f"Connecting to {config['server']}...")
            _state["mqtt_state_queue"].put_nowait("connecting")
            await _state["connect_task"]

            if _state["mqtt_up_task"] is not None:
                _state["mqtt_up_task"].cancel()
            if _state["mqtt_down_task"] is not None:
                _state["mqtt_down_task"].cancel()
            if _state["mqtt_messages_task"] is not None:
                _state["mqtt_messages_task"].cancel()

            for coroutine in (mqtt_up, mqtt_down, mqtt_message):
                asyncio.create_task(coroutine(client))

            # Wait for tasks to start
            await asyncio.sleep_ms(1000)

            log(f"Initial connection status is: {_state["initial_connection_establed"]}")
            
            if _state["initial_connection_establed"]:
                asyncio.create_task(process_broadcast_queue())
        except BaseException as e:
            if client:
                client.close()
            log("Connection error:", e)
            await asyncio.sleep_ms(1000)

    log("MQTT initialized")


    