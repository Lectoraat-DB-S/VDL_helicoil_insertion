from robodk import robomath
from robodk.robolink import *
import math
from camera import get_picture

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

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
target = RDK.Item('Camera Calibration', ITEM_TYPE_TARGET)
robot.MoveJ(target)
RDK.Render()


