# 2026-09-09: THE EAST PARAPET FROM BOTH SIDES AT ONCE, which is what breaks the tie.
#
# Reading that edge from the deck found a real disagreement and could not resolve it: 449 rays from
# cameras spanning 0.68 m of u fit a face 0.65 m nearer and a top 0.28 m higher just as well as the drawn
# pair, because with every camera on the same side and a metre apart the two unknowns slide along the
# sightline together. That is a conditioning problem, not a data problem, and conditioning is fixed by
# standing somewhere else.
#
# THE OTHER PLACE IS THE HALL FLOOR. From 10 to 40 m away and 8 m below, the same edge is a silhouette
# again, with the opposite polarity: the parapet's face is lit stone and the gallery recess above it is
# dark. A ray from there crosses the edge at a completely different angle from a ray shot over it from
# a metre behind, so the two together pin both unknowns instead of trading them off. The baseline goes
# from 0.68 m to tens of metres.
#
# The search is in image space in both cases and no height is seeded. The face station is used only to
# say which columns of a far picture look at the gallery at all, and the answer is free to land anywhere.
# The drawn pair is scored against the same rays at the end rather than assumed.
#   python tools/parapet_join.py [draw]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UFACE, DECK, DRAWN_TOP = 48.056, 8.34, 9.11
NEAR_CLASSES = ('b7sp', 'b7s', 'b3p', 'b3', 'b6gp', 'b6g')
FAR_CLASSES = ('walk', 'night', 'day4k')
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
BAND, CONTRAST = 40, 30.0
HWIN = 70          # samples of the 0.005 m height ladder averaged either side, so 0.35 m


def rays_of(cam, xs_rows):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(xs_rows, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def near_edge(grey, x):
    """from the deck: walking UP from the bottom, the first dark-below bright-above step"""
    col = grey[:, x].astype(np.float32)
    for r in range(len(col) - BAND - 2, BAND, -3):
        if col[r - BAND:r].mean() - col[r + 1:r + 1 + BAND].mean() > CONTRAST \
                and col[r + 1:r + 1 + BAND].mean() < 110.0:
            return r
    return None


def far_edge(grey, xs, ys, ok):
    """from the hall: the biggest bright-below dark-above step walked ALONG THE WALL, not down the image.

    THE FIRST TWO RUNS WALKED IMAGE COLUMNS AND BOTH WERE WRONG, because the hall-floor clips are shot
    with the phone held portrait and stored rolled about ninety degrees. A level line in the room is a
    VERTICAL line in those pictures, so a column walk crosses it at right angles and finds whatever else
    is there: drawn back, the detections sat along a canopy rib and then along the lift shaft. Walking the
    face plane's own height ladder instead is roll-agnostic, because it follows the geometry rather than
    the sensor.
    """
    idx = np.where(ok)[0]
    if idx.size < 3 * HWIN:
        return None
    a, b = int(idx.min()), int(idx.max())
    if not np.all(ok[a:b + 1]):
        return None
    xi = np.clip(np.round(xs[a:b + 1]), 0, grey.shape[1] - 1).astype(np.int32)
    yi = np.clip(np.round(ys[a:b + 1]), 0, grey.shape[0] - 1).astype(np.int32)
    v = grey[yi, xi].astype(np.float32)
    best, besti = -1e9, None
    for i in range(HWIN, len(v) - HWIN):
        d = float(v[i - HWIN:i].mean() - v[i + 1:i + 1 + HWIN].mean())
        if d > best:
            best, besti = d, i
    if besti is None or best < CONTRAST:
        return None
    return a + besti


near, far = [], []
frames = {}
for cls in NEAR_CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, ('near', v[0], v[1]))
    except Exception:
        pass
for cls in FAR_CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, ('far', v[0], v[1]))
    except Exception:
        pass

hs = np.arange(7.4, 12.0, 0.005)
ds = np.linspace(0.2, 15.2, 400)
face = np.array([O + UFACE * HU + dd * HD + np.array([0, float(v), 0]) for dd in ds for v in hs])

