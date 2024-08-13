import gc
import sys
import time
import json
import uasyncio as asyncio
from machine import Pin, Timer
from elastic_queue import Queue
from led import LED
from lamp import Lamp
import audio_visualizer
import device
import mqtt
import utils
from utils import log
import ui    

_TIMEOUT_MS = const(500)

audio_visualizer_task = None

UI_MENU_SELECT_COLOR = const(0)
UI_MENU_SELECT_ANIMATION = const(1)
UI_MENU_ENABLE_AUDIO_VISUALIZER = const(2)

ui_menu_state = {
    "last_active_feature": None,
    "selected_menu_item": None,
    "selected_submenu_item": None,
    "cancel_menu_timer": None,
    "state_locked": False
}

def state_lock():
    ui_menu_state["state_locked"] = True

def state_unlock():
    ui_menu_state["state_locked"] = False
    
def cancel_menu(_):
    ui.change_ui_state("idle", ui.TIMEOUT, time.ticks_ms())

def enable_menu_timeout():
    cancel_menu_timeout()
    ui_menu_state["cancel_menu_timer"] = Timer(-1) # type: ignore
    ui_menu_state["cancel_menu_timer"].init(mode = Timer.ONE_SHOT, period = 60 * 1000, callback = cancel_menu)

def cancel_menu_timeout():
    if ui_menu_state["cancel_menu_timer"] is not None:
        ui_menu_state["cancel_menu_timer"].deinit()
        ui_menu_state["cancel_menu_timer"] = None

def broadcast_updates(updates):
    for (feature_id, new_value) in updates:
        if feature_id is None:
            continue
        mqtt.broadcast(feature_id, new_value)
        
def reset_ui_menu_state():
    ui_menu_state["last_active_feature"] = None
    ui_menu_state["selected_menu_item"] = None
    ui_menu_state["selected_submenu_item"] = None
    

def lighting_message(msg):
    if 'request' not in msg:
        return False
    
    if msg['request'] != 'anouncement':
        return False

    if 'sender' not in msg:
        return False
    
    if msg['sender'] != 'fft_server':
        return False
    
    if 'message' not in msg:
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

def ui_message(msg):
    if 'ui_event' not in msg:
        return False
        
    if 'action' not in msg:
        return False
        
    if 'event' not in msg:
        return False
        
    if 'current_state' not in msg:
        return False
        
    return True

