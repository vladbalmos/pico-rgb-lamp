import sys
import os
import argparse
import math
import time
import queue
import fft_client
import screen

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import animation_utils as utils

SAMPLING_RATE = 20
ANIMATION_FRAMERATE = 60
starting_color = (0, 255, 0)
last_color = (0, 0, 0)
args = None


def transform_color(color, amplitudes, animation):
    if animation == 'pulse':
        return utils.pulse_color(color, amplitudes)

    if animation == 'pulse_rgb':
        return utils.pulse_rgb(color, amplitudes)

    return utils.pulse_color(color, amplitudes)

def main(colors_queue):
    global last_color
    
    if not fft_client.is_alive():
        exit(0)

    try:
        amplitudes = fft_client.data_queue.get_nowait()
    except queue.Empty:
        return
    except Exception as e:
        print(e)
        exit(1)
        
    colors_count = ANIMATION_FRAMERATE // SAMPLING_RATE
    color = transform_color(starting_color, amplitudes, args.animation)

    if colors_count == 1:
        colors_queue.appendleft(color)
        return
    
    for i in range(colors_count):
        t = i / (colors_count - 1)
        interpolated_color = utils.interpolate_color(last_color, color, t)
        colors_queue.appendleft(interpolated_color)
        
    last_color = color
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RGB Demo Lamp')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='The IP address of the host running the FFT server')
    parser.add_argument('--port', type=int, default=12345, help='The port of the FFT server')
    parser.add_argument('--animation', type=str, default='pulse', help='Animation type. Defaults to "pulse"')

    args = parser.parse_args()

    fft_client.start(args.host, args.port)
    
    while not fft_client.ready_event.is_set():
        time.sleep(0.1)
        if not fft_client.is_alive():
            exit(1)

    try:
        screen.init(ANIMATION_FRAMERATE)
        screen.mainloop(main)
    except KeyboardInterrupt:
        exit(0)
    finally:
        fft_client.stop()