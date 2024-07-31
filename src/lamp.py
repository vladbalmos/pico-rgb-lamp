import gc
import animation

class Lamp:

    def __init__(self, leds) -> None:
        self._leds = leds
        self._animation = None
        
    @micropython.native
    def change_state(self, feature_id, value):
        if self._animation:
            self._animation.stop()
            self._animation = None
            
        if feature_id == "change_global_color":
            self.change_all_colors(value)
            result = [(feature_id, value)]
            for i in range(len(self._leds)):
                result.append(('change_led' + str(i) + '_color', value))
            
            result.append(('animation', 'off'))
            return result
        
        if feature_id.startswith("change_led") and feature_id.endswith("_color"):
            try:
                led_idx = int(feature_id[10])
            except ValueError:
                return
            self.change_led_color(led_idx, value)
            return [(feature_id, value), ('animation', 'off')]
        
        if feature_id == "animation":
            self.set_animation(value)
            return [(feature_id, value)]
        
        return [(feature_id, value)]
    
    @micropython.native
    def set_animation(self, name):
        if self._animation:
            self._animation.stop()
            
        self._animation = animation.factory(name, self._leds)
        self._animation.start()
        
    @micropython.native
    def dance(self, amplitudes, fft_framerate):
        if not self._animation or not isinstance(self._animation, animation.AudioVisualizer):
            if self._animation:
                self._animation.stop()
                gc.collect()

            self._animation = animation.AudioVisualizer(self._leds, fft_framerate, "pulse")
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
                continue
            
            if feature["id"].startswith("change_led") and feature["id"].endswith("_color"):
                try:
                    led_idx = int(feature["id"][10])
                except ValueError:
                    return
                self.change_led_color(led_idx, value)

            if feature["id"] == "animation":
                self.set_animation(value)
                continue