from typing import Callable
from functools import partial
from dashboard.app import MainDashboard
import serial
from serial.tools import list_ports
import time

SERIAL = None
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
    if SERIAL is None or not SERIAL.is_open:
        SERIAL = serial.Serial(port, baudrate=115200, timeout=.1)
        print(f"Serial connected to {port}")

def run_serial_loop():
    global SERIAL, _dashboard
    print("Serial reader loop entering active state...")
    
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
                    print('GOT REXCV')
                    partial(_dashboard.logs.add, 'hello')
                    _dashboard._handle_backend_stream(partial(_dashboard.logs.add, 'hello', 'there', 'my', 'name'))
                        
        except serial.SerialException as e:
            print(f"Serial error encountered: {e}")
            time.sleep(1)