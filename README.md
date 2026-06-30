# Helicoil insertion 🦾

This repository contains the code for Project CAR. The aim of the project is to insert helicoils using a mobile cobot with an automatically generated robot program. This code connects the UR10e, OnRobot Screwdriver, Mako G131-C camera, and the simulation program RoboDK. It includes code for generating robot programs, calibrating the position of the robot, and performing helicoil insertion. The HMI/GUI is included in a separate folder but is no longer used.

---

## **Contents**

The code can be found in the `Python` folder. To generate a new robot program from scratch, use the numbered scripts:

* **`1.1 Find_hole.py`**: Generates a database containing all the holes in a 3D model (STEP-file format).
* **`1.2 Create_path.py`**: Generates the actual robot paths. Imports the holes as targets in RoboDK. Currently, the holes are imported and checked for collisions correctly, but the paths must be generated manually in RoboDK by linking the targets.

* **`2.0 Calibrate_camera-TCP.py`**: This code can be used to calibrate the camera TCP to ensure the accuracy of subsequent calibration steps. This is necessary after you have touched the camera, as there is some play between the camera lens and the image sensor.
* **`2.1 Calibrate_robotposition_Jorim.py`**: Calibrates the reference frame of the cobot in the horizontal direction.

* **`3.1 Insert_helicoils.py`**: This code contains the instructions for the actual helicoil insertion based on the generated robot paths.

* **`camera.py`**: The functions in this code are used by the calibration programs to access the camera and analyze the captured images.

* The subfolder `Extra Calibration` includes calibration scripts that are no longer used.

The folder `Example_Jorim` contains the required data files and RoboDK projects to demonstrate the individual Python scripts.
The folder `Example` contains older files used to run and demonstrate the path planning.
The folder `Archive` contains the code for the HMI/GUI, which is no longer used.

---

## **Dependencies & Versions**

Below is a list of the modules used in the code. The versions of most modules are not known yet.
The code should be run using Python 3.12.9 in a virtual environment.

* `robodk`
* `requests`: 2.32.5
* `time`
* `math`
* `tkinter`
* `numpy`
* `vmbpy`
* `pyzbar`
* `sys`
* `gmsh`
* `csv`
* `matplotlib`
* `PyQt5`
* `cv2`

---

## **Connections**

The different components are connected to a local network on the AMR:

| ------------------ | ---------------- |
| **Subnet Mask**    | `255.255.255.0`  |
| **IP Cobot**       | `192.168.12.120` |
| **IP Screwdriver** | `192.168.12.15`  |
| **IP Camera**      | `192.168.12.100` |

The Python code communicates with the cobot via RoboDK.
The code communicates directly with the screwdriver using HTTP requests.
Communication with the camera is handled through the Vimba module (`vmbpy`).
