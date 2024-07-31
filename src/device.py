import time
from machine import Timer
import json

_lamp = None
_state = {}
_persist_state_timer = None

def has_feature(id):
    for f in _state["features"]:
        if f["id"] == id:
            return True

def get_id():
    return _state["id"]
        
def persist_state(_ = None):
    try:
        with open("state.json", "w") as state_file:
            state_file.write(json.dumps(_state))
            print("State persisted")
    except Exception as e:
        print("Failed to persist state", e)
        
def schedule_state_persist():
    global _persist_state_timer
    if _persist_state_timer:
        _persist_state_timer.deinit()
        _persist_state_timer = None

    _persist_state_timer = Timer(-1)
    _persist_state_timer.init(mode=Timer.ONE_SHOT, period=500, callback=persist_state)


def update_features(data):
    if _lamp is None:
        return

    start_ms = time.ticks_ms()
    result = _lamp.change_state(data["featureId"], data["state"])
    print(time.ticks_diff(time.ticks_ms(), start_ms), "ms to update features")
    for (feature_id, value) in result:
        for f in _state["features"]:
            if f["id"] == feature_id:
                f["value"] = value
                break

    # schedule_state_persist()
    persist_state()
    return result

def config(key, value = None):
    if type(key) is dict:
        if "config" not in _state:
            _state["config"] = {}
        _state["config"].update(key)
        persist_state()
        # schedule_state_persist()
        return
    
    if type(key) is str and value is not None:
        if "config" not in _state:
            _state["config"] = {}
        _state["config"][key] = value
        persist_state()
        # schedule_state_persist()
        return
    
    if type(key) is str:
        if "config" not in _state:
            return None
        return _state["config"].get(key, None)
    
    raise ValueError("Invalid arguments")

def process_amplitudes(amplitudes, fft_framerate):
    _lamp.dance(amplitudes, fft_framerate) # type: ignore

def init(lamp, default_state):
    global _lamp, _state

    _lamp = lamp
    _state = json.loads(json.dumps(default_state))

    try:
        with open("state.json", "r") as state_file:
            contents = state_file.read()
            _state = json.loads(contents)
            print("Loaded previous state", _state)
    except Exception as e:
        print("No last state found. Using default config. Error: ", e)
        
    _lamp.restore_state(_state["features"])
    return _state