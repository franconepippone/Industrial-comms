from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional, List, Callable

from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments


# =============================================================================
# Control Panel
# =============================================================================

class ControlPanel:
    """Top control and configuration panel."""

    port_dropdown: Any
    connect_button: Any
    status_field: Any
    id_field: Any
    mac_field: Any
    
    # Control Elements
    checkbox_simulate_losses: Any
    slider_ack_loss: Any          # RENAMED/NEW
    slider_pkt_loss: Any          # RENAMED/NEW
    
    # Callback placeholders
    connect_callback: Optional[Callable[[str], None]]
    ack_loss_callback: Optional[Callable[[float], None]]  # NEW
    pkt_loss_callback: Optional[Callable[[float], None]]  # NEW

    def __init__(
        self,
        ports: Optional[List[str]] = None,
        device_id: str = "Unknown",
        mac: str = "--:--:--:--:--:--",
    ) -> None:

        if ports is None:
            ports = ["COM1", "COM3"]
            
        self.connect_callback = None
        self.ack_loss_callback = None
        self.pkt_loss_callback = None

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
                ui.label("Controls").classes("text-xs font-bold text-gray-400 uppercase")

                self.checkbox_echo_serial = ui.checkbox(
                    "Echo serial output",
                    value=False,
                    on_change=lambda x: None
                )

                self.checkbox_disable_auto_hop = ui.checkbox(
                    "Disable auto hopping", 
                    value=False, 
                    on_change=lambda x: None
                )

                # Simulate losses checkbox
                self.checkbox_simulate_losses = ui.checkbox(
                    "Simulate losses",
                    value=False,
                    on_change=self._handle_checkbox_change
                )

                # NEW: ACK Loss Probability Slider Row
                with ui.row().classes("items-center gap-4 w-full").bind_visibility_from(self.checkbox_simulate_losses, 'value'):
                    ui.label("ACK Loss Probability:").classes("text-sm text-gray-600 w-44")
                    self.slider_ack_loss = ui.slider(
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        on_change=self._handle_ack_change
                    ).classes("w-64")
                    
                    ui.label().bind_text_from(
                        self.slider_ack_loss, 
                        'value', 
                        backward=lambda v: f"{int(v)}%"
                    ).classes("text-sm font-bold text-gray-700 w-12")

                # NEW: Packet Loss Probability Slider Row
                with ui.row().classes("items-center gap-4 w-full").bind_visibility_from(self.checkbox_simulate_losses, 'value'):
                    ui.label("Packet Loss Probability:").classes("text-sm text-gray-600 w-44")
                    self.slider_pkt_loss = ui.slider(
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        on_change=self._handle_pkt_change
                    ).classes("w-64")
                    
                    ui.label().bind_text_from(
                        self.slider_pkt_loss, 
                        'value', 
                        backward=lambda v: f"{int(v)}%"
                    ).classes("text-sm font-bold text-gray-700 w-12")

    # --- Runtime Binding Hook Mechanics ---

    def set_autohop_callbacks(self, enable: Callable[[], None], disable: Callable[[], None]) -> None:
        def wrapper():
            if bool(self.checkbox_disable_auto_hop.value):
                enable()
            else:
                disable()        
        self.checkbox_disable_auto_hop.on_value_change(wrapper)

    def set_connect_callback(self, func: Callable[[str], None]) -> None:
        """Binds an external connection engine function."""
        self.connect_callback = func
    
    def set_echo_toggle_callback(self, func: Callable[[bool], None]) -> None:
        self.checkbox_echo_serial.on_value_change(lambda v: func(bool(v.value)))

    def bind_callbacks(self, ack_callback: Callable[[float], None], pkt_callback: Callable[[float], None]) -> None:
        """NEW: Single method to bind both loss simulation engine callbacks at once."""
        self.ack_loss_callback = ack_callback
        self.pkt_loss_callback = pkt_callback

    def _handle_connect(self) -> None:
        """Internal router triggering the bound execution engine."""
        if self.connect_callback:
            selected_port = self.get_selected_port()
            self.connect_callback(selected_port)

    def _handle_ack_change(self) -> None:
        """Evaluates and routes the ACK loss state to the runtime engine."""
        if self.ack_loss_callback:
            value = self.slider_ack_loss.value if self.checkbox_simulate_losses.value else 0.0
            self.ack_loss_callback(value)

    def _handle_pkt_change(self) -> None:
        """Evaluates and routes the Packet loss state to the runtime engine."""
        if self.pkt_loss_callback:
            value = self.slider_pkt_loss.value if self.checkbox_simulate_losses.value else 0.0
            self.pkt_loss_callback(value)

    def _handle_checkbox_change(self) -> None:
        """Triggers updates across both endpoints when loss simulation is toggled."""
        self._handle_ack_change()
        self._handle_pkt_change()

    def set_connection_status(self, text: str, color: Optional[str] = None) -> None:
        """Updates the inline outcome text box display text and background color."""
        self.status_field.value = text
        
        if color:
            self.status_field.style['background-color'] = color
        else:
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


