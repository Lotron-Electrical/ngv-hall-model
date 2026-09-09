# 2026-09-09: IS THE LENS WRONG RATHER THAN THE POSES? The one thing the registration was never allowed
# to question.
#
# Refining the poses barely helped. On b3 the cameras had to move a median 0.056 m to buy 0.013 m of ray
# agreement, and only 804 of 5,362 tracks could be reprojected into their own frames inside 8 px. Poses
# that need to move further than they gain are not slightly wrong; something they all share is wrong.
#
# THE THING THEY ALL SHARE IS THE CAMERA. Every balcony clip was registered with the day4k camera FROZEN,
# which is the right call when the aim is to place a clip in a model that already exists, and a silent
# assumption when the aim is to measure something a metre away. A focal length two per cent out barely
# moves a feature thirty metres away, which is all the registration ever checked, and throws a ray by a
# fifth of a degree, which is 4 mm one metre out and grows with every metre after that.
#
# So this leaves the poses exactly where they are and sweeps ONE number: a scale on the focal length. For
# each value it remakes every ray and remeasures how far apart matched rays pass in the near field. If the
# frozen camera is right, the curve bottoms out on 1.000. If it bottoms out somewhere else, every near
# measurement in this archive has been reading a lens error as a geometry error.
#   CLASSES="b3 b1" python tools/focal_probe.py
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

WIN, RNEAR, RFAR = 5, 0.25, 6.0
SCALES = np.arange(0.94, 1.0601, 0.005)
sift = cv2.SIFT_create(nfeatures=2000)


def rays_scaled(cam, pts, s):
    K = np.array([[cam.params[0] * s, 0, cam.params[2]],
                  [0, cam.params[1] * s, cam.params[3]], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pts, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def missdist(ca, va, cb, vb):
    w = cb.center - ca.center
    aa = np.einsum('ij,ij->i', va, va)
    bb = np.einsum('ij,ij->i', va, vb)
    cc = np.einsum('ij,ij->i', vb, vb)
    dd = va @ w
    ee = vb @ w
    den = aa * cc - bb * bb
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1.0)
    s = (cc * dd - bb * ee) / den
    t = (bb * dd - aa * ee) / den
    P1 = ca.center + s[:, None] * va
    P2 = cb.center + t[:, None] * vb
    return np.linalg.norm(P1 - P2, axis=1), s, t


classes = os.environ.get('CLASSES', 'b3 b1 b7s b5').split()
bf = cv2.BFMatcher(cv2.NORM_L2)
for cls in classes:
    try:
        frames = U.load_class(cls)
    except Exception:
        print('%-5s could not be loaded' % cls)
        continue
    items = []
    for stem in sorted(frames):
        cam, ip = frames[stem]
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        kp, de = sift.detectAndCompute(img, None)
        if de is not None and len(kp) >= 40:
            items.append((stem, cam, np.array([k.pt for k in kp]), de))
        if len(items) >= 40:
            break
    if len(items) < 6:
        print('%-5s too few frames' % cls)
        continue
    cam0 = items[0][1]
    print('')
    print('%-5s %d frames, camera %s %dx%d, fx %.1f fy %.1f cx %.1f cy %.1f'
          % (cls, len(items), cam0.model, cam0.w, cam0.h, cam0.params[0], cam0.params[1],
             cam0.params[2], cam0.params[3]))
    pairs = []
    for i in range(len(items)):
        for j in range(i + 1, min(i + WIN, len(items))):
            ca, cb = items[i][1], items[j][1]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < 0.10 or base > 2.0:
                continue
            mm = bf.knnMatch(items[i][3], items[j][3], k=2)
            good = [m for m, nn in mm if m.distance < 0.72 * nn.distance]
            if len(good) < 12:
                continue
            pairs.append((ca, items[i][2][[m.queryIdx for m in good]],
                          cb, items[j][2][[m.trainIdx for m in good]]))
    if len(pairs) < 4:
        print('      no usable pair')
        continue
    curve = []
    for s in SCALES:
        acc = []
        for ca, pa, cb, pb in pairs:
            va, vb = rays_scaled(ca, pa, s), rays_scaled(cb, pb, s)
            m, ss, tt = missdist(ca, va, cb, vb)
            sel = np.logical_and.reduce((ss > RNEAR, ss < RFAR, tt > RNEAR, tt < RFAR))
            if sel.any():
                acc.append(m[sel])
        curve.append(float(np.median(np.concatenate(acc))) if acc else np.nan)
    curve = np.array(curve)
    k = int(np.nanargmin(curve))
    one = int(np.argmin(np.abs(SCALES - 1.0)))
    print('      %d pairs. the sweep, focal scale then median near-field ray miss:' % len(pairs))
    for i in range(0, len(SCALES), 2):
        print('        %5.3f   %.4f m' % (SCALES[i], curve[i]))
    print('      best %.3f gives %.4f m, the frozen 1.000 gives %.4f m, %.0f per cent better'
          % (SCALES[k], curve[k], curve[one], 100.0 * (1.0 - curve[k] / curve[one])))
    if abs(SCALES[k] - 1.0) < 0.006:
        print('      THE FROZEN CAMERA IS RIGHT for this clip; the near error is not the lens.')
    else:
        print('      the frozen focal is out by %.1f per cent, %.1f px on this sensor'
              % (100.0 * (SCALES[k] - 1.0), abs(SCALES[k] - 1.0) * cam0.params[0]))