async def handle_ui_event(msg, device):
    '''
    Handle UI events and change state accordingly
    '''
    current_state = msg['current_state']
    action = msg['action']
    event = msg['event']
    event_value = msg['value']
    
    try:
        active_feature_id, active_value = device.active_feature()
    except Exception as e:
        log(e)
        return
    
    # Handle change states
    if action == 'change_state':

        if event_value == 'idle':
            state_unlock()
            # State changed to "idle"
            cancel_menu_timeout()

            if event == ui.KEY_DOWN_LP or event == ui.TIMEOUT:
                # menu section was cancelled, go back to last active feature
                if ui_menu_state["last_active_feature"] is not None:
                    feature_id, state = ui_menu_state["last_active_feature"] # type: ignore
                    device.update_features({"featureId": feature_id, "state": state})
                    
                    if feature_id == "enable_audio_visualizer" and state == 1:
                        enable_audio_visualizer(device.config("fft_streamer"))
                reset_ui_menu_state()

            # reset encoder
            ui.set_encoder_range()
            return
        
        if event_value == "menu":
            state_lock()
            # Entered main menu
            enable_menu_timeout()
            ui_menu_state["last_active_feature"] = (active_feature_id, active_value) # type: ignore
            disable_audio_visualizer()

            if active_feature_id == "change_global_color":
                encoder_value = UI_MENU_SELECT_COLOR
                device.flash_color("#ffffff")
            if active_feature_id == "animation":
                encoder_value = UI_MENU_SELECT_ANIMATION
                device.flash_color("#ff0000")
            if active_feature_id == "enable_audio_visualizer":
                encoder_value = UI_MENU_ENABLE_AUDIO_VISUALIZER
                device.flash_color("#00ff00")
                
            ui_menu_state["selected_menu_item"] = encoder_value # type: ignore
            ui.set_encoder_range(min_val = UI_MENU_SELECT_COLOR, max_val = UI_MENU_ENABLE_AUDIO_VISUALIZER, incr = 1, value = encoder_value)
            return
        
        if event_value == "submenu":
            # Entered submenu
            enable_menu_timeout()
            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_COLOR:
                available_colors = device.config("available_colors")
                color_index = None
                if active_feature_id == "change_global_color":
                    color_index = utils.color_index_of(available_colors, active_value)
                else:
                    color_index = 0

                if color_index is None:
                    color_index = 0
                ui.set_encoder_range(min_val = 0, max_val = len(available_colors) - 1, incr = 1, value = color_index)

                device.flash_color(available_colors[color_index], framerate = 4)
                
            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_ANIMATION:
                animation_schema = device.get_schema("animation")
                animations = [name for name in animation_schema["valid_values"] if name != 'off']
                
                animation_index = None
                if active_feature_id == "animation":
                    try:
                        animation_index = animations.index(active_value)
                    except ValueError:
                        animation_index = 0
                else:
                    animation_index = 0
                    
                if animation_index is None:
                    animation_index = 0

                device.demo_animation(animations[animation_index], color = '#00ff00')
                
            if ui_menu_state["selected_menu_item"] == UI_MENU_ENABLE_AUDIO_VISUALIZER:
                result = device.update_features({"featureId": "enable_audio_visualizer", "state": 1})
                disable_audio_visualizer()
                enable_audio_visualizer(device.config("fft_streamer"))

                broadcast_updates(result)
                # This feature doesn't have a submenu, so we go back to "idle"
                ui.change_ui_state("idle", "*", time.ticks_ms())
            return


        if event_value == "select":
            # Selected a submenu item
            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_COLOR:
                new_color = device.config("available_colors")[ui_menu_state["selected_submenu_item"]]
                result = device.update_features({"featureId": "change_global_color", "state": new_color})
                broadcast_updates(result)

            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_ANIMATION:
                animation_schema = device.get_schema("animation")
                animations = [name for name in animation_schema["valid_values"] if name != 'off']
                animation = animations[ui_menu_state["selected_submenu_item"]]  # type: ignore
                result = device.update_features({"featureId": "animation", "state": animation})
                broadcast_updates(result)
            return
        
    # Handle state updates
    if current_state == 'idle':
        # Handle the "idle" state
        if active_feature_id == 'change_global_color':
            if action == 'update' and (event == ui.SELECT_NEXT or event == ui.SELECT_PREV):
                new_color = utils.rgb_to_hex(utils.change_brightness(active_value, event_value))
                result = device.update_features({"featureId": "change_global_color", "state": new_color})
                broadcast_updates(result)
        return
        
        
    if current_state == 'menu':
        enable_menu_timeout()
        # Handle the "menu" state
        if action == "update" and (event == ui.SELECT_NEXT or event == ui.SELECT_PREV):
            if event_value == UI_MENU_SELECT_COLOR:
                device.flash_color("#ffffff")
            if event_value == UI_MENU_SELECT_ANIMATION:
                device.flash_color("#ff0000")
            if event_value == UI_MENU_ENABLE_AUDIO_VISUALIZER:
                device.flash_color("#00ff00")

            ui_menu_state["selected_menu_item"] = event_value # type: ignore
        return
    
    if current_state == 'submenu':
        enable_menu_timeout()
        if action == "update" and (event == ui.SELECT_NEXT or event == ui.SELECT_PREV):
            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_COLOR:
                try:
                    new_color = device.config("available_colors")[event_value]
                    device.flash_color(new_color, framerate = 4)
                    ui_menu_state["selected_submenu_item"] = event_value # type: ignore
                except KeyError as e:
                    log("Unknown color index", event_value, "Available colors", device.config("available_colors"))
                    
            if ui_menu_state["selected_menu_item"] == UI_MENU_SELECT_ANIMATION:
                animation_schema = device.get_schema("animation")
                animations = [name for name in animation_schema["valid_values"] if name != 'off']
                try:
                    animation = animations[event_value]
                    device.demo_animation(animation, color = '#00ff00')
                    ui_menu_state["selected_submenu_item"] = event_value # type: ignore
                except KeyError as e:
                    log("Unknown animation index", event_value, "Available animations", animations)
            return

