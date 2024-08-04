import gc
import sys
import time
import json
import asyncio
import network
from machine import Pin, freq
from elastic_queue import Queue
from led import LED
from lamp import Lamp
import audio_visualizer
import device
import mqtt

_TIMEOUT_MS = const(500)

def lighting_message(msg):
    if 'sender' not in msg:
        return False
    
    if msg['sender'] != 'fft-streamer':
        return False
    
    if 'payload' not in msg:
        return False
    
    return True
    

def valid_feature_state_update_request(msg):
    if 'request' not in msg:
        return False
        
    if msg['request'] != 'state-update':
        return False

    if 'payload' not in msg:
        return False
        
    payload = msg['payload']
    
    if 'deviceId' not in payload or 'featureId' not in payload:
        return False
        
    if payload['deviceId'] != device.get_id():
        return False
        
    return device.has_feature(payload['featureId'])


async def handle_messages(msg_queue, device):
    audio_visualizer_task = None
    while True:
        msg = await msg_queue.get()
        
        if valid_feature_state_update_request(msg):
            updates = device.update_features(msg["payload"])
            
            if len(updates) == 1 and updates[0][0] == 'animation' and updates[0][1] == 'audio visualizer':
                fft_stream_host = device.config("fft_stream_host")
                fft_stream_port = device.config("fft_stream_port")
                
                if type(fft_stream_host) is not str or len(fft_stream_host) == 0 or type(fft_stream_port) is not int or fft_stream_port < 1:
                    continue
                
                if audio_visualizer_task is not None:
                    audio_visualizer_task.cancel()
                    audio_visualizer_task = None
                    
                audio_visualizer_task = asyncio.create_task(audio_visualizer.run(fft_stream_host, fft_stream_port, device))
            else:
                if audio_visualizer_task is not None:
                    audio_visualizer_task.cancel()
                    audio_visualizer_task = None

            for (feature_id, new_value) in updates:
                if feature_id is None:
                    continue
                mqtt.broadcast(feature_id, new_value)

                    
        if lighting_message(msg):
            payload = msg['payload']
            if "event" in payload and payload["event"] == "announcement" and "data" in payload:
                data = payload["data"]
                
                if "host" in data and "port" in data:
                    host = data["host"]
                    port = data["port"]
                    print(f"FFT Stream is at {host}:{port}")
                    device.config({"fft_stream_host": host, "fft_stream_port": port})
                    continue
        
async def handle_mqtt_state_changes(mqtt_state_queue):
    while True:
        state = await mqtt_state_queue.get()
        print("MQTT state", state)

async def main():
    status_led = Pin('LED', Pin.OUT)
    LEDs = []
    
    msg_queue = Queue(8)
    mqtt_state_queue = Queue(8)

    with open("device.json", 'r') as device_config_file:
        contents = device_config_file.read()
        device_config = json.loads(contents)

    for rgb_pins in device_config["led_pins"]:
        led = LED(Pin(rgb_pins[0]), Pin(rgb_pins[1]), Pin(rgb_pins[2]), invert_duty_cycle = device_config["invert_pwm_duty_cycle"])
        LEDs.append(led)
        
    lamp = Lamp(LEDs)
    
    state = device.init(lamp, device_config)
        
    asyncio.create_task(mqtt.init(state, msg_queue, mqtt_state_queue))
    asyncio.create_task(handle_messages(msg_queue, device))
    asyncio.create_task(handle_mqtt_state_changes(mqtt_state_queue))
    
    last_gc_ms = time.ticks_ms()
    while True:
        status_led.toggle()
        now_ms = time.ticks_ms()
        elapsed_ms = time.ticks_diff(now_ms, last_gc_ms)
        
        gc_start_ms = time.ticks_ms()
        gc.collect()
        gc_duration_ms = time.ticks_diff(time.ticks_ms(), gc_start_ms)
        gc_duration_ms = 0

        if elapsed_ms > 5000:
            last_gc_ms = now_ms
            print("RAM free %d alloc %d. GC Duration %d"  % (gc.mem_free(), gc.mem_alloc(), gc_duration_ms))
        await asyncio.sleep_ms(_TIMEOUT_MS) # type: ignore

def handle_exception(loop, context):
    print('Global handler')
    sys.print_exception(context["exception"])
    sys.exit()  # Drastic - loop.stop() does not work when used this way 

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    asyncio.run(main())
    mqtt.disconnect()
    asyncio.new_event_loop()