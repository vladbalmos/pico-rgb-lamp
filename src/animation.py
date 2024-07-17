import time
from machine import Timer

FRAME_RATE = 60

class Animation:
    def __init__(self, leds):
        self._leds = leds
        self._timer = None
    
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
    
    def __init__(self, leds):
        super().__init__(leds)
        
class RainbowAnimation(Animation):
    
    def __init__(self, leds):
        super().__init__(leds)
        
class FadeAnimation(Animation):

    def __init__(self, leds):
        super().__init__(leds)
        self._last_tick = time.ticks_ms()
    
    def _update(self, _):
        # now = time.ticks_ms()
        r, g, b = self._leds[0].color
        
        new_r = r + 1
        if new_r >= 244:
            new_r = 0
            
        new_g = g + 1
        if new_g >= 255:
            new_g = 0
            
        new_b = b + 1
        if new_b > 255:
            new_b = 0
            
        print(r, g, b, ' -> ', new_r, new_g, new_b)
        for led in self._leds:
            led.set_color((new_r, new_g, new_b))

    
def factory(animation, leds):
    if animation == "rainbow":
        # return RainbowAnimation(leds)
        return FadeAnimation(leds)
    return NoAnimation(leds)