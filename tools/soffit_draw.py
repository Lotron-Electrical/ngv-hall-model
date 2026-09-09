# 2026-09-09: DRAW THE SOFFIT-EDGE DETECTIONS BACK INTO THE FRAME THEY CAME FROM.
# Looking at the output is what caught the 3,611 phantom triangulated points and the upside-down pose
# pair, so no number out of tools/soffit_edge.py is used or published until the found boundary has been
# put back on the picture and looked at.   python tools/soffit_draw.py <frame> [<frame> ...]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402
import soffit_edge as S  # noqa: E402

OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/balcony'
os.makedirs(OUT, exist_ok=True)
uF = S.ENDS['east'][0] - S.ENDS['east'][1] * S.FACE


def upright(im, cam):
    best, bk = -2.0, 0
    for k in range(4):
        t = np.radians(90.0 * k)
        rz = np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])
        sc = float(((rz @ cam.R).T @ np.array([0.0, -1.0, 0.0])) @ np.array([0.0, 1.0, 0.0]))
        if sc > best:
            best, bk = sc, k
    for _ in range(bk):
        im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    return im


frames = {}
for cls in ('b7sp', 'b6gp', 'b3p'):
    try:
        frames.update(U.load_class(cls))
    except Exception:
        pass
for stem in sys.argv[1:]:
    cam, ip = frames[stem]
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (5, 5), 0)
    im = cv2.imread(ip)
    for dd in np.linspace(1.0, 14.5, 10):
        pts = np.array([S.O + uF * S.HU + dd * S.HD + np.array([0, float(v), 0]) for v in S.levels])
        x, y, z = cam.project(pts)
        ok = (z > 0.4) * (x > 25) * (x < cam.w - 25) * (y > 25) * (y < cam.h - 25)
        for k in range(0, len(S.levels), 20):
            if ok[k]:
                cv2.circle(im, (int(x[k]), int(y[k])), 4, (90, 90, 90), -1)   # the scan path itself
        got = S.scan(cam, grey, uF, dd)
        if got is None:
            continue
        hv, contrast, P, elev = got
        px, py, pz = cam.project(np.asarray([P]))
        cv2.circle(im, (int(px[0]), int(py[0])), 18, (0, 255, 255), 4)
        cv2.putText(im, '%.2f' % hv, (int(px[0]) + 26, int(py[0])), cv2.FONT_HERSHEY_SIMPLEX,
                    1.3, (0, 255, 255), 3, cv2.LINE_AA)
    out = os.path.join(OUT, stem + '-soffit.jpg')
    im = upright(im, cam)
    k = 1500.0 / im.shape[0]
    cv2.imwrite(out, cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 84])
    print('wrote', out)