# Soft, clean pastel tones that look great on light-themed tables
class LogColor(str, Enum):
    WHITE = "#ffffff"
    SUCCESS = "#dcfce7"
    WARNING = "#fef3c7"
    ERROR = "#ffc6c6"
    INFO = "#dbeafe"
    LOG_INFO = "#f6e0ff"
    LOG_ERROR = "#ffa3e3"

# 1. Extensible Enum for Source Types
class SourceType(str, Enum):
    TX = "TX"
    RX = "RX"
    HOP = "HOP"
    # To add more source types later, just add them here:
    # EXAMPLE = "EXAMPLE"

class LogPanel:
    """Terminal-style log viewer with integrated toolbar controls."""

    rows: List[Dict[str, Any]]
    columns: List[Dict[str, str]]
    header_table: Any
    table: Any
    filter_source: Any
    auto_toggle: Any
    scroll_container: Any

    # Toolbar Sender elements
    send_button: ui.button
    periodic_checkbox: ui.checkbox
    interval_slider: ui.slider
    timer: ui.timer
    send_callback: Optional[Callable[[], None]]
    hop_callback: Optional[Callable[[], None]]

    max_rows = 100

    def __init__(self) -> None:
        self.rows = []
        self.next_row_id = 0
        self.auto_scroll = True
        self.send_callback = None
        self.hop_callback = None

        # 1. NEW: Force a rigid layout on both tables and prevent text overflow
        ui.add_css("""
            .sync-table table {
                table-layout: fixed !important;
                width: 100% !important;
            }
            .sync-table th, .sync-table td {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        """)

        # 2. NEW: Explicitly define both 'headerStyle' and 'style' so the empty table
        # and the populated table receive the exact same layout instructions.
        self.columns = [
            {"name": "source", "label": "Source", "field": "source", "align": "center", "headerStyle": "width: 80px;", "style": "width: 80px;"},
            {"name": "timestamp", "label": "Time (ms)", "field": "timestamp", "align": "center", "headerStyle": "width: 110px;", "style": "width: 110px;"},
            {"name": "mac", "label": "MAC", "field": "mac", "align": "center", "headerStyle": "width: 180px;", "style": "width: 180px;"},
            {"name": "size", "label": "Size", "field": "size", "align": "center", "headerStyle": "width: 70px;", "style": "width: 70px;"},
            {"name": "nonce", "label": "Nonce", "field": "nonce", "align": "center", "headerStyle": "width: 120px;", "style": "width: 120px;"},
            {"name": "packid", "label": "Pack ID", "field": "packid", "align": "center", "headerStyle": "width: 110px;", "style": "width: 110px;"},
            {"name": "status", "label": "Status", "field": "status", "align": "center", "headerStyle": "width: 90px;", "style": "width: 90px;"},
        ]

        # Initialize background timer for periodic triggering
        self.timer = ui.timer(1.0, self._handle_send, active=False)

        with ui.expansion("Event Log", icon="list", value=True):

            # --- Unified Control Toolbar ---
            with ui.row().classes("items-center w-full gap-4 mb-4 p-2 bg-slate-50 rounded-md"):
                
                # Group 1: Filters
                self.filter_source = ui.select(
                    options=[""] + [source.value for source in SourceType], # Adjust as needed
                    value="",
                    label="Source",
                    on_change=self.apply_filters
                ).classes("w-36")

                #self.filter_status = ui.select(
                #    ["", "SUCCESS", "WARNING", "ERROR"],
                #    value="",
                #    label="Outcome",
                #    on_change=self.apply_filters
                #).classes("w-28")

                self.selected = {
                    'OTHER': True,
                    'SUCCESS': True,
                    'WARNING': True,
                    'ERROR': True,
                }

                with ui.button('Status Filter'):
                    with ui.menu():
                        with ui.column().classes('gap-1 p-2'):
                            for name in self.selected:
                                ui.checkbox(name, on_change=self.apply_filters).bind_value(self.selected, name)

                #ui.button("Apply", on_click=self.apply_filters).props("flat color=primary")
                ui.button("Clear Filters", on_click=self.clear_filters).props("flat color=grey")

                # Visual Separator between Filters and Sender Action Group
                ui.element("div").classes("w-px h-8 bg-gray-300 mx-2")

                 # Group 3: Right-aligned Utilities
                #ui.element("div").classes("col-grow")
                
                ui.button("Clear Log", on_click=self.clear).props("flat color=negative").classes("mr-2")
                
                self.auto_toggle = ui.checkbox(
                    "Auto-scroll",
                    value=True,
                    on_change=self._toggle_autoscroll,
                )

                # Group 2: Action Sender Panel
                ui.element("div").classes("w-px h-8 bg-gray-300 mx-2")

                self.hop_button = ui.button("Hop", on_click=self._handle_hop)
                
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
                        max=5.0, 
                        value=1.0, 
                        step=0.1, 
                        on_change=self._update_timer_interval
                    ).classes("w-28")
                    ui.label().bind_text_from(self.interval_slider, "value", backward=lambda v: f"{v:.1f}s")

                self.send_button.bind_enabled_from(self.periodic_checkbox, "value", backward=lambda v: not v)

               

            # --- Dual Table Setup ---
                        # The wrapper controls the outer boundary
            with ui.column().classes("w-full gap-0 border border-gray-300 rounded overflow-hidden"):
                
                # 3. Header Table: Forces the same width calculation as the body
                with ui.element("div").classes("w-full bg-slate-100 overflow-x-hidden").style("overflow-y: scroll; border-bottom: 1px solid #e5e7eb;"):
                    self.header_table = ui.table(
                        columns=self.columns,
                        rows=[],
                    ).classes("w-full").props("flat hide-bottom").style("table-layout: fixed")
                    
                    self.header_table.add_slot("no-data", "")
                
                # 4. The Resizable Scroll Container
                self.scroll_container = ui.element("div").classes(
                    "w-full bg-white overflow-x-hidden"
                ).style(
                    "height: 320px;"
                    "resize: vertical;"
                    "overflow-y: scroll;"
                    "min-height: 120px;"
                    "max-height: 900px;"
                )
                
                # 5. The Body Table
                with self.scroll_container:
                    self.table = ui.table(
                        columns=self.columns,
                        rows=self.rows,
                    ).classes("w-full").props("flat hide-header").style("table-layout: fixed")

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

    # --- Control Toolbar Logic Engines ---

    def bind_send_callback(self, function: Callable[[], None]) -> None:
        """Binds a parameterless runtime action callback."""
        self.send_callback = function
    
    def bind_hop_callback(self, function: Callable[[], None]) -> None:
        """Binds a parameterless runtime action callback."""
        self.hop_callback = function

    def _handle_send(self) -> None:
        """Triggers the bound execution loop handler."""
        if self.send_callback:
            self.send_callback()
        else:
            print('NO SEND CALLBACK', id(self))
    
    def _handle_hop(self) -> None:
        """Triggers the bound execution loop handler."""
        if self.hop_callback:
            self.hop_callback()
        else:
            print('NO HOP CALLBACK', id(self))

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
        color: LogColor = LogColor.WHITE,
    ) -> int:

        row: Dict[str, Any] = {
            "id": self.next_row_id,
            "source": source,
            "timestamp": timestamp,
            "mac": mac,
            "size": size,
            "nonce": nonce,
            "packid": packid,
            "status": status,
            "color": color,
        }

        self.next_row_id += 1
        self.rows.append(row)

        if len(self.rows) > self.max_rows:
            self.rows.pop(0)
        
        if self.auto_scroll:
            self.scroll_container.run_method("scrollTo", {"top": 999999})
        
        self.table.rows = self.rows
        self.apply_filters()

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
        self, row_id: int, status: str, color: LogColor
    ) -> None:

        for r in self.rows:
            if r["id"] == row_id:
                r["status"] = status
                r["color"] = color
                break
        self.table.rows = self.rows
        self.table.update()

    def set_status(self, row_id: int, status: str) -> None:
        self.set_field(row_id, "status", status)

    def clear_filters(self) -> None:
        self.filter_source.value = ""
        self.table.rows = self.rows
        self.table.update()

    def apply_filters(self) -> None:
        filtered: List[Dict[str, Any]] = self.rows

        if self.filter_source.value:
            f: str = self.filter_source.value.lower()
            filtered = [r for r in filtered if f in r["source"].lower()]

        if True:
            color_map = {
                "SUCCESS": LogColor.SUCCESS,
                "WARNING": LogColor.WARNING,
                "ERROR": LogColor.ERROR,
            }

            show_other = self.selected.get("OTHER", False)

            enabled_colors = {
                color_map[name]
                for name, checked in self.selected.items()
                if checked and name in color_map
            }

            filtered = [
                r for r in filtered
                if (
                    r["color"] in enabled_colors
                    or (
                        show_other
                        and r["color"] not in color_map.values()
                    )
                )
            ]
        self.table.rows = filtered
        self.table.update()
        
