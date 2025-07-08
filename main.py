import ds18x20, onewire
from machine import Pin, PWM
from time import sleep, localtime
from dht import DHT11
from Send_mqtt_message import send_mqtt_message

### Define sensors ###

# Ambient sensor (humidity and temperature)
ambient_sensor = DHT11(Pin(15))

# Coffee sensor
coffee_sensor = ds18x20.DS18X20(onewire.OneWire(Pin(22)))
roms = coffee_sensor.scan()

# Button (used as toggle)
button = Pin(16,Pin.IN,Pin.PULL_UP)

# Process alive indication LED
process_led = Pin(0,Pin.OUT)

# Coffee temperature indication leds (order green, red, blue)
leds = [Pin(11, Pin.OUT),
        Pin(12, Pin.OUT),
        Pin(13, Pin.OUT)]

# Buzzer
buzzer = PWM(Pin(5))
buzzer.freq(466)

### Define variables ###

# Toggle indicator for button
button_toggle = 0

# Toggle indicator for alive indication LED
led_toggle = 0

# Variable to indicate if coffee ready sound has already been played once during this measurement period (True = has not been played yet)
once_indication = True

# Sleeping time between cycles (seconds)
sleep_time = 5

# Last minute variable. Used to determine if ambient measurement has already been taken in the current minute or not
last_min = -1

# Time between ambient measurements (minutes)
ambient_interval = 5

# Array to keep track of the coffee temperature history (last 12 values)
temperature_history = []

### Function definition block ###

def ambient_measurement():
    # Perform ambient measurement to get humidity and temperature
    ambient_sensor.measure()
    humidity = ambient_sensor.humidity()
    ambient_temperature = ambient_sensor.temperature()
    
    # Send the corresponding values to the correct feeds
    send_mqtt_message(ambient_temperature, 'ambient_temperature')
    send_mqtt_message(humidity,'ambient_humidity')
    print('Sent ambient values!')

def measure_coffee_temp():
    # Perform coffee temperature measurement
    coffee_sensor.convert_temp()
    for rom in roms:
        coffee_temperature = coffee_sensor.read_temp(rom)
        
    # Send the corresponding value to the correct feed
    send_mqtt_message(coffee_temperature,'coffee_temperature')
    print('Sent coffee values!')
    
    return coffee_temperature
        
def alive_check(led_toggle):
    # Blink with red led once every 15 cycles to indicate that the process is alive
    led_toggle = (led_toggle + 1) % 15
    if led_toggle == 1:
        process_led.value(1)
    else:
        process_led.value(0)
    
    return led_toggle
    
def indicate_coffee_temp(coffee_temperature):
    
    # Reset values
    leds_values = [0,0,0]
    
    # Red light condition (coffee is very hot)
    if coffee_temperature > 44:
        leds_values[1] = 1
    
    # Green light condition (coffee temp in a good range)
    if 45 > coffee_temperature > 42:
        leds_values[0] = 1
    
    # Blue light condition (coffee is getting cold)
    if 43 > coffee_temperature:
        leds_values[2] = 1
    
    # Activation
    for led, value in zip(leds,leds_values):
        led.value(value)
    
