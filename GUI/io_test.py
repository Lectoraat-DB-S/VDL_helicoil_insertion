import rtde_io
import rtde_receive
import time
import math

# Globale variabelen
rtde_io_ = None
rtde_receive_ = None
running = False
last_retraction_time = 0
PAUSE_DURATION = 10.0  # Veiligheidsmarge na oppakken

# Exacte target joints uit de afbeelding (in radialen)
TARGET_JOINTS_RAD = [
    math.radians(-45.78),
    math.radians(-49.41),
    math.radians(97.87),
    math.radians(132.33),
    math.radians(46.37),
    math.radians(89.99)
]
# Strenge tolerantie om ongewenste beweging bij andere joints te voorkomen
JOINT_TOLERANCE_RAD = math.radians(2.0)


def is_robot_at_pickup_point():
    """Controleert of de robot exact op de pick-up locatie staat."""
    global rtde_receive_
    if rtde_receive_ is None:
        return False
    try:
        current_q = rtde_receive_.getActualQ()
        # Vergelijk elk gewricht met de target
        return all(abs(current_q[i] - TARGET_JOINTS_RAD[i]) < JOINT_TOLERANCE_RAD for i in range(6))
    except Exception:
        return False


def run_feeder_loop(robot_ip="192.168.12.120"):
    global running, rtde_io_, rtde_receive_, last_retraction_time
    running = True

    try:
        rtde_io_ = rtde_io.RTDEIOInterface(robot_ip)
        rtde_receive_ = rtde_receive.RTDEReceiveInterface(robot_ip)

        # --- NIEUWE LOGICA: Eenmalige check bij start ---
        # Controleer direct of er een coil ligt (Digital In 0)
        coil_present_at_start = rtde_receive_.getDigitalInState(0)

        if coil_present_at_start:
            # Als er een coil ligt, schuif de actuator direct uit
            rtde_io_.setStandardDigitalOut(2, False)  # Stop intrekken
            rtde_io_.setStandardDigitalOut(4, True)  # Schuif uit
            print("Feeder gestart: Coil gedetecteerd, actuator direct uitgeschoven.")
        else:
            # Standaard reset: Actuator naar binnen als er GEEN coil ligt
            rtde_io_.setStandardDigitalOut(4, False)
            rtde_io_.setStandardDigitalOut(2, True)
        # ------------------------------------------------

        while running:
            current_time = time.time()
            at_pickup = is_robot_at_pickup_point()
            coil_present = rtde_receive_.getDigitalInState(0)
            actuator_retracted = rtde_receive_.getDigitalOutState(2)

            # 1. VEILIGHEID: Als we in de 10s pauze zitten, doe niks
            if current_time - last_retraction_time < PAUSE_DURATION:
                rtde_io_.setAnalogOutputVoltage(0, 0.0)
                time.sleep(0.1)
                continue

            # 2. ACTUATOR LOGICA: Alleen uitschuiven op de juiste plek (tijdens normale loop)
            if coil_present and actuator_retracted and at_pickup:
                rtde_io_.setAnalogOutputVoltage(0, 0.0)
                time.sleep(0.2)
                rtde_io_.setStandardDigitalOut(2, False)
                rtde_io_.setStandardDigitalOut(4, True)
                print("Robot op locatie gedetecteerd. Coil gepresenteerd.")

                while rtde_receive_.getDigitalOutState(4) and running:
                    time.sleep(0.1)

            # 3. FEEDER LOGICA: Alleen trillen als er GEEN coil is en de robot NIET op de pickup plek staat
            elif actuator_retracted and not coil_present and not at_pickup:
                rtde_io_.setAnalogOutputVoltage(0, 4.0)
            else:
                rtde_io_.setAnalogOutputVoltage(0, 0.0)

            time.sleep(0.05)

    finally:
        if rtde_io_:
            rtde_io_.setAnalogOutputVoltage(0, 0.0)

def stop_feeder_loop():
    global running
    running = False


def retract_actuator_now():
    """Trek de actuator alleen in als de robot bij de pick-up positie staat."""
    global rtde_io_, last_retraction_time

    # Voeg de positiecheck hier toe om ongewenste beweging bij het indraaien te blokkeren
    #if is_robot_at_pickup_point():
    if rtde_io_ is not None:
        print("Robot bij feeder gedetecteerd: Actuator intrekken en timer starten.")
        rtde_io_.setStandardDigitalOut(4, False)
        rtde_io_.setStandardDigitalOut(2, True)
        last_retraction_time = time.time()  # Start de 10s pauze
        time.sleep(0.8)
    else:
        print("Fout: Geen RTDE_IO verbinding.")
    #else:
        # Als de robot ergens anders is (bijv. bij het indraaien), negeren we het commando
        #print("Retract genegeerd: Robot is niet bij de feeder joint-positie.")