async def handle_messages(msg_queue, device):
    global audio_visualizer_task
    while True:
        msg = await msg_queue.get()
        # log("Received message")
        # log(msg)
        
        if ui_message(msg):
            await handle_ui_event(msg, device)
            continue
        
        if valid_feature_state_update_request(msg):
            if ui_menu_state["state_locked"]:
                log("Menu mode, skip message")
                continue
            
            updates = device.update_features(msg["payload"])
            disable_audio_visualizer()

            for feature_update in updates:
                feature, value = feature_update
                
                if feature == 'enable_audio_visualizer' and value == 1:
                    enable_audio_visualizer(device.config("fft_streamer"))
                    
                if feature == 'audio_visualizer_config':
                    audio_visualizer_enabled = device.get("enable_audio_visualizer")
                    if audio_visualizer_enabled == 1:
                        enable_audio_visualizer(device.config("fft_streamer"))

            broadcast_updates(updates)
                    
        if lighting_message(msg):
            message = msg['message']

            if "address" in message:
                address = message["address"]
                
                if "host" in address and "port" in address:
                    host = address["host"]
                    port = address["port"]
                    log(f"FFT Stream is at {host}:{port}")
                    device.config({"fft_streamer": {"host": host, "port": port}})
                    continue
        
async def handle_mqtt_state_changes(mqtt_state_queue):
    while True:
        state = await mqtt_state_queue.get()
        log("MQTT state", state)
        
def disable_audio_visualizer():
    global audio_visualizer_task    
            
    if audio_visualizer_task is not None:
        audio_visualizer_task.cancel()
        audio_visualizer_task = None

def enable_audio_visualizer(config):
    global audio_visualizer_task    
                
    fft_stream_host = config.get("host", None)
    fft_stream_port = config.get("port", None)

    if type(fft_stream_host) is not str or len(fft_stream_host) == 0 or type(fft_stream_port) is not int or fft_stream_port < 1:
        log("Invalid FFT Stream configuration")
        return
    
    audio_visualizer_task = asyncio.create_task(audio_visualizer.run(fft_stream_host, fft_stream_port, device))

async def main():
    status_led = Pin('LED', Pin.OUT)
    LEDs = []
    
    msg_queue = Queue(8)
    mqtt_state_queue = Queue(8)

    with open("device.json", 'r') as device_config_file:
        contents = device_config_file.read()
        device_config = json.loads(contents)
        
    config = device_config["config"]
    ui.init(msg_queue, config)

    led_pins = config["led_pins"]
    for rgb_pins in led_pins:
        led = LED(Pin(rgb_pins[0]), Pin(rgb_pins[1]), Pin(rgb_pins[2]), invert_duty_cycle = config["invert_pwm_duty_cycle"])
        LEDs.append(led)
        
    lamp = Lamp(LEDs)
    
    state = device.init(lamp, device_config)
        
    asyncio.create_task(mqtt.init(state, msg_queue, mqtt_state_queue))
    asyncio.create_task(handle_messages(msg_queue, device))
    asyncio.create_task(handle_mqtt_state_changes(mqtt_state_queue))
    
    if device.get("enable_audio_visualizer"):
        enable_audio_visualizer(device.config("fft_streamer"))
    
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
            log("RAM free %d alloc %d. GC Duration %d"  % (gc.mem_free(), gc.mem_alloc(), gc_duration_ms))
        await asyncio.sleep_ms(_TIMEOUT_MS)

def handle_exception(_, context):
    sys.print_exception(context["exception"]) # type: ignore
    sys.exit()

if __name__ == '__main__':
    # utils.DEBUG = False
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    asyncio.run(main())
    mqtt.disconnect()
    asyncio.new_event_loop()