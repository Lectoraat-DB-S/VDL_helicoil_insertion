from robodk import robomath
from robodk.robolink import *
import math

# Fill in manually the XYZ-coordinates of three measured points on the welding table.
# The order of the points is random
A = [-674, -368, -35.9]
B = [-672, -973, -29.6]
C = [162, -523, -36.6]

# Calculate 2 vectors in the plane
AB = robomath.subs3(B, A)
AC = robomath.subs3(C, A)

# Calculate normal vector of the plane relative to the real robotbase
n = robomath.normalize3(robomath.cross(AB, AC))
if n[2] < 0: # Makes the vector point upwards
    for i in range(len(n)):
        n[i]= -n[i]

# Calculate the rotations by calculating the angle of the normal vector with the Z-axis
RX = robomath.atan2(n[1], n[2])
RY = -robomath.atan2(n[0], n[2])
# RX and RY can be calculated alternatively by calculating the rotation vector (cross-product of the normal vector and the Z-axis)

# Calculate the height of the baseframe
distance = abs(robomath.dot(A, n)) #The dotproduct gives the normal distance between the robotbase and the measured plane
Z = distance + 50 # 50 is the height of the measured plane in the global reference frame
print(f'RX = {math.degrees(RX)}')
print(f'RY = {math.degrees(RY)}')
print(f'Z = {Z}')