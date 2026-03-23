from robodk import robomath
from robodk.robolink import *
import math
from camera import get_picture

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

# Get target waypoint
target = RDK.Item('Camera Calibration', ITEM_TYPE_TARGET)

# UNTESTED CODE ###########
if robot.Connect():
    real_joints = robot.Joints()
    target_joints = target.Joints()
    joint_error = robomath.norm(real_joints - target_joints)
    tolerance = 0.1
    if joint_error < tolerance:
        print(f"Success: Real robot is at waypoint. Error: {joint_error:.4f}")
    else:
        print(f"Warning: Real robot is NOT at waypoint. Error: {joint_error:.4f}")
        print("Real Joints:", real_joints.tolist())
        print("Target Joints:", target_joints.tolist())
else:
    print("Could not connect to the physical robot to verify position.")
# END OF UNTESTED CODE ###########

# Get baseframe of robot
baseframe = RDK.Item('UR10e Base', ITEM_TYPE_FRAME) #get baseframe of robot
baseframe_pose = baseframe.Pose()

# Get camera data and compute offset
camera_present, my_movement = get_picture()
#my_movement = [50, 50, 0] # Debug values

print(my_movement)
offset = robomath.transl(-my_movement[0], my_movement[1], 0) * robomath.rotz(my_movement[2])

# Compute new position of robot base
new_baseframe = baseframe_pose * offset
print(baseframe_pose)
print(new_baseframe)

baseframe.setPose(new_baseframe)

#move robot to updated position
robot.MoveJ(target)
RDK.Render()


