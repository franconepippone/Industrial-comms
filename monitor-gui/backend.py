import serial
from serial.tools import list_ports

from dashboard.app import App

def get_available_ports():
    ports = list_ports.comports()
    return [p.device for p in ports]


LOGSEQ = r'&&&'

def run(app: App):
    
    ser = serial.Serial('COM5', baudrate=115200)
    ser.timeout = .1

    print("reading")
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line == "":
            continue
        
        if not line.startswith(LOGSEQ):
            continue

        line = line[3:]
        args = line.split('::')
        command = args[0]
        print(args)

        match command:
            case 'RECV':
                mac, size, nonce, packid, time_ms = args[1:]
                #app.logs.add('-> RX', mac, str(size))
                app.call(app.logs.add, '-> RX', mac, str(size))

