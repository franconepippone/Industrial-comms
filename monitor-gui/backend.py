from typing import Callable
from functools import partial
from dashboard.app import MainDashboard
from dashboard.panels import LogColor
import serial
from serial.tools import list_ports
import time

SERIAL: serial.Serial | None = None
_dashboard: MainDashboard | None = None

def get_available_ports():
    return [p.device for p in list_ports.comports()]

def register_dashboard(dashboard: MainDashboard):
    """Allows the UI to register a handler for incoming serial data."""
    global _dashboard
    _dashboard = dashboard

def parse_ui_logs(line: str) -> tuple[None | str, tuple[str, ...]]:
    LOGSEQ = r'&&&'
    if not line.startswith(LOGSEQ):
        return None, tuple()
    
    line = line[3:]
    args = line.split('::')
    return args[0], tuple(args[1:])

def initialize_serial(port: str):
    global SERIAL
    if SERIAL is not None:
        print("closing serial", SERIAL)
        SERIAL.close()
        time.sleep(.5)
    
    try:
        SERIAL = serial.Serial(port, baudrate=115200, timeout=.1)
    except Exception as e:
        print('Serial failed to connect: ', e)
        if _dashboard is not None:
            _dashboard.controls.set_connection_status(str(e), LogColor.ERROR)
            return
    
    if _dashboard is not None:
        _dashboard.controls.set_connection_status(f'Connection successfull to {port}')
    print(f"Serial connected to {port}")

        


def request_send():
    if SERIAL and SERIAL.open:
        print('sending to serial')
        SERIAL.write(b's')
    else:
        print('Serial is not opened')

def run_serial_loop():
    global SERIAL, _dashboard
    print("Serial reader loop entering active state...")
    

    while _dashboard is None:
        time.sleep(.1)

    print('DASHBOARD FOUND')
    
    _dashboard.logs.bind_send_callback(request_send)
    print(_dashboard.logs.send_callback, id(_dashboard))

    _dashboard.controls.set_ports(get_available_ports())
    _dashboard.controls.set_connect_callback(initialize_serial)

    while True:
        if _dashboard is None:
            continue


        if SERIAL is None or not SERIAL.is_open:
            time.sleep(0.5)
            continue
            
        try:
            line = SERIAL.readline().decode(errors="ignore").strip()
            if not line:
                continue
            
            command, args = parse_ui_logs(line)
            
            match command:
                case 'RECV':
                    print('GOT RECV. ', args)
                    time_ms, mac, size, nonce, packid, duplicate_f = args
                    duplicate_f = bool(int(duplicate_f))
                    status = 'OK' if not duplicate_f else 'OK (duplicate)'
                    color = LogColor.SUCCESS if not duplicate_f else LogColor.WARNING
                    mac = '(from) ' + mac
                    _dashboard.logs.add('RX', mac, status, time_ms, size, nonce, packid, color)
                        
                case 'SEND':
                    MAX_ATTEMPTS = 5

                    print('GOT SEND:', args)
                    time_ms, mac, status, size, nonce, packid, attempt_n = args
                    color = LogColor.SUCCESS
                    if (int(attempt_n) > 0):
                        color = LogColor.WARNING
                    if (int(attempt_n) == MAX_ATTEMPTS):
                        color = LogColor.ERROR

                    mac = '(to) ' + mac
                    status_str = 'OK' if status != 0 else f'ERR ({status})'
                    status_str += f' (attempt#: {attempt_n})' if int(attempt_n) != 0 else ''

                    _dashboard.logs.add('TX', mac, status_str, time_ms, size, nonce, packid, color)
                
                case 'IDENT':
                    mac, name = args
                    _dashboard.controls.set_id(name)
                    _dashboard.controls.set_mac(mac)

                

        except Exception as e:
            print(f"Serial error encountered: {e}")
            time.sleep(1)