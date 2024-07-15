import json

_lamp = None
_state = None

def has_feature(id):
    for f in _state["features"]:
        if f["id"] == id:
            return True
        
def update(data):
    _lamp.change_state(data["featureId"], data["state"])
    return [(data["featureId"], data["state"])]

def init(lamp, default_state):
    global _lamp, _state

    _lamp = lamp
    _state = json.loads(json.dumps(default_state))

    try:
        with open("state.json") as state_file:
            _state = json.loads(state_file)
            print("Loaded previous state")
    except Exception as e:
        print("No last state found. Using default config")
        
    _lamp.restore_state(_state["features"])
    return _state