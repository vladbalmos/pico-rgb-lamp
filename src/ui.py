import time
from machine import Pin, Timer
import asyncio
from rotary_irq_rp2 import RotaryIRQ

KEY_UP = "KEY_UP"
KEY_DOWN = "KEY_DOWN"
KEY_DOWN_LP = "KEY_DOWN_LP"
SELECT_NEXT = "SELECT_NEXT"
SELECT_PREV = "SELECT_PREV"
TIMEOUT = "TIMEOUT"

_LONG_PRESS_MS = const(1000)

_menu_states = {
    "idle": {
        KEY_DOWN_LP: {
            "change_state": "menu"
        },
        SELECT_NEXT: "update_state",
        SELECT_PREV: "update_state",
    },
    "menu": {
        SELECT_NEXT: "update_state",
        SELECT_PREV: "update_state",
        KEY_DOWN_LP: {
            "change_state": "idle"
        },
        KEY_DOWN: {
            "change_state": "submenu"
        }
    },
    "submenu": {
        SELECT_NEXT: "update_state",
        SELECT_PREV: "update_state",
        KEY_DOWN_LP: {
            "change_state": "idle"
        },
        KEY_DOWN: {
            "change_state": "select"
        }
    },
    "select": {
        "*": {
            "change_state": "idle"
        }
    }
}
_state = {
    "queue": None,

    "encoder": None,
    "last_encoder_value": 0,

    "switch": None,
    "last_switch_state": 1,
    "switch_timer": None,
    
    "ui_current_state": "idle"
}

def update_ui_state(event, timestamp, value):
    _state["queue"].put_nowait({
        "ui_event": True,
        "action": "update",
        "event": event,
        "timestamp": timestamp,
        "value": value,
        "current_state": _state["ui_current_state"]
    });

def change_ui_state(next_state, event, timestamp, value = None):
    if not next_state in _menu_states:
        return
    
    _state["queue"].put_nowait({
        "ui_event": True,
        "action": "change_state",
        "value": next_state,
        "event": event,
        "timestamp": timestamp,
        "current_state": _state["ui_current_state"]
    });
    _state["ui_current_state"] = next_state

def handle_ui_event(event, timestamp, value = None):
    current_state = _state["ui_current_state"]
    
    if "*" in _menu_states[current_state]:
        event = "*"

    action = _menu_states[current_state].get(event, None)
    
    if action is None:
        return
    
    if 'update_state' == action:
        update_ui_state(event, timestamp, value)
        return
    
    if 'change_state' in action:
        next_state = action['change_state']
        change_ui_state(next_state, event, timestamp, value)
        return

def on_encoder_change():
    value = _state["encoder"].value()
    
    if value > _state["last_encoder_value"]:
        handle_ui_event(SELECT_NEXT, time.ticks_ms(), value)
    else:
        handle_ui_event(SELECT_PREV, time.ticks_ms(), value)
        
    _state["last_encoder_value"] = value

def check_long_press(t):
    _state["switch_close_elapsed"] = time.ticks_diff(time.ticks_ms(), _state["switch_close_time"])
    
    if _state["switch_close_elapsed"] >= _LONG_PRESS_MS:
        handle_ui_event(KEY_DOWN_LP, time.ticks_ms())
        t.deinit()
        _state["switch_close_time"] = None
        _state["switch_close_elapsed"] = None
        _state["switch_timer"] = None

def on_switch_close():
    switch_timer = Timer(-1)
    switch_timer.init(mode = Timer.PERIODIC, period = 100 , callback = check_long_press)
    _state["switch_close_time"] = time.ticks_ms()
    _state["switch_timer"] = switch_timer

def on_switch_open():
    if _state["switch_timer"]:
        _state["switch_timer"].deinit()
        _state["switch_timer"] = None
    
    if _state["switch_close_elapsed"] and _state["switch_close_elapsed"] < _LONG_PRESS_MS:
        _state["switch_close_elapsed"] = None
        _state["switch_close_time"] = None
        handle_ui_event(KEY_DOWN, time.ticks_ms())
        
    handle_ui_event(KEY_UP, time.ticks_ms())

async def switch_check():
    while True:
        switch_state = _state["switch"].value()
        if switch_state != _state["last_switch_state"]:
            if switch_state == 0:
                on_switch_close()
            else:
                on_switch_open()
            _state["last_switch_state"] = switch_state
        await asyncio.sleep_ms(50)
        
def set_encoder_range(min_val = 0, max_val = 255, incr = 10, value = 255):
    _state["encoder"].set(min_val = min_val, max_val = max_val, value = value, incr = incr)

def init(queue, config):
    encoder_pin_clk, encoder_pin_dt = config["rotary_encoder_pins"]
    encoder = RotaryIRQ(encoder_pin_clk, encoder_pin_dt, min_val = 0, max_val = 255, pull_up = True, range_mode = RotaryIRQ.RANGE_BOUNDED, incr = 10)
    encoder.set(value = 255)
    
    encoder.add_listener(on_encoder_change)
    _state["encoder"] = encoder
    _state["queue"] = queue
    
    _state["switch"] = Pin(config["select_switch_pin"], Pin.IN, Pin.PULL_UP)

    asyncio.create_task(switch_check())
    