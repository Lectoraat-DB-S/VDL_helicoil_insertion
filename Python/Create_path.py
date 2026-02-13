import csv
import os
import tkinter as tk
from tkinter import filedialog
from robodk import robolink, robomath
RDK = robolink.Robolink()
'''
Enable CUDA for Collision Checking: If you have an NVIDIA GPU, you can leverage CUDA cores to speed up collision detection. Go to Tools > Options > Display and switch Collision checking hardware to CUDA.
'''

# SET THIS TO TRUE IF YOUR CSV DATA IS RELATIVE TO THE STATION ORIGIN (0,0,0)
USE_GLOBAL_COORDINATES = False 
USE_FIXED_FILEPATHS = False 
USE_RENDER = True
CREATE_PATH = True

#For creating paths, create a map first. Add selected targets to help the motion planner
start_location = 'Bovenpickup'
Part_Frame = 'CSV Frame'
dRot = 10 #rotational resolution for Rz attempts
target_offset = 50 #offset with respect to hole position

#Set robot joint limits (important for performance in mapping)
lower_limits = [-180, -100, -30, -180, -180, -180]
upper_limits = [ 0,  0,  180,  180,  180,  180]


def get_roboDKproject_path():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    if USE_FIXED_FILEPATHS:
        path = r'C:/Users/qr0125816/Documents/GitHub/VDL_helicoil_insertion/RoboDK/Program_VDL_Testobject_AMR_mapped.rdk'
    else:
        path = filedialog.askopenfilename(title="Select RoboDK project", filetypes=[("RDK", "*.rdk")])
    root.destroy()
    return path

def get_file_path():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    if USE_FIXED_FILEPATHS:
        path = r'C:/Users/qr0125816/Documents/GitHub/VDL_helicoil_insertion/Pre-processor/hole_analysis.csv'
    else:
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV", "*.csv")])
    root.destroy()
    return path

