import time
import cv2
import math
import numpy as np
from vmbpy import *
from pyzbar.pyzbar import decode, ZBarSymbol

QR_REAL_SIZE = 40                               # in milimeters

QR_PIXEL_SIZE = 124                             # in pixels
REAL_PIXEL_SIZE = QR_REAL_SIZE/QR_PIXEL_SIZE    # 1 pixel in mm
MIDDLE_POINTQR = [[[577, 449]]]                 # in pixels
MIDDLE_POINT_CAMERA = [640, 512]                # in pixels
STANDARD_ANGLE = 0                              # in degrees

OFFSET_X = 7                                    # in pixels
OFFSET_Y = 7                                    # in pixels
OFFSET_ANGLE = 1                                # in degrees

def get_camera_pose(frame, camera_moves):
    movement = [0, 0, 0]
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    equ = cv2.equalizeHist(gray)
    
    decoded_objects = decode(equ, symbols=[ZBarSymbol.QRCODE])

    for obj in decoded_objects:
        # Extract the corner points
        points = obj.polygon
        
        # We need exactly 4 corners for PnP
        if len(points) == 4:
            image_points = np.array(points, dtype=np.float32)
            pts_draw = image_points.astype(int).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts_draw], True, (0, 255, 0), 3)

            # in pts_draw the first variable is X and the second is Y
            # it seems the order in which the points are listed in the array change.
            # it seems the firs point in the array is always the most left point and the rest follows counter clock wise
            
            x_ave = (pts_draw[0][0][0] + pts_draw[1][0][0] + pts_draw[2][0][0] + pts_draw[3][0][0])/4
            y_ave = (pts_draw[0][0][1] + pts_draw[1][0][1] + pts_draw[2][0][1] + pts_draw[3][0][1])/4

            point1 = 1111
            point2 = 1111
            point3 = 1111
            point4 = 1111

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

            organized_points = [point1, point2, point3, point4]

            # find orientation
            x_axis = math.fabs(organized_points[3][0] - organized_points[0][0])
            y_axis = math.fabs(organized_points[3][1] - organized_points[0][1])

            if x_axis == 0:
                tan_angle = 90
                degrees_angle = 90
            else:
                tan_angle = math.atan(y_axis/x_axis)
                degrees_angle = math.degrees(tan_angle)

            if organized_points[0][0] < organized_points[3][0]:
                oneEight = "left"
            else:
                oneEight = "right"

            turn_direction = ""

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

            # bepaal verplaatsing
            x_mid_point = organized_points[0][0] + ((organized_points[2][0] - organized_points[0][0])/2)
            y_mid_point = organized_points[0][1] + ((organized_points[2][1] - organized_points[0][1])/2)

            difX = MIDDLE_POINT_CAMERA[0] - x_mid_point # positive means the qr is left to the camera middle point
            difY = MIDDLE_POINT_CAMERA[1] - y_mid_point # positive means the qr is above to the camera middle point

            if camera_moves:
                print("implement")

                if turn_direction == "clockwise":
                    turn_direction = "counter clockwise"
                else:
                    turn_direction = "clockwise"

                if x_mid_point < (MIDDLE_POINT_CAMERA[0] + OFFSET_X) and x_mid_point > (MIDDLE_POINT_CAMERA[0] - OFFSET_X):
                    print(f"The QR is within {OFFSET_X*REAL_PIXEL_SIZE} mm of the centre of the camera")
                elif difX > 0:
                    print(f"Please move the camera {difX*REAL_PIXEL_SIZE} mm to the left")
                    movement[0] = -1*abs(difX*REAL_PIXEL_SIZE)
                else:
                    print(f"Please move the camera {difX*REAL_PIXEL_SIZE} mm to the right")
                    movement[0] = abs(difX*REAL_PIXEL_SIZE)

                if y_mid_point < (MIDDLE_POINT_CAMERA[1] + OFFSET_Y) and y_mid_point > (MIDDLE_POINT_CAMERA[1] - OFFSET_Y):
                    print(f"The QR is within {OFFSET_Y*REAL_PIXEL_SIZE} mm of the centre of the camera")
                elif difY > 0:
                    print(f"Please move the camera {difY*REAL_PIXEL_SIZE} mm to the up")
                    movement[1] = -1*abs(difY*REAL_PIXEL_SIZE)
                else:
                    print(f"Please move the camera {difY*REAL_PIXEL_SIZE} mm to the down")
                    movement[1] = abs(difY*REAL_PIXEL_SIZE)

                if dif_angle < (0 + OFFSET_ANGLE) and dif_angle > (0 - OFFSET_ANGLE):
                    print(f"The QR is within {OFFSET_ANGLE} degrees of the orientation of the camera")
                else:
                    print(f"Please turn the camera {dif_angle} degrees {turn_direction}")
                    if turn_direction == "counter clockwise":
                        movement[2] = -1*dif_angle
                    else:
                        movement[2] = dif_angle
            else:
                if x_mid_point < (MIDDLE_POINT_CAMERA[0] + OFFSET_X) and x_mid_point > (MIDDLE_POINT_CAMERA[0] - OFFSET_X):
                    print(f"The QR is within {OFFSET_X*REAL_PIXEL_SIZE} mm of the centre of the camera")
                elif difX > 0:
                    print(f"Please move the QR {difX*REAL_PIXEL_SIZE} mm to the right")
                else:
                    print(f"Please move the QR {difX*REAL_PIXEL_SIZE} mm to the left")

                if y_mid_point < (MIDDLE_POINT_CAMERA[1] + OFFSET_Y) and y_mid_point > (MIDDLE_POINT_CAMERA[1] - OFFSET_Y):
                    print(f"The QR is within {OFFSET_Y*REAL_PIXEL_SIZE} mm of the centre of the camera")
                elif difY > 0:
                    print(f"Please move the QR {difY*REAL_PIXEL_SIZE} mm to the down")
                else:
                    print(f"Please move the QR {difY*REAL_PIXEL_SIZE} mm to the up")

                if dif_angle < (0 + OFFSET_ANGLE) and dif_angle > (0 - OFFSET_ANGLE):
                    print(f"The QR is within {OFFSET_ANGLE} degrees of the orientation of the camera")
                else:
                    print(f"Please turn the QR {dif_angle} degrees {turn_direction}")
    return frame, movement

