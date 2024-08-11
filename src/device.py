import time
import json

_state = {
    "lamp": None,
    "device_state": {}
}

def has_feature(id):
    for f in _state["device_state"]["features"]:
        if f["id"] == id:
            return True

def get_id():
    return _state["device_state"]["id"]
        
def persist_state(_ = None):
    try:
        with open("state.json", "w") as state_file:
            state_file.write(json.dumps(_state["device_state"]))
            print("State persisted")
    except Exception as e:
        print("Failed to persist state", e)
        
def update_features(data):
    if _state["lamp"] is None:
        return

    start_ms = time.ticks_ms()
    result = _state["lamp"].change_state(data["featureId"], data["state"])
    print(time.ticks_diff(time.ticks_ms(), start_ms), "ms to update features")
    for (feature_id, value) in result:
        for f in _state["device_state"]["features"]:
            if f["id"] == feature_id:
                f["value"] = value
                break

    persist_state()
    return result

def config(key, value = None):
    if type(key) is dict:
        if "config" not in _state["device_state"]:
            _state["device_state"]["config"] = {}
        _state["device_state"]["config"].update(key)
        persist_state()
        return
    
    if type(key) is str and value is not None:
        if "config" not in _state["device_state"]:
            _state["device_state"]["config"] = {}
        _state["device_state"]["config"][key] = value
        persist_state()
        return
    
    if type(key) is str:
        if "config" not in _state["device_state"]:
            return None
        return _state["device_state"]["config"].get(key, None)
    
    raise ValueError("Invalid arguments")

def get(feature_id):
    for f in _state["device_state"]["features"]:
        if f["id"] == feature_id:
            return f["value"] if "value" in f else f["schema"]["default"]
    return None

def process_amplitudes(amplitudes, fft_samplerate, config):
    _state["lamp"].dance(amplitudes, fft_samplerate, config)

def init(lamp, default_state):
    _state["lamp"] = lamp
    _state["device_state"] = json.loads(json.dumps(default_state))

    try:
        with open("state.json", "r") as state_file:
            contents = state_file.read()
            _state["device_state"] = json.loads(contents)
            print("Loaded previous state", _state["device_state"])
    except Exception as e:
        print("No last state found. Using default config. Error: ", e)
        
    _state["lamp"].restore_state(_state["device_state"]["features"])
    return _state["device_state"]