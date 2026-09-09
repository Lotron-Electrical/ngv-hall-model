# 2026-09-09: THE BALCONY WALK DRAWN IN PLAN, so the argument can be read on a phone.
#
# One picture of the east top gallery seen from above: the drawn parapet face, the rival face the
# silhouette fit preferred, and every posed camera that stood on that deck. The rival line has to have the
# operator walking on the wrong side of the stone; the drawn one does not. That is the whole of test one in
# tools/parapet_arrival.py.
#   python tools/walk_proof.py
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UFACE, UBACK, RIVAL = 48.056, 51.906, 48.702
CLASSES = ('b3p', 'b3', 'b7sp', 'b7s', 'b6gp', 'b6g')
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
U0, U1, D0, D1 = 47.2, 52.2, -0.4, 15.6
W, TOP, PAD = 1080, 190, 60
# the two axes get their own scale on purpose: 5 m across the gallery and 16 m along it at one scale
# makes a picture too tall to read on a phone, and nothing here is measured off the drawing.
SC = (W - 2 * PAD) / (U1 - U0)
SCD = 62.0
HGT = int(TOP + (D1 - D0) * SCD + PAD)


def px(u, d):
    return int(PAD + (u - U0) * SC), int(TOP + (d - D0) * SCD)


im = np.full((HGT, W, 3), 22, np.uint8)
cv2.rectangle(im, px(U0, D0), px(U1, D1), (38, 38, 38), -1)
cv2.rectangle(im, px(UFACE, D0), px(UBACK, D1), (52, 46, 40), -1)      # the gallery as drawn

cams = []
seen = set()
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for f, (cam, _ip) in frames.items():
        if f in seen:
            continue
        q = cam.center - O
        cu, ch = float(q @ HU), float(cam.center[1] - O[1])
        if not (47.5 < cu < 52.2 and ch > 8.7):
            continue
        seen.add(f)
        cams.append((cu, float(q @ HD)))

for cu, cd in cams:
    x, y = px(cu, cd)
    col = (90, 200, 255) if cu >= RIVAL else (80, 90, 240)
    cv2.circle(im, (x, y), 5, col, -1)

for u, col, lab, below in ((UFACE, (110, 240, 130), 'drawn parapet face  u 48.056', False),
                           (RIVAL, (90, 120, 255), 'rival face  u 48.702', True)):
    x0, y0 = px(u, D0)
    x1, y1 = px(u, D1)
    cv2.line(im, (x0, y0), (x1, y1), col, 3)
    ty = y1 + 30 if below else y0 - 12
    cv2.putText(im, lab, (max(8, x0 - 8), ty), cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 1, cv2.LINE_AA)

x0, y0 = px(UBACK, D0)
cv2.line(im, (x0, y0), px(UBACK, D1), (150, 150, 150), 2)
cv2.putText(im, 'back wall  51.906', (x0 - 190, y0 - 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (150, 150, 150), 1, cv2.LINE_AA)

lines = [('THE EAST TOP GALLERY IN PLAN, and where Lloyd actually walked', (235, 235, 235), 0.66),
         ('%d posed cameras on that deck. RED = west of the rival face, out over the hall' % len(cams),
          (200, 200, 200), 0.52),
         ('rival face: 140 of %d cameras out over the hall, median 0.445 m, worst 0.807 m'
          % len(cams), (90, 120, 255), 0.52),
         ('drawn face: 31 of %d past it, median 0.115 m, which is a lean over the coping'
          % len(cams), (110, 240, 130), 0.52)]
yy = 44
for txt, col, sc in lines:
    cv2.putText(im, txt, (PAD, yy), cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1, cv2.LINE_AA)
    yy += 36

cv2.putText(im, 'north  d 0', (PAD, TOP - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1,
            cv2.LINE_AA)
cv2.putText(im, 'south  d 15.4', (W - 240, HGT - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1,
            cv2.LINE_AA)
bx, by = px(47.35, 4.0)
cv2.putText(im, 'b3 walks', (bx, by), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 200, 200), 1, cv2.LINE_AA)
cv2.putText(im, 'd 3.98 to 7.50', (bx, by + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 200, 200), 1,
            cv2.LINE_AA)
cv2.putText(im, 'b7s and b6g', (px(47.28, 12.6)[0], px(47.28, 12.6)[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
            (200, 200, 200), 1, cv2.LINE_AA)
os.makedirs(OUT, exist_ok=True)
dst = os.path.join(OUT, 'balcony-walk-plan.jpg')
cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(dst, im.shape, len(cams), 'cameras')
