# 2026-09-09: POSE THE FRAMES WHERE LLOYD LOOKS AT THE BALCONY, not just the ones where he looks at the hall.
#
# Lloyd, on being shown b5's 24 accepted poses: "those frames are me looking at the hall. but they should be
# more frames when I look around the actual balcony area."
#
# WHY THEY WERE MISSING. register_day4k.py solves every clip frame against the certified SITE model and
# nothing else. That model is the hall: floor, long walls, ceiling. It holds almost no surface on the
# balconies. So a frame aimed down the hall has hundreds of correspondences and a frame aimed at the parapet
# beside the operator's feet has almost none. b5: 287 offered, 242 solved, 24 accepted, and the refusals are
# overwhelmingly low inliers (median 15 against a gate of 30). The gate is not wrong to distrust a pose from
# five points. The information was never there to begin with, because the frames were never matched against
# EACH OTHER. tools/clip_selfmatch.py has now added those matches.
#
# WHAT A STANDING PAN GIVES AND WHAT IT DOES NOT. On a balcony the operator stands and turns. Over a look the
# camera CENTRE barely moves and only the ROTATION changes. That is the best case for rotation and the worst
# case for structure: with no baseline nothing can be triangulated, which is exactly why an earlier solo
# reconstruction of one clip collapsed into eight fragments with focals from 1300 to 2421 px, recorded in the
# register's docstring as "a rotation, not a reconstruction". So this tool does not attempt structure. It
# takes the CENTRE from a frame that solved against the site and the ROTATION from the clip's own matches:
#     rays in frame i and frame j of the same standing look satisfy  x_j = P x_i  with P = R_j R_i^T,
# so P comes from a rotation fit on the matched rays and R_j = P R_i, C_j = C_i.
# P is fitted by RANSAC over triples with Kabsch on UNIT RAYS, undistorted through the clip's own calibrated
# OPENCV camera, then refined on its inliers. No 3D points enter, so nothing about the model or the drawing
# can leak into the answer.
#
# THE HELD CENTRE IS THE ASSUMPTION AND IT IS TESTED, NOT ASSERTED. Two ways, both printed every run:
#   ROTATION HOLD-OUT. Every pair of anchors joined by a chain predicts the second anchor's rotation from the
#     first. The angle between the prediction and the anchor's own site-solved rotation is the error the
#     chaining actually makes, measured against poses this tool did not use to build the chain.
#   CENTRE SPREAD. The same anchor pairs report how far apart their solved centres are, which is how far the
#     operator really moved. A held centre in error by e metres tilts a sightline to a target D metres away
#     by about e/D radians, so the same 0.10 m of unnoticed shuffle is 0.06 degrees on the far end wall and
#     3 degrees on a parapet an arm's length away. The error is therefore reported as a bound in metres for a
#     stated range rather than as a single number.
# A frame is written out only if its chain to an anchor is short and every link on it is strong. Everything
# else is refused and counted.
#
#   python tools/pan_poses.py <prefix> [--min-inliers 60] [--max-hops 6]
import argparse
import os
import sqlite3
import struct
import sys

import numpy as np

sys.path.insert(0, 'tools')
from colmap_bin import read_model  # noqa: E402

WS = 'E:/sitecapture-captures/ngv-video/balcony2-register'
DB = 'E:/sitecapture-captures/ngv-video/balcony2-register/work/database.db'
MAX_PAIR_ID = 2147483647

ap = argparse.ArgumentParser()
ap.add_argument('prefix')
ap.add_argument('--min-inliers', type=int, default=60, help='verified matches a link must carry')
ap.add_argument('--max-hops', type=int, default=6, help='how far a frame may be chained from an anchor')
ap.add_argument('--max-resid-deg', type=float, default=0.20, help='rotation fit residual a link may have')
ap.add_argument('--ransac-deg', type=float, default=0.15, help='angular inlier threshold, some 7 px in a 4K frame')
a = ap.parse_args()
PRE = a.prefix

# ---------------------------------------------------------------- the database
con = sqlite3.connect(DB)
rows = con.execute('SELECT image_id, name, camera_id FROM images').fetchall()
ids, names, camof = {}, {}, {}
for iid, nm, cid in rows:
    ids[nm] = iid
    names[iid] = nm
    camof[iid] = cid
