# 2026-09-10: A MAN WALKED FROM HERE TO HERE. DOES THIS MODEL PUT A WALL BETWEEN THEM?
#
# THE COMPLEMENT OF YESTERDAY'S TEST. tools/body_in_wall.py showed that 250 posed cameras standing inside
# the thickness of the north wall are, 248 times out of 250, inside an opening this file draws. That test
# is one-sided by construction: it can show a hole is too NARROW and can never show one is too WIDE, and it
# said so. This is the other side. Consecutive frames of a clip are consecutive positions of one man
# holding one phone, a tenth of a metre apart, so the straight step between them is a path he actually
# took. IF A MODELLED SURFACE CROSSES THAT STEP, either the surface is not there or the pose is wrong.
#
# WHY IT IS WORTH RUNNING ON THIS GOAL SPECIFICALLY. It does not care which surface it is testing. Every
# balcony deck, parapet, upstand, fascia, wall face, reveal and corridor quad in the file is checked at
# once against every step anybody ever took, and the ones nobody walked near simply return nothing, which
# is the honest answer for them.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. A step counts only if the two frames are adjacent in their own clip and no further apart than
#      MAXSTEP, so a tracking jump is never read as a walk.
#   2. THE NULL IS THE SAME STEP TURNED ON THE SPOT. Each step is rotated about its own midpoint through
#      a set of angles, keeping its length and its place. That asks the only question that matters: from
#      where he was standing, how easy is it to hit something by walking any direction at all? A surface
#      that the real steps cross no more often than the turned ones is not being contradicted, it is just
#      in a crowded place.
#   3. A surface is CONTRADICTED only where the real steps cross it more often than the turned steps do,
#      by more than the spread of the turned rate over the angles tried.
#   4. Crossings are reported per surface with the clip and the step, because a fault worth acting on has
#      to be findable.
#
# WHAT IT CANNOT DO, AND ONE OF THESE MATTERS A LOT. The camera is held out in front of the body, so near
# a wall the phone can legitimately pass through a thin surface the man walked beside: expect the reveal
# and the jambs to take crossings that are the arm, not the wall. A door leaf is a surface people walk
# through by design, and that is the positive control rather than a fault. And this cannot tell a wrong
# surface from a wrong pose; the solver quotes 24 to 100 mm on these clips.
#   python tools/walk_through.py
import io
import json
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s',
           'b1p', 'b3p', 'b5p', 'b7sp')
MAXSTEP = 1.00        # metres between two frames before it stops being a step and becomes a jump
MAXGAP = 6            # frame numbers apart before two frames are not adjacent
ANGLES = (30, 75, 120, 165, 210, 255, 300, 345)


def load_tris():
    g = json.loads(io.open('render-match/geom.json', encoding='utf-8').read())
    names, tris = [], []
    for nm, flat in g['tri'].items():
        v = np.asarray(flat, float).reshape(-1, 3, 3)
        for t in v:
            names.append(nm)
            tris.append(t)
    return names, np.asarray(tris)


