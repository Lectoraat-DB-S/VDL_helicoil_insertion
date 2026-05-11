from robodk import robomath
from robodk.robolink import *
import math
import time
from camera import get_picture


A = [-692, -304, -34.95]
B = [217, -608, -33.3]
C = [-630, -1054, -24.6]

#Calculate vector AB
AB = robomath.subs3(B, A)
AC = robomath.subs3(C, A)

#Calculate normal vector of the plane relative to the real base
n = robomath.normalize3(robomath.cross(AB, AC))
if n[2] < 0: #Make the vector positive
    for i in range(len(n)):
        n[i]= -n[i]

RX = robomath.atan2(n[1], n[2])
RY = -robomath.atan2(n[0], n[2])
Z = abs(robomath.dot(A, n)) + 50 # 50 is the height of the plane in the global reference frame
print(f'RX = {math.degrees(RX)}')
print(f'RY = {math.degrees(RY)}')
print(f'z = {Z}')