mine = sorted((nm for nm in ids if nm.startswith(PRE) and nm[len(PRE)] == '_'))
if not mine:
    raise SystemExit('no frames for that prefix')
myids = set(ids[nm] for nm in mine)
cam_ids = set(camof[i] for i in myids)
if len(cam_ids) != 1:
    raise SystemExit('the clip spans more than one camera row, register it cleanly first')
cid = cam_ids.pop()
model_id, W, H, prm = con.execute('SELECT model, width, height, params FROM cameras WHERE camera_id = ?', (cid,)).fetchone()
prm = np.frombuffer(prm, dtype=np.float64)
print(PRE, len(mine), 'frames, camera model', model_id, W, 'x', H, np.round(prm, 4).tolist())
K = np.array([[prm[0], 0.0, prm[2]], [0.0, prm[1], prm[3]], [0.0, 0.0, 1.0]])
DIST = np.array(prm[4:8], dtype=np.float64)

kp = {}
for iid, r, c, blob in con.execute('SELECT image_id, rows, cols, data FROM keypoints'):
    if iid not in myids or blob is None:
        continue
    kp[iid] = np.frombuffer(blob, dtype=np.float32).reshape(r, c)[:, :2].astype(np.float64)

links = []
for pid, r, c, blob in con.execute('SELECT pair_id, rows, cols, data FROM two_view_geometries'):
    if blob is None or r < a.min_inliers:
        continue
    i1 = pid // MAX_PAIR_ID
    i2 = pid - i1 * MAX_PAIR_ID
    if i1 not in myids or i2 not in myids:
        continue
    m = np.frombuffer(blob, dtype=np.uint32).reshape(r, c)[:, :2].astype(np.int64)
    links.append((i1, i2, m))
con.close()
print('links carrying', a.min_inliers, 'or more verified matches:', len(links))

# ---------------------------------------------------------------- rays
import cv2  # noqa: E402


def rays(iid, idx):
    pts = kp[iid][idx].reshape(-1, 1, 2)
    und = cv2.undistortPoints(pts, K, DIST).reshape(-1, 2)
    v = np.concatenate([und, np.ones((und.shape[0], 1))], axis=1)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def kabsch(x, y):
    """R with y approx R x, both sets unit vectors."""
    U, _, Vt = np.linalg.svd(y.T @ x)
    d = np.sign(np.linalg.det(U @ Vt))
    S = np.diag([1.0, 1.0, d])
    return U @ S @ Vt


def fit_rotation(x, y, thresh_deg, iters=200):
    n = x.shape[0]
    if n < 8:
        return None
    ct = np.cos(np.radians(thresh_deg))
    rng = np.random.default_rng(12345)
    best, bestn = None, 0
    for _ in range(iters):
        s = rng.choice(n, 3, replace=False)
        R = kabsch(x[s], y[s])
        good = np.sum(y * (x @ R.T), axis=1) > ct
        k = int(good.sum())
        if k > bestn:
            bestn, best = k, good
        if bestn > 0.9 * n:
            break
    if best is None or bestn < 8:
        return None
    R = kabsch(x[best], y[best])
    for _ in range(3):
        good = np.sum(y * (x @ R.T), axis=1) > ct
        if int(good.sum()) < 8:
            break
        R = kabsch(x[good], y[good])
    good = np.sum(y * (x @ R.T), axis=1) > ct
    if int(good.sum()) < 8:
        return None
    ang = np.degrees(np.arccos(np.clip(np.sum(y[good] * (x[good] @ R.T), axis=1), -1.0, 1.0)))
    return R, int(good.sum()), float(np.median(ang))


print('fitting the rotation on every link')
graph = {}
kept = 0
for i1, i2, m in links:
    if i1 not in kp or i2 not in kp:
        continue
    x = rays(i1, m[:, 0])
    y = rays(i2, m[:, 1])
    f = fit_rotation(x, y, a.ransac_deg)
    if f is None:
        continue
    R, ninl, resid = f
    if ninl < a.min_inliers or resid > a.max_resid_deg:
        continue
    kept += 1
    graph.setdefault(i1, []).append((i2, R, ninl, resid))
    graph.setdefault(i2, []).append((i1, R.T, ninl, resid))
print('links that fit a rotation cleanly:', kept, 'of', len(links))

