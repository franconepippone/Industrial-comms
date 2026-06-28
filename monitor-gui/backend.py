import serial
from serial.tools import list_ports


def get_available_ports():
    ports = list_ports.comports()
    return [p.device for p in ports]


