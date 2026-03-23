import requests
import time
import socketio_SD

# Basic data
compute_box_ip = "192.168.12.15"
username = "admin"
password = "OnRobotPerron038"
tool_id = 0  # ID of the tool

# Srew motion input
max_torque = 5 #max torque untill stopping screw motion via default premount behavior
screw_length = 20 #helicoil length
target_torque = 1 #target torque to stop the screw motion early via monitoring current torque and no shank motion
shank_force = 20 #shank force

# URL's
stop_url = f"http://{compute_box_ip}/api/dc/sd/stop/{tool_id}"
start_url = f"http://{compute_box_ip}/api/dc/sd/setup/{tool_id}/{1}"
tighten_url = f"http://{compute_box_ip}/api/dc/sd/tighten/{tool_id}/{shank_force}/{screw_length}/{max_torque}"
loosen_url = f"http://{compute_box_ip}/api/dc/sd/loosen/{tool_id}/{shank_force}/{screw_length}"


#1. Start screw motion
response = requests.get(tighten_url, auth=(username, password))

#2. Check current torque via socket_IO and screw until target torque reached
while True:
    data = socketio_SD.get_screwdriver_data()
    if data:
            # Accessing the torque from the dictionary/dataclass
            # (Note: Using .get() because your current file stores it as a dict)
            current_torque = data.get("current_torque", 0.0)
            print(f"Torque: {current_torque:.2f} Nm", end="\r")
            if current_torque >= target_torque:
                   
                # Stop screw motion
                response = requests.get(stop_url, auth=(username, password))
                print(f"\nStopped at {current_torque} Nm")
                break
            time.sleep(0.01) # 10ms delay to match high-speed WebSocket updates

# 3. Re-enable screwdriver
response = requests.get(start_url, auth=(username, password))
time.sleep(0.1) # 100ms delay
# 4. Loosen screwdriver
response = requests.get(loosen_url, auth=(username, password))

# 5. Wait until finished
while True:
    data = socketio_SD.get_screwdriver_data()
    if data:
        # Accessing the torque from the dictionary/dataclass
        is_busy = data.get("screwdriver_busy", False) or data.get("shank_busy", False)
        if not is_busy:
             break
        


