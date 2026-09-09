# 2026-09-09: LOOK AT THE WEST COPING BEFORE MOVING IT, because a bound that says 24 % is a warning.
#
# The arrival test on the west deck came back very different from the east one. At the east face 1.62 % of
# the arriving rays passed below the drawn top; at the west face 24.30 % of 3,371 did. A quarter of the
# light those sixteen cameras received would have been stopped by the parapet the sim draws there. Either
# the west parapet is drawn too tall or too far into the hall, or those poses are wrong, or the thing at
# that end is not the solid the sim assumes.
#
# NONE OF THOSE IS SETTLED BY MORE ARITHMETIC. So this draws the drawn geometry back onto the photographs
# it disagrees with: the deck line h 8.340, the drawn top h 9.020, and the face plane u 4.194, each as a
# line of world points pushed through the frame's own camera. Where those land in the picture says which of
# the four explanations is live, and the answer is legible rather than inferred.
#   python tools/west_parapet_look.py [frame ...]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
WEST = (4.194, 9.020)          # face, top as index.html draws them
EAST = (48.056, 9.110)
DECK = 8.34
# THE EAST END IS THE CONTROL. The same picture drawn on an east frame has to come back almost empty, or
# the instrument is measuring itself rather than the building.
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'

frames = {}
for cls in ('b7s', 'b7sp', 'b3', 'b3p', 'b6g', 'b6gp'):
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass
stems = sys.argv[1:] or ['b7s_000908', 'b7s_000604']

# THE FIRST DRAW WAS UNREADABLE and the reason is worth keeping: a line at constant u and h, 0.86 m in
# front of a lens, subtends nearly 180 degrees, so it sweeps across the picture at whatever angle the near
# end happens to leave at instead of lying flat where a parapet would. The legible question is per PIXEL,
# not per world line: for every pixel, where does ITS ray cross the drawn face plane? Shade the pixels
# whose ray crosses below the drawn top. If that shaded region is stone, the drawn parapet is fine and the
# arrival sample was contaminated. If it is hall floor with people on it, the light in those pixels came
# through a parapet that the sim says is solid.
for stem in stems:
    if stem not in frames:
        print(stem, 'is not posed')
        continue
    cam, ip = frames[stem]
    q = cam.center - O
    cu, ch = float(q @ HU), float(cam.center[1] - O[1])
    UF, TOPD = EAST if cu > 26.0 else WEST
    print('%-14s u %6.2f d %6.2f h %5.2f  image %dx%d  %s end, face %.3f top %.3f'
          % (stem, cu, float(q @ HD), ch, cam.w, cam.h,
             'east' if cu > 26.0 else 'west', UF, TOPD))
    im = cv2.imread(ip)
    step = 4
    ys, xs = np.mgrid[0:cam.h:step, 0:cam.w:step]
    pix = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float64)
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(pix.reshape(-1, 1, 2), K, dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    vu, vy = v @ HU, v[:, 1]
    lam = (UF - cu) / np.where(np.abs(vu) < 1e-6, 1e-6, vu)
    hc = np.where(lam > 0.02, ch + vy * lam, np.inf)
    below = (hc < TOPD).reshape(xs.shape)
    deckb = (hc < DECK).reshape(xs.shape)
    m = cv2.resize(below.astype(np.uint8) * 255, (cam.w, cam.h), interpolation=cv2.INTER_NEAREST)
    md = cv2.resize(deckb.astype(np.uint8) * 255, (cam.w, cam.h), interpolation=cv2.INTER_NEAREST)
    tint = im.copy()
    tint[m > 0] = (0.45 * tint[m > 0] + 0.55 * np.array([90, 120, 255])).astype(np.uint8)
    tint[md > 0] = (0.45 * tint[md > 0] + 0.55 * np.array([255, 210, 90])).astype(np.uint8)
    im = tint
    frac = float(below.mean())
    print('   %.1f %% of the frame looks through the drawn parapet, %.1f %% through the deck under it'
          % (100 * frac, 100 * float(deckb.mean())))
    # THE TINTS ARE BGR TRIPLES AND THE FIRST LABELS NAMED THEM BACKWARDS. [90,120,255] renders RED and
    # [255,210,90] renders BLUE, so the captions now say what the eye actually sees.
    cv2.putText(im, '%s  RED: this pixel sees through the drawn parapet (top %.3f)' % (stem, TOPD),
                (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 3, cv2.LINE_AA)
    cv2.putText(im, 'BLUE: through the deck itself (%.3f). face plane u %.3f' % (DECK, UF),
                (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 3, cv2.LINE_AA)
    os.makedirs(OUT, exist_ok=True)
    k = 1500.0 / im.shape[0]
    dst = os.path.join(OUT, stem + '-coping-mask.jpg')
    cv2.imwrite(dst, cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('   drawn back into', dst)
