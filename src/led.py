import utils
from machine import PWM

_MAX_DUTY_CYCLE = const(65535)
_PWM_FREQ = const(1000)

_RED_MAX = const(255)
_GREEN_MAX = const(255)
_BLUE_MAX = const(255)

# When mixing red, down scale green & blue
_RED_GREEN_SCALING_FACTOR = const(1.7)
_RED_BLUE_SCALING_FACTOR = const(2)

if "micropython" not in globals():
    class Micropython:
        
        def native(self, func):
            return func
        
    micropython = Micropython()

class LED:
    def __init__(self, red_pin, green_pin, blue_pin, invert_duty_cycle = False) -> None:
        self._red_pin = PWM(red_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._green_pin = PWM(green_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._blue_pin = PWM(blue_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._invert_duty_cycle = invert_duty_cycle
        self.color = None
        
    @micropython.native
    def set_color(self, color) -> None:
        if not isinstance(color, tuple):
            color = utils.convert_color(color)
        
        if color is None:
            return
        
        self.color = color

        r, g, b = color
        
        r = r * 257
        g = g * 257
        b = b * 257
        
        if self._invert_duty_cycle:
            # If using PNP transistors for driving, we need to invert the duty cycle
            r = _MAX_DUTY_CYCLE - r
            g = _MAX_DUTY_CYCLE - g
            b = _MAX_DUTY_CYCLE - b

        self._red_pin.duty_u16(r)
        self._green_pin.duty_u16(g)
        self._blue_pin.duty_u16(b)
        
    @micropython.native
    def set_duty(self, r, g, b):
        self._red_pin.duty_u16(_MAX_DUTY_CYCLE - r)
        self._green_pin.duty_u16(_MAX_DUTY_CYCLE - g)
        self._blue_pin.duty_u16(_MAX_DUTY_CYCLE - b)
