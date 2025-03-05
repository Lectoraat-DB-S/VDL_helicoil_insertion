import requests

import socketio_interface
from socketio_interface import get_screwdriver_data



# Basisgegevens
compute_box_ip = "192.168.0.15"
username = "admin"
password = "OnRobotPerron038"
tool_id = 0  # ID van de tool

# Generieke functie om HTTP-requests te versturen
def send_request(endpoint, params=None):
    """
    Verstuur een HTTP GET-request naar de opgegeven endpoint.

    :param endpoint: De API-endpoint (bijv. "/api/dc/sd/move_shank/{tool_id}/{shaft_value}").
    :return: None
    """
    url = f"http://{compute_box_ip}{endpoint}"
    response = requests.get(url, auth=(username, password), params=params)

    if response.status_code == 200:
        print(f"Request succesvol: {endpoint}")
        return 0
    else:
        print(f"Fout: {response.status_code} - {response.text}")
        return None

# Functie om de shaft te bewegen
def move_shank(shaft_value=20):
    if not (0 <= shaft_value <= 55):
        print("Ongeldige waarde. Voer een getal in tussen 0 en 55.")
        return

    endpoint = f"/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    return send_request(endpoint)

# Functie Pick screw
def pick_screw(shank_force_n=25, screwing_l_mm=10):
    endpoint = f"/api/dc/sd/pickup_screw/{tool_id}/{shank_force_n}/{screwing_l_mm}"
    return send_request(endpoint)

# Functie Pre-mount screw
def premount_screw(shank_force_n=25, screwing_l_mm=25, torque_nm=0.5):
    endpoint = f"/api/dc/sd/premount/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Functie Tighten screw
def tighten_screw(shank_force_n=25, screwing_l_mm=1, torque_nm=2.00):
    endpoint = f"/api/dc/sd/tighten/{tool_id}/{shank_force_n}/{screwing_l_mm}/{torque_nm}"
    return send_request(endpoint)

# Functie Loosen screw
def loosen_screw(shank_force_n=25, unscrewing_lenght_mm=25):
    endpoint = f"/api/dc/sd/loosen/{tool_id}/{shank_force_n}/{unscrewing_lenght_mm}"
    return send_request(endpoint)

def check_busy():
    data = socketio_interface.get_screwdriver_data()

    if data:
      return data.get("screwdriver_busy", False)


# Functie om een schroef in te draaien
def indraaien():
    import time
    time.sleep(2)
    tighten_screw(screwing_l_mm=14, torque_nm=2)

    if check_busy() is not True:
     loosen_screw(unscrewing_lenght_mm=10)

# Functie om een schroef uit te draaien
def uitdraaien():
    import time
    time.sleep(2)
    tighten_screw(screwing_l_mm=15, torque_nm=0.30)

    if check_busy() is not True:
     loosen_screw(unscrewing_lenght_mm=8)