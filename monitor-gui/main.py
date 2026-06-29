import argparse
from threading import Thread
from nicegui import app, ui
from dashboard.app import MainDashboard
from backend import initialize_serial, run_serial_loop

# 1. Define what happens ONCE when the server boots up
@app.on_startup
def startup_backend():
    print("Backend server starting... Initializing serial port.")
    # Initialize the serial connection
    # initialize_serial('COM5')
    
    # Start the backend consumer loop in a dedicated daemon thread
    Thread(target=run_serial_loop, daemon=True).start()

# 2. Define the UI layout (runs once per browser session/connection)
@ui.page('/')
def index():
    # Instantiate your UI panels inside a page function 
    # so each connected browser gets its own clean view.
    MainDashboard()

# 3. Parse command-line arguments and start the server
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial Monitor Server")
    
    # Add the port argument with your original 8081 as the fallback default
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8081,
        help="Port to run the NiceGUI server on (default: 8081)"
    )
    
    args = parser.parse_args()

    ui.run(
        title="Serial Monitor",
        reload=False,  # Keeps the process stable without auto-restarting
        port=args.port,  # Uses the dynamically passed port
        show=False
    )