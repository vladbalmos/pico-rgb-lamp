import json
import asyncio
from machine import Pin, PWM
from elastic_queue import Queue
from led import LED, Colors
from lamp import Lamp
import mqtt

LED_PINS = [
    #r  g  b
    [1, 2, 0],
    [4, 5, 3],
    [7, 8, 6],
    [10, 11, 9],
]

async def main():
    status_led = Pin('LED', Pin.OUT)
    LEDs = []
    
    msg_queue = Queue(32)
    mqtt_state_queue = Queue(32)

    for rgb_pins in LED_PINS:
        led = LED(Pin(rgb_pins[0]), Pin(rgb_pins[1]), Pin(rgb_pins[2]))
        LEDs.append(led)
        
    lamp = Lamp(LEDs)
        
    with open("device.json", 'r') as device_config_file:
        contents = device_config_file.read()
        device_config = json.loads(contents)
        
    asyncio.create_task(mqtt.init(device_config, msg_queue, mqtt_state_queue))
    
    while True:
        status_led.toggle()
        
        if not msg_queue.empty():
            msg = msg_queue.get_nowait()
            print("Got message", msg)
            payload = msg["payload"]
            if msg["request"] == "state-update":
                lamp.change_state(payload["featureId"], payload["state"])
                mqtt.broadcast(payload["featureId"], payload["state"])
            
        while not mqtt_state_queue.empty():
            state = mqtt_state_queue.get_nowait()
            print("MQTT state", state)
        
        await asyncio.sleep_ms(50)

if __name__ == '__main__':
    asyncio.run(main())
    asyncio.new_event_loop()