def setup_camera(_cam):
    try:
        _cam.ExposureAuto.set('Off')
        _cam.ExposureTimeAbs.set(80000)
        _cam.Gain.set(3)
        return True
    except:
        return False

def get_picture():
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()
        if not cams:
            print("No Cameras found.")
            return

        with cams[0] as cam:
            print(f"Accessed Camera: {cam.get_id()}")

            state_camera = setup_camera(cam)
            
            try:
                frame = cam.get_frame()
                
                # 1. Access Raw Numpy Array
                img_buffer = frame.as_numpy_ndarray()
                
                # 2. Convert BayerRG -> BGR (As confirmed working)
                img_color = cv2.cvtColor(img_buffer, cv2.COLOR_BayerRG2BGR)
                
                # 3. Calculate Pose
                annotated_img, _movement = get_camera_pose(img_color, False)

                cv2.imshow("ZBar Tracking", annotated_img)
                
                while cv2.waitKey(1) != ord('q'):
                    continue
                cv2.destroyAllWindows()
                return
                    
            except Exception as e:
                print(f"Error: {e}")
                return
            
def stream_picture():
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()
        if not cams:
            print("No Cameras found.")
            return

        with cams[0] as cam:
            print(f"Accessed Camera: {cam.get_id()}")

            state_camera = setup_camera(cam)

            while True:
                try:
                    frame = cam.get_frame()
                    
                    # 1. Access Raw Numpy Array
                    img_buffer = frame.as_numpy_ndarray()
                    
                    # 2. Convert BayerRG -> BGR (As confirmed working)
                    img_color = cv2.cvtColor(img_buffer, cv2.COLOR_BayerRG2BGR)
                    
                    # 3. Calculate Pose
                    annotated_img = get_camera_pose(img_color, False)

                    cv2.imshow("ZBar Tracking", annotated_img)
                    
                    if cv2.waitKey(1) == ord('q'):
                        break
                        
                except Exception as e:
                    print(f"Error: {e}")
                    continue

            cv2.destroyAllWindows()

if __name__ == '__main__':
    start_time = time.time()

    get_picture()
    # stream_picture()

    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.6f} seconds")
