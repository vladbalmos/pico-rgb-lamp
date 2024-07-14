import asyncio
# from queue import Queue
from machine import Pin, PWM
from led import LED, Colors

LED_PINS = [
    #r  g  b
    [1, 2, 0],
    [4, 5, 3],
    [7, 8, 6],
    [10, 11, 9],
]

async def main():
    LEDs = []

    for rgb_pins in LED_PINS:
        led = LED(Pin(rgb_pins[0]), Pin(rgb_pins[1]), Pin(rgb_pins[2]))
        LEDs.append(led)
        # led.set_color("magenta")

if __name__ == '__main__':
    asyncio.run(main())
    asyncio.new_event_loop()