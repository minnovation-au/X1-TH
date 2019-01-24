####################### GLOBAL SETUP ############################

SITE = '#####' ############################### Site Gateway Prefix
key = b'################################' ### Encryption Key

###################### Device Setup ############################

import machine, utime, ubinascii, socket, pycom, crypto, gc
from machine import I2C, deepsleep, Pin, Timer, WDT
from network import LoRa, WLAN
from crypto import AES

iv = crypto.getrandbits(128) # hardware generated random IV (never reuse it)

wdt = WDT(timeout=10000)  # enable it with a timeout of 2 seconds
gc.enable()

def readSensor():
    sensorOn = machine.Pin('P11', mode=machine.Pin.OUT)
    sensorOn(1)

    i2c = I2C(0, I2C.MASTER)
    i2c = I2C(0, pins=('P10','P9'))

    import am2320
    am = am2320.AM2320(i2c)

    while True:
        try:
            temp = am.temperature
            hum = am.relative_humidity        
            break
        except Exception as e:
            # These sensors are a bit flakey, its ok if the readings fail
            pass

    sensorOn.value(0)

    return([temp,hum])

sensorVals = readSensor()
print(sensorVals)

def voltage():
    volts=0
    from machine import ADC
    adc = ADC()
    vpin = adc.channel(pin='P13')
    for i in range (0,999):
        volts+=vpin.voltage()/0.24444/1000
    return volts/i
voltage = voltage()

print("Voltage: ",voltage," millivolts")

def mac():
    mac=ubinascii.hexlify(machine.unique_id(),':').decode()
    mac=mac.replace(":","")
    return(mac)
print(mac())

def encrypt(send_pkg):
    cipher = AES(key, AES.MODE_CFB, iv)
    send_pkg = iv + cipher.encrypt(send_pkg)
    return(send_pkg)

def LoRaSend(val,ch):
    sl = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    sl.setblocking(True)
    sl.send(encrypt(SITE+mac()+'/'+ch+'&'+val)) # Send on LoRa Network & wait Reply
    sl.setblocking(False)
    try:
        pycom.nvs_set('num',pycom.nvs_get('num')+1)
    except:
        pycom.nvs_set('num',0)
    print("Sent",ch)

lora = LoRa(mode=LoRa.LORA, region=LoRa.AU915, power_mode=LoRa.TX_ONLY)
sl = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

msgID = str(pycom.nvs_get('num'))
string = '{"val":'+str(sensorVals[0])+',"msgID":'+str(msgID)+',"volt":'+str(voltage)+'}'
LoRaSend(string,str(1))
utime.sleep(0.1)
string = '{"val":'+str(sensorVals[1])+',"msgID":'+str(pycom.nvs_get('num'))+'}'
LoRaSend(string,str(2))

gc.collect()
machine.deepsleep(3600000)
