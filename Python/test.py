from robodk import robomath
from robodk.robolink import *
import math

QR_Postiion = [-101.47, -121.57, 102.82, 18.74, 78.53, -90]


# 1. Initialize API
RDK = Robolink()

# 2. Identify the robot and its base frame
robot = RDK.Item('', ITEM_TYPE_ROBOT)
base_frame = robot.Parent()

# Move to calibration position
robot.MoveJ(QR_Postiion)


# 3. Get the current Pose (4x4 Matrix)
current_pose = base_frame.Pose()

# 4. Define your offset
# transl(x, y, z) * rotx(angle_rad) * roty... etc.
#offset = robomath.transl(-100, 0, 0) * robomath.rotz(-45 * math.pi / 180)

# 5. Calculate the new pose
# Current * Offset = Relative to the frame's own axes
# Offset * Current = Relative to the Station (World) axes
new_pose = current_pose * offset

# 6. Apply the change
base_frame.setPose(new_pose)

print("Base frame offset applied.")