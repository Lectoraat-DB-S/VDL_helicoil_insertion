# This macro can load CSV files from Denso programs in RoboDK.
# Supported types of files are:
#  1-Tool data : Tool.csv
#  2-Work object data: Work.csv
#  3-Target data: P_Var.csv
# This macro can also filter a given targets file

# Type help("robodk.robolink") or help("robodk.robomath") for more information
# Press F5 to run the script
# Visit: http://www.robodk.com/doc/PythonAPI/
# For RoboDK API documentation

import os
import datetime

import tkinter as tk
from tkinter import messagebox

from robodk.robolink import *  # API to communicate with RoboDK
from robodk.robomath import *  # Robot toolbox
from robodk.robodialogs import *
from robodk.robofileio import *
import robodk.robolinkutils as RDKutils

DEBUG = False

debuglist = []

# Start communication with RoboDK
RDK = Robolink()

# Ask the user to select the robot
ROBOT = RDK.ItemUserPick('Select a robot', ITEM_TYPE_ROBOT)

# Check if the user selected a robot
if not ROBOT.Valid():
    quit()

# Ask the user to select a reference frame and get the active tool
BASE = ROBOT.Parent()
# BASE = RDK.Item('UR10e Base', ITEM_TYPE_FRAME)
# BASE = RDK.ItemUserPick('Select robot base frame', ITEM_TYPE_FRAME)
FRAME = RDK.ItemUserPick('Reference Frame', ITEM_TYPE_FRAME)
FRAMEPOSE = RDKutils.getPoseWrt(FRAME, BASE)  # frame pose wrt robot base
TOOL = ROBOT.getLink(ITEM_TYPE_TOOL)
TOOLPOSE = RDKutils.getPoseWrt(TOOL, TOOL.Parent())  # tool pose wrt robot flange

if not FRAME.Valid() or not TOOL.Valid():
    raise Exception("Select appropriate FRAME and TOOL references")


# Function to convert XYZWPR to a pose
# Important! Specify the order of rotation
def xyzwpr_to_pose(xyzwpr):
    x, y, z, rx, ry, rz = xyzwpr
    return point_Zaxis_2_pose([x, y, z], [-rx, -ry, -rz])
    # return transl(x, y, z) * rotz(rz * pi / 180) * roty(ry * pi / 180) * rotx(rx * pi / 180)
    # return transl(x,y,z)*rotx(rx*pi/180)*roty(ry*pi/180)*rotz(rz*pi/180)
    # return KUKA_2_Pose(xyzwpr)


# csv_file = 'C:/Users/Albert/Desktop/Var_P.csv'
csv_file = getOpenFileName(RDK.getParam('PATH_OPENSTATION'))

# Specify file codec
codec = 'utf-8'  # 'ISO-8859-1'


# Load P_Var.CSV data as a list of poses, including links to reference and tool frames
def load_targets(strfile):
    csvdata = LoadList(strfile, ',', codec)
    poses = []
    idxs = []
    for i in range(0, len(csvdata)):
        x, y, z, rx, ry, rz = csvdata[i][0:6]
        poses.append(xyzwpr_to_pose([x, y, z, rx, ry, rz]))
        # idxs.append(csvdata[i][6])
        idxs.append(i)

    return poses, idxs


# Load and display Targets from P_Var.CSV in RoboDK
def make_targets(strfile):
    poses, idxs = load_targets(strfile)
    program_name = getFileName(strfile)
    program_name = program_name.replace('-', '_').replace(' ', '_')

    for pose, idx in zip(poses, idxs):
        name = 'H-%s-%i' % (program_name, idx)
        target = RDK.Item(name, ITEM_TYPE_TARGET)
        if target.Valid():
            target.Delete()
        target = RDK.AddTarget(name, FRAME, ROBOT)

        target.setPose(pose)
        collision_free(target, idx)


def test_all_configurations(configurations):
    for joints in configurations:

        # turn collision checking off
        RDK.setCollisionActive(COLLISION_OFF)

        # move to target
        try:
            ROBOT.MoveJ(joints)
        except TargetReachError:
            continue

        # turn collision checking on, test for collisions
        RDK.setCollisionActive(COLLISION_ON)

        collision = RDK.Collisions()
        print(f"collision: {collision}")
        debuglist.append(f"collision: {collision}")

        collision_items = RDK.CollisionItems()
        if TOOL in collision_items or collision == 0:
            break

    try:
        collision
    except NameError:
        collision = -2
        print("Target cannot be reached or is to close to a singularity")
        debuglist.append("Target cannot be reached or is to close to a singularity")

    return collision


def test_collision_target(target, rz):
    if DEBUG:
        print("testing at target")
        debuglist.append("testing at target")

    possible_robot_configurations = ROBOT.SolveIK_All(target.Pose(), tool=TOOLPOSE, reference=FRAMEPOSE)
    issues_value = test_all_configurations(
        possible_robot_configurations)  # returns 0 if at least one configuration is without issues

    return issues_value


