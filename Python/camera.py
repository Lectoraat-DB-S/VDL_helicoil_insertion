import math
import cv2
import numpy as np
from vmbpy import *
from pyzbar.pyzbar import decode, ZBarSymbol

DEBUG_CODE = False                              # true if you want prints, false if you don't
QR_REAL_SIZE = 40                               # in milimeters
# QR_PIXEL_SIZE = 124                             # in pixels
# if SELF_CALIBRATING:
#     qr_pixel_size = 1
#     REAL_PIXEL_SIZE = QR_REAL_SIZE/qr_pixel_size    # 1 pixel in mm 
# else:
#     QR_PIXEL_SIZE = 145                         # in pixels
#     REAL_PIXEL_SIZE = QR_REAL_SIZE/QR_PIXEL_SIZE    # 1 pixel in mm 
OFFSET_X = 0                                  # in pixels
OFFSET_Y = 0                                  # in pixels
OFFSET_ANGLE = 0                                # in degrees
MIDDLE_POINT_CAMERA = [640, 512]                # in pixels

# function to calibrate the move commandos according to an QRcode
# it is expected that the robot has positioned the camera above the QRcode
# function that will return the position of the qr code compared to the camera
def calibrate_robot():
    
    # take picture and return the QR position
    camera_present, my_movement = get_picture()
    if camera_present == False:
        if DEBUG_CODE:
            print("There is no camera present")
        return False, [0,0,0]
    else:
        #my_movement[0] = my_movement[0]/1000
        #my_movement[1] = my_movement[1]/1000
        return True, my_movement

# function to get a picture
def get_picture():
    pictureTaken = False
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()

        # check if there is a camera
        if not cams:
            if DEBUG_CODE:
                print("No Cameras found.")
            return False, [0, 0, 0]

        with cams[0] as cam:
            if DEBUG_CODE:
                print(f"Accessed Camera: {cam.get_id()}")

            state_camera = setup_camera(cam)
            
            if not state_camera:
                if DEBUG_CODE:
                    print(f"State of the Camera: {state_camera}")
                return False, [0, 0, 0]

            try:
                frame = cam.get_frame()
                
                # 1. Access Raw Numpy Array
                img_buffer = frame.as_numpy_ndarray()

                # 2. Convert BayerRG -> BGR (As confirmed working)
                img_color = cv2.cvtColor(img_buffer, cv2.COLOR_BayerRG2BGR)

                # 3. Calculate Pose
                pictureTaken, _movement = get_camera_pose(img_color)
                if DEBUG_CODE:
                    print("get picture movement: ", _movement)

                return pictureTaken, _movement

            except Exception as e:
                print(f"Error: {e}")
                return pictureTaken, e

# initialize the camera with the correct settings
def setup_camera(_cam):
    try:
        _cam.ExposureAuto.set('Off')        # turn off auto exposure
        _cam.ExposureTimeAbs.set(80000)     # set exposure time to 80000 micros seconds
        _cam.Gain.set(4)                    # set gain to 3
        return True
    except:
        return False

# get the location of the camera compared to the QR code
def get_camera_pose(frame):
    pictureTaken = False
    # initialize variable that will return data
    movement = [0, 0, 0]    #[x, y, rz]

    # make frame grey scale
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    # equalize frame
    equ = cv2.equalizeHist(gray)

    # look for QRcodes in the frame
    decoded_objects = decode(equ, symbols=[ZBarSymbol.QRCODE])

    if DEBUG_CODE:
        if len(decoded_objects) != 0:
            print(decoded_objects[0][2].width)

        else:
            print("No QR is found")
        
    qr_pixel_size = decoded_objects[0][2].width
    real_pixel_size = QR_REAL_SIZE/qr_pixel_size

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

            organized_points = [point1, point2, point3, point4]     # LT, RT, RB, LB

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

            # check if the robot should move in the X direction
            if x_mid_point < (MIDDLE_POINT_CAMERA[0] + OFFSET_X) and x_mid_point > (
                    MIDDLE_POINT_CAMERA[0] - OFFSET_X):
                if DEBUG_CODE:
                    print(f"The QR is within {OFFSET_X * real_pixel_size} mm of the centre of the camera in the X direction, fault is {difX} pixels")
                # this value means the camera is within the expected offset
                movement[0] = 0.000000001
            elif difX < 0:
                if DEBUG_CODE:
                    print(f"Please move the camera {difX * real_pixel_size} mm to the left")
                movement[0] = abs(difX * real_pixel_size)
            else:
                if DEBUG_CODE:
                    print(f"Please move the camera {difX * real_pixel_size} mm to the right")
                movement[0] = -1 * abs(difX * real_pixel_size)
            
            # check if the robot should move in the Y direction
            if y_mid_point < (MIDDLE_POINT_CAMERA[1] + OFFSET_Y) and y_mid_point > (
                    MIDDLE_POINT_CAMERA[1] - OFFSET_Y):
                if DEBUG_CODE:
                    print(f"The QR is within {OFFSET_Y * real_pixel_size} mm of the centre of the camera in the Y direction, fault is {difY} pixels")
                # this value means the camera is within the expected offset
                movement[1] = 0.000000001
            elif difY < 0:
                if DEBUG_CODE:
                    print(f"Please move the camera {difY * real_pixel_size} mm up")
                movement[1] = abs(difY * real_pixel_size)
            else:
                if DEBUG_CODE:
                    print(f"Please move the camera {difY * real_pixel_size} mm down")
                movement[1] = -1 * abs(difY * real_pixel_size)

            # check if the robot should move around it's base
            if dif_angle < (0 + OFFSET_ANGLE) and dif_angle > (0 - OFFSET_ANGLE):
                if DEBUG_CODE:
                    print(f"The QR is within {OFFSET_ANGLE} degrees of the orientation of the camera in the Rz direction, fault is {dif_angle} degrees")
                # this value means the camera is within the expected offset
                movement[2] = 0.000000001
            else:
                if DEBUG_CODE:
                    print(f"Please turn the camera {dif_angle} degrees {turn_direction}")
                if turn_direction == "counter clockwise":
                    movement[2] = -1 * math.radians(dif_angle)
                else:
                    movement[2] = math.radians(dif_angle)
    if DEBUG_CODE:
        print("get camera movement: ", movement)

    if movement[0] != 0 or movement[1] != 0 or movement[2] != 0:
        pictureTaken = True

    return pictureTaken, movement