def play_ready_sound():
    # Play a sound bite to indicate that the coffee is in the requested temperature interval
    
    # Length of a single note (seconds)
    note_length = 0.1

    # Dictionary of the frequency for each note
    notes = {'NOTE_B0': 31, 'NOTE_C1': 33,'NOTE_CS1': 35,'NOTE_D1':  37,'NOTE_DS1': 39,'NOTE_E1':  41,'NOTE_F1':  44,'NOTE_FS1': 46,'NOTE_G1':  49,'NOTE_GS1': 52,'NOTE_A1':  55,'NOTE_AS1': 58,'NOTE_B1':  62,'NOTE_C2':  65,'NOTE_CS2': 69,'NOTE_D2':  73,'NOTE_DS2': 78,'NOTE_E2':  82,'NOTE_F2':  87,'NOTE_FS2': 93,'NOTE_G2':  98,'NOTE_GS2': 104,'NOTE_A2':  110,'NOTE_AS2': 117,'NOTE_B2':  123,'NOTE_C3':  131,'NOTE_CS3': 139,'NOTE_D3':  147,'NOTE_DS3': 156,'NOTE_E3':  165,'NOTE_F3':  175,'NOTE_FS3': 185,'NOTE_G3':  196,'NOTE_GS3': 208,'NOTE_A3':  220,'NOTE_AS3': 233,'NOTE_B3':  247,'NOTE_C4':  262,'NOTE_CS4': 277,'NOTE_D4':  294,'NOTE_DS4': 311,'NOTE_E4':  330,'NOTE_F4':  349,'NOTE_FS4': 370,'NOTE_G4':  392,'NOTE_GS4': 415,'NOTE_A4':  440,'NOTE_AS4': 466,'NOTE_B4':  494,'NOTE_C5':  523,'NOTE_CS5': 554,'NOTE_D5':  587,'NOTE_DS5': 622,'NOTE_E5':  659,'NOTE_F5':  698,'NOTE_FS5': 740,'NOTE_G5':  784,'NOTE_GS5': 831,'NOTE_A5':  880,'NOTE_AS5': 932,'NOTE_B5': 988,'NOTE_C6': 1047,'NOTE_CS6': 1109,'NOTE_D6': 1175,'NOTE_DS6': 1245,'NOTE_E6': 1319,'NOTE_F6':  1397,'NOTE_FS6': 1480,'NOTE_G6':  1568,'NOTE_GS6': 1661,'NOTE_A6':  1760,'NOTE_AS6': 1865,'NOTE_B6':  1976,'NOTE_C7':  2093,'NOTE_CS7': 2217,'NOTE_D7':  2349,'NOTE_DS7': 2489,'NOTE_E7':  2637,'NOTE_F7':  2794,'NOTE_FS7': 2960,'NOTE_G7':  3136,'NOTE_GS7': 3322,'NOTE_A7':  3520,'NOTE_AS7': 3729,'NOTE_B7':  3951,'NOTE_C8':  4186,'NOTE_CS8': 4435,'NOTE_D8':  4699,'NOTE_DS8': 4978}

    # Note order
    melody = ['F5', 'C6', 'B5', 'C6', 'B5', 'C6', 'B5', 'C6', 'GS5', 'F5', 'F5', 'GS5', 'C6', 'CS6', 'GS5', 'CS6', 'DS6', 'C6', 'CS6', 'C6', 'CS6', 'C6']
    
    # Time between notes (in terms of note lengths)
    pauses = [5, 1, 0, 0, 0, 0, 1, 1, 3, 5, 1, 1, 1, 3, 3, 3, 3, 1, 1, 1, 1, 0]

    # Loop through the song
    for note, pause in zip(melody, pauses):
        buzzer.freq(notes[f'NOTE_{note}'])
        buzzer.duty_u16(10000)
        sleep(note_length)
        buzzer.duty_u16(0)
        sleep(pause * note_length)
        
def update_history(temperature_history, coffee_temperature):
    if len(temperature_history) >= 12:
        temperature_history.pop(0)
    
    temperature_history.append(coffee_temperature)
    return temperature_history

def check_transient(temperature_history):
    if len(temperature_history) != 12:
        return True
    
    old_avg = 0
    new_avg = 0
    for i in range(6):
        old_avg += temperature_history[i] / 6
        new_avg += temperature_history[i+6] / 6
        
    if old_avg >= new_avg:
        return False
    else:
        return True
    
        
### Execution block ###

while True:
    # Get current time. If the minute value satisfies the interval (e.g., if ambient_interval = 10, then minutes 0,10,20,30,40,50 give true) and no measurement has already been taken this minute. Make measurement!
    t = localtime()
    if t[4] % ambient_interval == 0 and last_min != t[4]:        
        ambient_measurement()
        
    ### Coffee measurement block ###
    
    # If button is pressed (when button.value() is 0), alter the toggle status (0 -> 1 or 1 -> 0)
    if button.value() == 0:
        button_toggle = (button_toggle + 1) % 2
    
    # If toggle is on, measure coffee temperature
    if button_toggle == 1:
        coffee_temperature = measure_coffee_temp()
        
        # Use RGB leds to indicate temperature
        indicate_coffee_temp(coffee_temperature)
        
        # Update the coffee temperature history and check if in transient state
        temperature_history = update_history(temperature_history, coffee_temperature)
        is_transient = check_transient(temperature_history)
        
        # If the coffee has just reached the optimal temperature range, play sound bite. Can only happen once each time a coffee measurement has been initiated (monitored by once_indication)
        if 45 > coffee_temperature > 42 and once_indication and not is_transient:
            play_ready_sound()
            once_indication = False
            buzzer.duty_u16(0)
    else:
        # If toggle is off, reset the relevant items.
        for led in leds:
            led.value(0)
        once_indication = True
        temperature_history = []
        
    # Process alive check
    led_toggle = alive_check(led_toggle)
        
    # Update what minute it currently is
    last_min = t[4]
    
    # Complete cycle by sleeping the requested time
    sleep(sleep_time)
