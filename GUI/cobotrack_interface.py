import socket
import time

# Global connection variables
cobot_socket = None
cobot_connected = False
IP = "192.168.0.10"
PORT = 35000
TIMEOUT = 5  # Timeout in seconds
MAX_RETRIES = 10  # Maximum retries for move_to
RETRY_DELAY = 0.5  # Delay between retries in seconds

def connect():
    """Connect to the COBOTRACK system."""
    global cobot_socket, cobot_connected
    try:
        cobot_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cobot_socket.settimeout(TIMEOUT)
        cobot_socket.connect((IP, PORT))
        cobot_connected = True
        return True
    except socket.error as e:
        print(f"Connection error: {e}")
        cobot_connected = False
        return False

def disconnect():
    """Disconnect from the COBOTRACK system."""
    global cobot_socket, cobot_connected
    if cobot_socket:
        cobot_socket.close()
        cobot_socket = None
    cobot_connected = False

def send_command(command):
    """Send a command to COBOTRACK and return the response."""
    if not cobot_connected or not cobot_socket:
        print("Not connected. Please connect first.")
        return None

    try:
        cobot_socket.sendall(command.encode('utf-8'))
        response = cobot_socket.recv(1024).decode('utf-8')
        return response
    except socket.error as e:
        print(f"Communication error: {e}")
        cobot_connected = False
        return None

def check_connection():
    """Check if the connection to COBOTRACK is active."""
    if not cobot_connected:
        print("[Cobotrack] Not connected. Please connect first.")
        return False
    response = send_command("COBOTRACK_CONTROL_STATUS_CONNECTED(1)")
    return "COBOTRACK_CONNECTED:_PASS" in response if response else False

def move_to(location, speed):
    """Move COBOTRACK to a given location at the specified speed."""
    if not cobot_connected:
        print("[Cobotrack] Cannot move to position. Please connect first.")
        return False

    command = f"COBOTRACK_CONTROL_TRACK_MOVETO(0, {location}, {speed}, 0)"
    retries = 0
    while retries < MAX_RETRIES:
        response = send_command(command)
        if response and "COBOTRACK_MOVETO:_PASS" in response:
            print(f"Movement to location {location} at speed {speed} succeeded")
            return True
        time.sleep(RETRY_DELAY)
        retries += 1
    print("[Cobotrack] Movement failed after maximum retries.")
    return False

def get_position(track_id=0):
    """Get the current position of the specified track."""
    if not cobot_connected:
        print("[Cobotrack] Cannot go to position. Please connect first.")
        return None
    response = send_command(f"COBOTRACK_CONTROL_STATUS_POSITION({track_id})")
    if response and "COBOTRACK_POSITION:" in response:
        try:
            position = float(response.split("COBOTRACK_POSITION:")[1].strip())
            return position
        except ValueError as e:
            print(f"[Cobotrack] Error parsing position: {e}")
            return None
    return None

def stop_track(track_id=0):
    """Stop the LMK motion."""
    if not cobot_connected:
        print("[Cobotrack] Cannot stop. Please connect cobotrack first.")
        return False
    response = send_command(f"COBOTRACK_CONTROL_TRACK_STOP({track_id})")
    return "COBOTRACK_STOP:_PASS" in response if response else False

def get_status_word(track_id=0):
    """Get the LMK status word as a string."""
    if not cobot_connected:
        print("[Cobotrack] Couldn't fetch status. Please connect first.")
        return None
    response = send_command(f"COBOTRACK_CONTROL_STATUS_WORD({track_id})")
    return response if response else None

def is_connected(nr_of_tracks=1):
    """Check if the LMK controller is connected."""
    if not cobot_connected:
        print("[Cobotrack] Not connected. Please connect first.")
        return False
    response = send_command(f"COBOTRACK_CONTROL_STATUS_CONNECTED({nr_of_tracks})")
    return "COBOTRACK_CONNECTED:_PASS" in response if response else False
