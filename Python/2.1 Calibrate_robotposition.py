from robodk import robomath
from robodk.robolink import *
import math
import time
from camera import get_picture

# SETTINGS
twopoint_calibration = True         #Two QR-codes will be scanned when enabled for higher accuracy
move_robot = True                   #The program will be run on the real robot when enabled
Update_robotbase = True             #The position of the robotbase will be updated in RoboDK when enabled
move_to_calibration_check = True   #The robot will move to a given point halfway the QR-codes for a visual check of the calibration accuracy
DEBUG_CODE = True

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

# Initialize robot
if move_robot:
    RDK.setRunMode(RUNMODE_RUN_ROBOT)
robot.setPoseTool(RDK.Item('Camera', ITEM_TYPE_TOOL)) # Makes sure the right TCP is used for the move commands
robot.setFrame(RDK.Item('Hoek lastafel', ITEM_TYPE_FRAME))
robot.setSpeed(200, 10, 30, 10) #setSpeed(speed_linear, speed_joints, accel_linear, accel_joints)

# Import the points used to calculate the offset of the robotbase
QR1 = RDK.Item('QR1', ITEM_TYPE_TARGET)
QR2 = RDK.Item('QR2', ITEM_TYPE_TARGET)
robotbase = RDK.Item('UR10e Base', ITEM_TYPE_FRAME)

# function to measure the offsets
def get_offset(target):
    if target.Name() == 'QR2':
        robot.MoveL(target)
    else:
        robot.MoveJ(target) # Waits untill movement is finished (Blocking=True by default)
    time.sleep(1)
    camera_present, offset_local = get_picture()
    # Convert offset to global coordinates, regardless the orientaten of the target
    # This works only for multiples of 90 degrees yet
    offset_local[1] = -offset_local[1] # Mirror the coordinate system to get the X and Y axis right
    xyzwpr = robomath.Pose_2_Fanuc(target.PoseAbs())
    rotation = math.radians(xyzwpr[5]-90) # The rotation of the target with respect to the global reference frame
    offset_global = [offset_local[0]*robomath.cos(rotation) - offset_local[1]*robomath.sin(rotation), offset_local[1]*robomath.cos(rotation) + offset_local[0]*robomath.sin(rotation)]
    if DEBUG_CODE:
        print(f'offset {target.Name()} = {offset_global}')   
    return offset_global, offset_local[2]-rotation
    # For higher accuracy the offset needs to be rotated with the measured RZ

# Measure the offsets
A = QR1.PoseAbs().Pos()
B = QR2.PoseAbs().Pos()
C = robotbase.PoseAbs().Pos()
offset_A, RZ = get_offset(QR1)
if twopoint_calibration:
    offset_B, RZ = get_offset(QR2)
    angle_AB = math.atan2(B[1] - A[1], B[0] - A[0])
    angle_ApBp = math.atan2(B[1] + offset_B[1] - A[1] - offset_A[1], B[0] +  offset_B[0] - A[0] - offset_A[0])
    RZ = angle_ApBp - angle_AB #overwrites the RZ value
if DEBUG_CODE:
    print(f'RZ = {RZ}')

# CALCULATE OFFSET OF robotbase (offset_C)
AC = [C[0]-A[0], C[1]-A[1]] # vector AC
AC_polar = [math.dist(C, A), math.atan2(AC[1], AC[0])]
ApCp_polar = [AC_polar[0], AC_polar[1] + RZ]
ApCp = [ApCp_polar[0]*math.cos(ApCp_polar[1]), ApCp_polar[0]*math.sin(ApCp_polar[1])]
offset_C = [offset_A[0] + ApCp[0] - AC[0], offset_A[1] + ApCp[1] - AC[1]]
print(f'offset robotbase = {offset_C}')

# Compute new position of robot base
new_robotbase_rotated = robotbase.PoseAbs() * robomath.rotz(RZ) #Rotation in own reference frame
new_robotbase = robomath.transl(offset_C[0], offset_C[1], 0) * new_robotbase_rotated #Translation in global reference frame
if Update_robotbase:
    robotbase.setPose(new_robotbase)
# The rotation and translation can be calcaluted alternatively in the reference frame of the QR-code (point A): old_robotbase = QR1.Poseabs().inv() * robotbase.PoseAbs()
# That makes the calculation of offset_c redundant

RDK.Render()

if move_to_calibration_check:
    tool = RDK.Item('pointer', ITEM_TYPE_TOOL)
    robot.setPoseTool(tool) #Makes sure the right TCP is used for the move commands
    robot.MoveJ(RDK.Item('Check calibration 1', ITEM_TYPE_TARGET))


