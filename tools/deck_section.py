# 2026-09-09. Lloyd: "4/5 had some frames of when I'm standing on the balcony and looking along it...
# around frames 702 to 918 from that earlier frame sheet. I looked around while standing on the balcony."
# He is right and it changes what can be measured.
#
# THE LEVERAGE THAT WAS MISSING FOR THREE DAYS. Every number in this model's end balconies was read from
# the HALL FLOOR, 30 to 45 m away, looking up. From down there a balcony is a facade: you see the front
# and nothing else, one pixel spans 15 to 25 mm, and the deck, the ceiling over it and the back of the
# parapet are all out of sight behind the front. b7's frames 876 to 920 are posed and stand ON the WEST
# DECK, u 3.19 to 3.33, which is 0.86 to 1.00 m behind the drawn face. A pixel there spans about half a
# millimetre. The same edge is forty times better resolved, and the surfaces that were invisible from the
# floor are the ones filling the bottom of the frame.
#
# ONE UNKNOWN PER RAY, KEPT. A sightline to the parapet's top edge cannot separate how far away that edge
# is from how high it is; the two trade off along the ray. So the DEPTH is fixed on a named plane and only
# the HEIGHT is read, and the tool draws the two candidate planes separately: the solid upstand, which
# tools/end_face_scan.py put 0.484 m behind the face on the west end, and the glazed face itself. From
# 0.9 m away those two planes are thirty degrees apart in the picture, so which one the real coping sits
# on is not a fine judgement.
#
# WHAT IS DRAWN. First the model's own west section as a wireframe, so a reader can see whether it lands
# on the building. Then a labelled ladder of candidate heights on the solid plane, so that if it does not
# land, the correction can be read off rather than guessed.
#   python tools/deck_section.py <class> <frame> <west|east> <out.jpg>
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

CLS, FR, END, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
DS = 15.364
UF = {'west': 4.194, 'east': 48.056}[END]
UB = {'west': 0.344, 'east': 51.906}[END]
SGN = {'west': -1.0, 'east': 1.0}[END]
UPSTAND = {'west': 0.757, 'east': 0.755}[END]
SETB = {'west': 0.484, 'east': 0.0}[END]
RAILTOP = {'west': 1.459, 'east': 1.525}[END]
DECK = 8.34
US = UF + SGN * SETB

cam, ipath = U.load_class(CLS)[FR]
im = cv2.imread(ipath)
H, W = im.shape[:2]
q = cam.center - O
CU, CD, CH = float(q @ HU), float(q @ HD), float(q[1])


def X(u, d, lev):
    return O + u * HU + d * HD + np.array([0.0, lev, 0.0])


def P(u, d, lev):
    x, y, z = cam.project(np.asarray([X(u, d, lev)]))
    if z[0] < 0.15:
        return None
    a, b = float(x[0]), float(y[0])
    return None if (abs(a) > 40000 or abs(b) > 40000) else (a, b)


def seg(p0, p1, col, w=4):
    a, b = P(*p0), P(*p1)
    if a is None or b is None:
        return False
    cv2.line(im, (int(round(a[0])), int(round(a[1]))), (int(round(b[0])), int(round(b[1]))),
             col, w, cv2.LINE_AA)
    return True


def label(p, text, col, sc=1.1):
    v = P(*p)
    if v is None or not (-200 < v[0] < W + 200 and -200 < v[1] < H + 200):
        return
    cv2.putText(im, text, (int(v[0]) + 10, int(v[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, sc, col, 3,
                cv2.LINE_AA)


# the span across the hall that stays near this camera, because a line drawn the full 15 m width runs off
# to a vanishing point and reads as a diagonal rather than as a level
D0, D1 = max(0.3, CD - 3.2), min(DS - 0.3, CD + 3.2)

# THE MODEL'S OWN SECTION
seg((US, D0, DECK), (US, D1, DECK), (60, 220, 60), 3)
seg((US, D0, DECK + UPSTAND), (US, D1, DECK + UPSTAND), (60, 255, 60), 5)
label((US, CD, DECK + UPSTAND), 'solid upstand top %.3f' % (DECK + UPSTAND), (60, 255, 60))
seg((UF, D0, DECK + RAILTOP), (UF, D1, DECK + RAILTOP), (255, 200, 0), 5)
label((UF, CD, DECK + RAILTOP), 'glass top %.3f' % (DECK + RAILTOP), (255, 200, 0))
seg((UF, D0, DECK), (UF, D1, DECK), (255, 200, 0), 3)
label((UF, CD, DECK), 'the drawn face %.3f, deck %.2f' % (UF, DECK), (255, 200, 0))
for uu in np.arange(min(UB, UF), max(UB, UF) + 0.001, 0.5):
    seg((uu, D0, DECK), (uu, D1, DECK), (140, 140, 140), 2)
label((US + SGN * 1.0, CD, DECK), 'the drawn deck, lines every 0.5 m', (170, 170, 170), 0.95)

# THE LADDER, on the solid plane, so a wrong upstand can be read off rather than guessed
for lev in np.arange(8.40, 9.81, 0.05):
    ok = seg((US, D0, lev), (US, D1, lev), (0, 140, 255), 2)
    if ok and abs(lev * 10 - round(lev * 10)) < 1e-6 and int(round(lev * 10)) % 2 == 0:
        label((US, D0 + 0.15, lev), '%.2f' % lev, (0, 170, 255), 0.85)

cv2.putText(im, '%s %s   camera u %.2f d %.2f h %.2f, standing on the %s deck'
            % (CLS, FR, CU, CD, CH, END), (24, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
            (255, 255, 255), 3, cv2.LINE_AA)
cv2.putText(im, 'orange ladder: candidate heights on the SOLID plane u %.3f, every 0.05 m' % US,
            (24, 108), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 170, 255), 3, cv2.LINE_AA)
cv2.putText(im, 'green: the model solid.  yellow: the model glazed face.  grey: the model deck.',
            (24, 152), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 255, 200), 3, cv2.LINE_AA)

s = 1150.0 / max(H, W)
cv2.imwrite(OUT, cv2.resize(im, None, fx=s, fy=s), [cv2.IMWRITE_JPEG_QUALITY, 92])
print('%s -> %s   camera u %.3f d %.3f h %.3f, %.3f m behind the drawn face'
      % (FR, OUT, CU, CD, CH, abs(CU - UF)))
