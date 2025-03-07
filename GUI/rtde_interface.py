import rtde_receive
import rtde_io
from rtde_control import RTDEControlInterface as RTDEControl

# RTDE interfaces (lazy initialization)
rtde_r = None
rtde_c = None
rtde_i = None
rtde_connected = False

def initialize_rtde():
    """Initialize the RTDE interfaces if they have not been initialized yet."""
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
