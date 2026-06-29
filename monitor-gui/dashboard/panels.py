from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional

from nicegui import ui


# =============================================================================
# Control Panel
# =============================================================================

from typing import Any, Callable, List, Optional
from nicegui import ui

class ControlPanel:
    """Top control and configuration panel."""

    port_dropdown: Any
    connect_button: Any
    status_field: Any
    id_field: Any
    mac_field: Any
    slider_gain: Any
    slider_threshold: Any
    checkbox_enable: Any
    checkbox_logging: Any
    
    # Callback placeholder
    connect_callback: Optional[Callable[[str], None]]

    def __init__(
        self,
        ports: Optional[List[str]] = None,
        device_id: str = "Unknown",
        mac: str = "--:--:--:--:--:--",
    ) -> None:

        if ports is None:
            ports = ["COM1", "COM3"]
            
        self.connect_callback = None

        with ui.expansion("Control Panel", icon="settings", value=True):
            with ui.column().classes("w-full gap-3"):

                # Row grouping for Serial configuration elements
                with ui.row().classes("items-end gap-4 w-full"):
                    self.port_dropdown = ui.select(
                        options=ports,
                        value=ports[0],
                        label="Serial Port",
                    ).classes("w-48")

                    self.connect_button = ui.button(
                        "Connect", 
                        on_click=self._handle_connect
                    ).props("elevated")

                    # CHANGED: Increased size to 'w-80' and added a padding utility for clean colored backgrounds
                    self.status_field = ui.input(
                        label="Connection Status",
                        value="Disconnected",
                    ).props("readonly").classes("w-80 px-2 rounded transition-all")

                self.id_field = ui.input(
                    label="Device ID",
                    value=device_id,
                ).props("readonly").classes("w-48")

                self.mac_field = ui.input(
                    label="MAC Address",
                    value=mac,
                ).props("readonly").classes("w-48")

                ui.separator()
                ui.label("Example controls").classes("text-xs font-bold text-gray-400 uppercase")

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

    # --- Runtime Binding Hook Mechanics ---

    def set_connect_callback(self, func: Callable[[str], None]) -> None:
        """Binds an external connection engine function."""
        self.connect_callback = func

    def _handle_connect(self) -> None:
        """Internal router triggering the bound execution engine."""
        if self.connect_callback:
            selected_port = self.get_selected_port()
            self.connect_callback(selected_port)

    # CHANGED: Added optional color string parameter (supports Hex, RGB, or LogColor values)
    def set_connection_status(self, text: str, color: Optional[str] = None) -> None:
        """Updates the inline outcome text box display text and background color."""
        self.status_field.value = text
        
        if color:
            # Treat .style like a dictionary to directly modify the property safely
            self.status_field.style['background-color'] = color
        else:
            # Clear it or reset it back to transparent
            self.status_field.style['background-color'] = 'transparent'
            
        self.status_field.update()

    # --- Standard Field Getters and Setters ---

    def set_ports(self, ports: List[str]) -> None:
        self.port_dropdown.options = ports
        self.port_dropdown.value = ports[0] if ports else ""
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

from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from nicegui import ui



# Soft, clean pastel tones that look great on light-themed tables
class LogColor(str, Enum):
    SUCCESS = "#dcfce7"
    WARNING = "#fef3c7"
    ERROR = "#fee2e2"
    INFO = "#dbeafe"

# 1. Extensible Enum for Source Types
class SourceType(str, Enum):
    TX = "TX"
    RX = "RX"
    # To add more source types later, just add them here:
    # EXAMPLE = "EXAMPLE"

