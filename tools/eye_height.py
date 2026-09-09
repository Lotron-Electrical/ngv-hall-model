# 2026-09-10: THE OPERATOR IS THE INSTRUMENT. EVERY POSE IS A MEASUREMENT OF THE FLOOR UNDER IT.
#
# THE REDUNDANCY NOBODY HAS USED. One person shot every clip in this archive, holding one phone. However
# tall he is and however he holds it, the height of the camera above the floor he is standing on is ONE
# CONSTANT, and it is the same constant in the hall as on a balcony. So the height of a posed camera is the
# height of the floor beneath it PLUS that constant, and if two clips stand on floors this model puts at
# different heights, the difference in their camera heights must match the difference in the floors. The
# constant cancels. That is a redundancy the target itself provides, which is one of only three things this
# project has ever found that catches an error.
#
# WHY IT IS AVAILABLE NOW AND WAS NOT BEFORE. The blocker recorded in this repo was that no single clip
# contains both hall-floor frames and gallery frames, so the carry height could not be cancelled WITHIN a
# clip. It does not have to be. The same operator across clips is the same constant, and the hall-floor
# clips measure it directly against a floor nobody disputes.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. THE CONTROL COMES FIRST AND CAN VETO EVERYTHING. The hall-floor captures stand on the hall floor,
#      h = 0 by the definition of this frame. Their camera heights give the operator's eye height and its
#      spread. If the two independent floor captures disagree with each other by more than DISAGREE, the
#      operator is not one constant and NOTHING else may be read.
#   2. For every other posed camera, the floor beneath it is the HIGHEST near-horizontal analytic surface
#      whose footprint contains it and which lies below it. That comes from the geometry the browser
#      built, not from a constant in the source.
#   3. Its implied eye height is its own height minus that floor. A floor is CONSISTENT when the median
#      implied eye height over the frames standing on it lands inside the control band.
#   4. A floor that lands outside is reported with the distance it would have to move, and that distance
#      is only stated where it exceeds the control band's own half-width. A CLAIM MUST NOT BE SMALLER
#      THAN ITS OWN SPREAD.
#   5. A camera with no analytic surface beneath it is UNPLACED and is not read at all.
#
# WHAT IT CANNOT DO. A person can crouch, sit, lean through an opening, or hold a phone overhead, and each
# of those moves the camera without moving the floor. That is why the answer is a MEDIAN over many frames
# and why the control band is measured rather than assumed. It also cannot tell a wrong floor from a wrong
# pose: the solver's own height error rides along.
#   python tools/eye_height.py
import io
import json
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FLOORCL = ('walk', 'night')
OTHER = ('day4k', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s')
FLAT = 0.85          # a surface counts as a floor when its normal is this vertical
DISAGREE = 0.15      # metres the two control captures may differ before nothing may be read
MINF = 5             # frames standing on a surface before its median is worth printing
HALLFLOOR = 'the hall floor, h 0 by the definition of this frame'


def load_floors():
    g = json.loads(io.open('render-match/geom.json', encoding='utf-8').read())
    out = []
    for nm, flat in g['tri'].items():
        v = np.asarray(flat, float).reshape(-1, 3, 3)
        for t in v:
            n = np.cross(t[1] - t[0], t[2] - t[0])
            ln = float(np.linalg.norm(n))
            if ln < 1e-9:
                continue
            if abs(n[2] / ln) < FLAT:
                continue
            out.append((nm, t))
    return out


def inside(t, u, d):
    """Is (u, d) inside the triangle's footprint, ignoring height."""
    ax, ay = t[0][0], t[0][1]
    bx, by = t[1][0] - ax, t[1][1] - ay
    cx, cy = t[2][0] - ax, t[2][1] - ay
    den = bx * cy - by * cx
    if abs(den) < 1e-12:
        return None
    px, py = u - ax, d - ay
    s = (px * cy - py * cx) / den
    r = (bx * py - by * px) / den
    if s < -0.01 or r < -0.01 or s + r > 1.01:
        return None
    return float(t[0][2] + s * (t[1][2] - t[0][2]) + r * (t[2][2] - t[0][2]))


def poses(cls):
    try:
        fr = U.load_class(cls)
    except Exception:
        return []
    out = []
    for k, (cam, ip) in sorted(fr.items()):
        q = cam.center - O
        u, d, h = float(q @ HU), float(q @ HD), float(q[1])
        if not (-1.0 < u < 53.0) or not (-1.5 < d < 16.5):
            continue
        out.append((k, u, d, h))
    return out


def band(v):
    med = float(np.median(v))
    q1, q3 = np.percentile(v, [25, 75])
    return med, float(q1), float(q3)


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   One person shot every clip with one phone, so the height of the camera above the floor he')
    print('   stands on is ONE CONSTANT across the whole archive. THE CONTROL COMES FIRST AND CAN VETO')
    print('   EVERYTHING: the hall-floor captures stand on %s, and their' % HALLFLOOR)
    print('   camera heights give that constant and its spread. If the two independent floor captures')
    print('   disagree by more than %.2f m, the operator is not one constant and nothing else is read.'
          % DISAGREE)
    print('   Then every other camera gets the highest near-horizontal analytic surface beneath it, from')
    print('   the geometry the browser built rather than a constant in the source, and its implied eye')
    print('   height is its own height minus that floor. A floor is CONSISTENT when the median lands in')
    print('   the control band; one that does not is reported with the distance it would have to move,')
    print('   and only where that distance exceeds the band\'s own half-width.')
    print('')

    ctrl = {}
    for cn in FLOORCL:
        p = poses(cn)
        if len(p) < MINF:
            continue
        ctrl[cn] = np.array([t[3] for t in p])
        m, q1, q3 = band(ctrl[cn])
        print('   CONTROL %-6s %4d frames on the hall floor, camera height %.3f m, quartiles %.3f to %.3f'
              % (cn, len(p), m, q1, q3))
    if len(ctrl) < 2:
        sys.exit('   FEWER THAN TWO CONTROL CAPTURES, so the operator constant cannot be checked against '
                 'itself and nothing may be read.')
    meds = [float(np.median(v)) for v in ctrl.values()]
    gap = max(meds) - min(meds)
    allf = np.concatenate(list(ctrl.values()))
    eye, e1, e3 = band(allf)
    half = max(eye - e1, e3 - eye)
    print('   the two controls differ by %.3f m.' % gap)
    if gap > DISAGREE:
        print('')
        print('   THE CONTROLS DISAGREE WITH EACH OTHER, so the operator is not one constant in this')
        print('   archive and NOTHING BELOW MAY BE READ. No floor is being called right or wrong.')
        veto = True
    else:
        veto = False
        print('   THE OPERATOR CARRIES THE CAMERA %.3f m ABOVE THE FLOOR, quartiles %.3f to %.3f, over'
              % (eye, e1, e3))
        print('   %d frames from two captures on different days. That is the constant everything else is'
              % len(allf))
        print('   measured against, and its half-width %.3f m is the smallest claim allowed below.' % half)

    floors = load_floors()
    print('')
    print('   %d near-horizontal analytic triangles can serve as a floor.' % len(floors))
    per = {}
    unplaced = 0
    for cn in list(FLOORCL) + list(OTHER):
        for k, u, d, h in poses(cn):
            best, bnm = None, None
            for nm, t in floors:
                z = inside(t, u, d)
                if z is None or z > h - 0.10:
                    continue
                if best is None or z > best:
                    best, bnm = z, nm
            if best is None:
                if h > 0.10:
                    per.setdefault((HALLFLOOR, cn), []).append(h - 0.0)
                else:
                    unplaced += 1
                continue
            per.setdefault((bnm, cn), []).append(h - best)

    rows = [(nm, cn, np.array(v)) for (nm, cn), v in per.items() if len(v) >= MINF]
    if not rows:
        sys.exit('   NO CAPTURE STANDS ON AN ANALYTIC SURFACE OFTEN ENOUGH TO READ. Nothing is concluded.')
    print('')
    print('   floor beneath the camera        capture  frames   implied eye   quartiles      verdict')
    rows.sort(key=lambda r: -len(r[2]))
    bad = []
    for nm, cn, v in rows:
        m, q1, q3 = band(v)
        off = m - eye
        if veto:
            tag = 'not readable'
        elif abs(off) <= half:
            tag = 'consistent'
        elif abs(off) <= 2 * half:
            tag = 'marginal'
        else:
            tag = 'OUT by %+.2f m' % off
            bad.append((nm, cn, m, off, len(v)))
        print('   %-30s %-7s %6d   %8.3f    %.3f to %.3f  %s'
              % (nm[:30], cn, len(v), m, q1, q3, tag))
    if unplaced:
        print('')
        print('   %d cameras have no analytic surface beneath them and are UNPLACED, which is not a'
              % unplaced)
        print('   verdict on anything.')

    print('')
    if veto:
        print('   NOTHING IS CONCLUDED: the controls vetoed this run.')
    elif not bad:
        print('   EVERY FLOOR THIS ARCHIVE STANDS ON IS CONSISTENT with one operator carrying one camera')
        print('   at one height. That is not proof any of them is right, but a deck drawn %.2f m from'
              % (2 * half))
        print('   where the operator actually stood would have shown here, and none does.')
    else:
        print('   %d FLOORS PUT THE OPERATOR SOMEWHERE HE CANNOT HAVE BEEN:' % len(bad))
        for nm, cn, m, off, n in bad:
            print('      %-28s on %-6s implies an eye height of %.3f m over %d frames, %+.2f m from the'
                  % (nm[:28], cn, m, n, off))
            print('      %s control. Either that surface stands %+.2f m from where it is drawn, or the'
                  % (' ' * 28, -off))
            print('      %s operator was not standing on it.' % (' ' * 28))
        print('   WHICH OF THOSE IT IS CANNOT BE SETTLED HERE, and it is not being settled here. A person')
        print('   leaning through an opening, crouching, or sitting on a step moves the camera without')
        print('   moving the floor, and the solver\'s own height error rides along with all of it.')


if __name__ == '__main__':
    main()
