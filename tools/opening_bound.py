# 2026-09-09: THE OPENING HEAD AND SILL BOUNDED BY RAYS THAT ALREADY WENT THROUGH THEM.
#
# openY [8.99, 11.35] is the one number on this wall that a whole day of work could not settle. Every
# instrument aimed at it walked from the drawn height to the nearest gradient, and when the follow gain
# was finally fitted the surviving readings put the head 40 to 205 mm low while disagreeing by 165 mm,
# which is a lean without a magnitude. The gallery ceiling was stuck the same way this afternoon and came
# free the moment the question changed from "where is the edge" to "what did the light get past".
#
# The same question works here, and better, because the rays are already measured. Three lamps deep in
# the room behind this wall were triangulated from the hall floor (tools/corridor_lamp.py), 36 rays in
# all. Every one of those rays entered through an opening, so it cleared the sill under it, the head over
# it and both jambs beside it. The reveal is a rectangular tube 0.9 m deep, and a ray rising through it
# is highest where it leaves the tube, so:
#
#   the HEAD is at least the highest a surviving ray reaches inside the tube
#   the SILL is at most the lowest a surviving ray reaches inside the tube
#   the JAMBS are at least as far apart as the widest a surviving ray runs inside it
#
# Nothing is searched for and nothing is followed. The drawn values are used once, to say which part of
# each picture the lamp search may look in, and the bounds that come out are free to contradict them,
# which is exactly what would happen if the head really did sit 205 mm low.
#   python tools/opening_bound.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import cv2  # noqa: E402
import underside_geom as U  # noqa: E402
import corridor_lamp as CL  # noqa: E402

O, HU, HD = CL.O, CL.HU, CL.HD
DN = CL.DN
DEPTH = 0.9                      # WALLF.openDepth, the reveal's depth
SILL, HEAD = CL.SILL, CL.HEAD
TARGETS = (8, 9, 11)             # the openings whose lamps triangulated


def load_cams():
    seen, cams = set(), {}
    for cls in CL.CLASSES:
        try:
            fr = U.load_class(cls)
        except Exception:
            continue
        for f, v in fr.items():
            if f not in seen:
                seen.add(f)
                cams[f] = (cls, v[0], v[1])
    return cams


def solve(oi, cams):
    u0, u1 = CL.OPENINGS[oi]
    rays = []
    for f, (cls, cam, ip) in cams.items():
        qc = cam.center - O
        if float(qc @ HD) < 0.5 or abs(float(qc @ HU) - 0.5 * (u0 + u1)) > 22.0:
            continue
        q = CL.aperture(cam, u0, u1)
        if q is None or q[:, 0].min() < 0 or q[:, 0].max() > cam.w or q[:, 1].min() < 0 or q[:, 1].max() > cam.h:
            continue
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        for r in CL.rays_for(cam, cv2.GaussianBlur(img, (3, 3), 0), u0, u1):
            rays.append((f,) + r)
    if len(rays) < 4:
        return None
    best = None
    for i in range(len(rays)):
        for j in range(i + 1, len(rays)):
            if np.linalg.norm(rays[i][1] - rays[j][1]) < 1.0:
                continue
            P = CL.closest_point([rays[i][1:], rays[j][1:]])
            inl = [r for r in rays if CL.dist_to(P, r[1], r[2]) < 0.12]
            if best is None or len(inl) > len(best[1]):
                best = (P, inl)
    if best is None or len(best[1]) < 4:
        return None
    P = CL.closest_point([r[1:] for r in best[1]])
    for _ in range(3):
        inl = [r for r in rays if CL.dist_to(P, r[1], r[2]) < 0.12]
        if len(inl) < 4:
            break
        P = CL.closest_point([r[1:] for r in inl])
    inl = [r for r in rays if CL.dist_to(P, r[1], r[2]) < 0.12]
    qq = P - O
    if float(qq @ HD) > DN - 0.5:
        return None                      # not a fitting in the room, so it never crossed the reveal
    return P, inl


def crossings(inl):
    """where each surviving ray sits at the two ends of the reveal tube"""
    rows = []
    for _f, C, v, _a, _b in inl:
        dv = float(v @ HD)
        if abs(dv) < 1e-6:
            continue
        got = []
        for dplane in (DN, DN - DEPTH):
            t = (dplane - float((C - O) @ HD)) / dv
            if t <= 0:
                got = []
                break
            X = C + t * v
            got.append((float((X - O) @ HU), float(X[1] - O[1])))
        if len(got) == 2:
            rows.append(got)
    return rows


cams = load_cams()
print(len(cams), 'distinct posed frames offered to the search')
allhi, alllo = [], []
for oi in TARGETS:
    got = solve(oi - 1, cams)
    if got is None:
        print('opening %2d: no lamp in the room solved from this archive' % oi)
        continue
    P, inl = got
    qq = P - O
    rows = crossings(inl)
    if not rows:
        print('opening %2d: %d rays but none crosses the reveal cleanly' % (oi, len(inl)))
        continue
    hface = np.array([r[0][1] for r in rows])
    hback = np.array([r[1][1] for r in rows])
    uface = np.array([r[0][0] for r in rows])
    uback = np.array([r[1][0] for r in rows])
    hi = float(max(hface.max(), hback.max()))
    lo = float(min(hface.min(), hback.min()))
    u0, u1 = CL.OPENINGS[oi - 1]
    allhi.append(hi)
    alllo.append(lo)
    print('')
    print('opening %2d: lamp on u %.3f d %.3f h %.3f, %d rays through the reveal'
          % (oi, float(qq @ HU), float(qq @ HD), float(P[1] - O[1]), len(rows)))
    print('        at the wall face  h %.3f to %.3f, u %.3f to %.3f' % (hface.min(), hface.max(), uface.min(), uface.max()))
    print('        0.9 m deeper      h %.3f to %.3f, u %.3f to %.3f' % (hback.min(), hback.max(), uback.min(), uback.max()))
    print('        so the head is at least %.3f (drawn %.3f, %s by %.3f)'
          % (hi, HEAD, 'clears it' if HEAD > hi else 'REFUTED', abs(HEAD - hi)))
    print('        and the sill is at most %.3f (drawn %.3f, %s by %.3f)'
          % (lo, SILL, 'clears it' if SILL < lo else 'REFUTED', abs(SILL - lo)))
    ju = float(min(uface.min(), uback.min()))
    jv = float(max(uface.max(), uback.max()))
    print('        the jambs are drawn u %.3f to %.3f and the rays run %.3f to %.3f, %s'
          % (u0, u1, ju, jv, 'inside them' if u0 <= ju and jv <= u1 else 'OUTSIDE them'))

if allhi:
    print('')
    print('ACROSS THE THREE OPENINGS')
    print('   the head is at least %.3f. The sim draws %.3f, so it has %.3f m of clearance.'
          % (max(allhi), HEAD, HEAD - max(allhi)))
    print('   the sill is at most %.3f. The sim draws %.3f, so it has %.3f m of clearance.'
          % (min(alllo), SILL, min(alllo) - SILL))
    print('   the readings that wanted the head 0.040 to 0.205 m LOWER would put it on %.3f to %.3f,'
          % (HEAD - 0.205, HEAD - 0.040))
    if HEAD - 0.205 < max(allhi):
        print('   and light measurably came through above %.3f, so the lowest of them is refused outright.'
              % max(allhi))
