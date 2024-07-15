import time
import json
import asyncio
from machine import Pin
from elastic_queue import Queue
from led import LED, Colors
from lamp import Lamp
import device
import mqtt

TIMEOUT_MS = 16
STATUS_LED_TOGGLE_INTERVAL_MS = 64

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
        
    if payload['deviceId'] != device.id:
        return False
        
    return device.has_feature(payload['featureId'])

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
    
    status_led_last_toggled_ms = time.ticks_ms()
    while True:
        now_ms = time.ticks_ms()
        elapsed = time.ticks_diff(now_ms, status_led_last_toggled_ms)
        
        if elapsed >= STATUS_LED_TOGGLE_INTERVAL_MS:
            status_led.toggle()
            status_led_last_toggled_ms = now_ms
        
        while not msg_queue.empty():
            msg = msg_queue.get_nowait()
            
            if not valid_state_update_request(msg):
                continue

            updates = device.update(msg["payload"])
            for (feature_id, new_state) in updates:
                if feature_id is None:
                    continue
                mqtt.broadcast(feature_id, new_state)
            
        while not mqtt_state_queue.empty():
            state = mqtt_state_queue.get_nowait()
            print("MQTT state", state)
        
        await asyncio.sleep_ms(TIMEOUT_MS)

if __name__ == '__main__':
    asyncio.run(main())
    asyncio.new_event_loop()