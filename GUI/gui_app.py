import re
import threading
import time
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog

from requests_interface import *
from rtde_interface import *
from socketio_interface import *
from rtde_interface import is_robot_physically_moving
from requests_interface import check_busy
import cobotrack_interface


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
        self.running = False # for starting and stopping script
        self.debug = True

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
        socketio_interface.gui_app_instance = self
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
        data = socketio_interface.get_screwdriver_data()

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
        self.tab_control.add(self.tab3, text="SD - Functions")
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

        btn_stop_script = ttk.Button(button_frame, text="Stop Script", command=self.stop_script, width=18)
        btn_stop_script.pack(pady=8, padx=5, fill=tk.X)

        btn_start_script = ttk.Button(button_frame, text="Start Script", command=self.start_script, width=18)
        btn_start_script.pack(pady=8, padx=5, fill=tk.X)

        btn_indraaien = ttk.Button(button_frame, text="Tightening", command=self.run_indraaien, width=18)
        btn_indraaien.pack(pady=8, padx=5, fill=tk.X)

        btn_uitdraaien = ttk.Button(button_frame, text="Unscrewing", command=self.run_uitdraaien, width=18)
        btn_uitdraaien.pack(pady=8, padx=5, fill=tk.X)

        btn_check_connections = ttk.Button(button_frame, text="Check connections", command=self.check_connections,
                                           width=18)
        btn_check_connections.pack(pady=8, padx=5, fill=tk.X)

        btn_refresh_status = ttk.Button(button_frame, text="Refresh Status", command=self.update_screwdriver_data,
                                        width=18)
        btn_refresh_status.pack(pady=8, padx=5, fill=tk.X)


    def stop_script(self):
        self.running = 0
        self.log_message("Script Stopping !")

    def start_script(self):
        self.running = 1
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
        self.tab_control.add(self.tab3, text="Cobotrack")
        self.tab_control.pack(expand=1, fill=tk.BOTH)

        # Status-tab
        self.setup_status_tab()

        # Cobotrack tab
        self.setup_cobotrack_tab()

        # Logs-tab
        self.setup_logs_tab()

    def setup_status_tab(self):
        """
        Set up the status tab for system information.
        Displays connection status and screwdriver data.
        """
        # Create a card-like container for status info
        status_card = tk.Frame(self.tab1, bg=self.colors["accent"],
                               relief=tk.RIDGE, borderwidth=1, padx=15, pady=15)
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

    def setup_cobotrack_tab(self):
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

    def load_script(self):
        """
        Open a file dialog to select a script file.
        Parses and displays the commands found in the script.
        """
        file_path = filedialog.askopenfilename(
            title="Select Script File",
            filetypes=(("Script files", "*.script"), ("All files", "*.*"))
        )
        self.running = 1 # reset var running by setting it

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
            if line.startswith(('movej', 'movel', 'move_shank', 'move_to')):
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
        Supports movej, movel, move_shank, and move_to commands.

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
                pose_trans_match = re.match(r'movel\(pose_trans\([^,]+,p\[([-\d., ]+)\][^)]*\)', command)

                if bracket_match:
                    # Format: movel([2.959485, -2.090817, ...])
                    joints_str = bracket_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    print(f"Running: movel - joints {joints}")
                    self.log_message(f"Running: movel - joints {joints}")

                    if not self.debug:
                     move_to_positionl(joints)

                elif p_match:
                    # Format: movel(p[-0.969933, 0.499379, ...])
                    joints_str = p_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    print(f"Running: movel - joints {joints}")
                    self.log_message(f"Running: movel - joints {joints}")

                    if not self.debug:
                     move_to_positionl(joints)

                elif pose_trans_match:
                    # Format: movel(pose_trans(ref_frame,p[0.282414, 0.145343, ...]),accel,speed,...)
                    joints_str = pose_trans_match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    print(f"Running: movel with pose_trans - joints {joints}")
                    self.log_message(f"Running: movel with pose_trans - joints {joints}")

                    if not self.debug:
                     move_to_positionl(joints)

                else:
                    print(f"Couldn't find joint values in command: {command}")
                    self.log_message(f"Couldn't find joint values in command: {command}")

                    # UR10e movej command
            elif command.startswith('movej'):
                    # Standard format: movej([joints])
                    bracket_match = re.match(r'movej\(\[([-\d., ]+)\]', command)
                    # p format: movej(p[joints])
                    p_match = re.match(r'movej\(p\[([-\d., ]+)\]', command)
                    # pose_trans format: movej(pose_trans(ref_frame,p[joints]),accel,speed,blend,etc)
                    pose_trans_match = re.match(r'movej\(pose_trans\([^,]+,p\[([-\d., ]+)\][^)]*\)', command)

                    if bracket_match:
                        # Format: movej([2.959485, -2.090817, ...])
                        joints_str = bracket_match.group(1)
                        joints = [float(j.strip()) for j in joints_str.split(',')]

                        print(f"Running: movej - joints {joints}")
                        self.log_message(f"Running: movej - joints {joints}")

                        if not self.debug:
                         move_to_positionj(joints)

                    elif p_match:
                        # Format: movej(p[-0.969933, 0.499379, ...])
                        joints_str = p_match.group(1)
                        joints = [float(j.strip()) for j in joints_str.split(',')]

                        print(f"Running: movej - joints {joints}")
                        self.log_message(f"Running: movej - joints {joints}")

                        if not self.debug:
                         move_to_positionj(joints)

                    elif pose_trans_match:
                        # Format: movej(pose_trans(ref_frame,p[0.282414, 0.145343, ...]),accel,speed,...)
                        joints_str = pose_trans_match.group(1)
                        joints = [float(j.strip()) for j in joints_str.split(',')]

                        print(f"Running: movej with pose_trans - joints {joints}")
                        self.log_message(f"Running: movej with pose_trans - joints {joints}")

                        if not self.debug:
                         move_to_positionj(joints)

                    else:
                        print(f"Couldn't find joint values in command: {command}")
                        self.log_message(f"Couldn't find joint values in command: {command}")

            # Screwdriver move_shank command
            elif command.startswith('move_shank'):
                # Parse move_shank command
                match = re.match(r'move_shank\((\d+)\)', command)
                if match:
                    value = int(match.group(1))
                    print(f"Running: move_shank({value})")
                    move_shank(value)
                else:
                    print(f"Invalid move_shank command: {command}")

            # cobotrack move_to command
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

    def run_indraaien(self):
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

    # ------------------------------------------
    # Cobotrack Control Functions
    # ------------------------------------------

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
            print(f"Raw response from cobotrack_interface: {response}")  # Debug: Print raw response

            if response:  # Check if the response is not empty
                print("Response is not empty.")  # Debug: Confirm response is not empty
                try:
                    # Extract the integer value from the response string
                    if response.startswith("COBOTRACK_STATUS_INT:"):
                        #print("Response starts with 'COBOTRACK_STATUS_INT:'.")  # Debug: Confirm correct prefix
                        # Split the string to get the integer part
                        status_word_str = response.split(":")[1].strip()  # Extract the part after the colon
                        #print(f"Extracted status word string: '{status_word_str}'")  # Debug: Print extracted string
                        status_word = int(status_word_str)  # Convert to integer
                        #print(f"Converted status word to integer: {status_word}")  # Debug: Print converted integer
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
                    #print(f"Active statuses: {active_statuses}")  # Debug: Print active statuses
                    status_text = " | ".join(active_statuses)
                    #print(f"Final status text: {status_text}")  # Debug: Print final status text
                    self.cobotrack_status_display.config(text=f"Status: {status_text}")
                except (ValueError, TypeError, IndexError) as e:
                    # Handle errors (e.g., invalid format, conversion failure, etc.)
                    print(f"Error occurred: {e}")  # Debug: Print error
                    self.cobotrack_status_display.config(text=f"Status: Unknown (Error: {str(e)})",
                                                         fg=self.colors["danger"])
            else:
                print("Response is empty or None.")  # Debug: Confirm response is empty
                self.cobotrack_status_display.config(text="Status: Connection Lost!", fg=self.colors["danger"])
                self.stop_cobotrack()

            time.sleep(0.4)  # Update every second

    # ------------------------------------------
    # Connection and Utility Functions
    # ------------------------------------------

    def check_connections_periodically(self):
        """
        Check connections periodically and update the display.
        Sets a timer to repeat the check every 5 seconds.
        """
        self.check_connections()
        self.root.after(5000, self.check_connections_periodically)  # repeat every 5 secs

    def check_connections(self):
        """
        Check connections to RTDE, Socket.IO, and Cobotrack.
        Updates the status display with connection status.
        """
        rtde_conn = initialize_rtde()
        rtde_status = "RTDE connected" if rtde_conn else "RTDE not connected"
        socketio_status = "Socket.IO connected" if sio.connected else "Socket.IO not connected"
        cobotrack_interface.connect()
        cobotrack_status = "Cobotrack connected" if cobotrack_interface.is_connected() else "Cobotrack not connected"

        self.status_label.config(text=f"Status: {rtde_status} | {socketio_status} | {cobotrack_status}")

        if rtde_conn and sio.connected and cobotrack_status:
            self.status_canvas.itemconfig(self.status_indicator, fill=self.colors["success"])
        else:
            self.status_canvas.itemconfig(self.status_indicator, fill=self.colors["danger"])
            self.log_message("Connection failed!")

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

    def run_in_thread(self, func, *args):
        """execute function in a different thread."""
        thread = threading.Thread(target=func, args=args)
        thread.start()