# ---------------------------------------------------------------- anchors
MODEL = os.path.join(WS, 'work', 'model-' + PRE + '-accepted')
if not os.path.isdir(MODEL):
    MODEL = os.path.join(WS, 'work', 'model-' + PRE + '-accepted-with-site')
cams, imgs, _ = read_model(MODEL, with_points2d=False)
anchor = {}
for im in imgs.values():
    base = os.path.basename(im.name)
    if not base.startswith(PRE) or base not in ids:
        continue
    anchor[ids[base]] = (im.R(), np.asarray(im.t).reshape(3), base)
print('anchors from', os.path.basename(MODEL) + ':', len(anchor))
if len(anchor) < 3:
    raise SystemExit('too few anchors to trust anything')


def centre(R, t):
    return -R.T @ t


def chains_from(src, hops):
    """{image_id: (rotation carrying src rays onto its rays, hops, weakest link inliers)}"""
    seen = {src: (np.eye(3), 0, 10 ** 9)}
    front = [src]
    for _ in range(hops):
        nxt = []
        for u in front:
            Ru, hu, wu = seen[u]
            for v, Rv, ninl, _res in graph.get(u, []):
                if v in seen:
                    continue
                seen[v] = (Rv @ Ru, hu + 1, min(wu, ninl))
                nxt.append(v)
        front = nxt
        if not front:
            break
    return seen


# ---------------------------------------------------------------- the hold-out test
print('')
print('ROTATION HOLD-OUT and CENTRE SPREAD, anchor against anchor')
idx_of = {ids[nm]: int(nm.rsplit('_', 1)[1].split('.')[0]) for nm in mine}
errs = []
alist = sorted(anchor)
for src in alist:
    reach = chains_from(src, a.max_hops)
    Rs, ts, _ = anchor[src]
    for dst in alist:
        if dst == src or dst not in reach:
            continue
        P, hops, weak = reach[dst]
        Rpred = P @ Rs
        Rd, td, _ = anchor[dst]
        cosang = (np.trace(Rpred @ Rd.T) - 1.0) / 2.0
        ang = float(np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0))))
        dist = float(np.linalg.norm(centre(Rs, ts) - centre(Rd, td)))
        errs.append((abs(idx_of[dst] - idx_of[src]), hops, weak, ang, dist))

if not errs:
    raise SystemExit('no anchor pair is chain-connected, the chaining cannot be validated so nothing is written')

E = np.array(errs, dtype=float)
print('  ', E.shape[0], 'anchor pairs are chain-connected within', a.max_hops, 'hops')
for lo, hi in [(1, 2), (3, 4), (5, 8)]:
    sel = np.logical_and(E[:, 1] >= lo, E[:, 1] <= hi)
    if sel.sum() >= 3:
        print('   ', int(sel.sum()), 'pairs', lo, 'to', hi, 'hops apart: rotation error median',
              round(float(np.median(E[sel, 3])), 3), 'deg, p90', round(float(np.percentile(E[sel, 3], 90)), 3),
              '| centre distance median', round(float(np.median(E[sel, 4])), 3), 'm, p90',
              round(float(np.percentile(E[sel, 4], 90)), 3))
print('   overall rotation error: median', round(float(np.median(E[:, 3])), 3), 'deg, p90',
      round(float(np.percentile(E[:, 3], 90)), 3), 'worst', round(float(E[:, 3].max()), 3))
print('   overall centre distance: median', round(float(np.median(E[:, 4])), 3), 'm, p90',
      round(float(np.percentile(E[:, 4], 90)), 3), 'worst', round(float(E[:, 4].max()), 3))

# THE ERROR IS NOT THE CHAIN'S, IT IS THE OPERATOR'S FEET. Split the same anchor pairs by how far apart
# their own solved centres are. Where the two anchors stand within a few centimetres of each other the
# operator really was standing still and the pure-rotation model holds; where they are a third of a metre
# apart he was walking and the model is simply the wrong model there, so the disagreement is parallax and
# not a failure of the chaining. Reporting one pooled number for both hides which is which, and it was
# pooling of exactly this kind that produced every overstated certainty this project has had to withdraw.
print('')
print('   THE SAME PAIRS SPLIT BY HOW STILL THE OPERATOR WAS')
for lo, hi in [(0.0, 0.05), (0.05, 0.15), (0.15, 0.40), (0.40, 99.0)]:
    sel = np.logical_and(E[:, 4] >= lo, E[:, 4] < hi)
    if sel.sum() >= 3:
        print('   ', int(sel.sum()), 'pairs whose centres lie', lo, 'to', hi, 'm apart: rotation error median',
              round(float(np.median(E[sel, 3])), 3), 'deg, p90', round(float(np.percentile(E[sel, 3], 90)), 3))
