# 2026-09-09: LOOK AT WHAT IS OVER THE BALCONY, before measuring anything.
#
# Lloyd: "You can see how the ceiling goes above that balcony as well right? You can see that in the
# balcony videos." The model says there is no full ceiling there: ENDW draws a 2.1 m deep soffit on
# h 11.1 over the parapet and leaves the back 1.75 m open to the glass roof. That claim has never been
# checked against a camera standing on the deck, and the two frames it does rest on were shot from the
# hall floor 30 m away. This pulls the deck-standing frames out upright and puts the model's overhead
# geometry on them, so the answer can be read off the picture instead of argued.
#
# The phone was held portrait, so the frames are stored rolled about 90 degrees (tools/pose_pair.py).
# The overlay is drawn in the frame's own pixels first and the whole annotated picture is turned upright
# afterwards, which keeps the projection exact and still gives a picture a person can read.
#   python tools/balcony_look.py <class> <frame> [<frame> ...]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
HEAD, SOFFIT, TOP, DECK, FACE = 11.1, 2.1, 13.5, 8.34, 3.85
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/balcony'
os.makedirs(OUT, exist_ok=True)


def upright(im, cam):
    """the quarter turns that put world up to the top of the picture (pose_pair.py's result)"""
    best, bestk = -2.0, 0
    for k in range(4):
        t = np.radians(90.0 * k)
        rz = np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])
        up = (rz @ cam.R).T @ np.array([0.0, -1.0, 0.0])
        sc = float(up @ np.array([0.0, 1.0, 0.0]))
        if sc > best:
            best, bestk = sc, k
    for _ in range(bestk):
        im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    return im


cls = sys.argv[1]
frames = U.load_class(cls)
for stem in sys.argv[2:]:
    cam, ip = frames[stem]
    im = cv2.imread(ip)
    q = cam.center - O
    cu = float(q @ HU)
    west = cu < 26.0
    uB, s = (0.344, -1.0) if west else (51.906, 1.0)
    uF = uB - s * FACE
    uS = uF + s * SOFFIT

    def px(u, d, h):
        x, y, z = cam.project(np.asarray([O + u * HU + d * HD + np.array([0, h, 0])]))
        if z[0] <= 0.2 or abs(x[0]) > 20000 or abs(y[0]) > 20000:
            return None
        return (int(round(float(x[0]))), int(round(float(y[0]))))

    def poly(pts, col, w=2):
        for a, b in zip(pts, pts[1:]):
            pa, pb = px(*a), px(*b)
            if pa and pb:
                cv2.line(im, pa, pb, col, w, cv2.LINE_AA)

    # the drawn soffit, its front edge on the parapet face and its back edge 2.1 m in
    for dd in np.linspace(0.3, 15.0, 9):
        poly([(uF, dd, HEAD), (uS, dd, HEAD)], (0, 255, 255), 2)
    poly([(uF, 0.3, HEAD), (uF, 15.0, HEAD)], (0, 200, 255), 3)
    poly([(uS, 0.3, HEAD), (uS, 15.0, HEAD)], (0, 128, 255), 3)
    # the strip the model leaves OPEN to the glass roof: uS to the back wall, drawn on the plate
    for dd in np.linspace(0.3, 15.0, 9):
        poly([(uS, dd, TOP), (uB, dd, TOP)], (255, 80, 255), 2)
    poly([(uB, 0.3, DECK), (uB, 15.0, DECK)], (80, 255, 80), 2)      # deck meets back wall
    poly([(uB, 0.3, TOP), (uB, 15.0, TOP)], (255, 80, 255), 3)       # back wall top
    cv2.putText(im, stem, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
    out = os.path.join(OUT, stem + '-ceiling.jpg')
    cv2.imwrite(out, upright(im, cam), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('wrote', out, 'camera u %.2f d %.2f h %.2f' % (cu, float(q @ HD), float(cam.center[1] - O[1])))
