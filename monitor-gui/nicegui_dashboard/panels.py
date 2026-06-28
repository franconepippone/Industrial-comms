"""
panels.py

Contains the three GUI panels:

    - ControlPanel
    - LogPanel
    - PlotPanel

These classes contain ONLY UI logic.
Application logic should call their public methods.
"""

from datetime import datetime

from nicegui import ui


# =============================================================================
# Control Panel
# =============================================================================

class ControlPanel:
    """Top panel.

    Exposed methods:

        set_ports(...)
        set_selected_port(...)
        get_selected_port()

        set_id(...)
        set_mac(...)
    """

    def __init__(
        self,
        ports=None,
        device_id="Unknown",
        mac="--:--:--:--:--:--",
    ):

        if ports is None:
            ports = ["COM1", "COM3"]

        with ui.expansion("Control Panel", icon="settings", value=True):

            with ui.column().classes("w-full gap-3"):

                # ---------------------------------------------------------
                # Port selection
                # ---------------------------------------------------------

                self.port_dropdown = ui.select(
                    options=ports,
                    value=ports[0],
                    label="Serial Port",
                ).classes("w-48")

                # ---------------------------------------------------------
                # Device info
                # ---------------------------------------------------------

                self.id_field = ui.input(
                    label="Device ID",
                    value=device_id,
                ).props("readonly")

                self.mac_field = ui.input(
                    label="MAC Address",
                    value=mac,
                ).props("readonly")

                ui.separator()

                ui.label("Example controls")

                self.slider_gain = ui.slider(
                    min=0,
                    max=100,
                    value=50,
                )

                self.slider_threshold = ui.slider(
                    min=0,
                    max=100,
                    value=20,
                )

                self.checkbox_enable = ui.checkbox(
                    "Enable feature",
                    value=True,
                )

                self.checkbox_logging = ui.checkbox(
                    "Verbose logging",
                    value=False,
                )

    # ------------------------------------------------------------------

    def set_ports(self, ports):

        self.port_dropdown.options = ports
        self.port_dropdown.value = ports[0]
        self.port_dropdown.update()

    # ------------------------------------------------------------------

    def set_selected_port(self, port):

        self.port_dropdown.value = port
        self.port_dropdown.update()

    # ------------------------------------------------------------------

    def get_selected_port(self):

        return self.port_dropdown.value

    # ------------------------------------------------------------------

    def set_id(self, value):

        self.id_field.value = value
        self.id_field.update()

    # ------------------------------------------------------------------

    def set_mac(self, value):

        self.mac_field.value = value
        self.mac_field.update()


# =============================================================================
# Log Panel
# =============================================================================
from datetime import datetime
from nicegui import ui


from datetime import datetime
from nicegui import ui


class LogPanel:
    """Terminal-style log viewer with resizable scroll container."""

    def __init__(self):
        self.rows = []
        self.next_row_id = 0
        self.auto_scroll = True

        self.columns = [
            {"name": "source", "label": "Source", "field": "source"},
            {"name": "timestamp", "label": "Timestamp", "field": "timestamp"},
            {"name": "mac", "label": "MAC", "field": "mac"},
            {"name": "status", "label": "Status", "field": "status"},
        ]

        with ui.expansion("Event Log", icon="list", value=True):

            # -----------------------------
            # CONTROLS (always visible)
            # -----------------------------
            with ui.row().classes("items-center w-full"):
                self.filter_source = ui.input(label="Source").classes("w-40")
                self.filter_status = ui.select(
                    ["", "INFO", "WARN", "ERROR", "OK"],
                    value="",
                    label="Status",
                ).classes("w-32")

                ui.button("Apply", on_click=self.apply_filters)
                ui.button("Clear", on_click=self.clear_filters)

                self.auto_toggle = ui.checkbox(
                    "Auto-scroll",
                    value=True,
                    on_change=self._toggle_autoscroll,
                )

            # -----------------------------
            # HEADER (always visible, from table)
            # -----------------------------
            self.table = ui.table(
                columns=self.columns,
                rows=self.rows,
            ).classes("w-full")

            self.table.add_slot(
                "body",
                r"""
<q-tr :props="props"
      :style="{
        backgroundColor:
          props.row.status === 'ERROR' ? '#ffd6d6' :
          props.row.status === 'WARN'  ? '#fff3cd' :
          props.row.status === 'INFO'  ? '#e7f1ff' :
          props.row.status === 'OK'    ? '#d4edda' : ''
      }">
  <q-td v-for="col in props.cols" :key="col.name" :props="props">
    {{ col.value }}
  </q-td>
</q-tr>
"""
            )

            # -----------------------------
            # RESIZABLE SCROLL CONTAINER (BODY ONLY)
            # -----------------------------
            self.scroll_container = ui.element("div").classes(
                "w-full"
            ).style(
                "height: 320px;"
                "resize: vertical;"
                "overflow: auto;"
                "min-height: 120px;"
                "max-height: 900px;"
                "border: none;"
            )

            # move table into scroll container (important)
            self.table.move(self.scroll_container)

    # -------------------------------------------------------------

    def _toggle_autoscroll(self, e):
        self.auto_scroll = bool(e.value)

    # -------------------------------------------------------------

    def add(self, source, mac, status):
        row = {
            "id": self.next_row_id,
            "source": source,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "mac": mac,
            "status": status,
        }

        self.next_row_id += 1
        self.rows.append(row)

        self.table.rows = self.rows
        self.table.update()

        # terminal-style autoscroll (only body scroll container)
        if self.auto_scroll:
            self.scroll_container.run_method("scrollTo", {"top": 999999})

        return row["id"]

    # -------------------------------------------------------------

    def clear(self):
        self.rows.clear()
        self.table.rows = self.rows
        self.table.update()

    # -------------------------------------------------------------

    def remove(self, row_id):
        self.rows = [r for r in self.rows if r["id"] != row_id]
        self.table.rows = self.rows
        self.table.update()

    # -------------------------------------------------------------

    def set_field(self, row_id, field, value):
        for r in self.rows:
            if r["id"] == row_id:
                r[field] = value
                break
        self.table.rows = self.rows
        self.table.update()

    # -------------------------------------------------------------

    def set_status(self, row_id, status):
        self.set_field(row_id, "status", status)

    # -------------------------------------------------------------

    def clear_filters(self):
        self.filter_source.value = ""
        self.filter_status.value = ""
        self.table.rows = self.rows
        self.table.update()

    # -------------------------------------------------------------

    def apply_filters(self):
        filtered = self.rows

        if self.filter_source.value:
            f = self.filter_source.value.lower()
            filtered = [r for r in filtered if f in r["source"].lower()]

        if self.filter_status.value:
            filtered = [r for r in filtered if r["status"] == self.filter_status.value]

        self.table.rows = filtered
        self.table.update()


