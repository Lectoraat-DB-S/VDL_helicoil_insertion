import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, messagebox
import threading
import time
from rtde_interface import *
from socketio_interface import *
from requests_interface import *

class GUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OnRobot Schroefproject")
        self.root.geometry("1000x600")  # GUI grootte

        # Set the GUI instance before starting Socket.IO
        socketio_interface.gui_app_instance = self
        print("[INFO] GUI instance set in socketio_interface.")  # Debugging print



        # Frames voor layout
        self.left_frame = tk.Frame(root, bg="lightgray", width=300)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.right_frame = tk.Frame(root, bg="white", width=700)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # GUI setup
        self.setup_left_side()
        self.setup_right_side()

        # Start een thread voor WebSocket verbinding en data-updates
        threading.Thread(target=self.start_socket_io, daemon=True).start()

        self.update_screwdriver_data_periodically()  # Start automatische updates

        # check connections periodically
        self.check_connections_periodically()

    def start_socket_io(self):
        """Verbind met de Socket.IO server en houd de verbinding in stand."""
        while True:
            if connect_to_server():
                print("[INFO] Verbonden met de server. Wachten op berichten...")
                sio.wait()  # Houd de verbinding open
            else:
                print("[ERROR] Kan niet verbinden. Opnieuw proberen in 5 seconden...")
                time.sleep(5)  # Wacht voordat je opnieuw probeert

    def update_screwdriver_data(self):
        """Update the GUI with the latest screwdriver data."""
        data = socketio_interface.get_screwdriver_data()

        if data:
            status = "Bezig" if data.get("screwdriver_busy", False) else "Niet bezig"
            shank_position = round(data.get("shank_position", 0), 2)
            current_torque = round(data.get("current_torque", 0), 3)

            self.screwdriver_label.config(
                text=f"Screwdriver status: {status}\n"
                     f"Shank positie: {shank_position} mm\n"
                     f"Huidige torque: {current_torque} Nm",
                fg="green"
            )
            #print("[SUCCESS] GUI updated with new screwdriver data!")  # Debugging print
        else:
            self.screwdriver_label.config(text="Screwdriver data: Niet beschikbaar", fg="red")

    def update_screwdriver_data_periodically(self):
        """Periodically update the screwdriver data in the GUI."""
        self.update_screwdriver_data()
        self.root.after(1000, self.update_screwdriver_data_periodically)

    def setup_left_side(self):
        self.tab_control = ttk.Notebook(self.left_frame)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab3, text="SD - Functions")
        self.tab_control.add(self.tab4, text="Algemeen")

        self.tab_control.pack(expand=1, fill=tk.BOTH, padx=10, pady=10)

        # setup screwdriver functions tab
        self.setup_sd_functions_tab()

        # setup generic functions tab
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
            self.log_message(f"Succes {operation_name} voltooid!")
        except Exception as e:
            self.log_message(f"Fout {operation_name} mislukt: {str(e)}")

    def run_move_shank(self):
        """Voer de move_shank functie uit met een ingevoerde waarde."""
        value = simpledialog.askfloat("Move Shank", "Voer de shank positie in (0-55):")
        if value is not None:
            self.run_in_thread(self._execute_operation, "Move shank", move_shank, value)

    def run_pick_screw(self):
        """Voer de pick_screw functie uit met ingevoerde waarden."""
        prompts = ["Voer de shank force in (N):", "Voer de screwing lengte in (mm):"]
        self._run_operation("Pick Screw", prompts, pick_screw)

    def run_premount_screw(self):
        """Voer de premount_screw functie uit met ingevoerde waarden."""
        prompts = [
            "Voer de shank force in (N):",
            "Voer de screwing lengte in (mm):",
            "Voer het torque in (Nm):"
        ]
        self._run_operation("Pre-mount Screw", prompts, premount_screw)

    def run_tighten_screw(self):
        """Voer de tighten_screw functie uit met ingevoerde waarden."""
        prompts = [
            "Voer de shank force in (N):",
            "Voer de screwing lengte in (mm):",
            "Voer het torque in (Nm):"
        ]
        self._run_operation("Tighten Screw", prompts, tighten_screw)

    def run_loosen_screw(self):
        """Voer de loosen_screw functie uit met ingevoerde waarden."""
        prompts = [
            "Voer de shank force in (N):",
            "Voer de unscrewing lengte in (mm):"
        ]
        self._run_operation("Loosen Screw", prompts, loosen_screw)

    def setup_generic_tab(self):
        status_frame = tk.Frame(self.tab4)
        status_frame.pack(pady=10)

        """Knoppen in de linkerkolom van de GUI."""
        btn_indraaien = tk.Button(status_frame, text="Indraaien", command=self.run_indraaien, width=20)
        btn_indraaien.pack(pady=10)

        btn_uitdraaien = tk.Button(status_frame, text="Uitdraaien", command=self.run_uitdraaien, width=20)
        btn_uitdraaien.pack(pady=10)

        btn_sequence = tk.Button(status_frame, text="Voer Sequentie Uit (uitgeschakeld)", command=self.run_sequence,
                                 width=20)
        btn_sequence.pack(pady=10)

        btn_check_connections = tk.Button(status_frame, text="Controleer Connecties", command=self.check_connections,
                                          width=20)
        btn_check_connections.pack(pady=10)

        btn_refresh_status = tk.Button(status_frame, text="Refresh Status", command=self.update_screwdriver_data,
                                       width=20)
        btn_refresh_status.pack(pady=10)

    def get_input_values(self, title, prompts):
        """Toon een dialoogvenster om meerdere waarden in te voeren."""
        values = []
        for prompt in prompts:
            value = simpledialog.askfloat(title, prompt)
            if value is None:  # Als de gebruiker op 'Cancel' klikt
                return None
            values.append(value)
        return values

    def setup_right_side(self):
        """Configuratie van de rechterkant van de GUI."""
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
        """Tab voor statusinformatie."""
        status_frame = tk.Frame(self.tab1)
        status_frame.pack(pady=10)

        self.status_label = tk.Label(status_frame, text="Status: Verbindingen controleren...", fg="black")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.status_canvas = tk.Canvas(status_frame, width=20, height=20)
        self.status_canvas.pack(side=tk.LEFT)
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, fill="red")

        self.screwdriver_label = tk.Label(self.tab1, text="Screwdriver data: Niet beschikbaar", fg="black")
        self.screwdriver_label.pack(pady=20)

    def setup_logs_tab(self):
        """Tab voor logs."""
        self.log_text = tk.Text(self.tab2, height=20, width=80)
        self.log_text.pack(pady=10)

    def check_connections_periodically(self):
        """Periodieke controle van de verbindingen."""
        self.check_connections()
        self.root.after(5000, self.check_connections_periodically)  # Herhaal elke 5 seconden

    def check_connections(self):
        """Controleer de verbindingen."""
        rtde_conn = initialize_rtde()
        rtde_status = "RTDE verbonden" if rtde_conn else "RTDE niet verbonden"
        socketio_status = "Socket.IO verbonden" if sio.connected else "Socket.IO niet verbonden"

        self.status_label.config(text=f"Status: {rtde_status} | {socketio_status}")

        if rtde_conn and sio.connected:
            self.status_canvas.itemconfig(self.status_indicator, fill="green")
        else:
            self.status_canvas.itemconfig(self.status_indicator, fill="red")
            self.log_message("Verbindingsfout!")

    def run_indraaien(self):
        """Start een schroef indraaien in een aparte thread."""
        threading.Thread(target=self._indraaien, daemon=True).start()

    def _indraaien(self):
        try:
            indraaien()
            self.log_message("Succes", "Indraaien voltooid!")
        except Exception as e:
            self.log_message("Fout", f"Indraaien mislukt: {e}")

    def run_uitdraaien(self):
        """Start een schroef uitdraaien in een aparte thread."""
        threading.Thread(target=self._uitdraaien, daemon=True).start()

    def _uitdraaien(self):
        try:
            uitdraaien()
            self.log_message("Succes", "Uitdraaien voltooid!")
        except Exception as e:
            self.log_message("Fout", f"Uitdraaien mislukt: {e}")

    def run_sequence(self):
         """Voer een volledige sequentie uit in een aparte thread."""
         #threading.Thread(target=self.run_sequence, daemon=True).start()
         print("sequence")

    def log_message(self, message):
        """Voeg een bericht toe aan het log-tabblad."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def run_in_thread(self, func, *args):
        """Voer een functie uit in een aparte thread."""
        thread = threading.Thread(target=func, args=args)
        thread.start()