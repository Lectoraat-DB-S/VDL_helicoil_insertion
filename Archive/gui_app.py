import re
import threading
import time
import math
import cv2  # pip install opencv-python
import numpy as np
from vmbpy import *
from pyzbar.pyzbar import decode, ZBarSymbol
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog

from GUI.screwdriver_interface import *
from rtde_interface import *
from GUI.screwdriver_socketIO import *
from rtde_interface import is_robot_physically_moving
from GUI.screwdriver_interface import check_busy


DEBUG_CODE = False                               # true if you want prints, false if you don't
QR_REAL_SIZE = 40                               # in milimeters
QR_PIXEL_SIZE = 124                             # in pixels
REAL_PIXEL_SIZE = QR_REAL_SIZE/QR_PIXEL_SIZE    # 1 pixel in mm
MIDDLE_POINTQR = [[[577, 449]]]                 # in pixels
MIDDLE_POINT_CAMERA = [640, 512]                # in pixels
STANDARD_ANGLE = 0                              # in degrees
QRPOSITION = [math.radians(-101.47), math.radians(-121.57), math.radians(102.82), math.radians(18.74), math.radians(78.53), math.radians(-90.0000)]
OFFSET_X = 10                                   # in pixels
OFFSET_Y = 10                                   # in pixels
OFFSET_ANGLE = 1                                # in degrees


