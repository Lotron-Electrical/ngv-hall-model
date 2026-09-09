# 2026-09-09: TRIANGULATE WHAT THE OPERATOR WAS STANDING NEXT TO, now that those frames have poses.
#
# The pan poses from tools/pan_poses.py are weak for far targets and strong for near ones: the leave-one-out
# position error is 0.02 to 0.10 m and the rotation hold-out 0.17 to 0.58 deg, so a thing 30 m down the hall
# is placed to a third of a metre and a thing 1.5 m from the operator's hands to about 15 mm. The accepted
# frames already measure the far hall better than this ever will. What they cannot measure at all is what is
# CLOSE to a balcony camera, because no accepted frame is up there looking at it.
#
# So this triangulates only the near field. Every verified two-view match between two posed frames of the
# same clip is intersected, and a point is kept only when the geometry is honest about itself:
#   - both rays in front of both cameras,
#   - the angle between them wide enough that the intersection is defined rather than parallel,
#   - the reprojection error small in BOTH frames,
#   - the point within a stated range of the camera, because that is the regime the poses support.
# Nothing here starts from the model, so nothing here can echo it. The output is points in hall coordinates
# and a height histogram against the wall, which is how a rail, a sill or a deck edge shows itself: as a
# horizontal concentration of points at one height across a run of u.
#
#   python tools/pan_points.py <class> [--near 4.0] [--min-angle 1.0] [--max-reproj 3.0]
import argparse
import sqlite3
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

DB = 'E:/sitecapture-captures/ngv-video/balcony2-register/work/database.db'
MAX_PAIR_ID = 2147483647
O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

ap = argparse.ArgumentParser()
ap.add_argument('cls')
ap.add_argument('--near', type=float, default=4.0, help='metres from the camera a point may be')
ap.add_argument('--min-angle', type=float, default=1.0, help='degrees between the two rays')
ap.add_argument('--max-reproj', type=float, default=3.0, help='pixels, in both frames')
ap.add_argument('--out', default=None)
a = ap.parse_args()

frames = U.load_class(a.cls)
print(a.cls, len(frames), 'posed frames')

con = sqlite3.connect(DB)
name_of = {}
for iid, nm in con.execute('SELECT image_id, name FROM images'):
    st = nm.rsplit('.', 1)[0]
    if st in frames:
        name_of[iid] = st
kp = {}
for iid, r, c, blob in con.execute('SELECT image_id, rows, cols, data FROM keypoints'):
    if iid in name_of and blob is not None:
        kp[iid] = np.frombuffer(blob, dtype=np.float32).reshape(r, c)[:, :2].astype(np.float64)
pairs = []
for pid, r, c, blob in con.execute('SELECT pair_id, rows, cols, data FROM two_view_geometries'):
    if blob is None or r < 20:
        continue
    i1 = pid // MAX_PAIR_ID
    i2 = pid - i1 * MAX_PAIR_ID
    if i1 in name_of and i2 in name_of:
        pairs.append((i1, i2, np.frombuffer(blob, dtype=np.uint32).reshape(r, c)[:, :2].astype(np.int64)))
con.close()
print(len(pairs), 'verified pairs between posed frames')

import cv2  # noqa: E402

cams = {iid: frames[name_of[iid]][0] for iid in name_of}


def world_rays(cam, pts):
    K = np.array([[cam.params[0], 0, cam.params[2]], [0, cam.params[1], cam.params[3]], [0, 0, 1.0]])
    dist = np.array(cam.params[4:8], dtype=np.float64)
    und = cv2.undistortPoints(pts.reshape(-1, 1, 2), K, dist).reshape(-1, 2)
    v = np.concatenate([und, np.ones((und.shape[0], 1))], axis=1)
    v = v @ cam.R                      # R is world to camera, so right-multiplying applies its transpose
    return v / np.linalg.norm(v, axis=1, keepdims=True)


