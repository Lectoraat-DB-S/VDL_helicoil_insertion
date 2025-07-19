# template-repository 🦾

This repository contains the code for the VDL_helicoil_insertion HMI, designed to control a UR10e cobot with an OnRobot Screwdriver and a Cobotrack. This HMI offers flexible control of these components from a PC, streamlining complex tasks such as inserting screws into models with numerous holes that would be difficult to perform manually via Polyscope.

---

## **Code Guidelines**

When delivering code, we highly recommend including a `README` file. This makes it easier for others to understand, use, or build upon your work. This `README` describes the project, its dependencies, and how to use the code. While minor deviations are acceptable based on the programming language used, please try to adhere as closely as possible to these standards.

Here's what we'd like to see in a `README`:

---

## **Description**

The `VDL_helicoil_insertion` is a Human-Machine Interface (HMI) built to control a UR10e cobot, an OnRobot Screwdriver, and a Cobotrack. This HMI enables flexible component control directly from a PC, which is particularly beneficial for complex tasks. For instance, models with over 300 holes are challenging to process manually using Polyscope; this solution effectively circumvents that issue.

---

## **Dependencies & Versions**

Below is a list of all necessary imports, packages, and software with their respective versions. Please verify your code on another machine to ensure all dependencies are accurately noted.

* **Anaconda Python Interpreter:** 3.12.9
* `ur-rtde`: 1.6.0
* `websocket-client`: 1.8.0
* `sockets`: 1.0.0
* `requests`: 2.32.3
* `tkinter`
* `time`
* `re`
* `threading`
* `python-socketio`: 5.3.0
* `numpy-base`: 2.2.2

---

## **Architecture**

This section describes the architecture of the project, outlining the purpose of each file and its interdependencies.

GUI folder contents:

* **`cobotrack_interface`**: Contains functions for sending requests to control the Cobotrack, called by `gui_app`.
* **`gui_app`**: Implements the core logic of the HMI, managing function calls and file interactions.
* **`main`**: Solely responsible for the initialization of the HMI.
* **`requests_interface`**: Defines functions for sending requests to the OnRobot Screwdriver API, including specific screwdriver operations.
* **`rtde_interface`**: Manages cobot movement and status checks, along with connection functions.
* **`socketio_interface`**: Describes and initializes the SocketIO connection protocol for real-time status updates from the OnRobot Screwdriver.

Robodk folder contents:

* **`Instellingen folder`**: Contains every setting that should be set up in robodk

* **`csv_importernewest`**: Contains code for importing csv targets in robodk
* **`rdk file for robodk`**: robodk file where the setup is
* **`Generatefaceapproaches`**: Contains code for generating face approaches, generating links, creating sub and main programs
* 
---

## **References**

All code in this repository has been self-written based on the API descriptions of the respective libraries. Comments within the code were generated with the assistance of ChatGPT.

* No external code or adapted functions were used.

---

## **Usage**

When using external hardware such as a robot, it's crucial to understand the connection and startup procedures. For example, it might be necessary to start the program on the cobot before launching the Python code on your laptop.

1.  **Start Polyscope on the Cobot:** This cannot be done from the PC.
2.  **Configure Network Settings:** Ensure the IP address, gateway, and subnet mask are correctly configured in the cobot's settings. For detailed instructions, please consult the research document.

---

