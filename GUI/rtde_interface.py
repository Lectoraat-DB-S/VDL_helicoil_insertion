import rtde_control
import rtde_receive
import rtde_io
from rtde_control import RTDEControlInterface as RTDEControl
import math
import numpy as np  # Importeer numpy voor vector-bewerkingen

DEBUG_CODE = False           # true if you want prints, false if you don't
SPEED = 0.5
ACCELERATION = 0.25

# RTDE interfaces (lazy initialization)
rtde_r = None
rtde_c = None
rtde_connected = False

global_calibration_offset = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
global_joint_offset = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# ^ Opslag voor de 6D-waarde (mm/rad), hoewel de implementatie in moveJ complex is.

def initialize_rtde():
    """Initialize the RTDE interfaces if they have not been initialized yet."""
    global rtde_r, rtde_c, rtde_i, rtde_connected
    if not rtde_connected:
        try:
            rtde_r = rtde_receive.RTDEReceiveInterface("192.168.12.120")
            rtde_c = RTDEControl("192.168.12.120")

            rtde_connected = True
        except Exception as e:
            print(f"RTDE connection error: {e}")
            rtde_r = None
            rtde_c = None
            rtde_connected = False
    return rtde_connected


def disconnect_rtde():
    """Disconnect all RTDE interfaces and reset their state."""
    global rtde_r, rtde_c, rtde_connected

    print("Disconnecting RTDE...")
    try:
        if rtde_r:
            try:
                rtde_r.disconnect()
            except Exception:
                pass
            rtde_r = None

        if rtde_c:
            try:
                # Probeer script te stoppen voor disconnect
                rtde_c.stopScript()
                rtde_c.disconnect()
            except Exception:
                pass
            rtde_c = None

    except Exception as e:
        print(f"Error while disconnecting RTDE: {e}")
    finally:
        rtde_connected = False
        print("RTDE Disconnected.")


def is_robot_physically_moving(debug=False):
    """
    Check if the robot is physically moving, regardless of the program status.

    Args:
        debug (bool): If True, print debug information about each check

    Returns:
        bool: True if the robot is physically moving, False if it's idle
    """
    if rtde_r is None:
        raise RuntimeError("RTDE receive interface is not initialized.")

    # Check joint speeds (most direct indication of movement)
    actual_joint_velocities = rtde_r.getActualQd()
    velocity_threshold = 0.005

    any_joint_moving = any(abs(v) > velocity_threshold for v in actual_joint_velocities)
    if debug:
        print(f"Joint velocities: {[round(v, 6) for v in actual_joint_velocities]}")
        print(f"Any joint moving above threshold {velocity_threshold}: {any_joint_moving}")

    # If joints are moving, the robot is physically active
    if any_joint_moving:
        return True

    # Check target position vs. current position (if robot is moving towards a target)
    if hasattr(rtde_r, 'getTargetQ') and hasattr(rtde_r, 'getActualQ'):
        target_q = rtde_r.getTargetQ()
        actual_q = rtde_r.getActualQ()

        position_threshold = 0.01  # radians
        position_differences = [abs(t - a) for t, a in zip(target_q, actual_q)]

        has_position_difference = any(diff > position_threshold for diff in position_differences)

        if debug:
            print(f"Position differences: {[round(diff, 6) for diff in position_differences]}")
            print(f"Any position difference above threshold {position_threshold}: {has_position_difference}")
            print("Robot moving ---------------------------------------")

        # If there is a significant difference between target and current position,
        # the robot is probably moving or about to move
        if has_position_difference:
            return True

    # If neither method detects movement, the robot is idle
    return False


# set the offset in the global calibration variable, in this case the X and Y
def set_global_calibration_offset(offset_values):
    global global_calibration_offset
    if len(offset_values) == 6:
        global_calibration_offset = offset_values
        if DEBUG_CODE:
            print(f"Global calibration offset set to: {global_calibration_offset}")
            print(global_calibration_offset, global_joint_offset)
        return True
    if DEBUG_CODE:
        print("Fout: Calibration offset moet 6 waarden bevatten.")
    return False


# set the offset in the global calibration variable, in this case the Rz
def set_global_joint_offset(offset_values):
    global global_joint_offset
    if len(offset_values) == 6:
        global_joint_offset = offset_values
        if DEBUG_CODE:
            print(f"Global joint offset set to: {global_joint_offset}")
        return True
    if DEBUG_CODE:
        print("Fout: Joint offset moet 6 waarden bevatten.")
    return False


