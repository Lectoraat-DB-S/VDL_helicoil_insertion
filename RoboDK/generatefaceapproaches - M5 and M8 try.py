from robodk.robolink import *  # API to communicate with RoboDK
from robodk.robomath import *  # Robot toolbox
import robodk.robolinkutils as RDKutils
from robodk import robolink

DEBUG = False

# Link to RoboDK
RDK = Robolink()

# --- INITIAL SETUP ---
# Get user-selected robot and reference frame
ROBOT = RDK.ItemUserPick('Select a Robot', ITEM_TYPE_ROBOT)
FRAME = RDK.ItemUserPick('Reference Frame', ITEM_TYPE_FRAME)

if not ROBOT.Valid() or not FRAME.Valid():
    raise Exception("Select an appropriate ROBOT and FRAME to continue.")

# Get tool and all targets named with "H"
TOOL = ROBOT.getLink(ITEM_TYPE_TOOL)
All_items = RDK.ItemList(ITEM_TYPE_TARGET)
RDK_items = [item for item in All_items if "H" in item.Name()]  # Filter for H-8 and H-5

print(f"Found {len(RDK_items)} total holes to process.")

# Ensure collision checking is off for initial setup
RDK.setCollisionActive(COLLISION_OFF)


def print_xyzrpw(pose):
    """Helper function to print pose coordinates."""
    x, y, z, rx, ry, rz = pose_2_xyzrpw(pose)
    print(f"x:{x:.2f}, y:{y:.2f}, z:{z:.2f}, rx:{rx:.2f}, ry:{ry:.2f}, rz:{rz:.2f}")


# --- DATA STRUCTURES ---
class Hole:
    """Represents a single hole, storing its pose, target, and type (m8/m5)."""

    def __init__(self, pose, target):
        self.pose = pose
        self.target = target
        self.name = self.target.Name()

        # ** NEW: Determine hole type based on its name **
        if "H-8" in self.name:
            self.type = 'm8'
        elif "H-5" in self.name:
            self.type = 'm5'
        else:
            self.type = 'unknown'

        self.split_position_rotation(pose)

    def split_position_rotation(self, pose):
        """Extracts position and z-axis orientation from the pose matrix."""
        x, y, z, rx, ry, rz = pose_2_xyzrpw(pose)
        self.position = (x, y, z)
        self.rotation = pose[0:3, 2]  # Z-axis of the target
        z_facing_rounded = [round(val) for val in self.rotation.tolist()]
        self.rot_identifier = f"{z_facing_rounded[0]}_{z_facing_rounded[1]}_{z_facing_rounded[2]}"


class Face:
    """Represents a collection of holes on the same geometric face."""

    def __init__(self, key, holes_on_face):
        self.key = key
        self.holes = holes_on_face
        self.rotation = self.holes[0].rotation.tolist()
        self.get_midpoint()

    def get_midpoint(self):
        """Calculates the geometric center of all holes on this face."""
        x_vals = [h.position[0] for h in self.holes]
        y_vals = [h.position[1] for h in self.holes]
        z_vals = [h.position[2] for h in self.holes]

        mid_x = (min(x_vals) + max(x_vals)) / 2
        mid_y = (min(y_vals) + max(y_vals)) / 2
        mid_z = (min(z_vals) + max(z_vals)) / 2
        self.midpoint = (mid_x, mid_y, mid_z)

        # Create a representative pose for the face's center
        self.midpose = self.holes[0].pose
        self.midpose.setPos([mid_x, mid_y, mid_z])


# --- GLOBAL PROCESSING: Identify all faces ---
# This part runs once to identify all unique faces based on hole orientations.
all_holes = [Hole(item.Pose(), item) for item in RDK_items]
grouped_holes = {}
for hole in all_holes:
    if hole.rot_identifier not in grouped_holes:
        grouped_holes[hole.rot_identifier] = []
    grouped_holes[hole.rot_identifier].append(hole)

faces = [Face(key, hole_group) for key, hole_group in grouped_holes.items()]
print(f"Identified {len(faces)} unique faces.")


# --- PROGRAM GENERATION FUNCTIONS ---

