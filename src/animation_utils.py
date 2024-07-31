import math

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
def loudness_to_brightness(loudness):
    dbfs_min = -27
    dbfs_max = 0
    
    # Clamping the loudness to be within the specified range
    dbfs = max(min(loudness, dbfs_max), dbfs_min)
    
    # Normalizing the loudness within the range [0, 1]
    normalized = (dbfs - dbfs_min) / (dbfs_max - dbfs_min)
    
    # Applying an exponential transformation
    exponent = 2  # Adjust this exponent to tweak the curve
    brightness_normalized = math.pow(normalized, exponent)
    
    # Scaling the normalized brightness to [0, 255]
    brightness = int(brightness_normalized * 255)
    return brightness

def loudness_to_brightness_linear(loudness):
    # if loudness >= -1.5:
    #     return 255
    
    # if loudness >= -3:
    #     return 100
    
    # if loudness >= -6:
    #     return 75

    # if loudness >= -12:
    #     return 50

    # if loudness >= -15:
    #     return 25

    # if loudness >= -18:
    #     return 10

    # if loudness >= -30:
    #     return 5
    
    # return 0
    
    dbfs_min = -60
    dbfs_max = 0
    
    dbfs = max(min(loudness, dbfs_max), dbfs_min)
    brightness = int(((dbfs - dbfs_min) / (dbfs_max - dbfs_min)) * 255)
    return brightness

@micropython.native
def pulse_color(color, amplitudes):
    # loudness = sum(amplitudes) / len(amplitudes)
    # factor = loudness_to_brightness(loudness)
    factor = loudness_to_brightness(amplitudes[0])
    
    r, g, b = [int(c * factor / 255) for c in color]
    
    return (r, g, b)
    