cosmin = np.cos(np.radians(a.min_angle))
pts = []
for i1, i2, m in pairs:
    c1, c2 = cams[i1], cams[i2]
    C1, C2 = c1.center, c2.center
    if np.linalg.norm(C1 - C2) < 1e-6:
        continue                       # two frames sharing a held centre cannot triangulate anything
    v1 = world_rays(c1, kp[i1][m[:, 0]])
    v2 = world_rays(c2, kp[i2][m[:, 1]])
    w0 = C1 - C2
    b = np.sum(v1 * v2, axis=1)
    q1 = np.sum(v1 * w0, axis=1)
    q2 = np.sum(v2 * w0, axis=1)
    den = 1.0 - b * b
    ok = np.logical_and(den > 1e-9, np.abs(b) < cosmin)
    if not ok.any():
        continue
    safe = np.where(den > 1e-9, den, 1.0)
    s = (b * q2 - q1) / safe
    t = (q2 - b * q1) / safe
    P1 = C1 + v1 * s[:, None]
    P2 = C2 + v2 * t[:, None]
    X = 0.5 * (P1 + P2)
    gap = np.linalg.norm(P1 - P2, axis=1)
    r1 = np.linalg.norm(X - C1, axis=1)
    r2 = np.linalg.norm(X - C2, axis=1)
    keep = np.logical_and(ok, np.logical_and(s > 0, t > 0))
    keep = np.logical_and(keep, np.logical_and(r1 < a.near, r2 < a.near))
    keep = np.logical_and(keep, gap < 0.05)
    if not keep.any():
        continue
    Xk = X[keep]
    x1, y1, z1 = c1.project(Xk)
    x2, y2, z2 = c2.project(Xk)
    k1 = kp[i1][m[keep, 0]]
    k2 = kp[i2][m[keep, 1]]
    e1 = np.hypot(x1 - k1[:, 0], y1 - k1[:, 1])
    e2 = np.hypot(x2 - k2[:, 0], y2 - k2[:, 1])
    good = np.logical_and(e1 < a.max_reproj, e2 < a.max_reproj)
    if good.any():
        pts.append(Xk[good])

if not pts:
    raise SystemExit('nothing survived, the near field carries no triangulable structure in this class')
P = np.concatenate(pts, axis=0)
Q = P - O
hall_u = Q @ HU
hall_d = Q @ HD
hall_h = P[:, 1] - O[1]
print(len(P), 'near-field points survived every test')
print('   u', round(float(np.percentile(hall_u, 2)), 2), 'to', round(float(np.percentile(hall_u, 98)), 2),
      '| d', round(float(np.percentile(hall_d, 2)), 2), 'to', round(float(np.percentile(hall_d, 98)), 2),
      '| h', round(float(np.percentile(hall_h, 2)), 2), 'to', round(float(np.percentile(hall_h, 98)), 2))
print('')
print('  HEIGHT HISTOGRAM, 25 mm bins, the fifteen fullest bins')
lo = float(np.floor(hall_h.min() * 40) / 40)
hi = float(np.ceil(hall_h.max() * 40) / 40)
edges = np.arange(lo, hi + 0.025, 0.025)
cnt, _ = np.histogram(hall_h, bins=edges)
for k in np.argsort(cnt)[::-1][:15]:
    sel = np.logical_and(hall_h >= edges[k], hall_h < edges[k + 1])
    print('    h', round(float(edges[k]), 3), 'to', round(float(edges[k + 1]), 3), ':', int(cnt[k]),
          'points, u', round(float(np.percentile(hall_u[sel], 10)), 2), 'to',
          round(float(np.percentile(hall_u[sel], 90)), 2),
          ', d median', round(float(np.median(hall_d[sel])), 3))

if a.out:
    fh = open(a.out, 'w', encoding='utf-8', newline='\n')
    print('u,d,h', file=fh)
    for k in range(len(P)):
        print(round(float(hall_u[k]), 4), round(float(hall_d[k]), 4), round(float(hall_h[k]), 4), sep=',', file=fh)
    fh.close()
    print('wrote', a.out)
