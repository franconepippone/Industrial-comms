from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional

from nicegui import ui


# =============================================================================
# Control Panel
# =============================================================================

class ControlPanel:
    """Top panel."""

    port_dropdown: Any
    id_field: Any
    mac_field: Any
    slider_gain: Any
    slider_threshold: Any
    checkbox_enable: Any
    checkbox_logging: Any

    def __init__(
        self,
        ports: Optional[List[str]] = None,
        device_id: str = "Unknown",
        mac: str = "--:--:--:--:--:--",
    ) -> None:

        if ports is None:
            ports = ["COM1", "COM3"]

        with ui.expansion("Control Panel", icon="settings", value=True):
            with ui.column().classes("w-full gap-3"):

                self.port_dropdown = ui.select(
                    options=ports,
                    value=ports[0],
                    label="Serial Port",
                ).classes("w-48")

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

    def set_ports(self, ports: List[str]) -> None:
        self.port_dropdown.options = ports
        self.port_dropdown.value = ports[0]
        self.port_dropdown.update()

    def set_selected_port(self, port: str) -> None:
        self.port_dropdown.value = port
        self.port_dropdown.update()

    def get_selected_port(self) -> str:
        return self.port_dropdown.value

    def set_id(self, value: str) -> None:
        self.id_field.value = value
        self.id_field.update()

    def set_mac(self, value: str) -> None:
        self.mac_field.value = value
        self.mac_field.update()


# =============================================================================
# Log Panel
# =============================================================================

class LogPanel:
    """Terminal-style log viewer."""

    rows: List[Dict[str, Any]]
    columns: List[Dict[str, str]]
    table: Any
    filter_source: Any
    filter_status: Any
    auto_toggle: Any
    scroll_container: Any

    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self.next_row_id: int = 0
        self.auto_scroll: bool = True

        self.columns: List[Dict[str, str]] = [
            {"name": "source", "label": "Source", "field": "source"},
            {"name": "timestamp", "label": "Timestamp", "field": "timestamp"},
            {"name": "mac", "label": "MAC", "field": "mac"},
            {"name": "status", "label": "Status", "field": "status"},
        ]

        with ui.expansion("Event Log", icon="list", value=True):

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

            self.table = ui.table(
                columns=self.columns,
                rows=self.rows,
            ).classes("w-full")

            self.table.add_slot(
                "body",
                """
                <q-tr :props="props">
                  <q-td v-for="col in props.cols" :key="col.name" :props="props">
                    {{ col.value }}
                  </q-td>
                </q-tr>
                """,
            )

            self.scroll_container = ui.element("div").classes(
                "w-full"
            ).style(
                "height: 320px;"
                "resize: vertical;"
                "overflow: auto;"
                "min-height: 120px;"
                "max-height: 900px;"
            )

            self.table.move(self.scroll_container)

    def _toggle_autoscroll(self, e: Any) -> None:
        self.auto_scroll = bool(e.value)

    def add(self, source: str, mac: str, status: str) -> int:
        row: Dict[str, Any] = {
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

        if self.auto_scroll:
            self.scroll_container.run_method("scrollTo", {"top": 999999})

        return row["id"]

    def clear(self) -> None:
        self.rows.clear()
        self.table.rows = self.rows
        self.table.update()

    def remove(self, row_id: int) -> None:
        self.rows = [r for r in self.rows if r["id"] != row_id]
        self.table.rows = self.rows
        self.table.update()

    def set_field(self, row_id: int, field: str, value: Any) -> None:
        for r in self.rows:
            if r["id"] == row_id:
                r[field] = value
                break
        self.table.rows = self.rows
        self.table.update()

    def set_status(self, row_id: int, status: str) -> None:
        self.set_field(row_id, "status", status)

    def clear_filters(self) -> None:
        self.filter_source.value = ""
        self.filter_status.value = ""
        self.table.rows = self.rows
        self.table.update()

    def apply_filters(self) -> None:
        filtered: List[Dict[str, Any]] = self.rows

        if self.filter_source.value:
            f: str = self.filter_source.value.lower()
            filtered = [r for r in filtered if f in r["source"].lower()]

        if self.filter_status.value:
            filtered = [
                r for r in filtered if r["status"] == self.filter_status.value
            ]

        self.table.rows = filtered
        self.table.update()


# =============================================================================
# Plot Panel
# =============================================================================

class PlotPanel:
    """Streaming charts panel."""

    window_size: int
    series_names: List[str]

    x: List[Any]
    trace1: List[float]
    trace2: List[float]

    bar_chart: Any
    xy_chart: Any

    def __init__(
        self,
        window_size: int = 60,
        series_names: Tuple[str, str] = ("A", "B"),
    ) -> None:

        self.window_size = window_size
        self.series_names = list(series_names)

        self.x: List[Any] = []
        self.trace1: List[float] = []
        self.trace2: List[float] = []

        self.highlight: int = 0

        with ui.expansion("Plots", icon="bar_chart", value=True):

            self.bar_chart = ui.echart({
                "xAxis": {"type": "category", "data": list(range(1, 15))},
                "yAxis": {"type": "value", "min": 0, "max": 1},
                "series": [{"type": "bar", "data": [0] * 14}],
            }).classes("w-full h-64")

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

    def set_window_size(self, size: int) -> None:
        self.window_size = size
        self._apply_window()

    def set_series_names(self, name1: str, name2: str) -> None:
        self.series_names = [name1, name2]

        self.xy_chart.options["legend"]["data"] = self.series_names
        self.xy_chart.options["series"][0]["name"] = name1
        self.xy_chart.options["series"][1]["name"] = name2
        self.xy_chart.update()

    def highlight_bar(self, index: int) -> None:
        data: List[Dict[str, Any]] = [
            {
                "value": 1 if i == index - 1 else 0.3,
                "itemStyle": {
                    "color": "#1976d2" if i == index - 1 else "#cccccc"
                },
            }
            for i in range(14)
        ]

        self.bar_chart.options["series"][0]["data"] = data
        self.bar_chart.update()

    def append(self, t: Any, v1: float, v2: float) -> None:
        self.x.append(t)
        self.trace1.append(v1)
        self.trace2.append(v2)
        self._apply_window()

    def set_data(self, data: List[Tuple[Any, float, float]]) -> None:
        self.x = [d[0] for d in data]
        self.trace1 = [d[1] for d in data]
        self.trace2 = [d[2] for d in data]
        self._apply_window()

    def clear(self) -> None:
        self.x.clear()
        self.trace1.clear()
        self.trace2.clear()
        self._apply_window()

    def _apply_window(self) -> None:
        if len(self.x) > self.window_size:
            self.x = self.x[-self.window_size:]
            self.trace1 = self.trace1[-self.window_size:]
            self.trace2 = self.trace2[-self.window_size:]

        self.xy_chart.options["xAxis"]["data"] = self.x
        self.xy_chart.options["series"][0]["data"] = self.trace1
        self.xy_chart.options["series"][1]["data"] = self.trace2
        self.xy_chart.update()