# =============================================================================
# Plot Panel
# =============================================================================

from typing import Any, Dict, List, Tuple
from collections import deque
import time


class PlotPanel:
    """Streaming charts panel."""

    def __init__(
        self,
        window_size: int = 10,
        refresh_rate: float = 2,
        series_names: Tuple[str, str] = ("Reputation", "Degradation Estimate"),
    ) -> None:

        self.window_size = float(window_size)
        self.series_names = list(series_names)

        self.refresh_period = 1.0 / refresh_rate
        self._last_update = 0.0

        self.x = deque()
        self.trace1 = deque()
        self.trace2 = deque()

        # BAR STATE
        self.bar_values = [0.0] * 14
        self.highlight = 1

        self._bar_dirty = False
        self._line_dirty = False

        with ui.expansion("Plots", icon="bar_chart", value=True):

            with ui.row().classes("items-center gap-2"):
                ui.label("Window (s)").classes("text-xs")

                ui.slider(
                    min=1,
                    max=10,
                    step=1,
                    value=window_size,
                    on_change=lambda e: self.set_window_size(int(e.value)),
                ).props("label label-always dense").classes("w-32")

            self.bar_chart = ui.echart({
                "xAxis": {"type": "category", "data": list(range(1, 15))},
                "yAxis": {"type": "value", "min": 0, "max": 1},
                "series": [{
                    "type": "bar",
                    "data": [0] * 14,
                }],
            }).classes("w-full h-64")

            self.xy_chart = ui.echart({
                "legend": {"data": self.series_names},
                "xAxis": {"type": "value"},
                "yAxis": {"type": "value", "min": 0, "max": 1},
                "series": [
                    {
                        "name": self.series_names[0],
                        "type": "line",
                        "data": [],
                        "showSymbol": False,
                    },
                    {
                        "name": self.series_names[1],
                        "type": "line",
                        "data": [],
                        "showSymbol": False,
                    },
                ],
            }).classes("w-full h-72")

        self._render_bar()

        ui.timer(1 / refresh_rate, self._flush_updates)

    # -----------------------
    # WINDOW
    # -----------------------
    def set_window_size(self, size: int) -> None:
        self.window_size = float(size)
        self._line_dirty = True

    # -----------------------
    # SERIES
    # -----------------------
    def set_series_names(self, name1: str, name2: str) -> None:
        self.series_names = [name1, name2]
        self.xy_chart.options["legend"]["data"] = self.series_names
        self.xy_chart.options["series"][0]["name"] = name1
        self.xy_chart.options["series"][1]["name"] = name2
        self.xy_chart.update()

    # -----------------------
    # LINE DATA
    # -----------------------
    def append(self, t: float, v1: float, v2: float) -> None:
        self.x.append(t)
        self.trace1.append(v1)
        self.trace2.append(v2)

        cutoff = t - self.window_size
        MARGIN = 1 # additional margin for better displaying
        while self.x and self.x[0] < (cutoff - MARGIN):
            self.x.popleft()
            self.trace1.popleft()
            self.trace2.popleft()

        self._line_dirty = True

    def set_data(self, data: List[Tuple[float, float, float]]) -> None:
        self.x = deque(d[0] for d in data)
        self.trace1 = deque(d[1] for d in data)
        self.trace2 = deque(d[2] for d in data)
        self._line_dirty = True

    def clear_plot(self) -> None:
        self.x.clear()
        self.trace1.clear()
        self.trace2.clear()
        self._line_dirty = True

    # -----------------------
    # BAR CHART
    # -----------------------
    def _render_bar(self) -> None:
        self.bar_chart.options["series"][0]["data"] = [
            {
                "value": self.bar_values[i],
                "itemStyle": {
                    "color": "#1976d2" if i == self.highlight - 1 else "#cccccc"
                },
            }
            for i in range(14)
        ]
        self.bar_chart.update()

    def highlight_bar(self, index: int) -> None:
        self.highlight = index
        self._render_bar()

    def set_bar(self, index: int, value: float) -> None:
        if not 1 <= index <= 14:
            raise ValueError("Attempted set bar outside range")

        self.bar_values[index - 1] = value
        self.highlight = index
        self._render_bar()

    def clear_bars(self) -> None:
        self.bar_values = [0.5] * 14
        self.highlight = 1
        self._render_bar()

    # -----------------------
    # GLOBAL CLEAR
    # -----------------------
    def clear(self) -> None:
        self.clear_plot()
        self.clear_bars()

    # -----------------------
    # UPDATE LOOP
    # -----------------------
    def _flush_updates(self) -> None:
        now = time.perf_counter()
        if now - self._last_update < self.refresh_period:
            return

        self._last_update = now

        if self._line_dirty:
            if self.x:
                newest = self.x[-1]
                self.xy_chart.options["xAxis"]["min"] = newest - self.window_size
                self.xy_chart.options["xAxis"]["max"] = newest

            self.xy_chart.options["series"][0]["data"] = list(zip(self.x, self.trace1))
            self.xy_chart.options["series"][1]["data"] = list(zip(self.x, self.trace2))
            self.xy_chart.update()
            self._line_dirty = False