import requests

import socketio_interface
from socketio_interface import get_screwdriver_data


# Basic data
compute_box_ip = "192.168.0.15"
username = "admin"
password = "OnRobotPerron038"
tool_id = 0  # ID of the tool

# Generic function to send HTTP requests
def send_request(endpoint, params=None):
    """
    Send an HTTP GET request to the specified endpoint.

    :param endpoint: The API endpoint (e.g., "/api/dc/sd/move_shank/{tool_id}/{shaft_value}").
    :return: None
    """
    url = f"http://{compute_box_ip}{endpoint}"
    response = requests.get(url, auth=(username, password), params=params)

    if response.status_code == 200:
        print(f"Request successful: {endpoint}")
        return 0
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Function to move the shaft
def move_shank(shaft_value=20):
    if not (0 <= shaft_value <= 55):
        print("Invalid value. Enter a number between 0 and 55.")
        return

    endpoint = f"/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    return send_request(endpoint)

# Function to pick a screw
def pick_screw(shank_force_n=25, screwing_l_mm=10):
    endpoint = f"/api/dc/sd/pickup_screw/{tool_id}/{shank_force_n}/{screwing_l_mm}"
    return send_request(endpoint)

# Function to pre-mount a screw
def premount_screw(shank_force_n=25, screwing_l_mm=25, torque_nm=0.5):
    endpoint = f"/api/dc/sd/premount/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Function to tighten a screw
def tighten_screw(shank_force_n=25, screwing_l_mm=1, torque_nm=2.00):
    endpoint = f"/api/dc/sd/tighten/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Function to loosen a screw
def loosen_screw(shank_force_n=25, unscrewing_length_mm=25):
    endpoint = f"/api/dc/sd/loosen/{tool_id}/{shank_force_n}/{unscrewing_length_mm}"
    return send_request(endpoint)

# Function to check if the screwdriver is busy
def check_busy():
    data = socketio_interface.get_screwdriver_data()

    if data:
      return data.get("screwdriver_busy", False) or data.get("shank_busy", False)

# Function to screw in a screw
def screw_in():
    import time
    time.sleep(2)
    tighten_screw(screwing_l_mm=14, torque_nm=2)

    # Wait until screwdriver is no longer busy
    while check_busy():
        time.sleep(0.001)  # Small delay to prevent CPU overload

    loosen_screw(unscrewing_length_mm=10)


# Function to unscrew a screw
def screw_out():
    import time
    time.sleep(2)
    tighten_screw(screwing_l_mm=15, torque_nm=0.30)

    # Wait until screwdriver is no longer busy
    while check_busy():
        time.sleep(0.001)  # Small delay to prevent CPU overload

    loosen_screw(unscrewing_length_mm=8)
