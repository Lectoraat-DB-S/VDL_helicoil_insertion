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


class GUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VDL_ETG")
        self.root.geometry("1000x600")  # GUI size

        # Set the GUI instance before starting Socket.IO
        socketio_interface.gui_app_instance = self
        print("[INFO] GUI instance set in socketio_interface.")  # Debugging print

        # Frames for layouts
        self.left_frame = tk.Frame(root, bg="lightgray", width=300)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.right_frame = tk.Frame(root, bg="white", width=700)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # GUI setup
        self.setup_left_side()
        self.setup_right_side()

        # Start a thread for WebSocket connection and data updates
        threading.Thread(target=self.start_socket_io, daemon=True).start()

        self.update_screwdriver_data_periodically()  # Start automatic update

        # Check connections periodically
        # self.check_connections_periodically()

    def start_socket_io(self):
        """Connect to the Socket.io server and keep the connection alive"""
        while True:
            if connect_to_server():
                print("[INFO] Connected to server. Waiting for messages...")
                sio.wait()  # Keep the connection alive
            else:
                print("[ERROR] Unable to connect. Retrying in 5 seconds...")
                time.sleep(5)  # Wait before retrying

    def update_screwdriver_data(self):
        """Update the GUI with the latest screwdriver data."""
        data = socketio_interface.get_screwdriver_data()

        if data:
            status = "Busy" if data.get("screwdriver_busy", False) else "Not busy"
            shank_position = round(data.get("shank_position", 0), 2)
            current_torque = round(data.get("current_torque", 0), 3)

            self.screwdriver_label.config(
                text=f"Screwdriver status: {status}\n"
                     f"Shank position: {shank_position} mm\n"
                     f"Current torque: {current_torque} Nm",
                fg="green"
            )
            # print("[SUCCESS] GUI updated with new screwdriver data!")  # Debugging print
        else:
            self.screwdriver_label.config(text="Screwdriver data: Not available", fg="red")

    def update_screwdriver_data_periodically(self):
        """Periodically update the screwdriver data in the GUI."""
        self.update_screwdriver_data()
        self.root.after(1000, self.update_screwdriver_data_periodically)

    def setup_left_side(self):
        self.tab_control = ttk.Notebook(self.left_frame)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab3, text="SD - Functions")
        self.tab_control.add(self.tab4, text="General")

        self.tab_control.pack(expand=1, fill=tk.BOTH, padx=10, pady=10)

        # Setup screwdriver functions tab
        self.setup_sd_functions_tab()

        # Setup generic functions tab
        self.setup_generic_tab()

    def setup_sd_functions_tab(self):
        status_frame = tk.Frame(self.tab3)
        status_frame.pack(pady=10)

        btn_move_shank = tk.Button(status_frame, text="Move shank", command=self.run_move_shank, width=20)
        btn_move_shank.pack(pady=10)

        btn_pick_screw = tk.Button(status_frame, text="Pick screw", command=self.run_pick_screw, width=20)
        btn_pick_screw.pack(pady=10)

        btn_premount_screw = tk.Button(status_frame, text="Pre-mount screw", command=self.run_premount_screw, width=20)
        btn_premount_screw.pack(pady=10)

        btn_tighten_screw = tk.Button(status_frame, text="Tighten screw", command=self.run_tighten_screw, width=20)
        btn_tighten_screw.pack(pady=10)

        btn_loosen_screw = tk.Button(status_frame, text="Loosen screw", command=self.run_loosen_screw, width=20)
        btn_loosen_screw.pack(pady=10)

    def _run_operation(self, operation_name, prompts, operation_func):
        """
        Generic method to run an operation with user input and threading.

        :param operation_name: Name of the operation for dialog and logging
        :param prompts: List of input prompts
        :param operation_func: Function to execute the actual operation
        """
        values = self.get_input_values(operation_name, prompts)
        if values:
            self.run_in_thread(self._execute_operation, operation_name, operation_func, *values)

    def _execute_operation(self, operation_name, operation_func, *args):
        """
        Generic method to execute an operation and log results.

        :param operation_name: Name of the operation for logging
        :param operation_func: Function to execute the actual operation
        :param args: Arguments for the operation function
        """
        try:
            operation_func(*args)
            self.log_message(f"Success {operation_name} completed!")
        except Exception as e:
            self.log_message(f"Error {operation_name} failed: {str(e)}")

    def run_move_shank(self):
        """Execute the move_shank function with an input value."""
        value = simpledialog.askfloat("Move Shank", "Enter the shank position (0-55):")
        if value is not None:
            self.run_in_thread(self._execute_operation, "Move shank", move_shank, value)

    def run_pick_screw(self):
        """Execute the pick_screw function with input values."""
        prompts = ["Enter the shank force (N):", "Enter the screwing length (mm):"]
        self._run_operation("Pick Screw", prompts, pick_screw)

    def run_premount_screw(self):
        """Execute the premount_screw function with input values."""

        prompts = [
            "Shank force (N):",
            "Screwing lengte (mm):",
            "Torque (Nm):"
        ]
        self._run_operation("Pre-mount Screw", prompts, premount_screw)

    def run_tighten_screw(self):
        """Run tighten screw with the filled in data"""
        prompts = [
            "shank force (N):",
            "Screwing length (mm):",
            "Torque (Nm):"
        ]
        self._run_operation("Tighten Screw", prompts, tighten_screw)

    def run_loosen_screw(self):
        """Run loosen_screw with the filled in data."""
        prompts = [
            "Shank force (N):",
            "Unscrewing length (mm):"
        ]
        self._run_operation("Loosen Screw", prompts, loosen_screw)

    def setup_generic_tab(self):
        status_frame = tk.Frame(self.tab4)
        status_frame.pack(pady=10)

        """Buttons on leftside of the gui."""

        # Voeg een knop toe om een scriptbestand te selecteren
        btn_load_script = tk.Button(status_frame, text="Load Script", command=self.load_script, width=20)
        btn_load_script.pack(pady=10)

        btn_indraaien = tk.Button(status_frame, text="Tightening", command=self.run_indraaien, width=20)
        btn_indraaien.pack(pady=10)

        btn_uitdraaien = tk.Button(status_frame, text="Unscrewing", command=self.run_uitdraaien, width=20)
        btn_uitdraaien.pack(pady=10)

        btn_check_connections = tk.Button(status_frame, text="Check connections", command=self.check_connections,
                                          width=20)
        btn_check_connections.pack(pady=10)

        btn_refresh_status = tk.Button(status_frame, text="Refresh Status", command=self.update_screwdriver_data,
                                       width=20)
        btn_refresh_status.pack(pady=10)

    def load_script(self):
        """Open a window to select a script"""
        file_path = filedialog.askopenfilename(
            title="Selecteer het scriptbestand",
            filetypes=(("Python files", "*.py"), ("All files", "*.*"))
        )
        if file_path:
            commands = self.parse_script(file_path)
            self.display_commands(commands)

    def parse_script(self, file_path):
        """Parse the script and extract the commands."""
        commands = []
        with open(file_path, 'r') as file:
            for line in file:
                # Remove whitespace at the beginning and at the end
                line = line.strip()

                # Check if line begins with:
                if line.startswith(('movej', 'movel', 'move_shank')):
                    commands.append(line)
        return commands

    def display_commands(self, commands):
        """Show parsed commands and execute them one by one."""
        self.log_message("\nParsed commands: ")

        def execute_commands_with_delay(commands):
            for i, command in enumerate(commands):
                self.log_message(f"{i + 1}: {command}")  # log command

                # Check if robot or screwdriver is busy
                while is_robot_physically_moving(debug=True) or check_busy():

                    time.sleep(0.5)  # wait 500ms until robot is ready
                    self.log_message("Waiting until robot is ready")

                self.execute_command(command)

                # wait a second before executing the next one
                time.sleep(1)

        # Run function in a different thread
        self.run_in_thread(execute_commands_with_delay, commands)

    def execute_command(self, command):
        try:
            if command.startswith('movej'):
                # regex that's only filtering the joint values
                match = re.match(r'movej\(\[([-\d., ]+)\]', command)

                if match:
                    # Saving joint values
                    joints_str = match.group(1)
                    joints = [float(j.strip()) for j in joints_str.split(',')]

                    self.log_message(f"Running: movej - joints {joints}")

                    # Move to position
                    move_to_position(joints)

                else:
                    self.log_message(f"Couldn't find joint values in command: {command}")
                    print(f"Couldn't find joint values in command: {command}")

            # elif command.startswith('movel'):
            #
            #     match = re.match(r'movel\(pose_trans\(ref_frame,p\[([-\d., ]+)\]\)', command)
            #     if match:
            #         position = [float(p.strip()) for p in match.group(1).split(',')]
            #
            #
            #         self.log_message(f"Uitvoeren: movel met positie {position}")
            #
            #         if initialize_rtde() and rtde_c:
            #             rtde_c.moveL(position, speed, acceleration)
            #             print(f"moveL wordt uitgevoerd met positie: {position}")
            #         else:
            #             self.log_message("RTDE control interface is niet verbonden.")
            #     else:
            #         self.log_message(f"Kon geen positie vinden in commando: {command}")

            elif command.startswith('move_shank'):
                # Parseer move_shank commando
                match = re.match(r'move_shank\((\d+)\)', command)

                if match:
                    value = int(match.group(1))
                    self.log_message(f"Running: move_shank({value})")
                    move_shank(value)
                    print("move_shank is being executed")

                else:
                    self.log_message(f"Invalid move_shank command: {command}")

            else:
                self.log_message(f"Unknown command: {command}")
        except Exception as e:
            self.log_message(f"Execution of command failed: {command}\nError message: {e}")
            print(f"Failed: {e}")

    def get_input_values(self, title, prompts):
        """show a dialog window to enter characters."""
        values = []
        for prompt in prompts:
            value = simpledialog.askfloat(title, prompt)
            if value is None:  # If the user clicks on cancel
                return None
            values.append(value)
        return values

    def setup_right_side(self):
        """Right side of the GUI."""
        self.tab_control = ttk.Notebook(self.right_frame)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab1, text="Status")
        self.tab_control.add(self.tab2, text="Logs")
        self.tab_control.pack(expand=1, fill=tk.BOTH, padx=10, pady=10)

        # Status-tab
        self.setup_status_tab()

        # Logs-tab
        self.setup_logs_tab()

    def setup_status_tab(self):
        """Tab for statusinformation."""
        status_frame = tk.Frame(self.tab1)
        status_frame.pack(pady=10)

        self.status_label = tk.Label(status_frame, text="Status: Checking connections...", fg="black")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.status_canvas = tk.Canvas(status_frame, width=20, height=20)
        self.status_canvas.pack(side=tk.LEFT)
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, fill="red")

        self.screwdriver_label = tk.Label(self.tab1, text="Screwdriver data: Not available", fg="black")
        self.screwdriver_label.pack(pady=20)

    def setup_logs_tab(self):
        """Tab for logs."""
        self.log_text = tk.Text(self.tab2, height=20, width=80)
        self.log_text.pack(pady=10)

    def check_connections_periodically(self):
        self.check_connections()
        self.root.after(5000, self.check_connections_periodically)  # repeat every 5 secs

    def check_connections(self):
        """Check connections."""
        rtde_conn = initialize_rtde()
        rtde_status = "RTDE connected" if rtde_conn else "RTDE not connected"
        socketio_status = "Socket.IO connected" if sio.connected else "Socket.IO not connected"

        self.status_label.config(text=f"Status: {rtde_status} | {socketio_status}")

        if rtde_conn and sio.connected:
            self.status_canvas.itemconfig(self.status_indicator, fill="green")
        else:
            self.status_canvas.itemconfig(self.status_indicator, fill="red")
            self.log_message("Connection failed!")

    # this needs to be deleted
    def run_indraaien(self):
        """Start een schroef indraaien in een aparte thread."""
        threading.Thread(target=self._indraaien, daemon=True).start()
    # this needs to be deleted

    def _indraaien(self):
        try:
            indraaien()
            self.log_message("Succes", "Indraaien voltooid!")
        except Exception as e:
            self.log_message("Fout", f"Indraaien mislukt: {e}")

    # this needs to be deleted
    def run_uitdraaien(self):
        """Start een schroef uitdraaien in een aparte thread."""
        threading.Thread(target=self._uitdraaien, daemon=True).start()
    # this needs to be deleted


    def _uitdraaien(self):
        try:
            uitdraaien()
            self.log_message("Success", "Unscrewing success!")
        except Exception as e:
            self.log_message("Fail", f"Unscrewing failed: {e}")

    def log_message(self, message):
        """Add a message to the logs."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def run_in_thread(self, func, *args):
        """execute function in a different thread."""
        thread = threading.Thread(target=func, args=args)
        thread.start()