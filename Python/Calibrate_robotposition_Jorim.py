from robodk import robomath
from robodk.robolink import *
import math
import time
from camera import get_picture

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

#SETTINGS
twopoint_calibration = True
move_robot = True
Update_baseframe = True
move_to_calibration_check = True
DEBUG_CODE = True
if move_robot:
    RDK.setRunMode(RUNMODE_RUN_ROBOT)


# IMPORT TARGET WAYPOINTS
QR1 = RDK.Item('Camera Calibration', ITEM_TYPE_TARGET)
QR1_local = QR1.Pose()
QR1_global = QR1.PoseAbs()
QR1_global_pos = QR1_global.Pos()

QR2 = RDK.Item('Camera 2', ITEM_TYPE_TARGET)
QR2_local = QR2.Pose()
QR2_global = QR2.PoseAbs()
QR2_global_pos = QR2_global.Pos()

baseframe = RDK.Item('UR10e Base', ITEM_TYPE_FRAME)
baseframe_pose = baseframe.Pose()
baseframe_pos = baseframe_pose.Pos()

# X,Y coordinates of the points used to calculate the offset of the baseframe
A = QR1_global_pos[0:2]
B = QR2_global_pos[0:2]
C = baseframe_pos[0:2]

# MEASURE OFFSETS
tool = RDK.Item('Camera', ITEM_TYPE_TOOL)
robot.setPoseTool(tool) #Makes sure the right TCP is used for the move commands
robot.setSpeed(200, 50, 30, 10)

def get_offset(QR):
    robot.MoveJ(QR) #Waits untill movement is finished (Blocking=True by default)
    time.sleep(1)
    camera_present, offset = get_picture()
    offset[1] = -offset[1] #convert to the right coordinate system (global coordinates if rotation=0)
    #convert offset to the global coordinate system, regardless of the camera pose
    #This works only for right angles yet
    xyzwpr = robomath.Pose_2_Fanuc(QR.Pose())
    rotation = math.radians(xyzwpr[5])
    #print(f'rotation = {math.degrees(rotation)}')
    offset_x = [offset[0]*robomath.cos(rotation) - offset[1]*robomath.sin(rotation), offset[1]*robomath.cos(rotation) + offset[0]*robomath.sin(rotation)]
    if DEBUG_CODE:
        print(f'offset {QR.Name()} = {offset_x}')   
    return offset_x, offset[2]-rotation
    

offset_A, RZ = get_offset(QR1)
if twopoint_calibration:
    offset_B, RZ = get_offset(QR2)
    angle_AB = math.atan2(B[1] - A[1], B[0] - A[0])
    angle_ApBp = math.atan2(B[1] + offset_B[1] - A[1] - offset_A[1], B[0] +  offset_B[0] - A[0] - offset_A[0])
    RZ = angle_ApBp - angle_AB #overwrites the RZ value
if DEBUG_CODE:
    print(f'RZ = {RZ}')

#CALCULATE OFFSET OF BASEFRAME (offset_C)
AC = [C[0]-A[0], C[1]-A[1]] #vector AC
AC_polar = [math.dist(C, A), math.atan2(AC[1], AC[0])]
ApCp_polar = [AC_polar[0], AC_polar[1] + RZ]
ApCp = [ApCp_polar[0]*math.cos(ApCp_polar[1]), ApCp_polar[0]*math.sin(ApCp_polar[1])]
offset_C = [offset_A[0] + ApCp[0] - AC[0], offset_A[1] + ApCp[1] - AC[1]]
print(f'offset_C = {offset_C}')

# Compute new position of robot base
new_baseframe_rotated = baseframe_pose * robomath.rotz(RZ) #Rotation in own reference frame
new_baseframe = robomath.transl(offset_C[0], offset_C[1], 0) * new_baseframe_rotated #Translation in global reference frame
#print(new_baseframe)

if Update_baseframe:
    baseframe.setPose(new_baseframe)

#targets updaten naar Cartesian Targets
program = RDK.Item('main', ITEM_TYPE_PROGRAM)
frame = RDK.Item('Type 13', ITEM_TYPE_FRAME)
all_targets = RDK.ItemList(ITEM_TYPE_TARGET)
for target in all_targets:
    # Verify if the target is a child of the specified frame
    if target.Parent().Name() == frame.Name():
        target.setAsCartesianTarget()
program.setParam("RecalculateTargets")

RDK.Render()

if move_to_calibration_check:
    tool = RDK.Item('pointer', ITEM_TYPE_TOOL)
    robot.setPoseTool(tool) #Makes sure the right TCP is used for the move commands
    robot.MoveJ(RDK.Item('Check calibration 1', ITEM_TYPE_TARGET))


