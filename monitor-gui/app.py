from nicegui import ui
from nicegui_dashboard.app import App
from threading import Thread
import time

from backend import get_available_ports

app = App()


def backend():
    ...

    app.controls.set_ports(get_available_ports())


    while True:
        app.logs.add("ciccio", "bello", "idk")
        time.sleep(1)


t = Thread(target=backend, daemon=True).start()


ui.run(
    title="Serial Monitor",
    reload=False,
)