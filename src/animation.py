from collections import deque
import utils
from machine import Timer
import random

_FRAME_RATE = const(60)


class Animation:
    def __init__(self, leds, duration_s = 5.0):
        self._leds = leds
        self._timer = None
        self._duration_s = duration_s
        self._steps = duration_s * _FRAME_RATE
        self._current_step = 1
        self._framerate = _FRAME_RATE
    
    def stop(self):
        if self._timer:
            self._timer.deinit()
            self._timer = None
            
    def is_running(self):
        return self._timer is not None

    def start(self):
        if not len(self._leds):
            return
        
        if self._leds[0].color is None:
            return

        self._timer = Timer(-1)
        self._timer.init(mode = Timer.PERIODIC, freq = self._framerate, callback = self._update)
        
    def _update(self, _):
        # Implement in child class
        pass
    
class NoAnimation(Animation):
    
    def __init__(self, leds, duration_s = 5.0):
        super().__init__(leds, duration_s)
        
    def start(self):
        pass
    
    def stop(self):
        pass
        
class TransitionAnimation(Animation):

    def __init__(self, leds, from_color, to_color, duration_s = 5.0):
        super().__init__(leds, duration_s)
        self._from_color = from_color
        self._to_color = to_color
        self._dr = (to_color[0] - from_color[0]) / self._steps
        self._dg = (to_color[1] - from_color[1]) / self._steps
        self._db = (to_color[2] - from_color[2]) / self._steps
        
    def _update(self, _):
        from_color = self._from_color
        steps = self._steps
        leds = self._leds
        
        dr = self._dr
        dg = self._dg
        db = self._db

        r = from_color[0] + self._current_step * dr
        g = from_color[1] + self._current_step * dg
        b = from_color[2] + self._current_step * db
        
        
        for _led in leds:
            _led.set_color((round(r), round(g), round(b)))

        self._current_step += 1
        if self._current_step > steps:
            super().stop()
        
        
class RainbowAnimation(Animation):
    def __init__(self, leds, duration_s = 5, color = None):
        super().__init__(leds, duration_s)
        self._current_color_index = 0
        self._current_animation = None
        self._rainbow_colors = [
            (255, 0, 0), # red 
            (255, 127, 0), # orange 
            (255, 255, 0), # yellow 
            (0, 255, 0), # green 
            (0, 0, 255), # blue 
            (75, 0, 130), # indigo 
            (148, 0, 211) # violet 
        ]
        
    def start(self):
        self._timer = Timer(-1)
        self._timer.init(mode = Timer.PERIODIC, period = int(self._duration_s * 1000), callback = self._update)
        self._update(None)
    
    def stop(self):
        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None
        
        if self._timer:
            self._timer.deinit()
            self._timer = None
            
    def _update(self, _):
        if self._current_animation:
            self._current_animation.stop()
            
        rainbow_colors = self._rainbow_colors

        from_color = rainbow_colors[self._current_color_index]
        
        if self._current_color_index == len(rainbow_colors) - 1:
            to_color = rainbow_colors[0]
            self._current_color_index = 0
        else:
            to_color = rainbow_colors[self._current_color_index + 1]
            self._current_color_index += 1
            
        self._current_animation = TransitionAnimation(self._leds, from_color, to_color, self._duration_s)
        self._current_animation.start()

        
class BreatheAnimation(Animation):

    def __init__(self, leds, duration_s = 5, color = None):
        super().__init__(leds, duration_s)
        self._brighter = False
        if color:
            color = utils.convert_color(color)
        else:
            color = utils.maximize_brightness(self._leds[0].color)

        self._starting_r, self._starting_g, self._starting_b = color
        self._min_brightness = 0.05
        
    def _update(self, _):
        leds = self._leds
        steps = self._steps
        min_brightness = self._min_brightness
        starting_r = self._starting_r
        starting_g = self._starting_g
        starting_b = self._starting_b

        if self._current_step > steps:
            self._current_step = 1
            if not self._brighter:
                self._brighter = True
            else:
                self._brighter = False

        if not self._brighter:
            dim_factor = max(min_brightness, 1 - self._current_step / steps)
        else:
            dim_factor = max(min_brightness, self._current_step / steps)
        
        r = starting_r * dim_factor
        g = starting_g * dim_factor
        b = starting_b * dim_factor
        
        self._current_step += 1
        
        for _led in leds:
            _led.set_color((round(r), round(g), round(b)))

