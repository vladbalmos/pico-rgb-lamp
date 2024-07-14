# RGB Lamp

With MQTT support

# System requirements

* micropython (RPI_PICO_W-20240602-v1.23.0)
* mpremote

# Install

    git clone [url]
    git submodule update --init --recursive

# Building and flashing

Copy `device.json.tpl` to `device.json` and configure your wifi & mqtt settings

## Linux

## Windows

    build.ps1 -Command build
    
# Runnig while in development

Once micropython is flashed and the source code files are copied to the device (see [Building and flashing](#building-and-flashing)) run:

    build.ps1 -Command run
    
This will reset the device first, copy the `src/` dir to the device and then call `mpremote run src/main.py`


