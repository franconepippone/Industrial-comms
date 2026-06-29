from nicegui import ui
from dashboard.app import App
from threading import Thread

from backend import get_available_ports, run

app = App()
t = Thread(target=run, args=(app,), daemon=True).start()



ui.run(
    title="Serial Monitor",
    reload=False,
)