def test_issues_point(target, rz, flip_approach=False):
    if DEBUG:
        print("testing point")
        debuglist.append("testing point")

    # Get the original pose
    original_pose = target.Pose()

    # For vertical walls, we might need to completely flip the approach
    if flip_approach:
        # Rotate 180 degrees around Y axis (assuming Y is the axis parallel to the wall)
        # This effectively approaches from the opposite direction
        target_new_pose = RelTool(original_pose, 0, 0, 0, 0, 0, 0)  # even aangepast naar 0
        # Then apply the requested Z rotation
        target_new_pose = RelTool(target_new_pose, 0, 0, 0, 0, 0, rz)
    else:
        # Standard rotation around Z axis only
        target_new_pose = RelTool(original_pose, 0, 0, 0, 0, 0, rz)

    possible_robot_configurations = ROBOT.SolveIK_All(target_new_pose, tool=TOOLPOSE, reference=FRAMEPOSE)
    issues_value = test_all_configurations(possible_robot_configurations)

    return issues_value, target_new_pose


rotation_direction = "pos"
direction_changes = 0
holes_no_solution = []


def collision_free(target, idx):
    rotation_step = 10  # was 30
    repmax = 360 / rotation_step
    global rotation_direction
    global direction_changes
    s = 0
    rep = 0

    print(f"\nHole {idx}")
    debuglist.append(f"\nHole {idx}")

    # First try the original approach
    issues_value, target_new_pose = test_issues_point(target, 0, flip_approach=False)

    # If there's a collision, try different approaches
    while issues_value != 0 and s < 100:
        print(f"s before: {s}")
        debuglist.append(f"s before: {s}")
        print(f"rep: {rep}")
        debuglist.append(f"rep: {rep}")
        print(f"rotation direction: {rotation_direction}")
        debuglist.append(f"rotation direction: {rotation_direction}")
        print(f"direction changes: {direction_changes}")
        debuglist.append(f"direction changes: {direction_changes}")

        s += 1

        # For unreachable targets or potential vertical wall collision situations
        if issues_value == -2 and direction_changes < 2:
            if rotation_direction == "pos":
                rotation_direction = "neg"
                direction_changes += 1
                r = -1
            else:
                rotation_direction = "pos"
                direction_changes += 1
                r = 1

            # Try the opposite approach direction if we've changed direction once already
            # This is key for vertical walls
            if direction_changes >= 1:
                issues_value, target_new_pose = test_issues_point(target, r * rotation_step, flip_approach=True)
            else:
                issues_value, target_new_pose = test_issues_point(target, r * rotation_step, flip_approach=False)

            target.setPose(target_new_pose)

        # For collision situations, rotate around Z
        elif issues_value > 0 and rep < repmax:
            RDK.setCollisionActive(COLLISION_OFF)  # collision off

            ROBOT.MoveJ(target.Pose())

            if rotation_direction == "neg":
                r = -1
            elif rotation_direction == "pos":
                r = 1

            # After trying several rotations, try the flip approach
            if rep > repmax / 2:
                issues_value, target_new_pose = test_issues_point(target, r * rotation_step, flip_approach=True)
            else:
                issues_value, target_new_pose = test_issues_point(target, r * rotation_step, flip_approach=False)

            target.setPose(target_new_pose)
            rep += 1

        elif direction_changes >= 2 or rep >= repmax:
            break

        else:
            RDK.ShowMessage(f"Unknown error occured at Hole {idx} while looking for collision free position")

    direction_changes = 0
    if issues_value == 0:
        print(f"No issues at Hole {idx}")
        debuglist.append(f"No issues at Hole {idx}")
    elif direction_changes >= 2 or rep >= repmax or s >= 100:
        RDK.ShowMessage(f"No solution found for Hole {idx}", False)
        holes_no_solution.append(idx)

        print(f"No solution found for Hole {idx}")
        debuglist.append(f"No solution found for Hole {idx}")

    else:
        RDK.ShowMessage(f"Unknown error occured at Hole {idx} while looking for collision free position")

        print(f"Unknown error occured at Hole {idx} while looking for collision free position")
        debuglist.append(f"Unknown error occured at Hole {idx} while looking for collision free position")


MAKE_GUI_PROGRAM = True

ROBOT.setFrame(FRAME)
ROBOT.setTool(TOOL)

if RDK.RunMode() == RUNMODE_SIMULATE:
    MAKE_GUI_PROGRAM = True
    # MAKE_GUI_PROGRAM = mbox('Do you want to create a new program? If not, the robot will just move along the targets', 'Yes', 'No')
else:
    # if we run in program generation mode just move the robot
    MAKE_GUI_PROGRAM = False

if MAKE_GUI_PROGRAM:
    RDK.Render(False)  # Faster if we turn render off
    make_targets(csv_file)
else:
    l

if len(holes_no_solution) != 0:
    RDK.ShowMessage(f"Holes without solution: {holes_no_solution}")

if DEBUG:
    print(f"Holes without solution: {holes_no_solution}")
    debuglist.append(f"Holes without solution: {holes_no_solution}")

    current_time = datetime.datetime.now()
    filename = os.path.splitext(os.path.basename(__file__))
    with open("C:/Users/Laura/Documents/1.Windesheim/Stage/2024/Lectoraat/Deelvragen/2.Targets maken/debugfile.txt",
              "a") as file:
        file.write("\n\n-----------------------------------------------\n")
        file.write(current_time.strftime("%c"))
        file.write("\n-----------------------------------------------\n")
        for prints in debuglist:
            file.write(prints)
            file.write("\n")
        file.write(holes_no_solution)
        file.write(filename[0])
