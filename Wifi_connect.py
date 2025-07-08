import network
import time


def connect():
    ssid = ###
    password = ###

    wlan = network.WLAN()
    
    
    wlan.active(True)
    wlan.connect(ssid, password)
    
    while wlan.isconnected() == False:
        print('waiting for connection...')
        time.sleep(1)
    
    print('Connected!')
    
    return wlan