for stem, (kind, cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if kind == 'near':
        if not (48.2 < cu < 50.2 and ch > 8.9):
            continue
    else:
        if not (6.0 < cu < 44.0 and ch < 6.0 and cd > 0.8):
            continue
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
        # THE FIRST RUN LET IN FRAMES POINTED AT THE ROOF. Testing only the horizontal BEARING passes a
        # camera aimed almost straight up, because a nearly vertical forward vector still has its small
        # horizontal part aimed east. Drawn back on w1_000624 the detections sat in a row along a canopy
        # rib, forty degrees above the gallery. A view of the parapet has to be roughly level as well as
        # roughly east, so the vertical part of the direction is capped here too.
        if n < 1e-6 or float(fwd @ HU) / n < 0.6 or abs(float(fwd[1])) > 0.45:
            continue                                  # pointed at the east end, and not at the ceiling
    x, y, z = cam.project(face)
    ok = np.logical_and.reduce((z > 0.3, x > 60, x < cam.w - 60, y > 60, y < cam.h - 60))
    if ok.sum() < 200:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    hits = []
    if kind == 'near':
        cols = sorted(set(int(v) for v in np.round(x[ok] / 40.0) * 40))
        for c in cols:
            m = np.logical_and(ok, np.abs(x - c) < 22)
            if m.sum() < 30:
                continue
            r = near_edge(grey, c)
            if r is None or not (int(y[m].min()) - 60 <= r <= int(y[m].max()) + 60):
                continue
            hits.append((c, r))
    else:
        nh = len(hs)
        for di in range(0, len(ds), 8):
            sl = slice(di * nh, (di + 1) * nh)
            k = far_edge(grey, x[sl], y[sl], ok[sl])
            if k is None:
                continue
            hits.append((int(round(float(x[sl][k]))), int(round(float(y[sl][k])))))
    if len(hits) < 5:
        continue
    v = rays_of(cam, hits)
    for k in range(len(hits)):
        (near if kind == 'near' else far).append((cu, ch, float(v[k] @ HU), float(v[k][1]), stem, hits[k]))

print('%d rays from the deck, %d from the hall floor' % (len(near), len(far)))
if len(near) < 20 or len(far) < 20:
    raise SystemExit('one side is missing, so there is nothing to join')


def fit(rows):
    R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, sv = np.linalg.lstsq(A, y, rcond=None)
    res = A @ sol - y
    return float(sol[0]), float(sol[1]), float(np.sqrt((res ** 2).mean())), \
        (float(sv.max() / sv.min()) if sv.min() > 0 else float('inf')), R


def score(R, uu, vv):
    r = R[:, 3] * uu - R[:, 2] * vv - (R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1])
    return float(np.sqrt((r ** 2).mean()))


for label, rows in (('from the deck alone', near), ('from the hall alone', far),
                    ('both together', near + far)):
    uu, vv, rms, cond, R = fit(rows)
    span = float(R[:, 0].max() - R[:, 0].min())
    print('')
    print('%-20s %5d rays, cameras spanning %6.2f m of u' % (label, len(R), span))
    print('   best line u %.3f h %.3f, condition %.0f, residual %.4f' % (uu, vv, cond, rms))
    print('   the drawn line u %.3f h %.3f scores %.4f, %.2f times the best'
          % (UFACE, DRAWN_TOP, score(R, UFACE, DRAWN_TOP), score(R, UFACE, DRAWN_TOP) / max(rms, 1e-9)))

if 'draw' in sys.argv:
    os.makedirs(OUT, exist_ok=True)
    by = {}
    for r in far:
        by.setdefault(r[4], []).append(r[5])
    if by:
        stem = max(by, key=lambda k: len(by[k]))
        cam, ip = frames[stem][1], frames[stem][2]
        im = cv2.imread(ip)
        for c, r in by[stem]:
            cv2.circle(im, (c, r), 12, (0, 255, 255), 3)
        cv2.putText(im, '%s  %d far detections on the east parapet' % (stem, len(by[stem])), (40, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 255), 3, cv2.LINE_AA)
        k = 1400.0 / im.shape[0]
        cv2.imwrite(os.path.join(OUT, stem + '-parapet-far.jpg'),
                    cv2.resize(im, (int(im.shape[1] * k), 1400)), [cv2.IMWRITE_JPEG_QUALITY, 86])
        print('')
        print('drawn back into', os.path.join(OUT, stem + '-parapet-far.jpg'))
