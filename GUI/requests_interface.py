import time

import requests
import rtde_io

import socketio_interface
from socketio_interface import get_screwdriver_data
from rtde_interface import *

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
def premount_screw(shank_force_n=25, screwing_l_mm=25, torque_nm=0.7):
    endpoint = f"/api/dc/sd/premount/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Function to tighten a screw
def tighten_screw(shank_force_n=25, screwing_l_mm=1, torque_nm=2.00):
    endpoint = f"/api/dc/sd/tighten/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Function to loosen a screw
def loosen_screw(shank_force_n=25, unscrewing_length_mm=55):
    endpoint = f"/api/dc/sd/loosen/{tool_id}/{shank_force_n}/{unscrewing_length_mm}"
    return send_request(endpoint)

def stop():
    endpoint = f"/api/dc/sd/stop/{tool_id}"
    return send_request(endpoint)

# Function to check if the screwdriver is busy
def check_busy():
    data = socketio_interface.get_screwdriver_data()

    if data:
      return data.get("screwdriver_busy", False) or data.get("shank_busy", False)

# Function to screw in a screw
def screw_in(mode):

     if mode == 0: # inschroeven bij oppak locatie

        premount_screw()
        time.sleep(1.85) # delay voor hoelang de screwdriver moet schroeven voordat de klem open gaat

        # make connection with the rtdeio interface for de pickup station
        rtde_i = rtde_io.RTDEIOInterface("192.168.0.20")
        rtde_io.RTDEIOInterface.setStandardDigitalOut(rtde_i,1,1) # 1 is open

        time.sleep(5) # delay to make sure screw is picked up

        move_shank(0)

        #schuif open
        rtde_io.RTDEIOInterface.setStandardDigitalOut(rtde_i, 0, 1)  # 1 is open
        time.sleep(1)
        #klem dicht
        rtde_io.RTDEIOInterface.setStandardDigitalOut(rtde_i, 1, 0)  # 1 is dicht
        time.sleep(1)
        #schuif dicht
        rtde_io.RTDEIOInterface.setStandardDigitalOut(rtde_i, 0, 0)  # 0 is dicht
        return

     elif mode == 20: # inschroeven in testmodel

        premount_screw(torque_nm=1.3)

        time.sleep(3)

        move_shank(0)

     elif mode == 10:
        move_shank(0)

        time.sleep(3)

        premount_screw(torque_nm=0.3)

        time.sleep(3)

        move_shank(0)




# Function to unscrew a screw
def screw_out():
    loosen_screw()
    time.sleep(5)
    move_shank(0)
    time.sleep(5)
    return