def create_face_targets():
    """
    Creates a single approach target at the midpoint of each identified face.
    This function is NOT changed and runs only once.
    """
    for i, face in enumerate(faces):
        face_target_name = f"Face_Target_{i}"

        # Delete the target if it already exists to avoid duplicates
        existing_target = RDK.Item(face_target_name, ITEM_TYPE_TARGET)
        if existing_target.Valid():
            existing_target.Delete()

        # Create a new target at the face's midpoint
        face_target = RDK.AddTarget(face_target_name, FRAME, ROBOT)
        face_target.setPose(face.midpose)
        print(f"Created {face_target_name} at midpoint {face.midpoint}")


# ** MODIFIED FUNCTION **
def generate_pickup_links(hole_type):
    """
    Generates collision-free programs to move between face targets and a specific pickup target.
    :param hole_type: The type of hole to process ('m8' or 'm5').
    """
    print(f"\n--- Generating pickup links for type: {hole_type.upper()} ---")

    # Define pickup target name based on the hole type
    pickup_target_name = f"pickup_{hole_type}"
    target_pickup_item = RDK.Item(pickup_target_name, ITEM_TYPE_TARGET)

    if not target_pickup_item.Valid():
        print(f"Warning: Pickup target '{pickup_target_name}' not found. Skipping link generation.")
        return

    # For every face, create two programs: one to the pickup, and one from the pickup.
    for i, face in enumerate(faces):
        face_target_name = f"Face_Target_{i}"

        # Define program names dynamically based on face index and hole type
        prog_to_pickup_name = f"FaceTarget{i}ToPickup{hole_type}"
        prog_from_pickup_name = f"Pickup{hole_type}ToFaceTarget{i}"

        # Delete existing programs to ensure they are regenerated
        for prog_name in [prog_to_pickup_name, prog_from_pickup_name]:
            existing_prog = RDK.Item(prog_name, ITEM_TYPE_PROGRAM)
            if existing_prog.Valid():
                existing_prog.Delete()

        # Generate path from Face Target -> Pickup Target
        print(f"Joining: {face_target_name} -> {pickup_target_name}")
        RDK.PluginCommand("CollisionFreePlanner", "Join",
                          f"{face_target_name}|{pickup_target_name}|{prog_to_pickup_name}")

        # Generate path from Pickup Target -> Face Target
        print(f"Joining: {pickup_target_name} -> {face_target_name}")
        RDK.PluginCommand("CollisionFreePlanner", "Join",
                          f"{pickup_target_name}|{face_target_name}|{prog_from_pickup_name}")

    print(f"Pickup link generation for {hole_type.upper()} complete.")


# ** MODIFIED FUNCTION **
def create_face_programs(hole_type):
    """
    Generates a program for each face to handle all holes of a specific type.
    :param hole_type: The type of hole to process ('m8' or 'm5').
    """
    print(f"\n--- Creating face programs for type: {hole_type.upper()} ---")

    for i, face in enumerate(faces):
        # Filter for holes of the specified type on the current face
        holes_to_process = [h for h in face.holes if h.type == hole_type]

        # If no holes of this type exist on the face, skip it
        if not holes_to_process:
            continue

        face_target_name = f"Face_Target_{i}"
        face_target = RDK.Item(face_target_name, ITEM_TYPE_TARGET)

        # Program name now includes the hole type
        prog_name = f"Program_Face_{i}_{hole_type}"

        existing_prog = RDK.Item(prog_name, ITEM_TYPE_PROGRAM)
        if existing_prog.Valid():
            existing_prog.Delete()
        prog = RDK.AddProgram(prog_name, ROBOT)

        # Define the pickup link program names dynamically
        program_from_pickup = f'Pickup{hole_type}ToFaceTarget{i}'
        program_to_pickup = f'FaceTarget{i}ToPickup{hole_type}'

        # Start the sequence
        prog.RunInstruction('screw_in(0)', robolink.INSTRUCTION_CALL_PROGRAM)

        for j, hole in enumerate(holes_to_process):
            # On the first hole, move from pickup station
            if j == 0:
                prog.RunInstruction(program_from_pickup, robolink.INSTRUCTION_CALL_PROGRAM)

            # Move to the hole via the face's approach target
            prog.MoveL(face_target)
            prog.MoveL(hole.target)

            # Perform screwdriving operations
            prog.RunInstruction('screw_in(20)', robolink.INSTRUCTION_CALL_PROGRAM)
            prog.RunInstruction('screw_out(0)', robolink.INSTRUCTION_CALL_PROGRAM)

            # Return to approach point and go to pickup station
            prog.MoveL(face_target)
            prog.RunInstruction(program_to_pickup, robolink.INSTRUCTION_CALL_PROGRAM)

            # Pickup next screw
            prog.RunInstruction('screw_in(0)', robolink.INSTRUCTION_CALL_PROGRAM)

            # If it's not the last hole, travel back from pickup for the next one
            if j < len(holes_to_process) - 1:
                prog.RunInstruction(program_from_pickup, robolink.INSTRUCTION_CALL_PROGRAM)

        print(f"Generated program '{prog_name}' with {len(holes_to_process)} holes.")


