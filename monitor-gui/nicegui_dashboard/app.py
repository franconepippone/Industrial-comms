"""
app.py

Entry point of the application.

Responsibilities:
- Create NiceGUI app
- Instantiate panels
- Expose simple API:
      app.controls
      app.logs
      app.plots
"""

from nicegui import ui
import time
from panels import ControlPanel, LogPanel, PlotPanel


# =============================================================================
# Main Application Container
# =============================================================================

class App:
    """
    Lightweight wrapper around UI panels.

    This is the ONLY object you should use from backend code.
    """

    def __init__(self):

        #
        # Layout: vertical stack of collapsible panels
        #
        with ui.column().classes("w-full items-stretch"):

            # remove max-width completely
            self.controls = ControlPanel()
            self.logs = LogPanel()
            self.plots = PlotPanel()


# =============================================================================
# Create application instance
# =============================================================================

app = App()


# =============================================================================
# Optional: simple demo backend (remove later)
# =============================================================================

def demo_feed():
    """Simulates incoming data so you can see everything working."""

    import random

    ports = ["COM1", "COM3"]

    statuses = ["INFO", "WARN", "ERROR", "OK"]

    def tick():

        port = random.choice(ports)
        status = random.choice(statuses)
        mac = f"AA:BB:CC:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}"

        # --- Control panel updates ---
        app.controls.set_selected_port(port)
        app.controls.set_mac(mac)

        # --- Log panel ---
        app.logs.add(
            source=port,
            mac=mac,
            status=status,
        )

        # --- Plot panel ---
        app.plots.highlight_bar(random.randint(1, 14))
        app.plots.append(
            time.time(),
            random.random(),
            random.random(),
        )

    ui.timer(1.0, tick)


demo_feed()


# =============================================================================
# Run
# =============================================================================

ui.run(
    title="NiceGUI Dashboard",
    reload=False,
)