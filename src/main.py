import time
import json
import asyncio
import struct
from machine import Pin
from elastic_queue import Queue
from led import LED
from lamp import Lamp
import device
import mqtt

TIMEOUT_MS = 1
STATUS_LED_TOGGLE_INTERVAL_MS = 64

def lighting_message(msg):
    if 'sender' not in msg:
        return False
    
    if msg['sender'] != 'fft-streamer':
        return False
    
    if 'payload' not in msg:
        return False
    
    return True
    

def valid_state_update_request(msg):
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

async def read_size(reader):
    prefix_size = struct.calcsize("!I")
    try:
        buf = await asyncio.wait_for(reader.readexactly(prefix_size), 1)
    except asyncio.TimeoutError:
        return 0
    size = struct.unpack("!I", buf)[0]
    return size

async def read_data(reader, size):
    try:
        buf = await asyncio.wait_for(reader.readexactly(size), 1)
    except asyncio.TimeoutError:
        return b''

    return buf

async def main():
    status_led = Pin('LED', Pin.OUT)
    LEDs = []
    
    msg_queue = Queue(32)
    mqtt_state_queue = Queue(32)

    with open("device.json", 'r') as device_config_file:
        contents = device_config_file.read()
        device_config = json.loads(contents)

    for rgb_pins in device_config["led_pins"]:
        led = LED(Pin(rgb_pins[0]), Pin(rgb_pins[1]), Pin(rgb_pins[2]), invert_duty_cycle = device_config["invert_pwm_duty_cycle"])
        LEDs.append(led)
        
    lamp = Lamp(LEDs)
    
    state = device.init(lamp, device_config)
        
    asyncio.create_task(mqtt.init(state, msg_queue, mqtt_state_queue))
    
    tcp_reader = None
    tcp_writer = None
    
    status_led_last_toggled_ms = time.ticks_ms()
    last_fft_ms = time.ticks_ms()
    durations = []
    while True:
        now_ms = time.ticks_ms()
        elapsed = time.ticks_diff(now_ms, status_led_last_toggled_ms)
        
        if elapsed >= STATUS_LED_TOGGLE_INTERVAL_MS:
            status_led.toggle()
            status_led_last_toggled_ms = now_ms
        
        while not msg_queue.empty():
            msg = msg_queue.get_nowait()
            
            if valid_state_update_request(msg):
                updates = device.update(msg["payload"])
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
                        # TODO: set host and port for FFT stream
                        continue

        while not mqtt_state_queue.empty():
            state = mqtt_state_queue.get_nowait()
            if state == "up":
                tcp_reader, tcp_writer = await asyncio.open_connection('192.168.1.199', 12345)
            elif state == "down":
                if tcp_reader is not None:
                    try:
                        tcp_writer.close()
                        await tcp_writer.wait_closed()
                        tcp_reader = None
                    except:
                        pass
            print("MQTT state", state)

        if tcp_reader:
            try:
                size = await read_size(tcp_reader)
                if size == 0:
                    await asyncio.sleep_ms(TIMEOUT_MS)
                    continue
                data = await read_data(tcp_reader, size)
                if len(data) == 0:
                    await asyncio.sleep_ms(TIMEOUT_MS)
                    continue
                
                values_count = len(data) // struct.calcsize("!f")
                unpack_format = f'!{values_count}f'
                fft_values = struct.unpack(unpack_format, data)
                now_ms = time.ticks_ms()
                durations.append(time.ticks_diff(now_ms, last_fft_ms))
                
                if len(durations) > 100:
                    print(sum(durations) / len(durations))
                    durations = []
                last_fft_ms = now_ms
            except EOFError as e:
                tcp_reader = None
                tcp_writer.close()
                tcp_writer.wait_closed()
                print("Disconnected", e)
            except Exception as e:
                print("Error", e)
            
        await asyncio.sleep_ms(TIMEOUT_MS)

if __name__ == '__main__':
    asyncio.run(main())
    asyncio.new_event_loop()