STILL = np.logical_and(E[:, 4] < 0.15, E[:, 1] <= 2)
if STILL.sum() >= 3:
    print('    STANDING STILL, within two hops:', int(STILL.sum()), 'pairs, rotation error median',
          round(float(np.median(E[STILL, 3])), 3), 'deg, p90', round(float(np.percentile(E[STILL, 3], 90)), 3),
          'worst', round(float(E[STILL, 3].max()), 3))
    print('    that is the error this tool actually makes where its assumption holds; a target 3 m away moves',
          round(np.radians(float(np.median(E[STILL, 3]))) * 3.0, 4), 'm and one 30 m away moves',
          round(np.radians(float(np.median(E[STILL, 3]))) * 30.0, 3), 'm')
else:
    print('    NO anchor pair in this clip stands still within two hops, so nothing here can be')
    print('    measured on the standing assumption')
med_ang = float(np.median(E[:, 3]))
med_c = float(np.median(E[:, 4]))
print('')
print('   WHAT THAT MEANS FOR A MEASUREMENT.')
print('   A rotation error of', round(med_ang, 3), 'deg displaces a target 30 m away by',
      round(np.radians(med_ang) * 30.0, 3), 'm, and one 3 m away by', round(np.radians(med_ang) * 3.0, 3), 'm.')
print('   A held centre wrong by', round(med_c, 3), 'm swings a bearing to a target 30 m away by',
      round(np.degrees(med_c / 30.0), 3), 'deg, and to one 3 m away by', round(np.degrees(med_c / 3.0), 3), 'deg.')

# ---------------------------------------------------------------- pose the rest
print('')

# THE CENTRE DOES NOT HAVE TO BE HELD, IT CAN BE INTERPOLATED, and the numbers above say it must be.
# Holding one anchor's centre assumes the operator stood still, and the split by stillness shows he mostly
# did not: in b3 the anchors two hops apart stand a third of a metre from each other, because that clip is a
# WALK along the gallery edge. A walk is not a problem for a position, only for holding one. Between two
# anchors a few tenths of a second apart a person moves in a nearly straight line, so a frame between them
# takes its centre from the straight line joining them, weighted by where it falls in time. Rotation still
# comes from the clip's own matches, which do not care whether he was moving.
# This is tested LEAVE ONE OUT, the only way it can be: each anchor in turn is hidden, its centre predicted
# from the anchors either side of it, and the prediction compared with the centre the site solved for it
# independently. That error is in metres and it is the number that decides whether the pose can measure
# anything, because a wrongly placed camera and a wrongly aimed one are indistinguishable in one frame.
MAXGAP = 30
HOLD = 12         # frames a centre may be held past the end of an anchored stretch


def bracket(i, skip=None):
    lo, hi = None, None
    for j in alist:
        if j == skip:
            continue
        k = idx_of[j]
        if k <= i and (lo is None or k > idx_of[lo]):
            lo = j
        if k >= i and (hi is None or k < idx_of[hi]):
            hi = j
    return lo, hi


def centre_for(i, skip=None):
    """(centre, gap in frames, how it was obtained) or None when no position can be claimed."""
    lo, hi = bracket(i, skip)
    if lo is not None and hi is not None:
        ilo, ihi = idx_of[lo], idx_of[hi]
        Clo = centre(anchor[lo][0], anchor[lo][1])
        Chi = centre(anchor[hi][0], anchor[hi][1])
        if lo == hi:
            return Clo, 0, 'on an anchor'
        if ihi - ilo <= MAXGAP:
            w = (i - ilo) / float(ihi - ilo)
            return (1.0 - w) * Clo + w * Chi, ihi - ilo, 'interpolated'
        return None
    # OUTSIDE THE ANCHORED SPAN THERE IS NOTHING TO INTERPOLATE BETWEEN, and in these clips that is most of
    # the footage: b5's 24 anchors sit in exactly two clusters, frames 71-85 and 165-174, because the site
    # could only locate the operator at two moments of a 287-frame clip. A short reach past the end of a
    # cluster is still defensible, because a person does not teleport in a third of a second, so the nearest
    # anchor's centre is HELD for a few frames and labelled as held rather than interpolated. Beyond that
    # reach nothing is claimed: a frame with no anchor near it in time has no position, and a pose with a
    # guessed position measures nothing however well aimed it is.
    end = lo if lo is not None else hi
    if end is None or abs(i - idx_of[end]) > HOLD:
        return None
    return centre(anchor[end][0], anchor[end][1]), abs(i - idx_of[end]), 'held'


