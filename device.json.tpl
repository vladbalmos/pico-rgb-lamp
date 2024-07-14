{
    "id": "RGB_MQTT_LAMP_001",
    "name": "RGB MQTT Lamp",
    "ssid": "wifi SSID",
    "password": "wifi password",
    "server": "ip or domain of MQTT server",
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