class WheelAnimation(Animation):

    def __init__(self, leds, duration_s = 60, color = None):
        super().__init__(leds, duration_s)
        if color:
            color = utils.convert_color(color)
        else:
            color = utils.maximize_brightness(self._leds[0].color)

        self._h, self._s, self._v = utils.rgb_to_hsv(*color)

    def _update(self, _):
        leds = self._leds
        steps = self._steps
        self._h += 360 / steps
        
        s = self._s
        v = self._v
        
        if self._h > 360:
            self._h = 0
            
        r, g, b = utils.hsv_to_rgb(self._h, s, v)

        for _led in leds:
            _led.set_color((round(r), round(g), round(b)))
            
class FlashColorAnimation(Animation):
    
    def __init__(self, leds, framerate = 2, color = '#ffffff'):
        super().__init__(leds)
        self._r, self._g, self._b = utils.convert_color(color)
        self._framerate = framerate
        self._state = False
        
    def _update(self, _):
        if self._state:
            color = (0, 0, 0)
            self._state = False
        else:
            color = (self._r, self._g, self._b)
            self._state = True

        for _led in self._leds:
            _led.set_color((color))
            
class AudioVisualizer(Animation):
    
    def __init__(self, leds, samplerate, animation_config):
        super().__init__(leds)
        self._colors_queue = deque([], 8)
        self._state_change_frames_count = _FRAME_RATE // samplerate
        self._last_color = (0, 0, 0)
        self._last_brightness = 0
        self._color_transformer_fn = None
        self._last_updated_ms = 0
        self._last_fed_ms = 0
        self._animation_config = self._compile_config(animation_config)
        self._current_style = None
        
    def _compile_config(self, animation_config):
        config = {
            "dbfs": animation_config["dbfs"],
            "loudness_functions": {},
            "styles": {},
            "active_style": animation_config["active_style"]
        }
        for fn in animation_config["loudness_functions"]:
            name = fn["name"]
            code = compile(fn["eval"], "<string>", "eval")
            config["loudness_functions"][name] = code
            
        for style in animation_config["styles"]:
            name = style["name"]
            channel_functions = {}
            for channel in style["channels"]:
                fn_name, arg = style["channels"][channel]
                code = f"self._get_loudness('{fn_name}', {arg})"
                channel_functions[channel] = compile(code, "<string>", "eval")
            config["styles"][name] = channel_functions
            
        return config
    
    def _get_loudness(self, fn_name, amplitudes):
        if fn_name == "rand_loudness":
            fn_name = random.choice(list(self._animation_config["loudness_functions"].keys()))
            
        # TODO: pulse color wheel
        # TODO: pulse rogvaiv
        amplitude = eval(self._animation_config["loudness_functions"][fn_name], {"amplitudes": amplitudes, "random": random})
        return amplitude
    
    def _color_transformer(self, color, amplitudes):
        if self._current_style is None:
            current_style = self._animation_config["active_style"]
            for style in self._animation_config["styles"]:
                if style == current_style:
                    self._current_style = self._animation_config["styles"][style]
                    break
                
        if self._current_style is None:
            return color
        
        r_amplitude = eval(self._current_style["red"], {"self": self, "amplitudes": amplitudes})
        g_amplitude = eval(self._current_style["green"], {"self": self, "amplitudes": amplitudes})
        b_amplitude = eval(self._current_style["blue"], {"self": self, "amplitudes": amplitudes})
        
        red = utils.loudness_to_brightness(r_amplitude, self._animation_config["dbfs"])
        green = utils.loudness_to_brightness(g_amplitude, self._animation_config["dbfs"])
        blue = utils.loudness_to_brightness(b_amplitude, self._animation_config["dbfs"])
        
        return (red, green, blue)
        
    def feed(self, amplitudes):
        frames_count = self._state_change_frames_count
        
        current_color = self._color_transformer(self._leds[0].color, amplitudes)
        
        for i in range(frames_count):
            t = i / (frames_count - 1)
            interpolated_color = utils.interpolate_color(self._last_color, current_color, t)
            self._colors_queue.appendleft(interpolated_color)
            
        self._last_color = current_color
        
        if not self.is_running():
            self.start()
            
    def _update(self, _):

        if not len(self._colors_queue):
            return
        
        color = self._colors_queue.pop()
        
        for _led in self._leds:
            _led.set_color(color)

    
def factory(animation, leds, **kwargs):
    if animation == "rainbow":
        return RainbowAnimation(leds, **kwargs)
    if animation == "breathe":
        return BreatheAnimation(leds, **kwargs)
    if animation == "wheel":
        return WheelAnimation(leds, **kwargs)
    if animation == "flash_color":
        return FlashColorAnimation(leds, **kwargs)

    return NoAnimation(leds)