print('CENTRE LEAVE ONE OUT: each anchor hidden and its position predicted from its neighbours')
cerr = []
for j in alist:
    got = centre_for(idx_of[j], skip=j)
    if got is None:
        continue
    Cp, gap, _how = got
    Ct = centre(anchor[j][0], anchor[j][1])
    cerr.append((gap, float(np.linalg.norm(Cp - Ct))))
if len(cerr) >= 3:
    Cq = np.array(cerr, dtype=float)
    print('  ', Cq.shape[0], 'anchors could be predicted: error median', round(float(np.median(Cq[:, 1])), 3),
          'm, p90', round(float(np.percentile(Cq[:, 1], 90)), 3), 'worst', round(float(Cq[:, 1].max()), 3))
    for lo, hi in [(1, 6), (7, 14), (15, 30)]:
        sel = np.logical_and(Cq[:, 0] >= lo, Cq[:, 0] <= hi)
        if sel.sum() >= 3:
            print('    ', int(sel.sum()), 'with the neighbours', lo, 'to', hi, 'frames apart: median',
                  round(float(np.median(Cq[sel, 1])), 3), 'm, p90', round(float(np.percentile(Cq[sel, 1], 90)), 3))
    print('   NOTE this is a HARDER test than the frames it will be used on: a hidden anchor is predicted')
    print('   across a gap of two anchor spacings, while a real frame sits inside ONE spacing.')
else:
    print('   too few anchors bracket each other to test the interpolation')
print('')

# HOW STILL WAS HE JUST THERE. For a frame, the anchors within a short window of it either agree on where
# the operator stood or they do not. The spread between their solved centres is a direct, local measurement
# of the motion the held centre is about to ignore, taken from the same poses the site solved independently.
# It needs two anchors near the frame, so a stretch of clip with only one nearby anchor states no stillness
# and is written with an unknown motion rather than a flattering one.
WIN = 10


def local_motion(fi):
    cs = [centre(anchor[i][0], anchor[i][1]) for i in alist if abs(idx_of[i] - fi) <= WIN]
    if len(cs) < 2:
        return None
    C = np.array(cs)
    return float(np.max(np.linalg.norm(C[:, None, :] - C[None, :, :], axis=2)))


posed = {}
for src in alist:
    Rs, ts, _ = anchor[src]
    si = idx_of[src]
    for dst, (P, hops, weak) in chains_from(src, a.max_hops).items():
        if dst in anchor:
            continue
        got = centre_for(idx_of[dst])
        if got is None:
            continue                      # outside the anchored span, or across too long a gap
        Cd, gap, how = got
        # nearest IN TIME first among equally short chains: a closer anchor means a shorter rotation chain
        # over less of the operator's own movement, which matters more here than a few extra matches.
        rank = (hops, abs(idx_of[dst] - si), -weak)
        prev = posed.get(dst)
        if prev is None or rank < prev[0]:
            posed[dst] = (rank, P @ Rs, Cd, hops, weak, src, gap, how)
print('newly posed frames:', len(posed), 'on top of', len(anchor), 'anchors, out of', len(mine), 'in the clip')
byh = {}
for _k, v in posed.items():
    byh[v[3]] = byh.get(v[3], 0) + 1
for h in sorted(byh):
    print('   ', byh[h], 'frames', h, 'hops from an anchor')