# Plot Panel
# =============================================================================
from nicegui import ui


class PlotPanel:
    """Bottom panel with time-based streaming charts."""

    def __init__(self, window_size=60, series_names=("A", "B")):
        self.window_size = window_size
        self.series_names = list(series_names)

        # time-based storage
        self.x = []
        self.trace1 = []
        self.trace2 = []

        self.highlight = 0

        with ui.expansion("Plots", icon="bar_chart", value=True):

            # -----------------------------
            # Bar chart
            # -----------------------------
            self.bar_chart = ui.echart({
                "xAxis": {"type": "category", "data": list(range(1, 15))},
                "yAxis": {"type": "value", "name": "Reputation", "min": 0, "max": 1},
                "series": [{"type": "bar", "data": [0] * 14}],
            }).classes("w-full h-64")

            # -----------------------------
            # XY chart (time axis)
            # -----------------------------
            self.xy_chart = ui.echart({
                "legend": {"data": self.series_names},
                "xAxis": {"type": "category", "data": []},
                "yAxis": {"type": "value", "min": 0, "max": 1},
                "series": [
                    {"name": self.series_names[0], "type": "line", "data": []},
                    {"name": self.series_names[1], "type": "line", "data": []},
                ],
            }).classes("w-full h-72")

        self.highlight_bar(1)

    # -------------------------------------------------------------

    def set_window_size(self, size: int):
        self.window_size = size
        self._apply_window()

    # -------------------------------------------------------------

    def set_series_names(self, name1: str, name2: str):
        self.series_names = [name1, name2]

        self.xy_chart.options["legend"]["data"] = self.series_names
        self.xy_chart.options["series"][0]["name"] = name1
        self.xy_chart.options["series"][1]["name"] = name2
        self.xy_chart.update()

    # -------------------------------------------------------------

    def highlight_bar(self, index: int):
        data = [
            {
                "value": 1 if i == index - 1 else 0.3,
                "itemStyle": {"color": "#1976d2" if i == index - 1 else "#cccccc"},
            }
            for i in range(14)
        ]

        self.bar_chart.options["series"][0]["data"] = data
        self.bar_chart.update()

    # -------------------------------------------------------------

    def append(self, t, v1, v2):
        """t = timestamp (external), v1/v2 = values"""

        self.x.append(t)
        self.trace1.append(v1)
        self.trace2.append(v2)

        self._apply_window()

    # -------------------------------------------------------------

    def set_data(self, data):
        """
        Batch load:
        data = [(t, v1, v2), ...]
        """

        self.x = [d[0] for d in data]
        self.trace1 = [d[1] for d in data]
        self.trace2 = [d[2] for d in data]

        self._apply_window()

    # -------------------------------------------------------------

    def clear(self):
        self.x.clear()
        self.trace1.clear()
        self.trace2.clear()
        self._apply_window()

    # -------------------------------------------------------------

    def _apply_window(self):
        """Keep only last N seconds (based on timestamps)."""

        if len(self.x) > self.window_size:
            self.x = self.x[-self.window_size:]
            self.trace1 = self.trace1[-self.window_size:]
            self.trace2 = self.trace2[-self.window_size:]

        self.xy_chart.options["xAxis"]["data"] = self.x
        self.xy_chart.options["series"][0]["data"] = self.trace1
        self.xy_chart.options["series"][1]["data"] = self.trace2
        self.xy_chart.update()