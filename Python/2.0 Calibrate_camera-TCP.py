from robodk import robomath
from robodk.robolink import *
import time
from camera import get_picture
import numpy as np

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

# Initialize robot
RDK.setRunMode(RUNMODE_RUN_ROBOT)
tool = RDK.Item('Camera', ITEM_TYPE_TOOL)
robot.setPoseTool(tool) #Makes sure the right TCP is used for the move commands
robot.setFrame(RDK.Item('Hoek lastafel'))
robot.setSpeed(400, 15, 30, 10)


def get_offset(target):
    robot.MoveJ(target) #Waits untill movement is finished (Blocking=True by default)
    time.sleep(.5)
    camera_present, offset = get_picture()
    return np.array(offset)

#--- Main Program ---
offset_1 = get_offset(RDK.Item('QR1 -90 graden', ITEM_TYPE_TARGET))
print(offset_1)
offset_2 = get_offset(RDK.Item('QR1 +90 graden', ITEM_TYPE_TARGET))
print(offset_2)

# Calculate the difference between the two measurements
deviation = (offset_1 + offset_2)/2
# Voor een camera TCP die +90 graden geroteerd is over de y-as:
print(f'De camera TCP moet {deviation[0]}mm verschuiven in de Y-richting en {deviation[1]}mm in de Z-richting')