sidecar = {}
gaps = []
for iid, v in posed.items():
    lm = local_motion(idx_of[iid])
    gaps.append(v[6])
    sidecar[names[iid]] = {'hops': int(v[3]), 'weakest_link': int(v[4]), 'anchor': anchor[v[5]][2],
                           'local_motion_m': (None if lm is None else round(lm, 4)),
                           'anchor_gap_frames': int(v[6]), 'centre': v[7],
                           'frames_from_anchor': int(abs(idx_of[iid] - idx_of[v[5]]))}
for iid in anchor:
    lm = local_motion(idx_of[iid])
    sidecar[anchor[iid][2]] = {'hops': 0, 'weakest_link': None, 'anchor': anchor[iid][2],
                               'local_motion_m': (None if lm is None else round(lm, 4)),
                               'anchor_gap_frames': 0, 'centre': 'site solved',
                               'frames_from_anchor': 0}
if gaps:
    G = np.array(gaps, dtype=float)
    print('   the anchors bracketing them are', int(np.median(G)), 'frames apart at the median,',
          int(G.max()), 'worst')

# ---------------------------------------------------------------- write a COLMAP model
out = os.path.join(WS, 'work', 'model-' + PRE + '-pan')
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, 'cameras.bin'), 'wb') as fh:
    fh.write(struct.pack('<Q', 1))
    fh.write(struct.pack('<ii', int(cid), int(model_id)))
    fh.write(struct.pack('<QQ', int(W), int(H)))
    for v in prm:
        fh.write(struct.pack('<d', float(v)))

allp = [(iid, R, t, base) for iid, (R, t, base) in anchor.items()]
for iid, v in posed.items():
    R, C = v[1], v[2]
    allp.append((iid, R, -R @ C, names[iid]))


def quat(R):
    tr = float(np.trace(R))
    if tr > -0.99:
        qw = np.sqrt(max(1e-12, 1.0 + tr)) / 2.0
        return (qw, (R[2, 1] - R[1, 2]) / (4 * qw), (R[0, 2] - R[2, 0]) / (4 * qw), (R[1, 0] - R[0, 1]) / (4 * qw))
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = np.sqrt(max(1e-12, 1.0 + R[i, i] - R[j, j] - R[k, k]))
    q = [0.0, 0.0, 0.0]
    q[i] = s / 2.0
    q[j] = (R[j, i] + R[i, j]) / (2 * s)
    q[k] = (R[k, i] + R[i, k]) / (2 * s)
    return ((R[k, j] - R[j, k]) / (2 * s), q[0], q[1], q[2])


with open(os.path.join(out, 'images.bin'), 'wb') as fh:
    fh.write(struct.pack('<Q', len(allp)))
    for iid, R, t, base in allp:
        qw, qx, qy, qz = quat(np.asarray(R, dtype=float))
        fh.write(struct.pack('<i', int(iid)))
        fh.write(struct.pack('<4d', float(qw), float(qx), float(qy), float(qz)))
        fh.write(struct.pack('<3d', float(t[0]), float(t[1]), float(t[2])))
        fh.write(struct.pack('<i', int(cid)))
        fh.write(base.encode('utf-8') + b'\x00')
        fh.write(struct.pack('<Q', 0))

with open(os.path.join(out, 'points3D.bin'), 'wb') as fh:
    fh.write(struct.pack('<Q', 0))

# The sidecar is what keeps a measurement honest later: every frame carries how it was posed, how far from
# its anchor, and how still the operator was there, so a tool can refuse the moving stretches instead of
# quietly averaging them in.
import json  # noqa: E402
with open(os.path.join(out, 'pan-quality.json'), 'w', encoding='utf-8', newline='\n') as fh:
    json.dump({'prefix': PRE, 'anchors': len(anchor), 'posed': len(posed), 'offered': len(mine),
               'max_hops': a.max_hops, 'min_inliers': a.min_inliers,
               'holdout_rot_deg_median': round(med_ang, 4),
               'holdout_still_rot_deg_median': (round(float(np.median(E[STILL, 3])), 4) if STILL.sum() >= 3 else None),
               'centre_leave_one_out_m_median': (round(float(np.median(np.array(cerr)[:, 1])), 4) if len(cerr) >= 3 else None),
               'centre_leave_one_out_m_p90': (round(float(np.percentile(np.array(cerr)[:, 1], 90)), 4) if len(cerr) >= 3 else None),
               'frames': sidecar}, fh, indent=1)
print('wrote', out, 'with', len(allp), 'images, and pan-quality.json beside it')