class GUIApp:
    def __init__(self, root):
        """
        Initialize the main GUI application.
        Sets up the window, colors, layout, and starts necessary background threads.

        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("VDL_ETG")
        self.root.geometry("1000x600")  # GUI size
        self.running = False  # for starting and stopping script
        self.debug = False

        # Define color scheme
        self.colors = {
            "primary": "#2c3e50",  # Dark blue/gray
            "secondary": "#3498db",  # Blue
            "accent": "#95a5a6",  # Light gray
            "background": "#ecf0f1",  # Very light gray
            "danger": "#e74c3c",  # Red for stop buttons
            "success": "#2ecc71",  # Green for success indicators
            "text_dark": "#2c3e50",  # Dark text
            "text_light": "#ecf0f1"  # Light text
        }

        # Apply the theme
        self.apply_theme()

        # Set the GUI instance before starting Socket.IO
        screwdriver_socketIO.gui_app_instance = self
        print("[INFO] GUI instance set in socketio_interface.")

        # Main container frame with padding
        self.main_container = tk.Frame(root, bg=self.colors["background"], padx=15, pady=15)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Frames for layouts with more modern proportions
        self.left_frame = tk.Frame(self.main_container, bg=self.colors["background"], width=280)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.right_frame = tk.Frame(self.main_container, bg=self.colors["background"], width=700)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # GUI setup
        self.setup_left_side()
        self.setup_right_side()

        # Start a thread for WebSocket connection and data updates
        threading.Thread(target=self.start_socket_io, daemon=True).start()

        self.update_screwdriver_data_periodically()  # Start automatic update

    def apply_theme(self):
        """
        Apply custom styling to the application components.
        Configures styles for tabs, buttons, and other UI elements.
        """
        style = ttk.Style()
        style.theme_use('clam')  # Use a base theme that's easily customizable

        # Configure the tab appearance
        style.configure("TNotebook", background=self.colors["background"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["accent"],
                        padding=[10, 5], font=('Arial', 9, 'bold'))
        style.map("TNotebook.Tab", background=[("selected", self.colors["secondary"])],
                  foreground=[("selected", self.colors["text_light"])])

        # Configure the frame appearance
        style.configure("TFrame", background=self.colors["background"])

        # Button styling
        style.configure("TButton", background=self.colors["secondary"],
                        foreground=self.colors["text_light"],
                        font=('Arial', 9), padding=6)
        style.map("TButton", background=[("active", self.colors["primary"])])

        # Danger button style
        style.configure("Danger.TButton", background=self.colors["danger"],
                        foreground=self.colors["text_light"])
        style.map("Danger.TButton", background=[("active", "#c0392b")])  # Darker red when active

    # ------------------------------------------
    # Socket.IO and Status Update Functions
    # ------------------------------------------

    def start_socket_io(self):
        """
        Connect to the Socket.io server and keep the connection alive.
        Retries connection every 5 seconds if failed.
        """
        while True:
            if connect_to_server():
                print("[INFO] Connected to server. Waiting for messages...")
                sio.wait()  # Keep the connection alive
            else:
                print("[INFO] Unable to connect. Retrying in 5 seconds...")
                time.sleep(5)  # Wait before retrying

    def update_screwdriver_data(self):
        """
        Update the GUI with the latest screwdriver data.
        Updates the display with status, shank position, and torque.
        """
        data = screwdriver_socketIO.get_screwdriver_data()

        if data:
            status = "Busy" if data.get("screwdriver_busy", False) else "Not busy"
            shank_position = round(data.get("shank_position", 0), 2)
            current_torque = round(data.get("current_torque", 0), 3)

            self.screwdriver_label.config(
                text=f"Screwdriver status: {status}\n"
                     f"Shank position: {shank_position} mm\n"
                     f"Current torque: {current_torque} Nm",
                fg=self.colors["success"]
            )
        else:
            self.screwdriver_label.config(text="Screwdriver data: Not available", fg=self.colors["danger"])

    def update_screwdriver_data_periodically(self):
        """
        Periodically update the screwdriver data in the GUI.
        Sets a timer to refresh data every second.
        """
        self.update_screwdriver_data()
        self.root.after(1000, self.update_screwdriver_data_periodically)

    # ------------------------------------------
    # GUI Setup Functions
    # ------------------------------------------

    def setup_left_side(self):
        """
        Set up the left side of the GUI containing the control panel.
        Creates tabs for screwdriver functions and general controls.
        """
        panel_frame = tk.Frame(self.left_frame, bg=self.colors["background"])
        panel_frame.pack(fill=tk.BOTH, expand=True)

        # Title for the control panel
        header_label = tk.Label(panel_frame, text="CONTROL PANEL",
                                bg=self.colors["primary"], fg=self.colors["text_light"],
                                font=("Arial", 12, "bold"), pady=8)
        header_label.pack(fill=tk.X, pady=(0, 15))

        self.tab_control = ttk.Notebook(panel_frame)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab3, text="Screwdriver")
        self.tab_control.add(self.tab4, text="General")

        self.tab_control.pack(expand=1, fill=tk.BOTH)

        # Setup screwdriver functions tab
        self.setup_sd_functions_tab()

        # Setup generic functions tab
        self.setup_generic_tab()

    def setup_sd_functions_tab(self):
        """
        Set up the screwdriver functions tab.
        Creates buttons for various screwdriver operations.
        """
        status_frame = ttk.Frame(self.tab3)
        status_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Create a more modern grid layout
        functions = [
            ("Move shank", self.run_move_shank),
            ("Pick screw", self.run_pick_screw),
            ("Pre-mount screw", self.run_premount_screw),
            ("Tighten screw", self.run_tighten_screw),
            ("Loosen screw", self.run_loosen_screw)
        ]

        # Create a container for better button spacing
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.BOTH, expand=True)

        # Add buttons with consistent styling
        for i, (text, command) in enumerate(functions):
            btn = ttk.Button(button_frame, text=text, command=command, width=18)
            btn.pack(pady=8, padx=5, fill=tk.X)

    def setup_generic_tab(self):
        """
        Set up the generic tab with miscellaneous functions.
        Creates buttons for loading scripts, checking connections, etc.
        """
        status_frame = ttk.Frame(self.tab4)
        status_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Button container for consistent styling
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.BOTH, expand=True)

        # Create buttons with consistent styling
        btn_load_script = ttk.Button(button_frame, text="Load Script", command=self.load_script, width=18)
        btn_load_script.pack(pady=8, padx=5, fill=tk.X)

        btn_calibrate_robot = ttk.Button(button_frame, text="Calibrate Robot", command=self.calibrate_robot,
                                         width=18)
        btn_calibrate_robot.pack(pady=8, padx=5, fill=tk.X)

        btn_stop_start_script = ttk.Button(button_frame, text="Stop/Start Script", command=self.stop_start_script,
                                           width=18)
        btn_stop_start_script.pack(pady=8, padx=5, fill=tk.X)

        btn_stop_start_feederloop = ttk.Button(button_frame, text="Stop/Start Feeder Loop", command=self.stop_start_feederloop,
                                           width=18)
        btn_stop_start_feederloop.pack(pady=8, padx=5, fill=tk.X)

        #btn_indraaien = ttk.Button(button_frame, text="Tightening", command=self.run_indraaien, width=18)
        #btn_indraaien.pack(pady=8, padx=5, fill=tk.X)

        #btn_uitdraaien = ttk.Button(button_frame, text="Unscrewing", command=self.run_uitdraaien, width=18)
        #btn_uitdraaien.pack(pady=8, padx=5, fill=tk.X)

        btn_check_connections = ttk.Button(button_frame, text="Check connections",
                                           command=lambda: self.run_in_thread(self.check_connections),
                                           width=18)
        btn_check_connections.pack(pady=8, padx=5, fill=tk.X)

        btn_disconnect = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_all,
                                    width=18)
        btn_disconnect.pack(pady=8, padx=5, fill=tk.X)

    def stop_start_script(self):
        self.running = not self.running

        if self.running == 0:
            self.log_message("Script Stopping !")
        elif self.running == 1:
            self.log_message("Script Running !")

    def setup_right_side(self):
        """
        Set up the right side of the GUI containing system information.
        Creates tabs for status, logs, and Cobotrack controls.
        """
        # Add a header
        header_label = tk.Label(self.right_frame, text="SYSTEM INFORMATION",
                                bg=self.colors["primary"], fg=self.colors["text_light"],
                                font=("Arial", 12, "bold"), pady=8)
        header_label.pack(fill=tk.X, pady=(0, 15))

        self.tab_control = ttk.Notebook(self.right_frame)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)

        self.tab_control.add(self.tab1, text="Status")
        self.tab_control.add(self.tab2, text="Logs")
       # self.tab_control.add(self.tab3, text="Cobotrack")
        self.tab_control.pack(expand=1, fill=tk.BOTH)

        # Status-tab
        self.setup_status_tab()

       # # Cobotrack tab
       # self.setup_cobotrack_tab()

        # Logs-tab
        self.setup_logs_tab()

    def setup_status_tab(self):
        """
        Set up the status tab for system information.
        Displays connection status and screwdriver data.
        """
        # Create a card-like container for status info
        status_card = tk.Frame(self.tab1, bg=self.colors["accent"],
                               relief=tk.RIDGE, borderwidth=1, padx=15, pady=25)
        status_card.pack(fill=tk.X, pady=10)

        # Main status section with connection info
        status_header = tk.Label(status_card, text="Connection Status",
                                 bg=self.colors["accent"], fg=self.colors["primary"],
                                 font=("Arial", 10, "bold"))
        status_header.pack(anchor=tk.W, pady=(0, 10))

        status_frame = tk.Frame(status_card, bg=self.colors["accent"])
        status_frame.pack(fill=tk.X)

        self.status_canvas = tk.Canvas(status_frame, width=15, height=15,
                                       bg=self.colors["accent"], highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 13, 13, fill=self.colors["danger"])

        self.status_label = tk.Label(status_frame, text="Status: Checking connections...",
                                     fg=self.colors["text_dark"], bg=self.colors["accent"],
                                     font=("Arial", 9))
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.loading_label = tk.Label(status_frame, text="", fg="blue", bg=self.colors["accent"],
                                      font=("Arial", 9, "italic"))
        self.loading_label.pack(side=tk.LEFT, padx=(10, 0))

        # Screwdriver data in a separate card
        screwdriver_card = tk.Frame(self.tab1, bg=self.colors["background"],
                                    relief=tk.GROOVE, borderwidth=1, padx=15, pady=15)
        screwdriver_card.pack(fill=tk.X, pady=10)

        screwdriver_header = tk.Label(screwdriver_card, text="Screwdriver Data",
                                      bg=self.colors["background"], fg=self.colors["primary"],
                                      font=("Arial", 10, "bold"))
        screwdriver_header.pack(anchor=tk.W, pady=(0, 10))

        self.screwdriver_label = tk.Label(screwdriver_card, text="Screwdriver data: Not available",
                                          fg=self.colors["text_dark"], bg=self.colors["background"],
                                          font=("Arial", 9), justify=tk.LEFT)
        self.screwdriver_label.pack(fill=tk.X)

    def setup_logs_tab(self):
        """
        Set up the logs tab for system messages.
        Creates a scrollable text widget to display logs.
        """
        log_frame = ttk.Frame(self.tab2)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add a header
        log_header = tk.Label(log_frame, text="System Logs",
                              bg=self.colors["secondary"], fg=self.colors["text_light"],
                              font=("Arial", 10, "bold"), pady=5)
        log_header.pack(fill=tk.X, pady=(0, 10))

        # Text widget with scrollbar for logs
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_container, height=20, width=80,
                                bg=self.colors["background"], fg=self.colors["text_dark"],
                                font=("Consolas", 9), padx=5, pady=5)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)

    '''def setup_cobotrack_tab(self):
        """
        Set up the Cobotrack control tab.
        Creates slider and buttons to control Cobotrack movement.
        """
        self.cobotrack_frame = ttk.Frame(self.tab3)
        self.cobotrack_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Create a card-like container
        control_card = tk.Frame(self.cobotrack_frame, bg=self.colors["accent"],
                                relief=tk.RIDGE, borderwidth=1, padx=10, pady=10)
        control_card.pack(pady=10, fill=tk.X)

        # Connection status label
        self.cobotrack_status_label = tk.Label(control_card, text="Checking Cobotrack connection...",
                                               fg=self.colors["text_dark"], bg=self.colors["accent"],
                                               font=("Arial", 10, "bold"))
        self.cobotrack_status_label.pack(pady=5)

        # Slider
        slider_frame = tk.Frame(control_card, bg=self.colors["accent"], pady=5)
        slider_frame.pack(fill=tk.X)

        slider_label = tk.Label(slider_frame, text="Move to Position:",
                                bg=self.colors["accent"], fg=self.colors["text_dark"],
                                font=("Arial", 9))
        slider_label.pack(anchor=tk.W)

        self.cobotrack_slider = tk.Scale(slider_frame, from_=0, to=1240, orient=tk.HORIZONTAL,
                                         length=700, bg=self.colors["accent"],
                                         highlightthickness=0, troughcolor=self.colors["secondary"],
                                         sliderrelief=tk.FLAT)
        self.cobotrack_slider.pack(fill=tk.X, pady=5)
        # Slider

        # Control buttons in a horizontal layout
        button_frame = tk.Frame(control_card, bg=self.colors["accent"])
        button_frame.pack(fill=tk.X, pady=10)

        self.move_button = ttk.Button(button_frame, text="Move", command=self.move_cobotrack, width=10)
        self.move_button.pack(side=tk.LEFT, padx=5)

        # Stop button with danger styling
        self.stop_button = ttk.Button(button_frame, text="STOP", command=self.stop_cobotrack,
                                      style="Danger.TButton", width=10)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status display
        status_frame = tk.Frame(self.cobotrack_frame, bg=self.colors["background"],
                                relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        status_frame.pack(pady=10, fill=tk.X)

        status_header = tk.Label(status_frame, text="Cobotrack Status",
                                 bg=self.colors["background"], fg=self.colors["primary"],
                                 font=("Arial", 10, "bold"))
        status_header.pack(anchor=tk.W, pady=(0, 5))

        self.cobotrack_status_display = tk.Label(status_frame, text="Status: Unknown",
                                                 bg=self.colors["background"], fg=self.colors["text_dark"],
                                                 font=("Arial", 9), justify=tk.LEFT, padx=5)
        self.cobotrack_status_display.pack(fill=tk.X)

        # Start status monitoring in a separate thread
        self.run_in_thread(self.update_cobotrack_status)

    # ------------------------------------------
    # Script Loading and Execution Functions
    # ------------------------------------------
'''
    def load_script(self):
        """
        Open a file dialog to select a script file.
        Parses and displays the commands found in the script.
        """
        file_path = filedialog.askopenfilename(
            title="Select Script File",
            filetypes=(("Script files", "*.script"), ("All files", "*.*"))
        )
        self.running = 1  # reset var running by setting it

        if file_path:
            commands = self.parse_script(file_path)
            self.display_commands(commands)

    def parse_script(self, file_path):
        """
        Parse the script file by identifying functions and following execution flow
        from the main program.

        Args:
            file_path: Path to the script file

        Returns:
            List of commands in execution order
        """

        move_shank(0) #move shank to initial position

        # Read the entire script file
        with open(file_path, 'r') as file:
            script_content = file.read()

        # Dictionary to store function definitions
        function_definitions = {}

        # Extract all function definitions
        function_pattern = re.compile(r'def\s+(\w+)\(\):\s*(.*?)end', re.DOTALL)
        for match in function_pattern.finditer(script_content):
            function_name = match.group(1)
            function_body = match.group(2)
            function_definitions[function_name] = function_body

        # Find the main program section (after all function definitions)
        main_program_match = re.search(r'# Main program:(.*?)# End of main program', script_content, re.DOTALL)
        if main_program_match:
            main_program = main_program_match.group(1)
        else:
            # If no main program markers, find the last function call (usually the entry point)
            function_call_pattern = re.compile(r'(\w+)\(\)\s*$')
            match = function_call_pattern.search(script_content)
            if match:
                main_function_name = match.group(1)
                if main_function_name in function_definitions:
                    main_program = function_definitions[main_function_name]
                else:
                    raise ValueError(f"Couldn't find main program or entry function: {main_function_name}")
            else:
                # Fall back to the entire script
                main_program = script_content

        # Extract commands following program flow
        commands = self.extract_commands_with_flow(main_program, function_definitions)

        return commands

    def extract_commands_with_flow(self, program_section, function_definitions):
        """
        Extract commands from a program section, expanding function calls.

        Args:
            program_section: Section of code to extract commands from
            function_definitions: Dictionary of function definitions

        Returns:
            List of commands in execution order
        """
        commands = []
        lines = program_section.strip().split('\n')

        for line in lines:
            # Remove whitespace and comments
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            # Check if line is a command we're interested in
            if line.startswith(('movej', 'movel', 'move_shank', 'move_to', 'screw_in', 'screw_out')):
                commands.append(line)

            # Check if line is a function call
            function_call_match = re.match(r'(\w+)\(\)', line)
            if function_call_match:
                function_name = function_call_match.group(1)
                if function_name in function_definitions:
                    # Recursively expand function calls
                    function_commands = self.extract_commands_with_flow(
                        function_definitions[function_name], function_definitions)
                    commands.extend(function_commands)

        return commands

    def display_commands(self, commands):
        """
        Show parsed commands and execute them one by one.
        Waits for robot/screwdriver readiness between commands.

        Args:
            commands: List of commands to execute
        """
        print("Parsed commands: ")

        def execute_commands_with_delay(commands):
            for i, command in enumerate(commands):
                print(f"{i + 1}: {command}")  # log command

                if not self.debug:
                    # # Check if robot or screwdriver or cobotrack is busy
                    while is_robot_physically_moving(debug=True) or check_busy() or self.running == 1:
                        time.sleep(0.5)  # wait 500ms until robot is ready
                        print("Waiting until robot is ready")
                else:
                    # Check if robot or screwdriver or cobotrack is busy
                    while self.running == 0:
                        time.sleep(0.5)  # wait 500ms until robot is ready
                        print("Waiting until robot is ready")

                self.execute_command(command)

                # wait a second before executing the next one
                time.sleep(1)

        self.run_in_thread(execute_commands_with_delay, commands)

    def execute_command(self, command):
        """
        Execute a command from the parsed script.
        Supports movej, movel, move_shank, screw_in, screw_out and move_to commands.

        Args:
            command: Command string to execute
        """
        try:
            # UR10e movel command
            if command.startswith('movel'):
                # Standard format: movel([joints])
                bracket_match = re.match(r'movel\(\[([-\d., ]+)\]', command)
                # p format: movel(p[joints])
                p_match = re.match(r'movel\(p\[([-\d., ]+)\]', command)
                # pose_trans format: movel(pose_trans(ref_frame,p[joints]),accel,speed,blend,etc)
                #pose_trans_match = re.match(r'movel\(pose_trans\([^,]+,p\[([-\d., ]+)\][^)]*\)', command)

                if bracket_match:
                    # Format: movel([2.959485, -2.090817, ...])
                    joints_str = bracket_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    if not self.debug:
                        move_to_positionl_calibrated_joints(joints)

                elif p_match:
                 '''   # Format: movel(p[-0.969933, 0.499379, ...])
                    joints_str = p_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    #print(f"Running: movel - joints {joints}")
                    #self.log_message(f"Running: movel - joints {joints}")

                    if not self.debug:
                        move_to_positionl(joints)

                #elif pose_trans_match:
                    # Format: movel(pose_trans(ref_frame,p[0.282414, 0.145343, ...]),accel,speed,...)
                #    joints_str = pose_trans_match.group(1)
                #    joints = [float(j.strip()) for j in joints_str.split(',')]

                    #print(f"Running: movel with pose_trans - joints {joints}")
                    #self.log_message(f"Running: movel with pose_trans - joints {joints}")

                #    if not self.debug:
                 #       move_to_positionl(joints)

                else:
                    print(f"Couldn't find joint values in command: {command}")
                    self.log_message(f"Couldn't find joint values in command: {command}")

                    # UR10e movej command
                    '''
                 print(f"Do not use with pose: {command}")
                 self.log_message(f"Do not use with pose: {command}")
                 
            elif command.startswith('movej'):
                # Standard format: movej([joints])
                bracket_match = re.match(r'movej\(\[([-\d., ]+)\]', command)
                # p format: movej(p[joints])
                p_match = re.match(r'movej\(p\[([-\d., ]+)\]', command)
                # pose_trans format: movej(pose_trans(ref_frame,p[joints]),accel,speed,blend,etc)
                #pose_trans_match = re.match(r'movej\(pose_trans\([^,]+,p\[([-\d., ]+)\][^)]*\)', command)

                if bracket_match:
                    # Format: movej([2.959485, -2.090817, ...])
                    joints_str = bracket_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                   # print(f"Running: movej - joints {joints}")
                    #self.log_message(f"Running: movej - joints {joints}")

                    if not self.debug:
                        move_to_positionj(joints)

                elif p_match:
                   ''' # Format: movej(p[-0.969933, 0.499379, ...])
                    joints_str = p_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                   # print(f"Running: movej - joints {joints}")
                    #self.log_message(f"Running: movej - joints {joints}")

                    if not self.debug:
                        move_to_positionj_IK(joints)

                #elif pose_trans_match:
                    # Format: movej(pose_trans(ref_frame,p[0.282414, 0.145343, ...]),accel,speed,...)
                #    joints_str = pose_trans_match.group(1)
                 #   joints = [float(j.strip()) for j in joints_str.split(',')]

                    #print(f"Running: movej with pose_trans - joints {joints}")
                    #self.log_message(f"Running: movej with pose_trans - joints {joints}")

                  #  if not self.debug:
                   #     move_to_positionj(joints)

                else:
                    print(f"Couldn't find joint values in command: {command}")
                    self.log_message(f"Couldn't find joint values in command: {command}")
'''
                print(f"Do not use with pose: {command}")
                self.log_message(f"Do not use with pose: {command}")
                
            # Screwdriver move_shank command
            elif command.startswith('move_shank'):
                # Parse move_shank command
                match = re.match(r'move_shank\((\d+)\)', command)
                if match:
                    value = int(match.group(1))
                    print(f"Running: move_shank({value})")
                    self.log_message(f"Running: move_shank({value})")
                    move_shank(value)
                else:
                    print(f"Invalid move_shank command: {command}")

            elif command.startswith('screw_in'):
                # Parse screw_in command
                match = re.match(r'screw_in\((\d+)\)', command)
                if match:
                    value = int(match.group(1))
                    print(f"Running: screw_in({value})")
                    self.log_message(f"Running: screw_in({value})")
                    screw_in(value)
                else:
                    print(f"Invalid screw_in command: {command}")

            elif command.startswith('screw_out'):
                # Parse screw_out command
                match = re.match(r'screw_out\((\d+)\)', command)
                if match:
                    value = int(match.group(1))
                    print(f"Running: screw_out({value})")
                    self.log_message(f"Running: screw_out({value})")
                    screw_out()
                else:
                    print(f"Invalid screw_out command: {command}")

            '''# cobotrack move_to command
            elif command.startswith('move_to'):
                # Parse move_to command
                match = re.match(r'move_to\((\d+)\)', command)
                if match:
                    value = int(match.group(1))
                    print(f"Running: move_to({value})")
                    # cobotrack_interface.move_to(value)
                else:
                    print(f"Invalid move_to command: {command}")
            else:
                print(f"Unknown command: {command}")
                self.log_message(f"Unknown command: {command}")
                '''

        except Exception as e:
            print(f"Execution of command failed: {command}\nError message: {e}")

    # ------------------------------------------
    # Screwdriver Control Functions
    # ------------------------------------------

    def _run_operation(self, operation_name, prompts, operation_func):
        """
        Generic method to run an operation with user input and threading.

        Args:
            operation_name: Name of the operation for dialog and logging
            prompts: List of input prompts
            operation_func: Function to execute the actual operation
        """
        values = self.get_input_values(operation_name, prompts)
        if values:
            self.run_in_thread(self._execute_operation, operation_name, operation_func, *values)

    def _execute_operation(self, operation_name, operation_func, *args):
        """
        Generic method to execute an operation and log results.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute the actual operation
            args: Arguments for the operation function
        """
        try:
            operation_func(*args)
            self.log_message(f"Success: {operation_name} completed!")
        except Exception as e:
            self.log_message(f"Error: {operation_name} failed: {str(e)}")

    def run_move_shank(self):
        """
        Execute the move_shank function with user input.
        Opens a dialog to get shank position value.
        """
        value = simpledialog.askfloat("Move Shank", "Enter the shank position (0-55):")
        if value is not None:
            self.run_in_thread(self._execute_operation, "Move shank", move_shank, value)

    def run_pick_screw(self):
        """
        Execute the pick_screw function with user input.
        Opens dialogs to get shank force and screwing length.
        """
        prompts = ["Enter the shank force (N):", "Enter the screwing length (mm):"]
        self._run_operation("Pick Screw", prompts, pick_screw)

    def run_premount_screw(self):
        """
        Execute the premount_screw function with user input.
        Opens dialogs to get shank force, screwing length, and torque.
        """
        prompts = [
            "Shank force (N):",
            "Screwing lengte (mm):",
            "Torque (Nm):"
        ]
        self._run_operation("Pre-mount Screw", prompts, premount_screw)

    def run_tighten_screw(self):
        """
        Execute the tighten_screw function with user input.
        Opens dialogs to get shank force, screwing length, and torque.
        """
        prompts = [
            "shank force (N):",
            "Screwing length (mm):",
            "Torque (Nm):"
        ]
        self._run_operation("Tighten Screw", prompts, tighten_screw)

    def run_loosen_screw(self):
        """
        Execute the loosen_screw function with user input.
        Opens dialogs to get shank force and unscrewing length.
        """
        prompts = [
            "Shank force (N):",
            "Unscrewing length (mm):"
        ]
        self._run_operation("Loosen Screw", prompts, loosen_screw)

    '''def run_indraaien(self):
        """
        Start the screw tightening process in a separate thread.
        Maintained for compatibility.
        """
        threading.Thread(target=self._indraaien, daemon=True).start()

    def _indraaien(self):
        """
        Execute the screw tightening process and log result.
        """
        try:
            screw_in()
            self.log_message("Success: Tightening completed!")
        except Exception as e:
            self.log_message(f"Error: Tightening failed: {e}")

    def run_uitdraaien(self):
        """
        Start the screw loosening process in a separate thread.
        Maintained for compatibility.
        """
        threading.Thread(target=self._uitdraaien, daemon=True).start()

    def _uitdraaien(self):
        """
        Execute the screw loosening process and log result.
        """
        try:
            screw_out()
            self.log_message("Success: Unscrewing completed!")
        except Exception as e:
            self.log_message(f"Error: Unscrewing failed: {e}")
    '''
    # ------------------------------------------
    # Cobotrack Control Functions
    # ------------------------------------------
    '''
    def move_cobotrack(self):
        """
        Move Cobotrack to the position specified by the slider.
        Uses the cobotrack_interface to control movement.
        """
        position = self.cobotrack_slider.get()
        cobotrack_interface.move_to(position, 70)

    def stop_cobotrack(self):
        """
        Stop Cobotrack movement immediately.
        """
        cobotrack_interface.stop_track()

    def update_cobotrack_status(self):
        """
        Update Cobotrack status periodically in a background thread.
        Displays bit status of the Cobotrack system.
        """
        while True:
            response = cobotrack_interface.get_status_word()  # Get the full response
            # print(f"Raw response from cobotrack_interface: {response}")  # Debug: Print raw response

            if response:  # Check if the response is not empty
                # print("Response is not empty.")  # Debug: Confirm response is not empty
                try:
                    # Extract the integer value from the response string
                    if response.startswith("COBOTRACK_STATUS_INT:"):
                        # print("Response starts with 'COBOTRACK_STATUS_INT:'.")  # Debug: Confirm correct prefix
                        # Split the string to get the integer part
                        status_word_str = response.split(":")[1].strip()  # Extract the part after the colon
                        # print(f"Extracted status word string: '{status_word_str}'")  # Debug: Print extracted string
                        status_word = int(status_word_str)  # Convert to integer
                        # print(f"Converted status word to integer: {status_word}")  # Debug: Print converted integer
                    else:
                        raise ValueError(
                            "Invalid response format: Response does not start with 'COBOTRACK_STATUS_INT:'")

                    bit_status = {
                        0: "Motor Turning", 1: "Inverter Ready", 2: "Referenced",
                        3: "Target Position Reached", 4: "Brake Released", 5: "Error Status",
                        6: "Limit Switch CW", 7: "Limit Switch CCW"
                    }
                    # Extract each bit and check if it's set (1)
                    active_statuses = [bit_status[i] for i in range(8) if (status_word & (1 << i))]
                    # print(f"Active statuses: {active_statuses}")  # Debug: Print active statuses
                    status_text = " | ".join(active_statuses)
                    # print(f"Final status text: {status_text}")  # Debug: Print final status text
                    self.cobotrack_status_display.config(text=f"Status: {status_text}")
                except (ValueError, TypeError, IndexError) as e:
                    # Handle errors (e.g., invalid format, conversion failure, etc.)
                    print(f"Error occurred: {e}")  # Debug: Print error
                    self.cobotrack_status_display.config(text=f"Status: Unknown (Error: {str(e)})",
                                                         fg=self.colors["danger"])
            else:
                # print("Response is empty or None.")  # Debug: Confirm response is empty
                self.cobotrack_status_display.config(text="Status: Connection Lost!", fg=self.colors["danger"])
                self.stop_cobotrack()

            time.sleep(0.4)  # Update every second
    '''
    # ------------------------------------------
    # Connection and Utility Functions
    # ------------------------------------------

    def check_connections(self):
        """Check connections to RTDE, Socket.IO, and Cobotrack in a responsive, threaded way."""

        def task():
            self.set_button_state("disabled")
            try:
                rtde_conn = initialize_rtde()
                rtde_status = "RTDE connected" if rtde_conn else "RTDE not connected"

                socketio_status = "Socket.IO connected" if sio.connected else "Socket.IO not connected"

               # cobotrack_interface.connect()
               # cobotrack_status = "Cobotrack connected" if cobotrack_interface.is_connected() else "Cobotrack not connected"

              #  all_connected = rtde_conn and sio.connected and cobotrack_interface.is_connected()
                all_connected = rtde_conn and sio.connected

                self.root.after(0, lambda: self.update_connection_ui(
                    #rtde_status, socketio_status, cobotrack_status, all_connected
                    rtde_status, socketio_status, all_connected
                ))

            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"Connection error: {e}"))
                self.root.after(0, lambda: self.set_status("Connection failed!", color="danger"))
            finally:
                self.root.after(0, self.hide_loading)
                self.root.after(0, lambda: self.set_button_state("normal"))

        # Show loading message right away
        self.loading_label.config(text="Connecting...")

        # Run the task after GUI has a chance to update
        self.root.after(100, lambda: self.run_in_thread(task))

    def show_loading(self, message="Loading..."):
        self.loading_label.config(text=message)

    def hide_loading(self):
        self.loading_label.config(text="")

    def set_button_state(self, state):
        # Disable/enable "Check connections" button
        for child in self.tab4.winfo_children():
            if isinstance(child, ttk.Frame):  # Check in the frame where the buttons are
                for btn in child.winfo_children():
                    if isinstance(btn, ttk.Button) and btn["text"] == "Check connections":
                        btn.config(state=state)

    def update_connection_ui(self, rtde_status, socketio_status,  all_connected):
        self.status_label.config(text=f"Status: {rtde_status} | {socketio_status} ")
        color = "success" if all_connected else "danger"
        self.status_canvas.itemconfig(self.status_indicator, fill=self.colors[color])
        if not all_connected:
            self.log_message("Connection failed!")

    def set_status(self, text, color="grey"):
        self.status_label.config(text=f"Status: {text}")
        self.status_canvas.itemconfig(self.status_indicator, fill=self.colors.get(color, "grey"))

    def get_input_values(self, title, prompts):
        """
        Show a dialog window to enter multiple values.

        Args:
            title: Dialog window title
            prompts: List of prompt strings

        Returns:
            List of input values or None if canceled
        """
        values = []
        for prompt in prompts:
            value = simpledialog.askfloat(title, prompt)
            if value is None:  # If the user clicks on cancel
                return None
            values.append(value)
        return values

    def log_message(self, message):
        """Add a message to the logs."""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def disconnect_all(self):
        global rtde_connected

        if rtde_connected:
            disconnect_rtde()

        if sio.connected:
            sio.disconnect()


        self.status_label.config(text="Status: Disconnected")
        self.status_canvas.itemconfig(self.status_indicator, fill=self.colors["danger"])
        self.log_message("Disconnected all systems.")

    def run_in_thread(self, func, *args):
        """execute function in a different thread."""
        thread = threading.Thread(target=func, args=args)
        thread.start()

        # Binnen de GUIApp klasse, onder de bestaande methoden:

    # get the location of the camera compared to the QR code
    def get_camera_pose(self, frame, camera_moves):
        # initialize variable that will return data
        movement = [0, 0, 0]

        # make frame grey scale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # equalize frame
        equ = cv2.equalizeHist(gray)

        # look for QRcodes in the frame
        decoded_objects = decode(equ, symbols=[ZBarSymbol.QRCODE])

        # check if all found objects are the correct qr codes
        for obj in decoded_objects:
            # Extract the corner points
            points = obj.polygon

            # We need exactly 4 corners for PnP
            if len(points) == 4:
                # make it an numpy array
                image_points = np.array(points, dtype=np.float32)
                # draw the shape around the QRcode (is also used for different things)
                pts_draw = image_points.astype(int).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts_draw], True, (0, 255, 0), 3)

                # in pts_draw the first variable is X and the second is Y
                # it seems the order in which the points are listed in the array change.
                # it seems the firs point in the array is always the most left point and the rest follows counter clock wise

                # find the middle point of the QRcode
                x_ave = (pts_draw[0][0][0] + pts_draw[1][0][0] + pts_draw[2][0][0] + pts_draw[3][0][0]) / 4
                y_ave = (pts_draw[0][0][1] + pts_draw[1][0][1] + pts_draw[2][0][1] + pts_draw[3][0][1]) / 4

                # initialize the points with a standard number
                point1 = 1111
                point2 = 1111
                point3 = 1111
                point4 = 1111

                # arrange the points in an predetermind order
                for i in pts_draw:
                    if i[0][1] < y_ave:
                        if i[0][0] < x_ave:
                            point1 = [int(i[0][0]), int(i[0][1])]
                        else:
                            point2 = [int(i[0][0]), int(i[0][1])]
                    else:
                        if i[0][0] > x_ave:
                            point3 = [int(i[0][0]), int(i[0][1])]
                        else:
                            point4 = [int(i[0][0]), int(i[0][1])]

                organized_points = [point1, point2, point3, point4]  # LT, RT, RB, LB

                # find orientation (it should never happen, but the QRcode could be orientated more then 20 degrees)
                x_axis = math.fabs(organized_points[3][0] - organized_points[0][0])
                y_axis = math.fabs(organized_points[3][1] - organized_points[0][1])

                if x_axis == 0:
                    tan_angle = 90
                    degrees_angle = 90
                else:
                    tan_angle = math.atan(y_axis / x_axis)
                    degrees_angle = math.degrees(tan_angle)

                if organized_points[0][0] < organized_points[3][0]:
                    oneEight = "left"
                else:
                    oneEight = "right"

                turn_direction = ""
                if DEBUG_CODE:
                    print(obj.orientation)

                if obj.orientation == "RIGHT":
                    turn_direction = "counter clockwise"
                    if oneEight == "left":
                        dif_angle = degrees_angle
                    else:
                        dif_angle = (90 - degrees_angle) + 90
                elif obj.orientation == "LEFT":
                    turn_direction = "clockwise"
                    if oneEight == "right":
                        dif_angle = degrees_angle
                    else:
                        dif_angle = (90 - degrees_angle) + 90
                elif obj.orientation == "DOWN":
                    dif_angle = degrees_angle + 90
                    if oneEight == "left":
                        turn_direction = "counter clockwise"
                    else:
                        turn_direction = "clockwise"
                else:
                    dif_angle = 90 - degrees_angle
                    if oneEight == "left":
                        turn_direction = "counter clockwise"
                    else:
                        turn_direction = "clockwise"

                # calculate the X and Y position on the camera image
                x_mid_point = organized_points[0][0] + ((organized_points[2][0] - organized_points[0][0]) / 2)
                y_mid_point = organized_points[0][1] + ((organized_points[2][1] - organized_points[0][1]) / 2)

                # calculate the X and Y offset compared to the middlepoint of the camera
                difX = MIDDLE_POINT_CAMERA[0] - x_mid_point  # positive means the qr is left to the camera middle point
                difY = MIDDLE_POINT_CAMERA[1] - y_mid_point  # positive means the qr is above to the camera middle point

                # check if the camera is supposed to move or the QRcode
                if camera_moves:
                    # check if the robot should move in the X direction
                    if x_mid_point < (MIDDLE_POINT_CAMERA[0] + OFFSET_X) and x_mid_point > (
                            MIDDLE_POINT_CAMERA[0] - OFFSET_X):
                        if DEBUG_CODE:
                            print(
                                f"The QR is within {OFFSET_X * REAL_PIXEL_SIZE} mm of the centre of the camera in the X direction, fault is {difX} pixels")
                        # this value means the camera is within the expected offset
                        movement[0] = 0.000000001
                    elif difX < 0:
                        if DEBUG_CODE:
                            print(f"Please move the camera {difX * REAL_PIXEL_SIZE} mm to the left")
                        movement[0] = abs(difX * REAL_PIXEL_SIZE)
                    else:
                        if DEBUG_CODE:
                            print(f"Please move the camera {difX * REAL_PIXEL_SIZE} mm to the right")
                        movement[0] = -1 * abs(difX * REAL_PIXEL_SIZE)

                    # check if the robot should move in the Y direction
                    if y_mid_point < (MIDDLE_POINT_CAMERA[1] + OFFSET_Y) and y_mid_point > (
                            MIDDLE_POINT_CAMERA[1] - OFFSET_Y):
                        if DEBUG_CODE:
                            print(
                                f"The QR is within {OFFSET_Y * REAL_PIXEL_SIZE} mm of the centre of the camera in the Y direction, fault is {difY} pixels")
                        # this value means the camera is within the expected offset
                        movement[1] = 0.000000001
                    elif difY < 0:
                        if DEBUG_CODE:
                            print(f"Please move the camera {difY * REAL_PIXEL_SIZE} mm up")
                        movement[1] = abs(difY * REAL_PIXEL_SIZE)
                    else:
                        if DEBUG_CODE:
                            print(f"Please move the camera {difY * REAL_PIXEL_SIZE} mm down")
                        movement[1] = -1 * abs(difY * REAL_PIXEL_SIZE)

                    # check if the robot should move around it's base
                    if dif_angle < (0 + OFFSET_ANGLE) and dif_angle > (0 - OFFSET_ANGLE):
                        if DEBUG_CODE:
                            print(
                                f"The QR is within {OFFSET_ANGLE} degrees of the orientation of the camera in the Rz direction, fault is {dif_angle} degrees")
                        # this value means the camera is within the expected offset
                        movement[2] = 0.000000001
                    else:
                        if DEBUG_CODE:
                            print(f"Please turn the camera {dif_angle} degrees {turn_direction}")
                        if turn_direction == "counter clockwise":
                            movement[2] = -1 * math.radians(dif_angle)
                        else:
                            movement[2] = math.radians(dif_angle)
                else:
                    if x_mid_point < (MIDDLE_POINT_CAMERA[0] + OFFSET_X) and x_mid_point > (
                            MIDDLE_POINT_CAMERA[0] - OFFSET_X):
                        print(f"The QR is within {OFFSET_X * REAL_PIXEL_SIZE} mm of the centre of the camera")
                    elif difX > 0:
                        print(f"Please move the QR {difX * REAL_PIXEL_SIZE} mm to the right")
                    else:
                        print(f"Please move the QR {difX * REAL_PIXEL_SIZE} mm to the left")

                    if y_mid_point < (MIDDLE_POINT_CAMERA[1] + OFFSET_Y) and y_mid_point > (
                            MIDDLE_POINT_CAMERA[1] - OFFSET_Y):
                        print(f"The QR is within {OFFSET_Y * REAL_PIXEL_SIZE} mm of the centre of the camera")
                    elif difY > 0:
                        print(f"Please move the QR {difY * REAL_PIXEL_SIZE} mm to the down")
                    else:
                        print(f"Please move the QR {difY * REAL_PIXEL_SIZE} mm to the up")

                    if dif_angle < (0 + OFFSET_ANGLE) and dif_angle > (0 - OFFSET_ANGLE):
                        print(f"The QR is within {OFFSET_ANGLE} degrees of the orientation of the camera")
                    else:
                        print(f"Please turn the QR {dif_angle} degrees {turn_direction}")
        if DEBUG_CODE:
            print("get camera movement: ", movement)
        return frame, movement

    # initialize the camera with the correct settings
    def setup_camera(self, _cam):
        try:
            _cam.ExposureAuto.set('Off')  # turn off auto exposure
            _cam.ExposureTimeAbs.set(80000)  # set exposure time to 80000 micros seconds
            _cam.Gain.set(3)  # set gain to 3
            return True
        except:
            return False

    # function to get a picture
    def get_picture(self):
        with VmbSystem.get_instance() as vmb:
            cams = vmb.get_all_cameras()

            # check if there is a camera
            if not cams:
                print("No Cameras found.")
                return False, [0, 0, 0]

            with cams[0] as cam:
                print(f"Accessed Camera: {cam.get_id()}")

                state_camera = self.setup_camera(cam)

                try:
                    frame = cam.get_frame()

                    # 1. Access Raw Numpy Array
                    img_buffer = frame.as_numpy_ndarray()

                    # 2. Convert BayerRG -> BGR (As confirmed working)
                    img_color = cv2.cvtColor(img_buffer, cv2.COLOR_BayerRG2BGR)

                    # 3. Calculate Pose
                    annotated_img, _movement = self.get_camera_pose(img_color, True)
                    print("get picture movement: ", _movement)

                    return True, _movement

                except Exception as e:
                    print(f"Error: {e}")
                    return False, e

    # function to calibrate the move commandos according to an QRcode
    def calibrate_robot(self):
        """
        Activeert de kalibratieprocedure.
        Vraagt de gebruiker om te bevestigen dat de robot boven de QR-code staat.
        """
        result = self._ask_yes_no_calibration(
            "Robot Kalibratie Bevestiging",
            "Staat de UR10e Cobot boven de QR-code op het object?",
            width=400, height=200
        )

        if result == "Yes":
            self.log_message("USER CONFIRMED: Starting calibration script...")
            self.log_message("EXTERNAL CALL: Requesting camera offset data (X, Y, Z, Rx, Ry, Rz)...")
            self.show_loading("Waiting for camera data...")

            # start the first calibration, here a picture will be taken, will be calculated how much the base joint should move and will the base joint be moved
            if DEBUG_CODE:
                print("first calibration")

            # move robot joints in a position where it SHOULD hang perfect above the QR code
            move_to_positionj_uncalibrated(QRPOSITION)

            # take picture and return the QR position
            camera_present, my_movement = self.get_picture()
            if camera_present == False:
                print("There is no camera present")

            # check if an QR code has actually been found
            elif len(my_movement) == 3 and my_movement[0] != 0 and my_movement[1] != 0 and my_movement[2] != 0:
                # X, Y, Z needs to be in meters for the cobot
                camera_offset_values = [
                    (my_movement[0] / 1000),  # X offset (m)
                    (my_movement[1] / 1000),  # Y offset (m)
                    0,  # Z offset (m)
                    0,  # Rx offset (rad)
                    0,  # Ry offset (rad)
                    my_movement[2]  # Rz offset (rad)
                ]

                # set the offset of the base joint in a global variable
                self._execute_calibration_sequence(camera_offset_values, "joint")

                # apply base joint offset by only moving the base joint (the joint is accidently given back in the wrong +-)
                move_single_joint(-camera_offset_values[5], 0)
            elif len(my_movement) == 3:
                print("No QR code found during first calibration")
            else:
                self.log_message("USER CANCELLED: Error during first calibration.")
                pass

            if DEBUG_CODE:
                input("press key")

            # start the second calibration, here a picture will be taken, will be calculated how much the X and Y should move and will the robot make an linear movement
            # GOOD TO KNOW: the camera is turned 90 degrees compared to the robot, so X of the robot is Y for the camera
            if DEBUG_CODE:
                print("second calibration")

            # take picture and return the QR position
            camera_present, my_movement = self.get_picture()
            if camera_present == False:
                print("There is no camera present")

            # check if an QR code has actually been found
            elif len(my_movement) == 3 and my_movement[0] != 0 and my_movement[1] != 0 and my_movement[2] != 0:
                # X, Y, Z needs to be in meters for the cobot
                camera_offset_values = [
                    (my_movement[0] / 1000),  # X offset (m)
                    (my_movement[1] / 1000),  # Y offset (m)
                    0,  # Z offset (m)
                    0,  # Rx offset (rad)
                    0,  # Ry offset (rad)
                    my_movement[2]  # Rz offset (rad)
                ]

                # set the offset of the X and Y in a global variable
                self._execute_calibration_sequence(camera_offset_values, "calibration")

                # apply X and Y offset by making an linear movement
                move_to_positionl_calibration(camera_offset_values)
            elif len(my_movement) == 3:
                print("No QR code found during second calibration")
            else:
                self.log_message("USER CANCELLED: Error during second calibration.")
                pass

            if DEBUG_CODE:
                input("press key")

            # start the first control calibration. a picture will be taken and it should give back that the robot is in the correct position
            if DEBUG_CODE:
                print("first control calibration")

            # take picture and return the QR position
            camera_present, my_movement = self.get_picture()
            if camera_present == False:
                print("There is no camera present")

            # check if an QR code has actually been found
            elif len(my_movement) == 3 and my_movement[0] != 0 and my_movement[1] != 0 and my_movement[2] != 0:
                # X, Y, Z needs to be in meters for the cobot
                camera_offset_values = [
                    (my_movement[0] / 1000),  # X offset (m)
                    (my_movement[1] / 1000),  # Y offset (m)
                    0,  # Z offset (m)
                    0,  # Rx offset (rad)
                    0,  # Ry offset (rad)
                    my_movement[2]  # Rz offset (rad)
                ]

                # check if the calibration is within accaptable offsets
                if camera_offset_values[0] <= 0.0001 and camera_offset_values[1] <= 0.0001 and camera_offset_values[
                    5] <= 0.0001:
                    print("Calibration was succesful")
                else:
                    print("Calibration failed, couldn't find an correct offset.")
                    # return
            elif len(my_movement) == 3:
                print("No QR code found during second calibration")
            else:
                self.log_message("USER CANCELLED: Error during second calibration.")
                pass

            if DEBUG_CODE:
                input("press key")

            # start the second control calibration. the robot will be moved away, moved to the correct position with the calibrated function and then checked by taking a picture
            if DEBUG_CODE:
                print("second control calibration")

            # move robot joints in a position where it SHOULD hang perfect above the QR code
            move_to_positionj_uncalibrated(QRPOSITION)

            # move robot joints in a position where it WILL hang perfect above the QR code
            move_to_positionj_calibrated_Joints(QRPOSITION)

            # take picture and return the QR position
            camera_present, my_movement = self.get_picture()
            if camera_present == False:
                print("There is no camera present")

            # check if an QR code has actually been found
            elif len(my_movement) == 3 and my_movement[0] != 0 and my_movement[1] != 0 and my_movement[2] != 0:
                # X, Y, Z needs to be in meters for the cobot
                camera_offset_values = [
                    (my_movement[0] / 1000),  # X offset (m)
                    (my_movement[1] / 1000),  # Y offset (m)
                    0,  # Z offset (m)
                    0,  # Rx offset (rad)
                    0,  # Ry offset (rad)
                    my_movement[2]  # Rz offset (rad)
                ]

                # check if the calibration is within accaptable offsets
                if camera_offset_values[0] <= 0.0001 and camera_offset_values[1] <= 0.0001 and camera_offset_values[
                    5] <= 0.0001:
                    print("Calibration was succesful")
                else:
                    print("Calibration failed, couldn't find an correct offset.")
            elif len(my_movement) == 3:
                print("No QR code found during second calibration")
            else:
                self.log_message("USER CANCELLED: Error during second calibration.")
                pass

        elif result == "No":
            self.log_message("USER CANCELLED: Calibration script NOT started.")
            pass
        else:  # Window closed without clicking a button
            self.log_message("Calibration window closed without selection.")

    def _open_manual_drive_window(self):
        """
        Opent het venster voor positionering en kalibratie.
        """
        # Reset de variabelen om zeker te zijn dat ze leeg beginnen
        self.drive_dialog = None
        self.hold_btn = None
        self.calibrate_btn = None

        # Maak een nieuw toplevel venster
        self.drive_dialog = tk.Toplevel(self.root)
        self.drive_dialog.title("Robot Kalibratie")
        self.drive_dialog.geometry("500x450")
        self.drive_dialog.transient(self.root)
        self.drive_dialog.grab_set()
        self.drive_dialog.configure(bg=self.colors["background"])

        # Zorg dat variabelen worden gewist als het scherm wordt gesloten (kruisje)
        self.drive_dialog.protocol("WM_DELETE_WINDOW", self._on_drive_window_close)

        # Header
        header_label = tk.Label(self.drive_dialog, text="Stap 1: Positionering",
                                bg=self.colors["primary"], fg=self.colors["text_light"],
                                font=("Arial", 12, "bold"), pady=10)
        header_label.pack(fill=tk.X)

        # Instructie tekst
        instruction_frame = tk.Frame(self.drive_dialog, bg=self.colors["background"], padx=20, pady=20)
        instruction_frame.pack(fill=tk.BOTH, expand=True)

        msg = ("Zorg dat de robot in de startpositie staat voor de camera.\n\n"
               "1. Staat de robot NIET goed? \n   Houd de 'Naar Startpositie' knop ingedrukt.\n"
               "2. Is de positie bereikt? \n   Druk op 'Lees QR & Kalibreer'.")

        lbl_instruction = tk.Label(instruction_frame, text=msg,
                                   bg=self.colors["background"], fg=self.colors["text_dark"],
                                   font=("Arial", 11), justify=tk.LEFT)
        lbl_instruction.pack(pady=(0, 20), fill=tk.X)

        # --- KNOP 1: BEWEGEN (HOLD TO RUN) ---
        # Let op: 'self.hold_btn' zodat hij in de hele klasse beschikbaar is
        self.hold_btn = tk.Button(instruction_frame, text="HOUD INGEDRUKT\nNaar Startpositie",
                                  bg=self.colors["secondary"], fg=self.colors["text_light"],
                                  font=("Arial", 11, "bold"),
                                  activebackground=self.colors["success"],
                                  activeforeground=self.colors["text_light"],
                                  pady=10, bd=0, cursor="hand2")
        self.hold_btn.pack(fill=tk.X, padx=10, pady=(0, 20))

        # Event Bindings
        self.hold_btn.bind('<ButtonPress-1>', self._start_moving_to_qr)
        self.hold_btn.bind('<ButtonRelease-1>', self._stop_moving_robot)

        # --- KNOP 2: KALIBREREN ---
        # Let op: 'self.calibrate_btn' zodat hij in de hele klasse beschikbaar is
        self.calibrate_btn = tk.Button(instruction_frame, text="Lees QR & Kalibreer Cobot",
                                       bg=self.colors["accent"], fg="white",
                                       state="disabled",
                                       font=("Arial", 12, "bold"),
                                       command=self._run_calibration_process,
                                       pady=15, bd=0)
        self.calibrate_btn.pack(fill=tk.X, padx=10)

        # Sluit knop
        close_btn = ttk.Button(self.drive_dialog, text="Annuleren", command=self._on_drive_window_close)
        close_btn.pack(pady=10)

        # Start positie check
        self.run_in_thread(self._check_initial_position)

    def _check_initial_position(self):
        """Checkt bij openen venster of robot toevallig al goed staat."""
        target_deg = [-112.83, -34.59, -17.83, 52.15, 60.38, -90.04]
        target_rad = [math.radians(angle) for angle in target_deg]

        # Check positie
        if is_joint_goal_reached(target_rad, tolerance=0.01):
            print("DEBUG: Direct al op positie bij openen scherm!")
            # Veilige UI update
            self.root.after(0, self._enable_calibration_button)

    def _enable_calibration_button(self):
        """
        Maakt de kalibratieknop groen en klikbaar.
        Bevat extra checks en fallbacks.
        """
        print("DEBUG: _enable_calibration_button wordt uitgevoerd in Main Thread.")

        succes = False

        # POGING 1: Probeer de Calibrate knop te activeren
        try:
            if hasattr(self, 'calibrate_btn') and self.calibrate_btn is not None:
                # Check of widget nog bestaat in Tcl/Tk
                if self.calibrate_btn.winfo_exists():
                    self.calibrate_btn.config(state="normal", bg=self.colors["success"], cursor="hand2")
                    succes = True
                    print("DEBUG: Calibrate knop succesvol geactiveerd.")
                else:
                    print("DEBUG: Calibrate knop variabele bestaat, maar widget is destroyed.")
            else:
                print("DEBUG: self.calibrate_btn is None of bestaat niet.")
        except Exception as e:
            print(f"DEBUG: Fout bij update calibrate_btn: {e}")

        # POGING 2: Probeer de Hold knop te updaten (als visuele bevestiging)
        try:
            if hasattr(self, 'hold_btn') and self.hold_btn is not None:
                if self.hold_btn.winfo_exists():
                    # Tekst aanpassen zodat je weet dat je klaar bent
                    self.hold_btn.config(text="POSITIE BEREIKT!\nGebruik Kalibreer knop",
                                         bg=self.colors["success"])
                    print("DEBUG: Hold knop succesvol geupdate.")
                else:
                    print("DEBUG: Hold knop widget destroyed.")
        except Exception as e:
            print(f"DEBUG: Fout bij update hold_btn: {e}")

        # FAILSAFE: Als alles faalt, probeer het venster titel of log
        if not succes:
            self.log_message("LET OP: Positie bereikt, maar kon knop niet activeren.")
            # Als laatste redmiddel: probeer het venster opnieuw te initialiseren als de gebruiker vast zit
            # maar dat is riskant. Voor nu vertrouwen we op de log.

    def _execute_calibration_sequence(self, offset_data, mode):

        # saves the offset in the correct variable
        if mode == "calibration":
            if set_global_calibration_offset(offset_data):
                self.log_message(f"Calibration successful! Offset [{offset_data}] applied.")
            else:
                self.log_message("Error: Failed to set calibration offset.")
        elif mode == "joint":
            if set_global_joint_offset(offset_data):
                self.log_message(f"Calibration successful! Offset [{offset_data}] applied to joints.")
            else:
                self.log_message("Error: Failed to set calibration offset.")

        # 2. Verberg de laadmelding
        self.root.after(0, self.hide_loading)

    def _ask_yes_no_calibration(self, title, prompt, width=300, height=150):
        """
        Aangepaste pop-up voor Ja/Nee-bevestiging, aangepast aan het thema.
        Returns: "Yes", "No", of None
        """
        self.dialog_result = None

        # Maak een nieuw toplevel venster
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.resizable(False, False)
        dialog.transient(self.root)  # Blijft boven de hoofdtoepassing
        dialog.grab_set()  # Blokkeer interactie met andere vensters

        # Functie om het venster te sluiten en de keuze vast te leggen
        def on_close(choice=None):
            self.dialog_result = choice
            dialog.destroy()
            self.root.event_generate("<<DialogClosed>>")  # Genereer een event

        # Centraal Frame met thema-kleuren
        main_frame = tk.Frame(dialog, bg=self.colors["background"], padx=15, pady=15)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Label voor de vraag (Prompt)
        prompt_label = tk.Label(main_frame, text=prompt,
                                bg=self.colors["background"], fg=self.colors["text_dark"],
                                font=("Arial", 10))
        prompt_label.pack(pady=10)

        # Container voor de knoppen
        button_frame = tk.Frame(main_frame, bg=self.colors["background"])
        button_frame.pack(pady=10)

        # 'Ja' Knop (Succes/Doorgaan)
        yes_button = ttk.Button(button_frame, text="Ja",
                                command=lambda: on_close("Yes"),
                                style="TButton",  # Gebruik de standaard (blauwe) stijl
                                width=10)
        yes_button.pack(side=tk.LEFT, padx=10)

        # 'Nee' Knop (Annuleren/Stoppen)
        no_button = ttk.Button(button_frame, text="Nee",
                               command=lambda: on_close("No"),
                               style="Danger.TButton",  # Gebruik de rode 'Danger' stijl
                               width=10)
        no_button.pack(side=tk.LEFT, padx=10)

        # Wacht tot het venster is gesloten
        dialog.wait_window(dialog)

        return self.dialog_result

    # ------------------------------------------
    # HIER ZOUDEN DE NIEUWE CALIBRATIE EXECUTION FUNCTIES KOMEN
    # ------------------------------------------

    # def _execute_calibration_sequence(self):
    #     """Simuleert de kalibratie-uitvoering."""
    #     # 1. Roep de RoboDK/UR-functie aan die de camerawaarden ophaalt
    #     # data = get_camera_six_values()
    #     # 2. Vertaal deze data naar een Pose
    #     # 3. Roep de RoboDK-API aan om het werkframe aan te passen
    #     self.hide_loading()
    #     self.log_message("Calibration successful! New work frame set.")

    # def move_robot_to_home(self):
    #     """Simuleert het sturen van de robot naar de Home positie."""
    #     # self.log_message("Moving robot to Home position...")
    #     # move_to_home() # of een andere RTDE functie
    #     # self.log_message("Robot is at Home position.")
    #     pass

    def _open_manual_drive_window(self):
        """
        Opent het venster voor positionering en kalibratie.
        """
        # 1. Reset eerst alle referenties veilig
        self.drive_dialog = None
        self.hold_btn = None
        self.calibrate_btn = None

        # 2. Maak venster
        self.drive_dialog = tk.Toplevel(self.root)
        self.drive_dialog.title("Robot Kalibratie")
        self.drive_dialog.geometry("500x450")
        self.drive_dialog.transient(self.root)
        self.drive_dialog.grab_set()
        self.drive_dialog.configure(bg=self.colors["background"])

        # Koppel de sluit-actie aan onze opruimfunctie
        self.drive_dialog.protocol("WM_DELETE_WINDOW", self._on_drive_window_close)

        # Header
        header_label = tk.Label(self.drive_dialog, text="Stap 1: Positionering",
                                bg=self.colors["primary"], fg=self.colors["text_light"],
                                font=("Arial", 12, "bold"), pady=10)
        header_label.pack(fill=tk.X)

        # Instructie tekst
        instruction_frame = tk.Frame(self.drive_dialog, bg=self.colors["background"], padx=20, pady=20)
        instruction_frame.pack(fill=tk.BOTH, expand=True)

        msg = ("Zorg dat de robot in de startpositie staat voor de camera.\n\n"
               "1. Staat de robot NIET goed? \n   Houd de 'Naar Startpositie' knop ingedrukt.\n"
               "2. Is de positie bereikt? \n   Druk op 'Lees QR & Kalibreer'.")

        lbl_instruction = tk.Label(instruction_frame, text=msg,
                                   bg=self.colors["background"], fg=self.colors["text_dark"],
                                   font=("Arial", 11), justify=tk.LEFT)
        lbl_instruction.pack(pady=(0, 20), fill=tk.X)

        # --- KNOP 1: BEWEGEN (HOLD TO RUN) ---
        # We wijzen dit toe aan self.hold_btn
        self.hold_btn = tk.Button(instruction_frame, text="HOUD INGEDRUKT\nNaar Startpositie",
                                  bg=self.colors["secondary"], fg=self.colors["text_light"],
                                  font=("Arial", 11, "bold"),
                                  activebackground=self.colors["success"],
                                  activeforeground=self.colors["text_light"],
                                  pady=10, bd=0, cursor="hand2")
        self.hold_btn.pack(fill=tk.X, padx=10, pady=(0, 20))

        # Events
        self.hold_btn.bind('<ButtonPress-1>', self._start_moving_to_qr)
        self.hold_btn.bind('<ButtonRelease-1>', self._stop_moving_robot)

        # --- KNOP 2: KALIBREREN ---
        # BELANGRIJK: We wijzen dit toe aan self.calibrate_btn
        self.calibrate_btn = tk.Button(instruction_frame, text="Lees QR & Kalibreer Cobot",
                                       bg=self.colors["accent"], fg="white",
                                       state="disabled",
                                       font=("Arial", 12, "bold"),
                                       command=self._run_calibration_process,
                                       pady=15, bd=0)
        self.calibrate_btn.pack(fill=tk.X, padx=10)

        print("DEBUG: Knoppen zijn aangemaakt en toegewezen aan self.")  # DEBUG CHECK

        # Sluit knop
        close_btn = ttk.Button(self.drive_dialog, text="Annuleren", command=self._on_drive_window_close)
        close_btn.pack(pady=10)

        # Start check
        self.run_in_thread(self._check_initial_position)

    def _start_moving_to_qr(self, event):
        """Wordt aangeroepen als je de knop INDRUKT."""
        print("DEBUG: Knop INGEDRUKT detected!")  # <--- Check of je dit ziet

        self.manual_move_active = True

        # Check of de knop bestaat voordat we tekst aanpassen
        if hasattr(self, 'hold_btn') and self.hold_btn:
            self.hold_btn.config(bg=self.colors["secondary"], text="BEWEGEN... (Houd vast)")

        # Start de thread die de commando's stuurt
        self.run_in_thread(self._execute_move_to_fixed_pos)

    def _stop_moving_robot(self, event):
        """Wordt aangeroepen als je de knop LOSLAAT."""
        print("DEBUG: Knop LOSGELATEN detected!")  # <--- Check of je dit ziet

        self.manual_move_active = False
        stop_robot_movement()

        # Reset tekst alleen als we nog NIET klaar zijn (kalibreer knop disabled)
        try:
            # Check of we al klaar zijn (dan is calibrate_btn 'normal')
            finished = False
            if hasattr(self, 'calibrate_btn') and self.calibrate_btn:
                if self.calibrate_btn['state'] == 'normal':
                    finished = True

            # Als we nog niet klaar zijn, zet tekst terug
            if not finished:
                if hasattr(self, 'hold_btn') and self.hold_btn:
                    self.hold_btn.config(bg=self.colors["secondary"], text="HOUD INGEDRUKT\nNaar Startpositie")

        except Exception as e:
            print(f"DEBUG: Fout bij stop update: {e}")

    def _execute_move_to_fixed_pos(self):
        """
        De lus die de robot aanstuurt.
        """
        print("DEBUG: Thread _execute_move_to_fixed_pos is gestart.")

        # 1. Doel posities
        target_deg = [-96.69, -117.26, 101.84, 15.45, 86.05, -90.09]
        target_rad = [math.radians(angle) for angle in target_deg]

        # 2. Check limieten
        if not check_joint_limits(target_rad):
            print("DEBUG: FOUT - Buiten joint limieten!")
            self.root.after(0, lambda: self.hold_btn.config(bg=self.colors["danger"], text="FOUT: Buiten Bereik"))
            return

        try:
            print("DEBUG: Stuur move_to_positionj commando...")
            # 3. Stuur commando
            move_to_positionj(target_rad, speed=0.5, acceleration=0.5, asynchronous=True)

            # 4. Monitor lus
            while self.manual_move_active:
                # Check of we er zijn
                if is_joint_goal_reached(target_rad, tolerance=0.005):
                    print("DEBUG: DOEL BEREIKT!")
                    self.log_message("Startpositie BEREIKT!")

                    stop_robot_movement()
                    self.manual_move_active = False

                    # Update de UI (Knoppen activeren)
                    self.root.after(0, self._enable_calibration_button)
                    break

                # Slaap kort om CPU te sparen
                time.sleep(0.1)

        except Exception as e:
            print(f"DEBUG: CRASH in bewegings-thread: {e}")
            self.log_message(f"Fout tijdens bewegen: {e}")

    def _run_calibration_process(self):
        """
        Wordt aangeroepen door de 'Lees QR & Kalibreer' knop.
        Sluit het venster en voert de camera-detectie uit.
        """
        # 1. Sluit het positioneringsvenster
        self.drive_dialog.destroy()

        # 2. Voer de logica uit die vroeger onder 'if result == "Yes":' stond
        self.log_message("Start kalibratie sequence...")
        self.show_loading("Camera data verwerken...")

        # Start dit in een thread zodat de GUI niet bevriest tijdens camera analyse
        self.run_in_thread(self._process_camera_and_calibrate)

    def _process_camera_and_calibrate(self):
        """De camera logica en offset berekening."""
        try:
            # Camera code (overgenomen van je originele bestand)
            camera_present = True
            if camera_present:
                camera_present, my_movement = self.get_picture()

                if camera_present == False:
                    print("There is no camera")
                    self.log_message("Error: Geen camera gevonden.")
                    self.root.after(0, self.hide_loading)
                    return

                if len(my_movement) == 3 and (my_movement[0] != 0 or my_movement[1] != 0 or my_movement[2] != 0):
                    # X, Y, Z needs to be in meters for the cobot
                    camera_offset_values = [
                        (my_movement[0] / 1000),  # X offset (m)
                        (my_movement[1] / 1000),  # Y offset (m)
                        0,  # Z offset (m)
                        0,  # Rx offset (rad)
                        0,  # Ry offset (rad)
                        my_movement[2]  # Rz offset (rad)
                    ]
                    self.log_message(f"QR Gevonden. Offset: {camera_offset_values}")
                elif len(my_movement) == 3:
                    print("No QR code found")
                    self.log_message("Geen QR code gevonden.")
                    self.root.after(0, self.hide_loading)
                    return
                else:
                    self.log_message("Fout bij verwerken camera beeld.")
                    self.root.after(0, self.hide_loading)
                    return
            else:
                # Fallback dummy waarden
                camera_offset_values = [0, 0, 0, 0, 0, 0]

            # Pas offset toe
            self._execute_calibration_sequence(camera_offset_values)

        except Exception as e:
            self.log_message(f"Fout in kalibratieproces: {e}")
            self.root.after(0, self.hide_loading)

    def _on_drive_window_close(self):
        """Wordt aangeroepen als het kalibratiescherm sluit."""
        self.manual_move_active = False  # Stop eventuele loops
        stop_robot_movement()  # Stop de robot
        if self.drive_dialog:
            self.drive_dialog.destroy()
        # Reset referenties om AttributeErrors te voorkomen bij threads die nog draaien
        self.drive_dialog = None
        self.calibrate_btn = None
        self.hold_btn = None

    def stop_start_feederloop(self):
         import GUI.feeder_IO as feeder_IO
         # We gebruiken een variabele om de status bij te houden in de GUI
         if not hasattr(self, 'feeder_active'):
             self.feeder_active = False

         if not self.feeder_active:
             # STARTEN
             self.feeder_active = True
             self.log_message("Feeder Loop gestart.")
             # Start de loop in een thread zodat de GUI niet bevriest
             self.feeder_thread = threading.Thread(target=feeder_IO.run_feeder_loop, daemon=True)
             self.feeder_thread.start()
             # Optioneel: verander kleur van de knop (je moet de knop dan wel opslaan als self.btn_feeder)
         else:
             # STOPPEN
             self.feeder_active = False
             feeder_IO.stop_feeder_loop()
             self.log_message("Feeder Loop stop-commando verzonden...")