def add_main_programs():
    """Creates a main program for each hole type that calls the relevant face programs."""
    for hole_type in ['m8', 'm5']:
        main_prog_name = f"Program_Main_{hole_type}"

        # Find all face programs created for this type
        sub_progs = []
        for i in range(len(faces)):
            sub_prog_name = f"Program_Face_{i}_{hole_type}"
            item = RDK.Item(sub_prog_name, ITEM_TYPE_PROGRAM)
            if item.Valid():
                sub_progs.append(item)

        if not sub_progs:
            continue  # Skip if no programs were created for this type

        existing_main_prog = RDK.Item(main_prog_name, ITEM_TYPE_PROGRAM)
        if existing_main_prog.Valid():
            existing_main_prog.Delete()

        main_prog = RDK.AddProgram(main_prog_name, ROBOT)
        main_prog.setTool(TOOL)
        main_prog.setFrame(FRAME)

        # Call each sub-program in order
        for prog in sub_progs:
            main_prog.RunInstruction(prog.Name(), robolink.INSTRUCTION_CALL_PROGRAM)

        print(f"Created main program '{main_prog_name}'")


def create_tool_change_subprograms():
    """
    Creates dedicated subprograms for picking up and dropping off each tool,
    including collision-free paths between pickup and tool-switch stations.
    """
    print("\n--- Creating Tool Change Subprograms ---")
    for hole_type in ['m8', 'm5']:
        # Define targets needed for tool change
        pickup_target = RDK.Item(f"pickup_{hole_type}", ITEM_TYPE_TARGET)
        toolswitch_target = RDK.Item(f"toolswitch_{hole_type}", ITEM_TYPE_TARGET)
        toolswitch_approach_target = RDK.Item(f"toolswitch_{hole_type}_approach", ITEM_TYPE_TARGET)

        if not all([pickup_target.Valid(), toolswitch_target.Valid(), toolswitch_approach_target.Valid()]):
            print(f"Warning: One or more targets for '{hole_type}' tool change not found. Skipping.")
            continue

        # --- Generate Collision-Free Paths between Pickup and Toolswitch stations ---
        from_pickup_path_name = f"pickup{hole_type}Totoolswitch{hole_type}approach"
        to_pickup_path_name = f"toolswitch{hole_type}approachTopickup{hole_type}"

        # Delete existing paths to regenerate
        for path_name in [from_pickup_path_name, to_pickup_path_name]:
            if (item := RDK.Item(path_name, ITEM_TYPE_PROGRAM)).Valid(): item.Delete()

        print(f"Joining: {pickup_target.Name()} -> {toolswitch_approach_target.Name()}")
        RDK.PluginCommand("CollisionFreePlanner", "Join",
                          f"{pickup_target.Name()}|{toolswitch_approach_target.Name()}|{from_pickup_path_name}")

        print(f"Joining: {toolswitch_approach_target.Name()} -> {pickup_target.Name()}")
        RDK.PluginCommand("CollisionFreePlanner", "Join",
                          f"{toolswitch_approach_target.Name()}|{pickup_target.Name()}|{to_pickup_path_name}")

        # --- Create Tool Pickup Program ---
        pickup_prog_name = f"Tool_Pickup_{hole_type}"
        if (prog := RDK.Item(pickup_prog_name, ITEM_TYPE_PROGRAM)).Valid(): prog.Delete()

        pickup_prog = RDK.AddProgram(pickup_prog_name, ROBOT)
        pickup_prog.RunInstruction(from_pickup_path_name, robolink.INSTRUCTION_CALL_PROGRAM)  # Travel to tool
        pickup_prog.MoveL(toolswitch_target)
        pickup_prog.RunInstruction("screw_out(0)", robolink.INSTRUCTION_CALL_PROGRAM)  # Attach tool
        pickup_prog.MoveL(toolswitch_approach_target)
        pickup_prog.RunInstruction(to_pickup_path_name, robolink.INSTRUCTION_CALL_PROGRAM)  # Travel back to pickup
        print(f"Created program: {pickup_prog_name}")

        # --- Create Tool Dropoff Program ---
        dropoff_prog_name = f"Tool_Dropoff_{hole_type}"
        if (prog := RDK.Item(dropoff_prog_name, ITEM_TYPE_PROGRAM)).Valid(): prog.Delete()

        dropoff_prog = RDK.AddProgram(dropoff_prog_name, ROBOT)
        dropoff_prog.RunInstruction(from_pickup_path_name, robolink.INSTRUCTION_CALL_PROGRAM)  # Travel to tool
        dropoff_prog.MoveL(toolswitch_target)
        dropoff_prog.RunInstruction("screw_in(10)", robolink.INSTRUCTION_CALL_PROGRAM)  # Detach tool
        dropoff_prog.MoveL(toolswitch_approach_target)
        dropoff_prog.RunInstruction(to_pickup_path_name, robolink.INSTRUCTION_CALL_PROGRAM)  # Travel back to pickup
        print(f"Created program: {dropoff_prog_name}")


