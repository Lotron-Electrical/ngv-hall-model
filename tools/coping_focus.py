# 2026-09-09: THE COPING FOUND BY FOCUS, which is the one cue the stone cannot hide behind.
#
# Every earlier attempt on a parapet edge looked for BRIGHTNESS: dark stone under a lit hall, or the
# reverse. That is why they kept locking onto canopy ribs and lift shafts. The stone at these decks is the
# same grey as the hall floor beyond it and the contrast is a few grey levels.
#
# BUT IT IS HALF A METRE FROM THE LENS AND THE HALL IS THIRTY. A phone focused on the room throws that
# coping out of focus, and out-of-focus stone has almost no high-frequency energy while the hall floor,
# with people and joints and furniture on it, has a great deal. Walking a row of Laplacian energy up from
# the bottom of the frame finds the boundary between them without ever asking what colour anything is.
#
# WHAT THE ANSWER MEANS, and the limit is the same one that has bitten all day: one camera sees the coping
# edge along a single sightline, so it measures the PAIR (face station, top height) and not either alone.
# The height is therefore printed at a ladder of candidate face stations rather than at one, and the east
# end, where 163 cameras and two independent tests already agree with the drawn face, is run as the control.
# If the east frames return the drawn east top, the instrument works and the west answer means something.
#   python tools/coping_focus.py [east|west|both]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
WEST, EAST, DECK = (4.194, 9.020), (48.056, 9.110), 8.34
CLASSES = ('b7s', 'b7sp', 'b3', 'b3p', 'b6g', 'b6gp')
BAND, RATIO = 60, 2.4                     # rows averaged either side of a candidate boundary, and the jump
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'


def boundary(img):
    """the row where sharp hall gives way to blurred near stone, walking UP from the bottom"""
    h, w = img.shape
    c0, c1 = int(w * 0.20), int(w * 0.80)
    lap = cv2.Laplacian(cv2.GaussianBlur(img[:, c0:c1], (3, 3), 0), cv2.CV_32F)
    e = (lap * lap).mean(axis=1)
    e = np.convolve(e, np.ones(9) / 9.0, 'same')
    lo = float(np.percentile(e, 10))
    for r in range(h - BAND - 2, int(h * 0.35), -2):
        below = float(e[r + 1:r + 1 + BAND].mean())
        above = float(e[r - BAND:r].mean())
        if below < lo * 3.0 and above > below * RATIO:
            return r, below, above
    return None, None, None


def ray_of(cam, x, y):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.array([[[float(x), float(y)]]]), K, dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((1, 1))], 1) @ cam.R
    return (v / np.linalg.norm(v))[0]


want = sys.argv[1] if len(sys.argv) > 1 else 'both'
frames = {}
for cls in CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass

rows = {'east': [], 'west': []}
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, ch = float(q @ HU), float(cam.center[1] - O[1])
    if ch < 8.7:
        continue
    end = 'east' if cu > 26.0 else 'west'
    if want != 'both' and want != end:
        continue
    UF, TOPD = EAST if end == 'east' else WEST
    if abs(cu - UF) < 0.45:
        continue          # the lens is almost on the face, so no sightline of its own crosses it low
    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    r, below, above = boundary(img)
    if r is None:
        continue
    v = ray_of(cam, cam.w * 0.5, r)
    vu, vy = float(v @ HU), float(v[1])
    if abs(vu) < 1e-6:
        continue
    lam = (UF - cu) / vu
    if lam <= 0.02:
        continue
    rows[end].append((stem, cu, ch, float(ch + vy * lam), vu, vy, r, above / max(below, 1e-9)))

for end in ('east', 'west'):
    got = rows[end]
    UF, TOPD = EAST if end == 'east' else WEST
    print('')
    print('%s END: %d frames found a focus boundary. drawn face %.3f, drawn top %.3f (deck %.3f + %.3f)'
          % (end.upper(), len(got), UF, TOPD, DECK, TOPD - DECK))
    if len(got) < 4:
        print('   too few to say anything')
        continue
    hh2 = np.array([g[3] for g in got])
    print('   at the drawn face the boundary sits on h %.3f, quartiles %.3f to %.3f, %d frames'
          % (float(np.median(hh2)), float(np.percentile(hh2, 25)), float(np.percentile(hh2, 75)), len(hh2)))
    print('   that is %+.3f m against the drawn top, an upstand of %.3f rather than %.3f'
          % (float(np.median(hh2)) - TOPD, float(np.median(hh2)) - DECK, TOPD - DECK))
    print('   the locus, because one camera cannot separate the face from the top:')
    for uf in np.arange(UF - 0.6, UF + 0.61, 0.20):
        vals = []
        for _s, cu, ch, _h0, vu, vy, _r, _k in got:
            lam = (uf - cu) / vu
            if lam > 0.02:
                vals.append(ch + vy * lam)
        if len(vals) >= 4:
            print('      face %8.3f  ->  top %8.3f   (upstand %.3f)'
                  % (uf, float(np.median(vals)), float(np.median(vals)) - DECK))
    for g in sorted(got, key=lambda g: g[3])[:4]:
        print('      lowest: %-14s lens u %6.2f h %5.2f, boundary row %4d, sharpness jump %.1fx -> h %.3f'
              % (g[0], g[1], g[2], g[6], g[7], g[3]))

# and one picture per end, so the boundary can be seen rather than trusted
os.makedirs(OUT, exist_ok=True)
for end in ('east', 'west'):
    if not rows[end]:
        continue
    g = sorted(rows[end], key=lambda g: -g[7])[0]
    cam, ip = frames[g[0]]
    im = cv2.imread(ip)
    cv2.line(im, (0, g[6]), (cam.w, g[6]), (90, 255, 255), 5)
    cv2.putText(im, '%s  focus boundary -> h %.3f at the drawn face (drawn top %.3f)'
                % (g[0], g[3], (EAST if end == 'east' else WEST)[1]), (30, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (90, 255, 255), 3, cv2.LINE_AA)
    k = 1500.0 / im.shape[0]
    dst = os.path.join(OUT, '%s-coping-focus.jpg' % end)
    cv2.imwrite(dst, cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('')
    print('%s drawn back into %s' % (end, dst))
