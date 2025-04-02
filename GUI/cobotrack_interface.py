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
        print(f"Connection state: {cobot_connected}")
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
    global cobot_connected  # Explicitly declare global
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


def move_to(location, speed=1):
    """Move COBOTRACK to a given location at the specified speed."""
    global cobot_connected  # Explicitly declare global
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
    global cobot_connected  # Explicitly declare global
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
    global cobot_connected  # Explicitly declare global
    if not cobot_connected:
        print("[Cobotrack] Cannot stop. Please connect cobotrack first.")
        return False
    response = send_command(f"COBOTRACK_CONTROL_TRACK_STOP({track_id})")
    return "COBOTRACK_STOP:_PASS" in response if response else False


def get_status_word(track_id=0):
    """Get the LMK status word as a string."""
    global cobot_connected  # Explicitly declare global
    if not cobot_connected:
        print("[Cobotrack] Couldn't fetch status. Please connect first.")
        return None
    response = send_command(f"COBOTRACK_CONTROL_STATUS_WORD_INT({track_id})")
    return response if response else None


def is_connected(nr_of_tracks=0):
    """Check if the LMK controller is connected."""
    global cobot_connected  # Explicitly declare global
    if not cobot_connected:
        print("[Cobotrack] Not connected. Please connect first.")
        return False
    response = send_command(f"COBOTRACK_CONTROL_STATUS_CONNECTED({nr_of_tracks})")
    return "COBOTRACK_CONNECTED:_PASS" in response if response else False

#connect to server
def connect_track(track_id=0):

    command = f"COBOTRACK_CONTROL_NETWORK_CONNECT()"
    response = send_command(command)

    if response:
        if "COBOTRACK_CONNECT:_PASS" in response:
            print("[Cobotrack] Controller connection to the Cobot succeeded.")
            return True
        elif "COBOTRACK_CONNECT:_FAIL" in response:
            print("[Cobotrack] Controller connection to the Cobot failed")
        else:
            print(f"[Cobotrack] Unexpected response: {response}")
    else:
        print("[Cobotrack] No response received from controller.")

    return False

#identify
def identify_track(track_id=0):

    command = f"COBOTRACK_CONTROL_NETWORK_IDENTIFY(1, 192.168.0.20)"
    response = send_command(command)

    if response:
        if "COBOTRACK_IDENTIFY:_PASS" in response:
            print("[Cobotrack] Identify passed.")
            return True
        elif "COBOTRACK_IDENTIFY:_FAIL" in response:
            print("[Cobotrack] Identify failed.")
        elif "COBOTRACK_IDENTIFY:_INVALID_ARGS" in response:
            print("[Cobotrack] Identify failed due to invalid arguments.")
        else:
            print(f"[Cobotrack] Unexpected response: {response}")
    else:
        print("[Cobotrack] No response received from controller.")

    return False

#disconnect
def reference_track(track_id=0):

    command = f"COBOTRACK_CONTROL_NETWORK_DISCONN()"
    response = send_command(command)

    if response:
        if "COBOTRACK_DISCONNECT:_PASS" in response:
            print("[Cobotrack] Disconnect succeeded.")
            return True
    else:
        print("[Cobotrack] No response received from controller.")

    return False

#isconnected
def isconnected_track(track_id=0):

    command = f"COBOTRACK_CONTROL_STATUS_CONNECTED({track_id})"
    response = send_command(command)

    if response:
        if "COBOTRACK_CONNECTED:_PASS" in response:
            print("[Cobotrack] LMK Controller is connected to the LMK's.")
            return True
        elif "COBOTRACK_CONNECTED:_FAIL" in response:
            print("[Cobotrack] LMK Controller is not connected to the LMK's.")
        elif "COBOTRACK_CONNECTED:_INVALID_ARGS" in response:
            print("[Cobotrack] Isconnected check failed due to invalid arguments.")
        else:
            print(f"[Cobotrack] Unexpected response: {response}")
    else:
        print("[Cobotrack] No response received from controller.")

    return False

#isunlocked
def isunlocked_track(track_id=0):
    command = f"COBOTRACK_CONTROL_STATUS_UNLOCKED()"
    response = send_command(command)

    if response:
        if "COBOTRACK_UNLOCKED:_PASS" in response:
            print("[Cobotrack] LMK is unlocked.")
            return True
        elif "COBOTRACK_UNLOCKED:_FAIL" in response:
            print("[Cobotrack] LMK is not unlocked.")
        else:
            print(f"[Cobotrack] Unexpected response: {response}")
    else:
        print("[Cobotrack] No response received from controller.")

    return False

def main():
    """Test function to demonstrate connecting and moving the COBOTRACK."""
    try:
        print("Starting COBOTRACK test...")

        # Connect to COBOTRACK
        print("Connecting to COBOTRACK...")
        if not connect():
            print("Failed to connect. Exiting.")
            return

        print("Connection successful!")

        # Verify connection
        if is_connected():
            print("Connection verified.")
        else:
            print("Connection could not be verified. Continuing anyway...")

        # Get current position
        current_position = get_position()
        if current_position is not None:
            print(f"Current position: {current_position}")
        else:
            print("Could not retrieve current position.")

        # Move to a new position
        target_position = 100  # Set your desired position here
        move_speed = 1  # Set your desired speed here

        print(f"Attempting to move to position {target_position} at speed {move_speed}...")
        if move_to(target_position, move_speed):
            print("Movement completed successfully.")

            # Get new position to verify movement
            new_position = get_position()
            if new_position is not None:
                print(f"New position after movement: {new_position}")
            else:
                print("Could not retrieve position after movement.")
        else:
            print("Movement failed.")

        reference_track(0)

        time.sleep(50)
        # Stop the track
        # print("Stopping the track...")
        # if stop_track():
        #     print("Track stopped successfully.")
        # else:
        #     print("Failed to stop the track.")

        # Get status
        status = get_status_word()
        if status:
            print(f"COBOTRACK status: {status}")
        else:
            print("Could not retrieve status.")

    except Exception as e:
        print(f"An error occurred during the test: {e}")

    finally:
        # Always disconnect at the end
        print("Disconnecting from COBOTRACK...")
        disconnect()
        print("Test completed.")


if __name__ == "__main__":
    main()