from robodk import robomath
from robodk.robolink import *
from camera import get_picture_hole

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

#Get the offset of the hole at a distance of 200mm
hole_offset = get_picture_hole(200)
print('Return values:')
print(hole_offset)

# Calculate the new position
current_pose = robot.Pose()
new_pose = current_pose * robomath.transl(hole_offset[1], -hole_offset[0],0)# POST-MULTIPLY to apply the change in the local coordinate system

# Update the target's pose in RoboDK
RDK.Item('Hole calibrated', ITEM_TYPE_TARGET).setPose(new_pose)