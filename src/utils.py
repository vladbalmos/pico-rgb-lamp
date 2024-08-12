import math

if "micropython" not in globals():
    class Micropython:
        
        def native(self, func):
            return func
        
    micropython = Micropython()
    
def rgb_to_hex(color):
    return "#{:02x}{:02x}{:02x}".format(*color)

@micropython.native
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

@micropython.native
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

@micropython.native
def interpolate(a, b, t):
    return int((1 - t) * a + t * b)

@micropython.native
def interpolate_color(c1, c2, t):
    result = [interpolate(c1[i], c2[i], t) for i in range(3)]
    return tuple(result)

@micropython.native
def loudness_to_brightness(loudness, dbfs = None):
    if dbfs is None:
        dbfs_min = -27
        dbfs_max = 0
        exponent = 2  # Adjust this exponent to tweak the curve
    else:
        dbfs_min = dbfs["min"]
        dbfs_max = dbfs["max"]
        exponent = dbfs["exponent"]
    
    # Clamping the loudness to be within the specified range
    dbfs = max(min(loudness, dbfs_max), dbfs_min)
    
    # Normalizing the loudness within the range [0, 1]
    normalized = (dbfs - dbfs_min) / (dbfs_max - dbfs_min)
    
    # Applying an exponential transformation
    brightness_normalized = math.pow(normalized, exponent)
    
    # Scaling the normalized brightness to [0, 255]
    brightness = int(brightness_normalized * 255)
    return brightness

@micropython.native
def pulse_rgb(_, amplitudes):
    red = loudness_to_brightness(max(amplitudes[0:3]))
    green = loudness_to_brightness(min(amplitudes[3:7]))
    blue = loudness_to_brightness(sum(amplitudes[7:]) / 3)
    
    return (red, green, blue)

@micropython.native
def convert_color(color, red_max = 255, green_max = 255, blue_max = 255, red_green_scaling_factor = 1, red_blue_scaling_factor = 1):
    # Convert color to tuple(red, green, blue)
    # where each color channel is between 0, 255
    color_tuple = None
    
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
            adjusted_green = int(color_tuple[1] / red_green_scaling_factor)
            adjusted_blue = int(color_tuple[2] / red_blue_scaling_factor)
        else:
            adjusted_green = color_tuple[1]
            adjusted_blue = color_tuple[2]
        color_tuple = (min(red_max, adjusted_red), min(green_max, adjusted_green), min(blue_max, adjusted_blue))
    return color_tuple
    
def color_index_of(colors_list, color):
    for i, c in enumerate(colors_list):
        if convert_color(c) == convert_color(color):
            return i
    return None

def change_brightness(color, brightness):
    color = convert_color(color)
    h, s, v = rgb_to_hsv(*color)
    print(color, h, s, v)
    
    v = brightness / 255.0 * 100

    r, g, b = hsv_to_rgb(h, s, v)
    return (r, g, b)