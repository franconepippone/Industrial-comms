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

        time.sleep(.5)
        request_ident()

    except Exception as e:
        print('Serial failed to connect: ', e)
        if _dashboard is not None:
            _dashboard.controls.set_connection_status(str(e), LogColor.ERROR)
            return
    
    if _dashboard is not None:
        _dashboard.controls.set_connection_status(f'Connection successfull to {port}')
    print(f"Serial connected to {port}")

def _send_serial(data: bytes) -> serial.Serial | None:
    if SERIAL and SERIAL.open:
        print('sending to serial ->', data)
        SERIAL.write(data)
    else:
        print('Serial is not opened, could not send', data)

def request_ident():
    _send_serial(b'i')
   
def change_send_loss_p(p: float):
    n = int(p)
    _send_serial(f"l{n}\n".encode())

def change_ack_loss_p(p: float):
    n = int(p)
    _send_serial(f"a{n}\n".encode())

def request_send():
    _send_serial(b's')

def run_serial_loop():
    global SERIAL, _dashboard
    print("Serial reader loop entering active state...")
    

    while _dashboard is None:
        time.sleep(.1)

    print('DASHBOARD FOUND')
    
    # handles sending arbitrary message
    _dashboard.logs.bind_send_callback(request_send)
    print(_dashboard.logs.send_callback, id(_dashboard))

    # handles selecting and connecting to serial
    _dashboard.controls.set_ports(get_available_ports())
    _dashboard.controls.set_connect_callback(initialize_serial)
    
    # handles simulated fault probability change
    _dashboard.controls.bind_callbacks(change_ack_loss_p, change_send_loss_p)

    for i in range(14):
        _dashboard.plots.set_bar(i, .8)

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

            #print("BOARD ECHO >>> \t", line)
            
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

                    print('GOT SEND:', args)
                    time_ms, mac, status, size, nonce, packid, attempt_n, err_code = args
                    color = LogColor.SUCCESS
                    if (int(status) != 0):
                        color = LogColor.WARNING
                    

                    mac = '(to) ' + mac
                    status_str = 'OK' if int(status) == 0 else f'ERR {status}'
                    if err_code == "timeout":
                        status_str = 'T/O '
                        color = LogColor.ERROR
                    if err_code == "maxretries":
                        status_str = 'REX'
                    
                    status_str += f' (retry# {attempt_n})' if int(attempt_n) != 0 else ''
                    

                    _dashboard.logs.add('TX', mac, status_str, time_ms, size, nonce, packid, color)
                
                case 'IDENT':
                    mac, name = args
                    _dashboard.controls.set_id(name)
                    _dashboard.controls.set_mac(mac)

                case 'HOPCTRL':
                    print('GoT HOPCTRL', args)
                    time_ms, current_ch, D, R = args

                    time_s = int(time_ms) / 1000
                    D = float(D)
                    R = float(R)

                    _dashboard.plots.append(time_s, R, D)
                    _dashboard.plots.set_bar(int(current_ch), R)
                

        except Exception as e:
            print(f"Serial error encountered: {e}")
            time.sleep(1)