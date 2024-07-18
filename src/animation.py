import time
import led
from machine import Timer

FRAME_RATE = 60

rainbow_colors = [
    (255, 0, 0), # red 
    (255, 127, 0), # orange 
    (255, 255, 0), # yellow 
    (0, 255, 0), # green 
    (0, 0, 255), # blue 
    (75, 0, 130), # indigo 
    (148, 0, 211) # violet 
]

def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0:
        s = 0
    else:
        s = (df/mx) * 100
    v = mx * 100
    return (h, s, v)    

def hsv_to_rgb(h, s, v):
    s /= 100  # Convert percentage to [0, 1]
    v /= 100  # Convert percentage to [0, 1]
    
    if s == 0:
        # Achromatic (grey)
        r = g = b = v * 255
        return int(r), int(g), int(b)
    
    h = h / 60  # sector 0 to 5
    i = int(h)
    f = h - i  # factorial part of h
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:  # i == 5
        r, g, b = v, p, q
    
    r = r * 255
    g = g * 255
    b = b * 255
    
    return int(r), int(g), int(b)

class Animation:
    def __init__(self, leds, duration_s = 5.0):
        self._leds = leds
        self._timer = None
        self._duration_s = duration_s
        self._steps = duration_s * FRAME_RATE
        self._current_step = 1
    
    def stop(self):
        if self._timer:
            self._timer.deinit()
            self._timer = None

    def start(self):
        if not len(self._leds):
            return
        
        if self._leds[0].color is None:
            return

        self._timer = Timer(-1)
        self._timer.init(mode = Timer.PERIODIC, freq = FRAME_RATE, callback = self._update)
        
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
        r = self._from_color[0] + self._current_step * self._dr
        g = self._from_color[1] + self._current_step * self._dg
        b = self._from_color[2] + self._current_step * self._db
        
        
        for _led in self._leds:
            _led.set_color((round(r), round(g), round(b)))

        self._current_step += 1
        if self._current_step > self._steps:
            super().stop()
        
        
class RainbowAnimation(Animation):
    def __init__(self, leds, duration_s = 5):
        super().__init__(leds, duration_s)
        self._current_color_index = 0
        self._current_animation = None
        
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

    def __init__(self, leds, duration_s = 5):
        super().__init__(leds, duration_s)
        self._brighter = False
        self._starting_r, self._starting_g, self._starting_b = self._leds[0].color
        self._min_brightness = 0.05
        
    def _update(self, _):
        if self._current_step > self._steps:
            self._current_step = 1
            if not self._brighter:
                self._brighter = True
            else:
                self._brighter = False

        if not self._brighter:
            dim_factor = max(self._min_brightness, 1 - self._current_step / self._steps)
        else:
            dim_factor = max(self._min_brightness, self._current_step / self._steps)
        
        r = self._starting_r * dim_factor
        g = self._starting_g * dim_factor
        b = self._starting_b * dim_factor
        
        self._current_step += 1
        
        for _led in self._leds:
            _led.set_color((round(r), round(g), round(b)))

class WheelAnimation(Animation):

    def __init__(self, leds, duration_s = 20.0):
        super().__init__(leds, duration_s)
        self._h, self._s, self._v = rgb_to_hsv(*self._leds[0].color)

    def _update(self, _):
        self._h += 360 / self._steps
        
        if self._h > 360:
            self._h = 0
            
        r, g, b = hsv_to_rgb(self._h, self._s, self._v)

        for _led in self._leds:
            _led.set_color((round(r), round(g), round(b)))

    
def factory(animation, leds):
    if animation == "rainbow":
        return RainbowAnimation(leds)
    if animation == "breathe":
        return BreatheAnimation(leds)
    if animation == "wheel":
        return WheelAnimation(leds)
    return NoAnimation(leds)