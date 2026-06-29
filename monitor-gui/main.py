from nicegui import app, ui
from dashboard.app import MainDashboard
from backend import initialize_serial, run_serial_loop
from threading import Thread

# 1. Define what happens ONCE when the server boots up
@app.on_startup
def startup_backend():
    print("Backend server starting... Initializing serial port.")
    # Initialize the serial connection
    initialize_serial('COM5')
    
    # Start the backend consumer loop in a dedicated daemon thread
    Thread(target=run_serial_loop, daemon=True).start()

# 2. Define the UI layout (runs once per browser session/connection)
@ui.page('/')
def index():
    # Instantiate your UI panels inside a page function 
    # so each connected browser gets its own clean view.
    MainDashboard()

# 3. Start the server
ui.run(
    title="Serial Monitor",
    reload=False, # Keeps the process stable without auto-restarting
)