# movej that is calibrated by using the offset
# untested
def move_to_positionj_calibrated_TCP(position, speed=SPEED, acceleration=ACCELERATION):
    # the incomming position is in rad [r1, r2, r3, r4, r5, r6]
    if initialize_rtde() and rtde_c:
        global global_calibration_offset
        global global_joint_offset

        # get actual TCP offset of the robot
        tcp_offset = rtde_c.getTCPOffset()

        # to get the inverse kinematics to work we add these magical elements
        maxPositionError = 1e-10
        maxOrientationError = 1e-10

        # change pose to position. so x, y, z, rx, ry, rz to r1, r2, r3, r4, r5, r6
        joint_position = rtde_c.getInverseKinematics(position, position, maxPositionError, maxOrientationError)

        if DEBUG_CODE:
            print(tcp_offset)
            print(position)

        # initialize a new position list and copy the original positions into a different list
        new_position = [0, 0, 0, 0, 0, 0]
        rotated_position = list(joint_position)

        if DEBUG_CODE:
            print(rotated_position)
            print(rtde_c.getForwardKinematics(rotated_position))

        # add base rotation (somewhere i made an mistake so it is here fixed with a -= instead of a +=)
        rotated_position[0] -= global_joint_offset[5]

        if DEBUG_CODE:
            print(rotated_position)

        # change position to pose. so r1, r2, r3, r4, r5, r6 to x, y, z, rx, ry, rz
        rotated_pose = rtde_c.getForwardKinematics(rotated_position, tcp_offset)

        if DEBUG_CODE:
            print(f"rotated pose: {rotated_pose}")
            print(global_joint_offset)

        # add xy offset     WATCH OUT: the X of the camera is the Y of the robot
        new_position[0] = rotated_pose[0] + global_calibration_offset[1]
        new_position[1] = rotated_pose[1] + global_calibration_offset[0]
        new_position[2] = rotated_pose[2]
        new_position[3] = rotated_pose[3]
        new_position[4] = rotated_pose[4]
        new_position[5] = rotated_pose[5]

        if DEBUG_CODE:
            print(f"new pose: {new_position}")
            print(global_calibration_offset)

        # to get the inverse kinematics to work we add these magical elements
        maxPositionError = 1e-10
        maxOrientationError = 1e-10

        # change pose to position. so x, y, z, rx, ry, rz to r1, r2, r3, r4, r5, r6
        target_position = rtde_c.getInverseKinematics(new_position, position, maxPositionError, maxOrientationError)

        if DEBUG_CODE:
            print(f"MoveJ gestart. Nominale positie: {position}")

        rtde_c.moveJ(target_position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is niet verbonden.")


# movej that is calibrated by using the offset
def move_to_positionj_calibrated_Joints(position, speed=SPEED, acceleration=ACCELERATION):
    # the incomming position is in rad [r1, r2, r3, r4, r5, r6]
    if initialize_rtde() and rtde_c:
        global global_calibration_offset
        global global_joint_offset

        # get actual TCP offset of the robot
        tcp_offset = rtde_c.getTCPOffset()

        if DEBUG_CODE:
            print(tcp_offset)
            print(position)

        # initialize a new position list and copy the original positions into a different list
        new_position = [0, 0, 0, 0, 0, 0]
        rotated_position = list(position)

        if DEBUG_CODE:
            print(rotated_position)
            print(rtde_c.getForwardKinematics(rotated_position))

        # add base rotation (somewhere i made an mistake so it is here fixed with a -= instead of a +=)
        rotated_position[0] -= global_joint_offset[5]

        if DEBUG_CODE:
            print(rotated_position)

        # change position to pose. so r1, r2, r3, r4, r5, r6 to x, y, z, rx, ry, rz
        rotated_pose = rtde_c.getForwardKinematics(rotated_position, tcp_offset)

        if DEBUG_CODE:
            print(f"rotated pose: {rotated_pose}")
            print(global_joint_offset)

        # add xy offset     WATCH OUT: the X of the camera is the Y of the robot
        new_position[0] = rotated_pose[0] + global_calibration_offset[1]
        new_position[1] = rotated_pose[1] + global_calibration_offset[0]
        new_position[2] = rotated_pose[2]
        new_position[3] = rotated_pose[3]
        new_position[4] = rotated_pose[4]
        new_position[5] = rotated_pose[5]

        if DEBUG_CODE:
            print(f"new pose: {new_position}")
            print(global_calibration_offset)

        # to get the inverse kinematics to work we add these magical elements
        maxPositionError = 1e-10
        maxOrientationError = 1e-10

        # change pose to position. so x, y, z, rx, ry, rz to r1, r2, r3, r4, r5, r6
        target_position = rtde_c.getInverseKinematics(new_position, position, maxPositionError, maxOrientationError)

        if DEBUG_CODE:
            print(f"MoveJ gestart. Nominale positie: {position}")

        rtde_c.moveJ(target_position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is niet verbonden.")


# function that only moves a single specified joint
def move_joint(angle, joint, speed=SPEED, acceleration=ACCELERATION):
    if initialize_rtde() and rtde_c and rtde_r:
        # get actual joint positions
        start_joints = rtde_r.getActualQ()
        # add the amount of degrees it needs to turn
        start_joints[joint] += angle
        if DEBUG_CODE:
            print(f"MoveJ gestart. Joint {joint} wordt gedraaid voor {angle} graden.")
        rtde_c.moveJ(start_joints, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface of RTDE receive interface is niet verbonden.")


# function to move the robot without the calibration offset
def move_to_positionj_uncalibrated(position, speed=SPEED, acceleration=ACCELERATION):
    if initialize_rtde() and rtde_c:
        rtde_c.moveJ(position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


# function to move the robot without the calibration offset
def move_to_positionl_uncalibrated(position, speed=SPEED, acceleration=ACCELERATION):
    if initialize_rtde() and rtde_c:
        rtde_c.moveL(position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


# function that is used during calibration to move the robot
def move_to_positionl_calibration(relative_position, speed=SPEED, acceleration=ACCELERATION):
    if initialize_rtde() and rtde_c and rtde_r:
        # get actual tcp pose
        start_position = rtde_r.getActualTCPPose()
        new_position = list(start_position)
        # add the amount it needs to move
        if len(new_position) >= 2:
            new_position[0] += relative_position[1]
            new_position[1] += relative_position[0]
            new_position[3] = new_position[3]
            new_position[4] = new_position[4]
            new_position[5] = new_position[5]
        rtde_c.moveL(new_position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


# movel that is calibrated by using the offset
# untested
def move_to_positionl_calibrated_TCP(position, speed=SPEED, acceleration=ACCELERATION):
    # the incoming position is [x, y, z, rx, ry, rz]
    if initialize_rtde() and rtde_c:

        global global_calibration_offset
        global global_joint_offset

        # get actual TCP offset of the robot
        tcp_offset = rtde_c.getTCPOffset()

        # initialize a new position list and copy the original positions into a different list
        new_position = [0, 0, 0, 0, 0, 0]
        rotated_position = list(position)

        # change pose to position. so x, y, z, rx, ry, rz to r1, r2, r3, r4, r5, r6
        # joint_position = rtde_c.getInverseKinematics(position)

        # to get the inverse kinematics to work we add these magical elements
        maxPositionError = 1e-10
        maxOrientationError = 1e-10

        # change pose to position. so x, y, z, rx, ry, rz to r1, r2, r3, r4, r5, r6
        joint_position = rtde_c.getInverseKinematics(position, maxPositionError=maxPositionError,
                                                     maxOrientationError=maxOrientationError)

        # add base rotation (somewhere i made an mistake so it is here fixed with a -= instead of a +=)
        joint_position[0] -= global_joint_offset[5]

        # change position to pose. so r1, r2, r3, r4, r5, r6 to x, y, z, rx, ry, rz
        rotated_pose = rtde_c.getForwardKinematics(joint_position, tcp_offset)

        # add xy offset     WATCH OUT: the X of the camera is the Y of the robot
        rotated_pose[0] += global_calibration_offset[1]
        rotated_pose[1] += global_calibration_offset[0]

        if DEBUG_CODE:
            print(f"MoveJ gestart. Nominale positie: {position}")
            print(f"Gekorrigeerde positie: {rotated_pose}")

        rtde_c.moveL(rotated_pose, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


# movel that is calibrated by using the offset
# untested
def move_to_positionl_calibrated_joints(position, speed=SPEED, acceleration=ACCELERATION):
    # the incoming position is [x, y, z, rx, ry, rz]
    if initialize_rtde() and rtde_c:

        global global_calibration_offset
        global global_joint_offset

        # get actual TCP offset of the robot
        tcp_offset = rtde_c.getTCPOffset()

        # initialize a new position list and copy the original positions into a different list
        new_position = [0, 0, 0, 0, 0, 0]
        joint_position = list(position)

        # add base rotation (somewhere i made an mistake so it is here fixed with a -= instead of a +=)
        joint_position[0] -= global_joint_offset[5]

        # change position to pose. so r1, r2, r3, r4, r5, r6 to x, y, z, rx, ry, rz
        rotated_pose = rtde_c.getForwardKinematics(joint_position, tcp_offset)

        # add xy offset     WATCH OUT: the X of the camera is the Y of the robot
        rotated_pose[0] += global_calibration_offset[1]
        rotated_pose[1] += global_calibration_offset[0]

        if DEBUG_CODE:
            print(f"MoveJ gestart. Nominale positie: {position}")
            print(f"Gekorrigeerde positie: {rotated_pose}")

        rtde_c.moveL(rotated_pose, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")

def move_to_positionj_IK(position, speed=3, acceleration=1.8):
    if initialize_rtde() and rtde_c:
        print(f"MoveJ pose gestart. Nominale positie: {position}")
        rtde_c.moveJ_IK(position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


# Aangepaste move_to_positionj
def move_to_positionj(position, speed=3, acceleration=1.8):
    """
    Voert een gezamenlijke beweging uit.
    OPMERKING: Correcte 6D-kalibratie met moveJ vereist complexe inverse kinematica.
    Voor dit voorbeeld passen we alleen een aangenomen gezamenlijke offset toe
    op de EERSTE TWEE GEWRICHTEN, uitsluitend om de verwerking van de kalibratiedata
    in de bewegingslogica te demonstreren.
    """
    if initialize_rtde() and rtde_c:
        # Haal de aangenomen offset op (dit zou in een echte app de vertaling zijn
        # van de 6D-offset naar een gewrichts-offset voor de huidige configuratie).
        global global_calibration_offset

        # Voor demonstratie: we gebruiken de eerste twee waarden van de 6D offset
        # als EENVOUDIGE GEWRICHTS-OFFSET (dit is theoretisch onjuist voor 6D-kalibratie,
        # maar demonstreert de datastroom).
        joint_offset_1 = global_calibration_offset[0] * 0.001  # Zet mm naar een kleine radiaal-waarde voor demo
        joint_offset_2 = global_calibration_offset[1] * 0.001

        # Maak een nieuwe positielijst met de offsets toegepast
        new_position = list(position)
        #if len(new_position) >= 2:
        #    new_position[0] += joint_offset_1
         #   new_position[1] += joint_offset_2

       # print(f"MoveJ gestart. Nominale positie: {position}")
      #  print(f"Toegepaste offset: J1={joint_offset_1:.6f}, J2={joint_offset_2:.6f}")
       # print(f"Gekorrigeerde positie: {new_position}")
        print(f"MoveJ joints gestart. Nominale positie: {position}")
        rtde_c.moveJ(position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is niet verbonden.")


# Aangepaste move_to_positionj
def move_to_positionjV2(position, speed=3, acceleration=1.8):
    # de commando's die je verstuurd zijn geloof ik geen radialen maar [X, Y, Z, rx, ry, rz], oftewel de tcp. de X, Y, Z zijn in meters en de rx, ry, rz zijn in radialen
    if initialize_rtde() and rtde_c:

        global global_calibration_offset

        # Maak een nieuwe positielijst met de offsets toegepast
        new_position = list(position)
        if len(new_position) >= 2:
            new_position[0] += global_calibration_offset[0]
            new_position[1] += global_calibration_offset[1]
            new_position[2] += global_calibration_offset[2]
            new_position[3] += global_calibration_offset[3]
            new_position[4] += global_calibration_offset[4]
            new_position[5] += global_calibration_offset[5]

        print(f"MoveJ gestart. Nominale positie: {position}")
        print(f"Gekorrigeerde positie: {new_position}")

        rtde_c.moveJ(new_position, speed, acceleration)
    else:
        raise RuntimeError("RTDE control interface is niet verbonden.")


def move_to_positionl(position, speed=3.0, acceleration=1.8):
    if initialize_rtde() and rtde_c:
        print(f"MoveL gestart pose. Nominale positie: {position}")
        rtde_c.moveL(position, 3, 1.8)
    else:
        raise RuntimeError("RTDE control interface is not connected.")

def move_to_positionl_FK(position, speed=3.0, acceleration=1.8):
    if initialize_rtde() and rtde_c:
        print(f"MoveL gestart joint. Nominale positie: {position}")
        rtde_c.moveL_FK(position, 3, 1.8)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


def move_to_positionlV2(position, speed=3.0, acceleration=1.8):
    # de commando's die je verstuurd zijn geloof ik geen radialen maar [X, Y, Z, rx, ry, rz], oftewel de tcp. de X, Y, Z zijn in meters en de rx, ry, rz zijn in radialen
    if initialize_rtde() and rtde_c:

        global global_calibration_offset

        # Maak een nieuwe positielijst met de offsets toegepast
        new_position = list(position)
        if len(new_position) >= 2:
            new_position[0] += global_calibration_offset[0]
            new_position[1] += global_calibration_offset[1]
            new_position[2] += global_calibration_offset[2]
            new_position[3] += global_calibration_offset[3]
            new_position[4] += global_calibration_offset[4]
            new_position[5] += global_calibration_offset[5]

        print(f"MoveJ gestart. Nominale positie: {position}")
        print(f"Gekorrigeerde positie: {new_position}")

        rtde_c.moveL(position, 3, 1.8)
    else:
        raise RuntimeError("RTDE control interface is not connected.")


def get_actual_joint_positions():
    if initialize_rtde() and rtde_r:
        return rtde_r.getActualQ()
    else:
        raise RuntimeError("RTDE receive interface is not connected.")

#------------------------------------------------------------------------------------------------------------------
#nee knop
def ensure_connection():
    """Controleert verbinding en herstart indien nodig."""
    global rtde_c, rtde_connected

    # Check of de interface bestaat en verbonden is
    if rtde_c is None or not rtde_c.isConnected():
        print("Verbinding verbroken, probeert opnieuw te verbinden...")
        disconnect_rtde()  # Eerst netjes afsluiten
        return initialize_rtde()  # Opnieuw opstarten
    return True


def stop_robot_movement():
    """
    Stuurt een stopcommando. Als dit faalt, wordt de verbinding als verbroken beschouwd.
    """
    global rtde_c
    try:
        if rtde_c and rtde_c.isConnected():
            rtde_c.stopJ(2.0)
    except Exception as e:
        print(f"Kon robot niet stoppen (mogelijk al gestopt): {e}")
        # Als stoppen faalt, is de verbinding waarschijnlijk corrupt. Resetten.
        disconnect_rtde()


def move_to_positionj(position, speed=1.0, acceleration=0.5, asynchronous=False):
    """
    Voert een MoveJ uit met automatische 'retry' bij script-crashes.
    """
    global rtde_c, global_calibration_offset, rtde_connected

    # Pas offset toe (jouw bestaande logica)
    new_position = list(position)
    if len(new_position) >= 6 and len(global_calibration_offset) >= 6:
        for i in range(6):
            new_position[i] += global_calibration_offset[i]

    # PROBEER-LUS: We proberen het maximaal 2 keer.
    # 1e keer: Normale poging.
    # 2e keer: Als 1e faalt op 'Script not running', herstarten we en proberen opnieuw.
    for attempt in range(2):
        try:
            # Zorg dat we verbonden zijn
            if not rtde_connected or rtde_c is None or not rtde_c.isConnected():
                print(f"Verbinding herstellen (poging {attempt + 1})...")
                disconnect_rtde()
                if not initialize_rtde():
                    print("Kan geen verbinding maken met robot.")
                    return

            # Voer commando uit
            rtde_c.moveJ(new_position, speed, acceleration, asynchronous)

            # Als we hier komen zonder error, is het gelukt!
            return

        except Exception as e:
            error_msg = str(e)
            print(f"Fout tijdens MoveJ (poging {attempt + 1}): {error_msg}")

            # Check of dit de specifieke 'Script not running' fout is
            if "RTDE control script is not running" in error_msg or "Broken pipe" in error_msg:
                print(">> DETECTIE: Control script is gestopt. Forceer herstart...")
                disconnect_rtde()
                # De lus gaat nu naar attempt 1 (de tweede poging) en zal initialize_rtde() aanroepen
            else:
                # Bij een andere fout (bijv. safety stop), niet opnieuw proberen, gewoon crashen/loggen
                raise e


def is_joint_goal_reached(target_position, tolerance=0.01):
    """
    Checkt of de huidige positie overeenkomt met de target positie.
    Tolerance is in radialen (0.01 rad is ca. 0.5 graad).
    """
    if initialize_rtde() and rtde_r:
        actual_q = rtde_r.getActualQ()

        # Bereken het verschil voor elk gewricht
        diffs = [abs(t - a) for t, a in zip(target_position, actual_q)]

        # Als de grootste afwijking kleiner is dan de tolerantie, zijn we er
        return max(diffs) < tolerance
    return False


def check_joint_limits(target_position):
    # UR limiet is +/- 360 graden (2 PI).
    # We voegen 0.1 rad toe als buffer voor afrondingsfouten.
    limit_rad = (2 * math.pi) + 0.1

    for i, joint_val in enumerate(target_position):
        if abs(joint_val) > limit_rad:
            print(f"Fout: Joint {i} waarde {joint_val:.2f} buiten limiet {limit_rad:.2f}")
            return False
    return True