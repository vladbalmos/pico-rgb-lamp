from machine import PWM

MAX_DUTY_CYCLE = 65535
PWM_FREQ = 1000

RED_MAX = 240
GREEN_MAX = 255
BLUE_MAX = 255

# When mixing red, down scale green & blue
RED_GREEN_SCALING_FACTOR = 1.7
RED_BLUE_SCALING_FACTOR = 2

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

class LED:
    
    def __init__(self, red_pin, blue_pin, green_pin) -> None:
        self._red_pin = PWM(red_pin, freq=PWM_FREQ, duty_u16=MAX_DUTY_CYCLE)
        self._green_pin = PWM(blue_pin, freq=PWM_FREQ, duty_u16=MAX_DUTY_CYCLE)
        self._blue_pin = PWM(green_pin, freq=PWM_FREQ, duty_u16=MAX_DUTY_CYCLE)
        self._color = None
        
    def _convert_color(self, color):
        # Convert color to tuple(red, green, blue)
        # where each color channel is between 0, 255
        color_tuple = None
        if isinstance(color, str):
            if color in Colors:
                color_tuple = Colors[color]
        if not color_tuple and isinstance(color, int):
            red = (color >> 16) & 0xFF
            green = (color >> 8) & 0xFF
            blue = color & 0xFF
            color_tuple = (red, green, blue)
            
        if color_tuple:
            # Adjust the color values and create a new tuple
            adjusted_red = color_tuple[0]
            if adjusted_red > 0:
                adjusted_green = int(color_tuple[1] / RED_GREEN_SCALING_FACTOR)
                adjusted_blue = int(color_tuple[2] / RED_BLUE_SCALING_FACTOR)
            else:
                adjusted_green = color_tuple[1]
                adjusted_blue = color_tuple[2]
            color_tuple = (min(RED_MAX, adjusted_red), min(GREEN_MAX, adjusted_green), min(BLUE_MAX, adjusted_blue))

        return color_tuple

    def set_color(self, color) -> None:
        if not isinstance(color, tuple):
            color = self._convert_color(color)
        
        if color is None:
            return
        
        r, g, b = color
        
        # We're driving PNP transistors, thus we need to invert the duty cycle
        r = MAX_DUTY_CYCLE - (r * 257)
        g = MAX_DUTY_CYCLE - (g * 257)
        b = MAX_DUTY_CYCLE - (b * 257)
        self._red_pin.duty_u16(r)
        self._green_pin.duty_u16(g)
        self._blue_pin.duty_u16(b)
        
    def set_duty(self, r, g, b):
        self._red_pin.duty_u16(MAX_DUTY_CYCLE - r)
        self._green_pin.duty_u16(MAX_DUTY_CYCLE - g)
        self._blue_pin.duty_u16(MAX_DUTY_CYCLE - b)
