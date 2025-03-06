import rtde_receive
import rtde_io
from rtde_control import RTDEControlInterface as RTDEControl

# RTDE interfaces (lazy initialization)
rtde_r = None
rtde_c = None
rtde_i = None
rtde_connected = False

def initialize_rtde():
    """Initialiseer de RTDE-interfaces als ze nog niet zijn geïnitialiseerd."""
    global rtde_r, rtde_c, rtde_i, rtde_connected
    if not rtde_connected:
        try:
            rtde_r = rtde_receive.RTDEReceiveInterface("192.168.0.20")

            rtde_c = RTDEControl("192.168.0.20")
            rtde_i = rtde_io.RTDEIOInterface("192.168.0.20")
            rtde_connected = True
        except Exception as e:
            print(f"RTDE connection error: {e}")
            rtde_r = None
            rtde_c = None
            rtde_i = None
            rtde_connected = False
    return rtde_connected

# Define joint positions to move between
joint_position_1 = [-0.029192272816793263, -0.7469827693751832, 1.3175094763385218, -0.5753325384906312, 0.9964199662208557, 4.718315124511719]
joint_position_2 = [-0.02115327516664678, -0.7476166051677247, 1.3301270643817347, -0.5728175205043335, 1.1413614749908447, 4.7532830238342285]


import rtde_receive

def is_robot_busy():
    """
    Controleer of de robot bezig is met een beweging.

    :param rtde_r: Een RTDEReceiveInterface-object.
    :return: True als de robot bezig is, False als de robot stilstaat.
    """
    if rtde_r is None:
        raise RuntimeError("RTDE receive interface is niet geïnitialiseerd.")

    # Controleer de runtime status van de robot
    runtime_state = rtde_r.getRobotStatus()
    program_running = runtime_state & (1 << 3)  # Bit 3: Program running

    # Als het programma actief is, is de robot bezig
    return program_running != 0

    # TO-DO
    # controleren hoe de getrobotstatus eigenlijk werkt, want het werkt niet zoals verwacht


def move_to_position(position, speed=0.5, acceleration=0.3):
    if initialize_rtde() and rtde_c:
        rtde_c.moveJ(position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")

def get_actual_joint_positions():
    if initialize_rtde() and rtde_r:
        return rtde_r.getActualQ()
    else:
        raise RuntimeError("RTDE receive interface is not connected.")

# import Robodk script
# manier bedenken om schroevendraaier functies te implementeren tussen de movej functies
# manier bedenken om .script files te verwerken, misschien weergeven, status tracken, wanneer we aan het oppakken en indraaien zijn