def create_grouped_targets():
    csv_path = get_file_path()
    if not csv_path: return
    
    # Path for the unsuccessful targets file
    failed_csv_path = csv_path.replace('.csv', '_failed.csv')

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames # Capture original headers
            data = list(reader)
    except Exception as e:
        RDK.ShowMessage(f"Error reading CSV: {str(e)}", False)
        return

    # Select robot and tool
    robot = None
    selection = RDK.Selection()
    for item in selection:
        if item.Type() == robolink.ITEM_TYPE_ROBOT:
            robot = item
            break
    
    if robot is None or not robot.Valid():
        robot = RDK.Item('', robolink.ITEM_TYPE_ROBOT)
    else:
        # Convert lists to strings separated by commas (RoboDK requirement)
        lower_str = ", ".join(map(str, lower_limits))
        upper_str = ", ".join(map(str, upper_limits))

        # Set the parameters
        robot.setParam("JointLimitsLow", lower_str)
        robot.setParam("JointLimitsHigh", upper_str)


    tool = None
    for item in selection:
        if item.Type() == robolink.ITEM_TYPE_TOOL:
            tool = item
            break
    
    if tool is None or not robot.Valid():
        tool = RDK.Item('', robolink.ITEM_TYPE_TOOL)

    # Get part frame
    if USE_FIXED_FILEPATHS:
        master_frame = RDK.Item(Part_Frame, robolink.ITEM_TYPE_FRAME)
    else:
        master_frame = RDK.ItemUserPick("Select the Part Reference Frame", robolink.ITEM_TYPE_FRAME)
        if not master_frame.Valid(): return
    
    type_frames = {}
    # Create new program
    prog = RDK.AddProgram('CollisionFreeProg', robot)

    # Open the failed targets CSV for writing
    with open(failed_csv_path, mode='w', newline='', encoding='utf-8') as f_failed:
        writer = csv.DictWriter(f_failed, fieldnames=fieldnames)
        writer.writeheader()

        RDK.Render(False)

        for row in data:
            target_type = row['Type'].strip()
            target_name = f"{target_type}_{row['Instance'].strip()}"
            
            if target_type not in type_frames:
                group_frame = RDK.Item(target_type, robolink.ITEM_TYPE_FRAME)
                if not group_frame.Valid():
                    group_frame = RDK.AddFrame(target_type, master_frame)
                group_frame.setPose(robomath.eye(4))
                type_frames[target_type] = group_frame
            
            current_parent = type_frames[target_type]

            # 1. Get position and direction vector
            pos = [float(row['PosX']), float(row['PosY']), float(row['PosZ'])]
            direction = [float(row['DirX']), float(row['DirY']), float(row['DirZ'])]
            length = float(row['Length'])

            # 2. Setup orientations (Primary and Mirrored)
            z_axis_primary = robomath.normalize3(direction)
            offset_pos_primary = [pos[i] - direction[i] * (0.5 * length + target_offset) for i in range(3)]

            z_axis_secondary = [-z for z in z_axis_primary]
            offset_pos_secondary = [pos[i] + direction[i] * (0.5 * length + target_offset) for i in range(3)]
            
            orientations_to_try = [
                (z_axis_primary, offset_pos_primary, "Primary"),
                (z_axis_secondary, offset_pos_secondary, "Mirrored")
            ]

            success = False 
            target = RDK.AddTarget(target_name, current_parent)

            for z_axis, offset_pos, label in orientations_to_try:
                # Build the orientation matrix
                if abs(z_axis[0]) < 0.9:
                    x_axis = robomath.normalize3(robomath.cross([1, 0, 0], z_axis))
                else:
                    x_axis = robomath.normalize3(robomath.cross([0, 1, 0], z_axis))
                y_axis = robomath.cross(z_axis, x_axis)
                
                mat = robomath.Mat([
                    [x_axis[0], y_axis[0], z_axis[0], offset_pos[0]],
                    [x_axis[1], y_axis[1], z_axis[1], offset_pos[1]],
                    [x_axis[2], y_axis[2], z_axis[2], offset_pos[2]],
                    [0, 0, 0, 1]
                ])

                if USE_GLOBAL_COORDINATES:
                    target.setPoseAbs(mat)
                else:
                    target.setPose(mat)

                # --- REACHABILITY & COLLISION CHECK ---
                target_pose_abs = target.PoseAbs()
                robot_base_abs = robot.PoseAbs()
                tool_pose = robot.PoseTool()

                for angle_deg in range(0, 360, dRot):
                    rotation_z = robomath.rotz(angle_deg * robomath.pi / 180.0)
                    pose_rel_robot = (robot_base_abs.inv() * target_pose_abs) * rotation_z
                    
                    all_solutions = robot.SolveIK_All(pose_rel_robot, tool=tool_pose)
                    n_sols = all_solutions.size(1)

                    for i in range(n_sols):
                        joints_sol = all_solutions[:, i]
                        if joints_sol is not None and len(joints_sol.rows) > 0:
                            robot.setJoints(joints_sol)
                            if RDK.Collisions() == 0:
                                # Convert to Joint Target and save
                                target.setAsJointTarget()
                                target.setJoints(joints_sol)
                                 
                                #Create a robot path 

                                if CREATE_PATH:
                                    success = create_robot_path(robot,target, prog)
                                    break
                                else:
                                    success = True
                                    break 
                    if success: break
                if success: break 

            # Handle failed solutions
            if not success:
                print(f"FAILED: {target_name} - writing to log and deleting.")
                writer.writerow(row) # Save original data to failed CSV
                target.Delete()      # Remove from RoboDK tree
            
            if USE_RENDER: RDK.Render(True)

    RDK.ShowMessage(f"Done! Failed targets logged to:\n{failed_csv_path}", False)

def create_robot_path(robot,target,prog):
    RDK.PluginCommand("PathPlanner", "IsInitialized")
    target_start = RDK.Item(start_location, robolink.ITEM_TYPE_TARGET)
    robot.setJoints(target_start.Joints())
    
    try:
        robot.setParam("Connect", "1")
        robot.MoveJ(target)
        prog.MoveJ(target_start)
        prog.MoveJ(target)

        print("Path found and move completed successfully.")
        success = True
    except Exception as e:
        print(f"Movement failed: {e}") # Good practice to log the error
        success = False
    return success


def check_map():
    prm_stats = RDK.Command("CheckRoadmap")
    if "0 nodes" in prm_stats or not prm_stats:
        print("No map available. You need to generate the motion planner map first.")
        raise Exception("No map available for path generation")
    else:
        print(f"Map found")
        prm_info = RDK.PluginCommand("CollisionFreePlanner", "Info")
        if prm_info:
            samples, edges, robot_name = prm_info.split('-')
            print(f"Robot: {robot_name}")
            print(f"Number of Samples: {samples}")
            print(f"Number of Edges: {edges}")


if __name__ == "__main__":
    RDKproject_path = get_roboDKproject_path()
    station = RDK.AddFile(RDKproject_path)
    if CREATE_PATH: check_map()

    if station.Valid():
        print("Project loaded successfully!")
        create_grouped_targets()
    else:
        print("Failed to load the project.")