class LogPanel:
    """Terminal-style log viewer with integrated toolbar controls."""

    rows: List[Dict[str, Any]]
    columns: List[Dict[str, str]]
    table: Any
    filter_source: Any
    filter_status: Any
    auto_toggle: Any
    scroll_container: Any

    # Toolbar Sender elements
    send_button: ui.button
    periodic_checkbox: ui.checkbox
    interval_slider: ui.slider
    timer: ui.timer
    send_callback: Optional[Callable[[], None]]

    def __init__(self) -> None:
        self.rows = []
        self.next_row_id = 0
        self.auto_scroll = True
        self.send_callback = None

        self.columns = [
            {"name": "source", "label": "Source", "field": "source", "align": "center", "style": "width: 80px; max-width: 80px;"},
            {"name": "timestamp", "label": "Time (ms)", "field": "timestamp", "align": "center", "style": "width: 110px;"},
            {"name": "mac", "label": "MAC", "field": "mac", "align": "center", "style": "width: 180px;"},
            {"name": "size", "label": "Size", "field": "size", "align": "center", "style": "width: 70px;"},
            {"name": "nonce", "label": "Nonce", "field": "nonce", "align": "center", "style": "width: 120px;"},
            {"name": "packid", "label": "Pack ID", "field": "packid", "align": "center", "style": "width: 110px;"},
            {"name": "status", "label": "Status", "field": "status", "align": "center", "style": "width: 90px;"},
        ]

        # Initialize background timer for periodic triggering
        self.timer = ui.timer(1.0, self._handle_send, active=False)

        with ui.expansion("Event Log", icon="list", value=True):

            # --- Unified Control Toolbar ---
            with ui.row().classes("items-center w-full gap-4 mb-4 p-2 bg-slate-50 rounded-md"):
                
                # Group 1: Filters
                self.filter_source = ui.select(
                    options=[""] + [source.value for source in SourceType],
                    value="",
                    label="Source",
                ).classes("w-36")

                self.filter_status = ui.select(
                    ["", "INFO", "WARN", "ERROR", "OK"],
                    value="",
                    label="Status",
                ).classes("w-28")

                ui.button("Apply", on_click=self.apply_filters).props("flat color=primary")
                ui.button("Clear", on_click=self.clear_filters).props("flat color=grey")

                # Visual Separator between Filters and Sender Action Group
                ui.element("div").classes("w-px h-8 bg-gray-300 mx-2")

                # Group 2: Action Sender Panel
                self.send_button = ui.button("Send", on_click=self._handle_send)

                self.periodic_checkbox = ui.checkbox(
                    "Periodic", 
                    value=False, 
                    on_change=self._toggle_periodic
                )

                # Dynamic Interval Slider (Visible only when 'Periodic' is checked)
                with ui.row().classes("items-center gap-2").bind_visibility_from(self.periodic_checkbox, "value"):
                    ui.label("Interval:")
                    self.interval_slider = ui.slider(
                        min=0.1, 
                        max=10.0, 
                        value=1.0, 
                        step=0.1, 
                        on_change=self._update_timer_interval
                    ).classes("w-28")
                    ui.label().bind_text_from(self.interval_slider, "value", backward=lambda v: f"{v:.1f}s")

                # Disable 'Send' button if auto-periodic processing loop is executing
                self.send_button.bind_enabled_from(self.periodic_checkbox, "value", backward=lambda v: not v)

                # Push the Auto-scroll checkbox to the far right side
                ui.element("div").classes("col-grow")
                self.auto_toggle = ui.checkbox(
                    "Auto-scroll",
                    value=True,
                    on_change=self._toggle_autoscroll,
                )

            # --- Table Setup ---
            self.table = ui.table(
                columns=self.columns,
                rows=self.rows,
            ).classes("w-full")

            self.table.add_slot(
                "body",
                """
                <q-tr :props="props" :style="props.row.color ? 'background-color: ' + props.row.color : ''">
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

    # --- Control Toolbar Logic Engines ---

    def bind_send_callback(self, function: Callable[[], None]) -> None:
        """Binds a parameterless runtime action callback."""
        self.send_callback = function

    def _handle_send(self) -> None:
        """Triggers the bound execution loop handler."""
        if self.send_callback:
            self.send_callback()
        else:
            print('NO SEND CALLBACK', id(self))

    def _toggle_periodic(self, e: Any) -> None:
        if e.value:
            self.timer.interval = self.interval_slider.value
            self.timer.activate()
        else:
            self.timer.deactivate()

    def _update_timer_interval(self, e: Any) -> None:
        self.timer.interval = e.value

    # --- Standard Panel Log Handlers ---

    def _toggle_autoscroll(self, e: Any) -> None:
        self.auto_scroll = bool(e.value)

    def add(
        self,
        source: str,
        mac: str,
        status: str,
        timestamp: str,
        size: str = "",
        nonce: str = "",
        packid: str = "",
        color: Optional[LogColor | str] = None,
    ) -> int:
        resolved_color = None
        if color:
            resolved_color = color.value if isinstance(color, LogColor) else color

        row: Dict[str, Any] = {
            "id": self.next_row_id,
            "source": source,
            "timestamp": timestamp,
            "mac": mac,
            "size": size,
            "nonce": nonce,
            "packid": packid,
            "status": status,
            "color": resolved_color,
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

    def update_status_and_color(
        self, row_id: int, status: str, color: Optional[LogColor | str]
    ) -> None:
        resolved_color = None
        if color:
            resolved_color = color.value if isinstance(color, LogColor) else color

        for r in self.rows:
            if r["id"] == row_id:
                r["status"] = status
                r["color"] = resolved_color
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