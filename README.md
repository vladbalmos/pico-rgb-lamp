# RGB Lamp based on RP2040

An RGB lamp powered by a Raspberry Pi Pico, offering seamless control via MQTT. Customize your lighting experience with simple commands for color changes, dynamic animations, and an audio visualizer mode.

### Features:
- **MQTT Control**
- **Color Selection**
- **Animation Selection**
- **Audio Visualizer Mode**: Requires [python-fft-streamer](https://github.com/vladbalmos/python-fft-streamer).

This project is part of my basic home automation suit and requires the [pihub](https://github.com/vladbalmos/pihub) server for remote control.

#### Demo
[![Demo](https://img.youtube.com/vi/2PfCFWdMnYo/0.jpg)](https://www.youtube.com/watch?v=2PfCFWdMnYo)

[View on YouTube](https://www.youtube.com/watch?v=2PfCFWdMnYo)

# System requirements

* micropython (RPI_PICO_W-20240602-v1.23.0)
* mpremote

For a complete bill of materials see the [hw/pcb](https://github.com/vladbalmos/pico-rgb-lamp/tree/main/hw/pcb/rgb-lamp) folder.

# Install

    git clone [url]
    git submodule update --init --recursive
    
# Building and flashing
Copy `device.tpl.json` to `device.json` and configure your wifi & mqtt settings. See [Device configuration](#device-configuration) for available options

## Linux

## Windows

    build.ps1 -Command build
    
# Runnig while in development

Once micropython is flashed and the source code files are copied to the device (see [Building and flashing](#building-and-flashing)) run:

    build.ps1 -Command run
    
This will reset the device first, copy the `src/` dir to the device and then call `mpremote run src/main.py`


# Device configuration

The configuration is provided in JSON format and is used to customize various aspects of the lamp, including its MQTT communication, features, and hardware setup.

## Configuration Fields

### 1. `id`
- **Type**: String
- **Description**: A unique identifier for the RGB MQTT Lamp.
- **Example**: `"RGB_MQTT_LAMP_001"`

### 2. `name`
- **Type**: String
- **Description**: The name of the RGB MQTT Lamp.
- **Example**: `"RGB MQTT Lamp"`

### 3. `ssid`
- **Type**: String
- **Description**: The SSID of the WiFi network to which the lamp should connect.

### 4. `password`
- **Type**: String
- **Description**: The password for the WiFi network.

### 5. `server`
- **Type**: String
- **Description**: The IP address or domain of the MQTT server that the lamp will communicate with.
- **Example**: `"mqtt.example.com"`

### 6. `config`
- **Type**: Object
- **Description**: Configuration related to the hardware setup and features of the lamp.

#### 6.1 `led_pins`
- **Type**: Array of integers
- **Description**: The GPIO pins used for controlling the RGB channels: [red pin, green pin, blue pin]
- **Example**: `[0, 1, 2]`

#### 6.2 `rotary_encoder_pins`
- **Type**: Array of integers
- **Description**: The GPIO pins used for the rotary encoder: [clk_pin, dt_pin]
- **Example**: `[14, 13]`

#### 6.3 `select_switch_pin`
- **Type**: Integer
- **Description**: The GPIO pin used for the select switch.
- **Example**: `15`

#### 6.4 `invert_pwm_duty_cycle`
- **Type**: Boolean
- **Description**: Whether to invert the PWM duty cycle for LED control. Usefull when using PNP / P-MOSFET drivers
- **Example**: `false`

#### 6.5 `fft_streamer`
- **Type**: Object
- **Description**: Configuration for the FFT (Fast Fourier Transform) streamer used in the audio visualizer. Not required - the lamp will automatically subscribe to the streamer mqtt channel and autoconfigure, see [python-fft-streamer](https://github.com/vladbalmos/pihub)

##### `host`
- **Type**: String or null
- **Description**: The host for the FFT streamer.
- **Example**: `null`

##### `port`
- **Type**: Integer or null
- **Description**: The port for the FFT streamer.
- **Example**: `null`

#### 6.6 `available_colors`
- **Type**: Array of strings
- **Description**: A list of predefined colors available for selection. Colors are defined in hexadecimal format.
- **Example**: `["#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff"]`

### 7. `features`
- **Type**: Array of objects
- **Description**: A list of features that the RGB MQTT Lamp supports.

#### 7.1 `name`
- **Type**: String
- **Description**: The name of the feature.
- **Example**: `"Change global color"`

#### 7.2 `id`
- **Type**: String
- **Description**: A unique identifier for the feature.
- **Example**: `"change_global_color"`

#### 7.3 `schema`
- **Type**: Object
- **Description**: The schema that defines the configuration options for the feature.

##### `type`
- **Type**: String
- **Description**: The data type of the feature's configuration value.
- **Example**: `"color"`, `"boolean"`, `"json"`, `"list"`

##### `default`
- **Type**: Depends on `type`
- **Description**: The default value for the feature's configuration.

###### For `change_global_color`:
- **Example**: `"#ff0000"`

###### For `enable_audio_visualizer`:
- **Example**: `false`

###### For `audio_visualizer_config`:
- **Example**: JSON object with audio visualizer settings.

###### For `animation`:
- **Example**: `"off"`

#### 7.4 `valid_values` (for `list` type)
- **Type**: Array of strings
- **Description**: A list of valid values for the feature.
- **Example**: `["off", "breathe", "wheel", "rainbow"]`

### 8. `topics`
- **Type**: Object
- **Description**: The MQTT topics used for subscription and publishing.

#### 8.1 `subscription`
- **Type**: Object
- **Description**: MQTT topics to which the lamp subscribes.

##### `manager`
- **Type**: String
- **Description**: The MQTT topic for manager requests.
- **Example**: `"acme/devices/request"`

##### `lighting`
- **Type**: String
- **Description**: The MQTT topic for lighting control.
- **Example**: `"acme/devices/lighting"`

##### `device`
- **Type**: String
- **Description**: The MQTT topic for device-specific requests.
- **Example**: `"acme/devices/lighting/name-of-device/request"`

#### 8.2 `publish`
- **Type**: Object
- **Description**: MQTT topics to which the lamp publishes messages.

##### `manager`
- **Type**: String
- **Description**: The MQTT topic for manager responses.
- **Example**: `"acme/devices/response"`

##### `device`
- **Type**: String
- **Description**: The MQTT topic for device-specific responses.
- **Example**: `"acme/devices/lighting/name-of-device/response"`