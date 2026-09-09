# 2026-09-09: the west parapet measured from a camera standing behind it, which is the first time anything
# in this model has been.
#
# WHY THIS IS DIFFERENT FROM EVERY EARLIER READING. The end balconies were built from hall-floor frames 30
# to 45 m out. One pixel there covers 15 to 25 mm on the parapet and the only surface in view is its front.
# Lloyd: "4/5 had some frames of when I'm standing on the balcony and looking along it... around frames 702
# to 918. I looked around while standing on the balcony." b7's frames 604 to 920 are posed, they stand ON
# the west deck, u 3.19 to 3.33, and the drawn parapet is 0.43 to 0.91 m in front of the lens. A pixel
# covers about half a millimetre. It is the same edge measured forty times better.
#
# ONE UNKNOWN PER RAY. A sightline over the parapet's top cannot say how far away that top is and how high
# it is at once; the two trade along the ray. So the DEPTH is fixed on a named plane and only the HEIGHT is
# solved. Two planes are named and both are reported, because which one the coping stands on is itself the
# question tools/end_face_scan.py answered from the floor and this frame can answer again from a metre:
#   u 3.710, the SOLID upstand, 0.484 m behind the face
#   u 4.194, the GLAZED face itself
# If the coping were on the face, its solved height comes out below the deck, which is impossible, and that
# refutes the face without any appeal to the earlier fit.
#
# THE EDGE IS FOUND WITHOUT BEING TOLD WHERE TO LOOK, over the whole lower half of the frame, so a wrong
# drawn height cannot pull the answer to itself. The parity is fixed by physics rather than by preference:
# going DOWN the picture you leave the lit hall floor and enter the parapet's own top, so brightness falls.
#
# THE NULL IS THE SECOND PLANE PLUS THE SPREAD ACROSS FRAMES. These frames were shot at pitches from -12 to
# -23 degrees and from positions 0.14 m apart in u and 1.2 m apart across the hall. A real edge gives the
# same height from all of them. A detector locking onto something in the picture rather than in the
# building does not.
#   python tools/parapet_top.py [class] [end]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

CLS = sys.argv[1] if len(sys.argv) > 1 else 'b7sp'
END = sys.argv[2] if len(sys.argv) > 2 else 'west'
UFACE = {'west': 4.194, 'east': 48.056}[END]
SETB = {'west': 0.484, 'east': 0.0}[END]
SGN = {'west': -1.0, 'east': 1.0}[END]
USOLID = UFACE + SGN * SETB
DECK, DRAWN_UPSTAND = 8.34, {'west': 0.757, 'east': 0.755}[END]
HLO, HHI, HSTEP = 8.45, 9.75, 0.005
NCOL = 24
HWIN = int(os.environ.get('HWIN', '18'))
CONTRAST = float(os.environ.get('CONTRAST', '14'))


def X(u, d, lev):
    return O + u * HU + d * HD + np.array([0.0, lev, 0.0])


def row_of(cam, plane_u, lev, cd, col, W, H):
    """where the horizontal line (plane_u, lev) crosses image column `col`, or None."""
    ds = np.linspace(cd - 6.0, cd + 6.0, 121)
    P = np.array([X(plane_u, d, lev) for d in ds])
    x, y, z = cam.project(P)
    ok = z > 0.15
    if ok.sum() < 3:
        return None
    x, y = x[ok], y[ok]
    order = np.argsort(x)
    x, y = x[order], y[order]
    if col < x[0] or col > x[-1]:
        return None
    return float(np.interp(col, x, y))


frames = U.load_class(CLS)
rows = []
print('%s: %d posed frames' % (CLS, len(frames)))
for k in sorted(frames):
    cam, ipath = frames[k]
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
    if abs(cu - UFACE) > 2.0 or ch < 8.8:
        continue           # only the frames standing on this deck
    im = cv2.imread(ipath, cv2.IMREAD_GRAYSCALE)
    if im is None:
        continue
    im = cv2.GaussianBlur(im, (7, 7), 0)
    H, W = im.shape[:2]
    for col in np.linspace(0.18 * W, 0.82 * W, NCOL):
        c = int(round(col))
        v = im[:, c].astype(np.float64)
        lo = H // 2
        best, brow = 0.0, None
        for r in range(lo + HWIN, H - HWIN - 1):
            s = float(v[r - HWIN:r].mean() - v[r + 1:r + 1 + HWIN].mean())
            if s > best:
                best, brow = s, r
        if brow is None or best < CONTRAST:
            continue
        sol = {}
        for name, pu in (('solid', USOLID), ('face', UFACE)):
            levs = np.arange(HLO, HHI + 1e-9, HSTEP)
            got = [(abs(row_of(cam, pu, lv, cd, c, W, H) - brow), lv)
                   for lv in levs if row_of(cam, pu, lv, cd, c, W, H) is not None]
            sol[name] = min(got)[1] if got else None
        rows.append((k, cu, cd, ch, c, brow, best, sol['solid'], sol['face']))

if not rows:
    sys.exit('no frames stand on the %s deck in class %s' % (END, CLS))

byframe = {}
for r in rows:
    byframe.setdefault(r[0], []).append(r)
print('')
print('   frame            u      d      h     n   solid plane u %.3f   face plane u %.3f'
      % (USOLID, UFACE))
allsolid, allface = [], []
for k in sorted(byframe):
    rs = byframe[k]
    s = np.array([r[7] for r in rs if r[7] is not None])
    f = np.array([r[8] for r in rs if r[8] is not None])
    if len(s) < 6:
        continue
    allsolid += list(s)
    allface += list(f)
    print('   %-14s %5.2f %6.2f %6.2f %4d      %.3f +- %.3f       %.3f'
          % (k, rs[0][1], rs[0][2], rs[0][3], len(s), np.median(s),
             float(np.percentile(s, 75) - np.percentile(s, 25)) / 2, np.median(f)))

S = np.array(allsolid)
F = np.array(allface)
print('')
print('   %d rays over %d frames' % (len(S), len(byframe)))
print('   ON THE SOLID PLANE the coping top solves to h %.3f, quartile spread %.0f mm'
      % (np.median(S), 1000 * (np.percentile(S, 75) - np.percentile(S, 25))))
print('   ON THE FACE PLANE it solves to h %.3f, which is %.3f m %s the drawn deck %.2f'
      % (np.median(F), abs(np.median(F) - DECK), 'BELOW' if np.median(F) < DECK else 'above', DECK))
print('')
drawn = DECK + DRAWN_UPSTAND
print('   the model draws the solid upstand top on %.3f, so this reads %+.0f mm against it'
      % (drawn, 1000 * (np.median(S) - drawn)))
if np.median(F) < DECK:
    print('   THE FACE PLANE IS REFUSED BY ITS OWN ANSWER: a coping there would stand below the deck it')
    print('   sits on. The coping is set back, which is what the floor fit said and this did not use.')
per = np.array([np.median([r[7] for r in byframe[k] if r[7] is not None])
                for k in sorted(byframe) if len([r for r in byframe[k] if r[7] is not None]) >= 6])
print('   FRAME TO FRAME, over pitches this set spans, the per-frame medians run %.3f to %.3f, a spread'
      % (per.min(), per.max()))
print('   of %.0f mm. These frames share no pitch and no station, so that spread is the honest error.'
      % (1000 * (per.max() - per.min())))
