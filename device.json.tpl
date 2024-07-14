{
    "id": "RGB_MQTT_LAMP_001",
    "name": "RGB MQTT Lamp",
    "ssid": "wifi SSID",
    "password": "wifi password",
    "server": "ip or domain of MQTT server",
    "features": [
        {
            "name": "Change global color",
            "id": "change_global_color",
            "schema": {
                "type": "color",
                "default": "#ff0000"
            }
        },
        {
            "name": "Change LED 0 color",
            "id": "change_led0_color",
            "schema": {
                "type": "color",
                "default": "#ff0000"
            }
        },
        {
            "name": "Change LED 1 color",
            "id": "change_led1_color",
            "schema": {
                "type": "color",
                "default": "#ff0000"
            }
        },
        {
            "name": "Change LED 2 color",
            "id": "change_led2_color",
            "schema": {
                "type": "color",
                "default": "#ff0000"
            }
        },
        {
            "name": "Change LED 3 color",
            "id": "change_led3_color",
            "schema": {
                "type": "color",
                "default": "#ff0000"
            }
        }
    ],
    "topics": {
        "subscription": {
            "manager": "acme/devices/request",
            "device": "acme/devices/type-of-device/name-of-device/request"
        },
        "publish": {
            "manager": "acme/devices/response",
            "device": "acme/devices/type-of-device/name-of-device/response"
        }
    }
}