import gc
import json
import animation

if "micropython" not in globals():
    class Micropython:
        
        def native(self, func):
            return func
        
    micropython = Micropython()

class Lamp:

    def __init__(self, leds) -> None:
        self._leds = leds
        self._animation = None
        self._current_state = None
        
    def flash_color(self, color, framerate = 2):
        if self._animation:
            self._animation.stop()
            self._animation = None
            
        self.set_animation('flash_color', color = color, framerate = framerate)

        
    @micropython.native
    def change_state(self, feature_id, value):
        if self._animation:
            self._animation.stop()
            self._animation = None
            
        if feature_id == "change_global_color":
            self._current_state = (feature_id, value)

            self.change_all_colors(value)
            result = [(feature_id, value)]
            
            result.append(('animation', 'off'))
            result.append(('enable_audio_visualizer', 0))
            return result
        
        if feature_id == "animation":
            if value != "off":
                self._current_state = (feature_id, value)

            self.set_animation(value)
            return [(feature_id, value), ('enable_audio_visualizer', 0)]
        
        if feature_id == "enable_audio_visualizer":
            if value:
                self._current_state = (feature_id, value)

            self.set_animation('off')
            return [(feature_id, value), ('animation', "off")]
        
        if feature_id == "audio_visualizer_config":
            return [(feature_id, json.loads(value))]
            
        
        return [(feature_id, value)]
    
    def current_state(self):
        return self._current_state
    
    @micropython.native
    def set_animation(self, name, **kwargs):
        if self._animation:
            self._animation.stop()
            
        self._animation = animation.factory(name, self._leds, **kwargs)
        self._animation.start()
        
    @micropython.native
    def dance(self, amplitudes, samplerate, config):
        if not self._animation or not isinstance(self._animation, animation.AudioVisualizer):
            if self._animation:
                self._animation.stop()
                gc.collect()

            self._animation = animation.AudioVisualizer(self._leds, samplerate, config)
        self._animation.feed(amplitudes)

    @micropython.native
    def change_all_colors(self, color):
        for led in self._leds:
            led.set_color(color)
            
    @micropython.native
    def change_led_color(self, led_idx, color):
        try:
            self._leds[led_idx].set_color(color)
        except IndexError:
            return 
        
    @micropython.native
    def restore_state(self, state) -> None:
        for feature in state:
            value = feature["schema"]["default"]
            try:
                value = feature["value"]
            except:
                pass

            if feature["id"] == "change_global_color":
                self.change_all_colors(value)
                self._current_state = ("change_global_color", value)    
                continue
            
            if feature["id"] == "animation":
                self.set_animation(value)
                if value != "off":
                    self._current_state = ("animation", value)
                continue