import network
import time
from machine import Pin
from umqtt.simple import MQTTClient
from dht import DHT11
from Wifi_connect import connect

def send_mqtt_message(message,feed):
    wlan = network.WLAN()

    if not wlan.isconnected():
        wlan = connect()

    ADAFRUIT_IO_USERNAME = ###
    ADAFRUIT_IO_KEY = ###
    ADAFRUIT_IO_FEED = feed

    client = MQTTClient(
        client_id="pico",
        server="io.adafruit.com",
        user=ADAFRUIT_IO_USERNAME,
        password=ADAFRUIT_IO_KEY,
        ssl=False
    )

    try:
        client.connect()
        topic = bytes(f"{ADAFRUIT_IO_USERNAME}/feeds/{ADAFRUIT_IO_FEED}", "utf-8")
        client.publish(topic, bytes(str(message), "utf-8"))
        print("Sent:", message)
        client.disconnect()
    except:
        print('Could not send message!')
