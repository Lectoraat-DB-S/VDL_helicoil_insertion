from robodk import robomath
from robodk.robolink import *
import time
from camera import get_picture_hole
import tkinter as tk
from tkinter import messagebox
import requests

# Settings
run_on_robot = True         # Set to False if you want to simulate only
Run_main_program = True     # Set to False if you don't want to run the main program, but test something else instead
test_aanvoer = False
DEBUG_CODE = False

# Initialize API
RDK = Robolink()
robot = RDK.Item('', ITEM_TYPE_ROBOT)

# Screwdriver data
compute_box_ip = "192.168.12.15"
username = "admin"
password = "OnRobotPerron038"
tool_id = 0  # ID of the tool

# Robot settings
if run_on_robot:
    RDK.setRunMode(RUNMODE_RUN_ROBOT)
    robot.setSpeed(100, 20, 100, 40) #setSpeed(speed_linear, speed_joints, accel_linear, accel_joints)

# ---Functions of the main program---

def run_generated_program(program_name):
    program = RDK.Item(program_name, ITEM_TYPE_PROGRAM)
    if run_on_robot:
        program.setRunType(PROGRAM_RUN_ON_ROBOT)
    else:
        program.setRunType(PROGRAM_RUN_ON_SIMULATOR)
    program.RunCode()
    program.WaitFinished()

def scan_hole(target):
    # Move robot to take a picture
    robot.setPoseTool(RDK.Item('Camera', ITEM_TYPE_TOOL))
    robot.setFrame(RDK.Item('CSV Frame'))
    robot.MoveL(target)

    # Take picture and measure the offset
    camera_TCP = RDK.Item('Camera', ITEM_TYPE_TOOL).PoseTool().Pos()
    camera_distance = camera_TCP[0]-104
    hole_offset = get_picture_hole(camera_distance)
    print(f'Hole offset = {hole_offset}')

    # Update the target
    current_pose = robot.Pose()
    new_pose = current_pose * robomath.transl(hole_offset[1], -hole_offset[0],0)# POST-MULTIPLY to apply the change in the local coordinate system
    RDK.Item('Hole calibrated', ITEM_TYPE_TARGET).setPose(new_pose)

    # Move robot to the updated target
    robot.setPoseTool(RDK.Item('indraaien', ITEM_TYPE_TOOL))
    robot.MoveL(RDK.Item('Hole calibrated', ITEM_TYPE_TARGET))

def pickup_helicoil():
    robot.MoveJ(RDK.Item('boven pick-up')) # No need to set frame and tool as only joint targets are used
    shaft_value = 0
    shank_url =  f"http://{compute_box_ip}/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    requests.get(shank_url, auth=(username, password))

    #Get and clamp helicoil
    if robot.getDI(0) == '0.000000': #This part will be passed if there is a helicoil in the holder when starting the program
        #Move actuator in
        robot.setDO(4, 0)
        robot.setDO(2, 1)
        time.sleep(4)
        #trigger feeder
        robot.setAO(0, 0.4)
        while robot.getDI(1) != '1.000000':
            time.sleep(.05)
        time.sleep(.3)
        robot.setAO(0, 0)
    #robot.waitDI(0, '1.000000')
    #time.sleep(0.5)
    time.sleep(1)
    robot.setDO(2, 0)
    robot.setDO(4, 1)
    time.sleep(5)

    # Screw in helicoil
    robot.MoveL(RDK.Item('pick-up'))
    shank_force = 20 #shank force
    screw_length = 16.5 #helicoil length
    max_torque = 0.3 #max torque untill stopping screw motion via default premount behavior
    tighten_url = f"http://{compute_box_ip}/api/dc/sd/tighten/{tool_id}/{shank_force}/{screw_length}/{max_torque}"
    requests.get(tighten_url, auth=(username, password))
    time.sleep(12)
    shaft_value = 27
    shank_url =  f"http://{compute_box_ip}/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    requests.get(shank_url, auth=(username, password))
    time.sleep(4)

    # Open clamp and retract tool
    robot.setDO(4, 0)
    robot.setDO(2, 1) 
    time.sleep(.2)
    robot.setDO(2, 0)
    robot.MoveL(RDK.Item('unclamped'))
    shaft_value = 0
    shank_url =  f"http://{compute_box_ip}/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    requests.get(shank_url, auth=(username, password))
    robot.MoveL(RDK.Item('boven pick-up')) 


def insert_helicoil():
    """
    root = tk.Tk()
    root.withdraw() # Hide the main tkinter window
    messagebox.showinfo("Notification", "Is the tool aligned with the hole?")
    root.destroy()
    """

    # Insert helicoil
    shank_force = 20 #shank force
    screw_length = 20 #helicoil length
    max_torque = 2.0 #max torque untill stopping screw motion via default premount behavior
    tighten_url = f"http://{compute_box_ip}/api/dc/sd/tighten/{tool_id}/{shank_force}/{screw_length}/{max_torque}"
    requests.get(tighten_url, auth=(username, password))
    time.sleep(13)

    # Unscrew tool
    shank_force = 20 #shank force
    unscrewing_length_mm = 20
    unscrew_url = f"http://{compute_box_ip}/api/dc/sd/loosen/{tool_id}/{shank_force}/{unscrewing_length_mm}"
    requests.get(unscrew_url, auth=(username, password))
    time.sleep(8)

    # Retract shank
    shaft_value = 0
    shank_url =  f"http://{compute_box_ip}/api/dc/sd/move_shank/{tool_id}/{shaft_value}"
    requests.get(shank_url, auth=(username, password))
    time.sleep(2)


# Get all the hole locations
holes = [target for target in RDK.ItemList(ITEM_TYPE_TARGET) if target.Name().startswith('Type ') and target.Parent().Parent().Name() == 'CSV Frame' and target.Visible()]
if DEBUG_CODE:
    for target in holes:
        print(target.Name())

# --- Main Program ---
if Run_main_program:
    for target in holes:
        pickup_helicoil()
        # Move to the hole
        program_name = f'bovenpickupTo{target.Name().replace(" ", "").replace("_", "")}'
        run_generated_program(program_name)
        scan_hole(target)
        time.sleep(10)
        insert_helicoil()
        # Move back to the pickup location
        program_name = f'{target.Name().replace(" ", "").replace("_", "")}Tobovenpickup'
        run_generated_program(program_name)

# Test aanvoer
while test_aanvoer:
    robot.setAO(0, 0.4)
    while robot.getDI(1) != '1.000000':
        time.sleep(.02)
    time.sleep(.2)
    robot.setAO(0, 0)
    time.sleep(5)