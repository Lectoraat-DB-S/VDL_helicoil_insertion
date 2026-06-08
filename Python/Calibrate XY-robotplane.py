from robodk.robolink import *
from robodk import robomath
import math

A = [-674, -368, -35.9]
B = [-672, -973, -29.6]
C = [162, -523, -36.6]

#Calculate 2 vectors in the plane
AB = robomath.subs3(B, A)
AC = robomath.subs3(C, A)

#Calculate normal vector of the plane relative to the real robotbase
n = robomath.normalize3(robomath.cross(AB, AC))
if n[2] < 0: #Make the vector point upwards
    for i in range(len(n)):
        n[i]= -n[i]

RX = robomath.atan2(n[1], n[2])
RY = -robomath.atan2(n[0], n[2])
Z = abs(robomath.dot(A, n)) + 50 # 50 is the height of the plane in the global reference frame
print(f'RX = {math.degrees(RX)}')
print(f'RY = {math.degrees(RY)}')
print(f'z = {Z}')