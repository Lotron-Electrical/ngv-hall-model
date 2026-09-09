# 2026-09-09: A VALID PHOTOGRAPH-AND-MODEL PAIR FROM A ROLLED CAMERA.
#
# Rendering the model from a real frame's pose is the most direct way to answer whether a thing is built
# right, and the first attempt from a hall-floor frame produced a pair that did not correspond at all. The
# cause is not the pose and not the model. THE HALL-FLOOR WALKS WERE SHOT WITH THE PHONE HELD PORTRAIT and
# stored landscape, so the world is rolled about 90 degrees inside every frame: measured on four of them,
# the roll about the view axis is -89.6, -91.5, -92.8 and -84.7 degrees. The registered pose carries that
# roll, so every measurement that projects a point into these frames is correct and always has been.
# What cannot carry it is the shot script, which drives the sim's own camera and can set yaw and pitch and
# nothing else. A first-person controller has no roll, so a render from a rolled pose is a different view
# of the same place, and comparing the two says nothing about the model.
#
# The fix is to take the roll out of the PHOTOGRAPH instead of trying to put it into the renderer. Rotating
# an image by a multiple of 90 degrees about its centre is exactly a change of roll when the principal
# point is the centre, which it is here (cx 960, cy 540 of 1920x1080), and it is lossless. So the frame is
# turned upright, its width and height swap, its two fields of view swap with them, and the shot is taken
# with the upright geometry. Nothing is resampled and no angle is approximated.
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

cls, stem = sys.argv[1], sys.argv[2]
outstem = sys.argv[3] if len(sys.argv) > 3 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/pair'
cam, imgfile = U.load_class(cls)[stem]
Rw = cam.R
imw, imh = int(cam.w), int(cam.h)
fx, fy = float(cam.params[0]), float(cam.params[1])


def rotz(deg):
    t = np.radians(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])


best, bestk = -2.0, 0
for k in range(4):
    Rk = rotz(90.0 * k) @ Rw
    up_world = Rk.T @ np.array([0.0, -1.0, 0.0])
    score = float(up_world @ np.array([0.0, 1.0, 0.0]))
    if score > best:
        best, bestk = score, k
Rk = rotz(90.0 * bestk) @ Rw
print(stem, 'needs', bestk, 'quarter turns; world up then sits',
      round(float(np.degrees(np.arccos(min(1.0, best)))), 1), 'deg from image up')

fwd = Rk.T @ np.array([0.0, 0.0, 1.0])
q = cam.center - O
cu, cd, cy = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
fu, fd = float(fwd @ HU), float(fwd @ HD)
n = float(np.hypot(fu, fd))
pitch = float(np.degrees(np.arctan2(float(fwd[1]), n)))
if bestk % 2 == 1:
    rw, rh, vf = imh, imw, 2.0 * np.degrees(np.arctan(imw / 2.0 / fx))
else:
    rw, rh, vf = imw, imh, 2.0 * np.degrees(np.arctan(imh / 2.0 / fy))
print('   width', rw, 'height', rh, 'vfov', round(float(vf), 1))
print('   u', round(cu, 2), 'd', round(cd, 2), 'h', round(cy, 2),
      'forward u', round(fu / n, 3), 'd', round(fd / n, 3), 'pitch', round(pitch, 1))

im = cv2.imread(imgfile)
# CLOCKWISE, and the reason is worth stating because the first attempt came out upside down and the
# printed diagnostic still said the world's up was 2.3 degrees from the image's up. The pose maths is in
# camera coordinates where the image y axis points DOWN, so the quarter turn that fixes the camera frame
# is the opposite sense to the one that fixes the picture. The check on this is the picture itself, not
# the number: a diagnostic that agrees with a wrong answer is how the follow bias hid for two days.
for _ in range(bestk):
    im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
cv2.imwrite(outstem + '-photo.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 92])
print('   wrote the upright photograph', outstem + '-photo.jpg', im.shape)
