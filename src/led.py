from machine import PWM

_MAX_DUTY_CYCLE = const(65535)
_PWM_FREQ = const(1000)

_RED_MAX = const(240)
_GREEN_MAX = const(255)
_BLUE_MAX = const(255)

# When mixing red, down scale green & blue
_RED_GREEN_SCALING_FACTOR = const(1.7)
_RED_BLUE_SCALING_FACTOR = const(2)


class LED:
    Colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
    }
    
    def __init__(self, red_pin, blue_pin, green_pin, invert_duty_cycle = False) -> None:
        self._red_pin = PWM(red_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._green_pin = PWM(blue_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._blue_pin = PWM(green_pin, freq=_PWM_FREQ, duty_u16=_MAX_DUTY_CYCLE)
        self._invert_duty_cycle = invert_duty_cycle
        self.color = None
        
    def _convert_color(self, color):
        colors = LED.Colors
        # Convert color to tuple(red, green, blue)
        # where each color channel is between 0, 255
        color_tuple = None
        if isinstance(color, str) and color in colors:
            color_tuple = colors[color]
        
        if not color_tuple and isinstance(color, str) and color.startswith("#"):
            color = color[1:]
            if len(color) == 6:
                try:
                    color_tuple = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                except ValueError:
                    pass
        
        if not color_tuple and isinstance(color, int):
            red = (color >> 16) & 0xFF
            green = (color >> 8) & 0xFF
            blue = color & 0xFF
            color_tuple = (red, green, blue)
            
        if color_tuple:
            # Adjust the color values and create a new tuple
            adjusted_red = color_tuple[0]
            if adjusted_red > 0:
                adjusted_green = int(color_tuple[1] / _RED_GREEN_SCALING_FACTOR)
                adjusted_blue = int(color_tuple[2] / _RED_BLUE_SCALING_FACTOR)
            else:
                adjusted_green = color_tuple[1]
                adjusted_blue = color_tuple[2]
            color_tuple = (min(_RED_MAX, adjusted_red), min(_GREEN_MAX, adjusted_green), min(_BLUE_MAX, adjusted_blue))

        return color_tuple

    def set_color(self, color) -> None:
        if not isinstance(color, tuple):
            color = self._convert_color(color)
        
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
        
    def set_duty(self, r, g, b):
        self._red_pin.duty_u16(_MAX_DUTY_CYCLE - r)
        self._green_pin.duty_u16(_MAX_DUTY_CYCLE - g)
        self._blue_pin.duty_u16(_MAX_DUTY_CYCLE - b)
