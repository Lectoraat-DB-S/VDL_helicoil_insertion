import socketio
import base64
from dataclasses import dataclass

# WebSocket connection details
compute_box_ip = "192.168.0.15"
username = "admin"
password = "OnRobotPerron038"

# Create Socket.IO client
sio = socketio.Client()
screwdriver_data = None
gui_app_instance = None  # GUI reference will be set later



@dataclass
class ScrewdriverData:
    status: int
    screwdriver_busy: bool
    shank_busy: bool
    z_safety_activated: bool
    error_code: int
    current_torque: float
    shank_position: float
    force: float
    torque_gradient: int
    achieved_torque: float
    command_results: int
    qc_version: int
    current_extender_length: int
    maximum_shank_position: int

def connect_to_server():
    """Connect to the WebSocket server."""
    try:
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        }
        sio.connect(f"ws://{compute_box_ip}/socket.io/", headers=headers, transports=["websocket"])
        return True
    except Exception as e:
        print(f"[ERROR] Socket.IO connection failed: {e}")
        return False

@sio.event
def connect():
    print("[EVENT] Verbonden met de server!")

@sio.event
def disconnect():
    print("[EVENT] Verbinding verbroken.")

@sio.on("message")
def on_message(data):
    """Handle incoming WebSocket messages and update the GUI."""
    global screwdriver_data, gui_app_instance

    print(f"[DEBUG] Raw message received: {data}")

    try:
        # Check if the message contains the expected data structure
        if isinstance(data, dict) and "devices" in data:
            devices = data.get("devices", [])
            for device in devices:
                if device.get("deviceType") == 14:  # Ensure it's the screwdriver
                    screwdriver_data = device.get("variable", {})

                    # Log the received data
                    if screwdriver_data:
                        ScrewdriverData(**screwdriver_data)
                        print("[SUCCESS] Screwdriver data stored:", ScrewdriverData)
                    else:
                        print("[WARNING] Received empty screwdriver data!")

                    # Update the GUI if the instance is available
                    if gui_app_instance is not None:
                        try:
                            gui_app_instance.root.after(100, gui_app_instance.update_screwdriver_data)
                            print("[SUCCESS] GUI update scheduled!")
                        except AttributeError:
                            print("[ERROR] GUI instance does not have 'update_screwdriver_data'.")
                    else:
                        print("[WARNING] GUI instance is not set yet!")

                    break
    except Exception as e:
        print(f"[ERROR] Failed to process message: {e}")

def get_screwdriver_data():
    """Return the latest screwdriver data."""
    global screwdriver_data
    print("[INFO] get_screwdriver_data() called")
    if screwdriver_data is None:
        print("[WARNING] No screwdriver data available yet!")
    else:
        print(f"[INFO] Returning screwdriver data: {screwdriver_data}")
    return screwdriver_data