######################################################################
#####                      hole calibration                      #####
######################################################################

# function to get a picture
def get_picture_hole(distance):
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()

        # check if there is a camera
        if not cams:
            if DEBUG_CODE:
                print("No Cameras found.")
            return False, [0, 0, 0]

        with cams[0] as cam:
            if DEBUG_CODE:
                print(f"Accessed Camera: {cam.get_id()}")

            state_camera = setup_camera_holes(cam)
            
            if not state_camera:
                if DEBUG_CODE:
                    print(f"State of the Camera: {state_camera}")
                return False, [0, 0, 0]

            try:
                frame = cam.get_frame()

                # 1. Access Raw Numpy Array
                img_buffer = frame.as_numpy_ndarray()

                # 2. Convert BayerRG -> BGR (As confirmed working)
                gray = cv2.cvtColor(img_buffer, cv2.COLOR_BayerRG2GRAY)
                # gray = cv2.cvtColor(img_buffer, cv2.COLOR_BGR2GRAY)

                # Reduce noise
                gray = cv2.medianBlur(gray, 5)

                # 3. Calculate Pose
                hole_cords = hole_location(gray, True, img_buffer)
                if DEBUG_CODE:
                    print("gotten hole location:")
                    print(hole_cords)

                # 4. Find nearest hole to center of picture
                distances = []
                for i in range(len(hole_cords)):
                    circle = hole_cords[i]
                    dist = math.dist(circle[0:2], MIDDLE_POINT_CAMERA)
                    distances.append(dist)
                nearest_hole = hole_cords[distances.index(min(distances))]
                #offset = [nearest_hole[0]-MIDDLE_POINT_CAMERA[0], MIDDLE_POINT_CAMERA[1]-nearest_hole[1]]
                offset = np.subtract(nearest_hole[0:2], MIDDLE_POINT_CAMERA)
                offset = offset*(40*distance/90750) # Empirical relation between pixelsize in mm and distance from camera lense
                return offset.tolist()
                # return True, hole_cords

            except Exception as e:
                print(f"Error: {e}")
                return False, e

def setup_camera_holes(_cam):
    try:
        _cam.ExposureAuto.set('Off')        # turn off auto exposure
        _cam.ExposureTimeAbs.set(50000)     # set exposure time to 80000 micros seconds
        _cam.Gain.set(3)                    # set gain to 3
        return True
    except:
        return False

def hole_location(gray_frame, isItTrue, color_frame):
    # Detect circles
    circles = cv2.HoughCircles(
        gray_frame,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=100,      
        param1=100,         
        param2=40,       
        minRadius=10,       
        maxRadius=600
    )

    if DEBUG_CODE:
        # Draw only the first detected circle
        for i in circles[0]:
            i = np.uint16(np.around(i))
            x, y, r = i
            cv2.circle(color_frame, (x, y), r, (0, 255, 0), 2)  # Circle outline
            cv2.circle(color_frame, (x, y), 2, (0, 0, 255), 3)  # Center point
        #print("The following circles are present: ")
        #print(circles)

        # Show result
        cv2.imshow('Detected Circle', color_frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return circles[0]