def combine_main_programs():
    """Creates a single, combined main program that calls the tool change and main work programs in sequence."""
    print("\n--- Combining all main programs ---")
    combined_prog_name = "Program_Main_Combined"

    existing_combined_prog = RDK.Item(combined_prog_name, ITEM_TYPE_PROGRAM)
    if existing_combined_prog.Valid():
        existing_combined_prog.Delete()

    combined_prog = RDK.AddProgram(combined_prog_name, ROBOT)
    combined_prog.setTool(TOOL)
    combined_prog.setFrame(FRAME)

    # Loop through the defined screw sizes and add their complete sequence
    for hole_type in ['m8', 'm5']:
        main_prog_to_call = f"Program_Main_{hole_type}"
        pickup_prog_to_call = f"Tool_Pickup_{hole_type}"
        dropoff_prog_to_call = f"Tool_Dropoff_{hole_type}"

        # Check if all necessary programs exist for this type
        if RDK.Item(main_prog_to_call).Valid() and RDK.Item(pickup_prog_to_call).Valid() and RDK.Item(
                dropoff_prog_to_call).Valid():
            print(f"Adding sequence for {hole_type.upper()}...")
            # 1. Pick up the correct tool
            combined_prog.RunInstruction(pickup_prog_to_call, robolink.INSTRUCTION_CALL_PROGRAM)
            # 2. Run the main program for all holes of this type
            combined_prog.RunInstruction(main_prog_to_call, robolink.INSTRUCTION_CALL_PROGRAM)
            # 3. Drop off the tool
            combined_prog.RunInstruction(dropoff_prog_to_call, robolink.INSTRUCTION_CALL_PROGRAM)
        else:
            print(f"Warning: One or more programs for '{hole_type}' are missing. Skipping this sequence.")

    print(f"Created combined main program: '{combined_prog_name}'")


# --- MAIN EXECUTION SCRIPT ---
if __name__ == '__main__':
    print("\nStarting program generation...")

    # 1. Create the geometric face approach targets
    create_face_targets()

    # 2. Generate programs for M8 screws
    generate_pickup_links('m8')
    create_face_programs('m8')

    # 3. Generate programs for M5 screws
    generate_pickup_links('m5')
    create_face_programs('m5')

    # 4. Create main programs for each screw type
    add_main_programs()

    # 5. Create the dedicated tool change subprograms
    create_tool_change_subprograms()

    # 6. Create one final program to run everything in sequence
    combine_main_programs()

    print("\n--- All processing complete. ---")
