from __future__ import annotations
from typing import Callable
from nicegui import ui
from queue import Queue

from .panels import ControlPanel, LogPanel, PlotPanel

class MainDashboard:
    def __init__(self):
        self._queue: Queue[Callable] = Queue()

        with ui.column().classes("w-full items-stretch"):
            self.controls = ControlPanel()
            self.logs = LogPanel()
            self.plots = PlotPanel()

        import backend  # import local to instantiation, otherwise circular dependency
        backend.register_dashboard(self)

        # 2. UI-side dispatcher loop (safe inside NiceGUI)
        ui.timer(0.02, self._process_queue)

    def _handle_backend_stream(self, f: Callable):
        """
        Receives raw data from the backend thread.
        Schedules the data processing safely into the UI main thread queue.
        """
        self._queue.put(f)

    def _process_queue(self):
        """Runs safely on the main thread, pulling jobs out of the queue."""
        while not self._queue.empty():
            f = self._queue.get()
            try:
                f()
            except Exception as e:
                print(f"Error handling command {f}: {e}")