def crossings(a, b, T):
    """Which triangles of T the segment a->b passes through. Moller-Trumbore, vectorised."""
    d = b - a
    e1 = T[:, 1] - T[:, 0]
    e2 = T[:, 2] - T[:, 0]
    p = np.cross(d, e2)
    det = np.einsum('ij,ij->i', e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.zeros_like(det)
    inv[ok] = 1.0 / det[ok]
    s = a - T[:, 0]
    u = np.einsum('ij,ij->i', s, p) * inv
    q = np.cross(s, e1)
    v = np.einsum('j,ij->i', d, q) * inv
    t = np.einsum('ij,ij->i', e2, q) * inv
    hit = ok
    hit = np.logical_and(hit, u >= 0.0)
    hit = np.logical_and(hit, u <= 1.0)
    hit = np.logical_and(hit, v >= 0.0)
    hit = np.logical_and(hit, u + v <= 1.0)
    hit = np.logical_and(hit, t >= 0.0)
    hit = np.logical_and(hit, t <= 1.0)
    return hit


def turn(a, b, deg):
    """The same step, same length, same midpoint, pointed somewhere else."""
    m = 0.5 * (a + b)
    d = b - a
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    r = np.array([c * d[0] - s * d[1], s * d[0] + c * d[1], d[2]])
    return m - 0.5 * r, m + 0.5 * r


def steps():
    out = []
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception:
            continue
        pts = {}
        for k, (cam, ip) in fr.items():
            mo = re.search(r'(\d+)$', k)
            if not mo:
                continue
            q = cam.center - O
            pts.setdefault(k[:mo.start()], []).append(
                (int(mo.group(1)), np.array([float(q @ HU), float(q @ HD), float(q[1])]), k))
        for pre, lst in pts.items():
            lst.sort()
            for i in range(len(lst) - 1):
                n0, p0, k0 = lst[i]
                n1, p1, k1 = lst[i + 1]
                if n1 - n0 > MAXGAP:
                    continue
                if np.linalg.norm(p1 - p0) > MAXSTEP:
                    continue
                out.append((cn, k0, k1, p0, p1))
    return out


def pt_tri(p, T):
    """Distance from one point to every triangle in T, vectorised. Standard closest-point-on-triangle."""
    a = T[:, 0]
    e0 = T[:, 1] - a
    e1 = T[:, 2] - a
    dd = a - p
    A = np.einsum('ij,ij->i', e0, e0)
    B = np.einsum('ij,ij->i', e0, e1)
    C = np.einsum('ij,ij->i', e1, e1)
    D = np.einsum('ij,ij->i', e0, dd)
    E = np.einsum('ij,ij->i', e1, dd)
    det = np.maximum(A * C - B * B, 1e-18)
    s = (B * E - C * D) / det
    t = (B * D - A * E) / det
    # the six regions of the standard solution, done with clamps rather than branches
    s = np.clip(s, 0.0, 1.0)
    t = np.clip(t, 0.0, 1.0)
    over = s + t > 1.0
    if over.any():
        half = 0.5 * (s[over] + t[over] - 1.0)
        s[over] = np.clip(s[over] - half, 0.0, 1.0)
        t[over] = np.clip(t[over] - half, 0.0, 1.0)
    q = a + s[:, None] * e0 + t[:, None] * e1
    return np.sqrt(((q - p) ** 2).sum(1))


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   Consecutive frames of a clip are consecutive positions of one man holding one phone, so the')
    print('   straight step between them is a path he actually took. A step counts only if the frames are')
    print('   adjacent in their own clip, no more than %d frame numbers apart, and no further than %.2f m,'
          % (MAXGAP, MAXSTEP))
    print('   so a tracking jump is never read as a walk. If a modelled surface crosses a real step,')
    print('   either the surface is not there or the pose is wrong.')
    print('   THE NULL IS THE SAME STEP TURNED ON THE SPOT: same length, same midpoint, pointed somewhere')
    print('   else, through %d angles. That asks the only question that matters, which is how easy it is'
          % len(ANGLES))
    print('   to hit something by walking ANY direction from where he was standing. A surface is')
    print('   CONTRADICTED only where the real steps cross it more often than the turned ones, by more')
    print('   than the spread of the turned rate over those angles.')
    print('')

    names, T = load_tris()
    S = steps()
    if not S:
        sys.exit('   NO CLIP YIELDS AN ADJACENT PAIR OF FRAMES. Nothing to test.')
    print('   %d analytic triangles over %d names, and %d real steps from %d captures.'
          % (len(T), len(set(names)), len(S), len({s[0] for s in S})))
    lens = [float(np.linalg.norm(s[4] - s[3])) for s in S]
    print('   a step is %.3f m at the median, %.3f m at the upper quartile.'
          % (float(np.median(lens)), float(np.percentile(lens, 75))))

    nm = np.asarray(names)
    real = {}
    for cn, k0, k1, p0, p1 in S:
        h = crossings(p0, p1, T)
        if not h.any():
            continue
        for x in set(nm[h]):
            real.setdefault(x, []).append((cn, k0, k1))
    null = {}
    for deg in ANGLES:
        c = {}
        for cn, k0, k1, p0, p1 in S:
            a, b = turn(p0, p1, deg)
            h = crossings(a, b, T)
            if not h.any():
                continue
            for x in set(nm[h]):
                c[x] = c.get(x, 0) + 1
        for x, v in c.items():
            null.setdefault(x, []).append(v)

    allnames = sorted(set(list(real.keys()) + list(null.keys())))
    if not allnames:
        print('')
        print('   NOT ONE STEP, REAL OR TURNED, CROSSES ANY MODELLED SURFACE. Nobody in this archive ever')
        print('   walked near enough to the balconies, the walls or the corridor for this test to speak.')
        sys.exit(0)

    rows = []
    for x in allnames:
        r = len(real.get(x, []))
        nl = null.get(x, [])
        nmean = float(np.mean(nl)) if nl else 0.0
        nspread = float(max(nl) - min(nl)) if len(nl) > 1 else 0.0
        rows.append((x, r, nmean, nspread, r - nmean > max(nspread, 1.0)))
    rows.sort(key=lambda t: -(t[1] - t[2]))
    print('')
    print('   surface                    real steps   turned steps   spread   verdict')
    for x, r, nmean, nspread, bad in rows:
        print('   %-26s %10d   %12.1f   %6.1f   %s'
              % (x[:26], r, nmean, nspread, 'CONTRADICTED' if bad else 'not contradicted'))

    # AND THE PASS IS ONLY WORTH WHAT THE COVERAGE IS WORTH. A step is a tenth of a metre, so it crosses
    # a surface only where a man walked within a tenth of a metre of it, and a surface nobody went near
    # returns nothing whether it is right or wrong. So the closest approach is measured for every surface,
    # and that turns a pass into a BOUND: a surface cannot be further out towards the path than the
    # closest anyone came, because he would have walked through it. One-sided, in one direction, and
    # exactly the direction yesterday's body-in-the-wall test could not reach.
    print('')
    print('   HOW CLOSE ANYBODY EVER CAME, which is what the pass above is worth:')
    print('   surface                    closest approach   what that bounds')
    P = np.array([s[3] for s in S] + [S[-1][4]])
    best = {}
    for i in range(len(P)):
        d = pt_tri(P[i], T)
        for x in set(nm):
            sel = nm == x
            v = float(d[sel].min())
            if x not in best or v < best[x][0]:
                best[x] = (v, i)
    for x, (v, i) in sorted(best.items(), key=lambda t: t[1][0]):
        if v > 5.0:
            note = 'nobody came near it, so this says nothing'
        elif v > 1.0:
            note = 'it could be %.1f m out towards the path unnoticed' % v
        else:
            note = 'it cannot be more than %.3f m out towards the path' % v
        print('   %-26s %16.3f   %s' % (x[:26], v, note))
    who = [(s[0], s[1]) for s in S] + [(S[-1][0], S[-1][2])]
    tight = [(x, v, i) for x, (v, i) in best.items() if v <= 0.35]
    print('')
    if tight:
        print('   %d SURFACES ARE BOUNDED TO 0.35 m OR BETTER BY SOMEBODY WALKING PAST THEM:' % len(tight))
        for x, v, i in sorted(tight, key=lambda t: t[1]):
            cn, k = who[i] if i < len(who) else ('?', '?')
            print('      %-26s cannot be more than %.3f m out towards where he walked, set by %s %s'
                  % (x[:26], v, cn, k))
        print('   AND ONE OF THOSE NEEDS SAYING PLAINLY. A bound of a millimetre is not a measurement of a')
        print('   rail, it is a camera sitting ON it, which is what a phone resting on a balustrade looks')
        print('   like. It still bounds the rail in the one direction this test can bound anything, but it')
        print('   is not evidence that the rail is right, only that it is not further out than the phone.')
    else:
        print('   NO SURFACE IS BOUNDED TO 0.35 m: nobody in this archive walked close enough to any of')
        print('   them for the pass above to constrain much, and that is the honest size of this result.')

    bad = [t for t in rows if t[4]]
    print('')
    if not bad:
        print('   NOT ONE SURFACE IS CONTRADICTED. Every crossing this archive makes is one a man turning')
        print('   on the spot would have made just as often, which is what a model with its walls in the')
        print('   right places looks like from the inside.')
    else:
        print('   %d SURFACES ARE CROSSED MORE OFTEN THAN TURNING ON THE SPOT EXPLAINS:' % len(bad))
        for x, r, nmean, nspread, _ in bad:
            who = real.get(x, [])
            caps = sorted({c for c, _, _ in who})
            print('      %-26s %d real against %.1f turned, spread %.1f, from %s'
                  % (x[:26], r, nmean, nspread, ', '.join(caps)))
            for cn, k0, k1 in who[:3]:
                print('         %s %s to %s' % (cn, k0, k1))
        print('')
        print('   AND WHAT THAT DOES NOT MEAN. The phone is held out in front of the body, so beside a')
        print('   wall the camera can pass through a thin surface the man walked past: a reveal or a jamb')
        print('   taking crossings is an arm, not a fault. A door leaf is a surface people walk through by')
        print('   design and is the positive control here rather than an error. What deserves attention is')
        print('   a DECK, a PARAPET or a WALL FACE in this list, because nobody walks through those.')


if __name__ == '__main__':
    main()
