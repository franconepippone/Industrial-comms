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




QUEUED_SENDS: int = 0


def _send_serial(data: bytes) -> bool:
    if SERIAL and SERIAL.open:
        print('sending to serial ->', data)
        SERIAL.write(data)
        return True
    else:
        print('Serial is not opened, could not send', data)
        return False

def set_autohop_pause(paused: bool):
    if paused:
        _send_serial(b'p') # paused
    else:
        _send_serial(b'r') # resume


def request_ident():
    _send_serial(b'i')
   
def change_send_loss_p(p: float):
    n = int(p)
    _send_serial(f"l{n}\n".encode())

def change_ack_loss_p(p: float):
    n = int(p)
    _send_serial(f"a{n}\n".encode())

def request_send():
    global QUEUED_SENDS
    if QUEUED_SENDS > 5:
        print('Sending too fast, cannot send')
        return
    
    if _send_serial(b's'): QUEUED_SENDS += 1

def request_hop():
    _send_serial(b'h')

def run_serial_loop():
    global SERIAL, _dashboard
    print("Serial reader loop entering active state...")
    

    while _dashboard is None:
        time.sleep(.1)

    print('DASHBOARD FOUND')
    
    ECHO_SER = False
    def set_echo(v):
        nonlocal ECHO_SER
        ECHO_SER = v

    # handles sending and hopping on demand
    _dashboard.logs.bind_send_callback(request_send)
    _dashboard.logs.bind_hop_callback(request_hop)
    print(_dashboard.logs.send_callback, id(_dashboard))

    # handles selecting and connecting to serial
    _dashboard.controls.set_ports(get_available_ports())
    _dashboard.controls.set_connect_callback(initialize_serial)

    # set
    _dashboard.controls.set_echo_toggle_callback(set_echo)
    _dashboard.controls.set_autohop_callbacks(
        partial(set_autohop_pause, True),
        partial(set_autohop_pause, False)
    )
    
    # handles simulated fault probability change
    _dashboard.controls.bind_callbacks(change_ack_loss_p, change_send_loss_p)


    for i in range(1, 15):
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
            
            if ECHO_SER:
                print("BOARD ECHO >>> \t", line)
            
            command, args = parse_ui_logs(line)
            
            match command:
                case 'RECV':
                    print('GOT RECV. ', args)
                    time_ms, mac, size, nonce, packid, duplicate_f = args
                    duplicate_f = bool(int(duplicate_f))
                    status = 'OK' if not duplicate_f else 'OK (duplicate)'
                    color = LogColor.SUCCESS if not duplicate_f else LogColor.WARNING
                    mac = '(from) ' + mac
                    _dashboard.logs.add('➟ RX', mac, status, time_ms, size, nonce, packid, color)
                        
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
                    
                    global QUEUED_SENDS
                    if QUEUED_SENDS > 0 and (int(status) == 0 or err_code in ("timeout", "maxretries")):
                        QUEUED_SENDS -= 1 # consume one send if succesfull
                        print("QUEUED SENDS: ", QUEUED_SENDS)
                    
                    status_str += f' (retry# {attempt_n})' if int(attempt_n) != 0 else ''
                    

                    _dashboard.logs.add('TX ➟', mac, status_str, time_ms, size, nonce, packid, color)
                
                case 'IDENT':
                    mac, name = args
                    _dashboard.controls.set_id(name)
                    _dashboard.controls.set_mac(mac)

                case 'HOPCTRL':
                    print('GoT HOPCTRL', args)
                    subcomm, args = args[0], args[1:]

                    match subcomm:
                        case 'LOG':
                            time_ms, current_ch, D, R = args

                            time_s = int(time_ms) / 1000
                            D = float(D)
                            R = float(R)

                            _dashboard.plots.append(time_s, R, D)
                            _dashboard.plots.set_bar(int(current_ch), R)
                        
                        case 'TRIGGER':
                            pass
                        
                        case 'PAUSE':
                            pass

                case 'HOP':
                    print("got HOP", args)
                    subcomm, args = args[0], args[1:]

                    def log_hop(status: str, color: LogColor):
                        if _dashboard:
                            _dashboard.logs.add('HOP', '—', status, time_ms, '—', '—', '—', color)

                    if subcomm == "INIT":
                        time_ms, ch  = args
                        log_hop(f'INIT (ch {ch})', LogColor.LOG_INFO)
                    elif subcomm == 'CHANNEL':
                        time_ms, ch  = args
                        log_hop(f'CURRENT CH: {ch}', LogColor.LOG_INFO)
                        _dashboard.plots.clear_plot()
                    elif subcomm == 'GOTACK':
                        time_ms, ch  = args
                        log_hop(f'GOTACK (ch {ch})', LogColor.LOG_INFO)
                    elif subcomm == 'GOTRQST':
                        time_ms, ch  = args
                        log_hop(f'GOTRQST (ch {ch})', LogColor.LOG_INFO)

                    elif subcomm == 'INITWRN':
                        time_ms, errcode  = args
                        log_hop(f'INWRN (ERR {errcode})', LogColor.LOG_ERROR)
                    elif subcomm == 'ACKRFAIL':
                        time_ms, ch  = args
                        log_hop(f'ACKR FAIL (ch {ch})', LogColor.LOG_ERROR)
                    elif subcomm == 'WRONGCHANNEL':
                        time_ms, ch_ack, ch_rqst  = args
                        log_hop(f'EACK ({ch_ack}!={ch_rqst})', LogColor.LOG_ERROR)
                    elif subcomm == 'TIMEOUT':
                        time_ms, ch = args
                        log_hop(f'T/O (ch {ch})', LogColor.LOG_ERROR)

        except Exception as e:
            print(f"Serial error encountered: {e}")
            time.sleep(1)