# 2026-09-10: THE SOUTH WALL MEASURED ON THE FINS' OWN EDGES, WITH THE NORTH JAMBS AS CONTROL.
#
# tools/wall_plane.py tried to place this hall's long walls from the certified cloud and its control
# failed: the north face, known to 1 to 2 mm by the near-far V test, came back scattered by up to 150 mm
# with the two halves of a height band disagreeing by half a metre. So the cloud is out, and the note left
# on that run said what to try instead: the V test itself, pointed at the fins.
#
# WHY A FIN EDGE IS THE RIGHT FEATURE. The south glazing fins stand at known u (18.12, 22.02, 25.92,
# 29.83, 33.73), each 0.40 m wide, and their hall-side face is a strip in one plane of constant d. Each
# vertical edge of that strip is therefore a line at KNOWN u and UNKNOWN d, running the full height of the
# wall. A ray from a posed camera to a point on that edge carries exactly ONE unknown, which is the shape
# of problem this archive has solved before and the shape it keeps failing at when there are two.
#
# THE FOLLOW BIAS IS DESIGNED OUT RATHER THAN HOPED AWAY. tools/follow_test.py measured a finder that
# searched near the line the model drew and found that roughly 45 per cent of its answer was the model
# agreeing with itself. Here DETECTION HAPPENS ONCE, in a window fixed around the drawn d, and the answer
# is then solved from the recorded pixel positions. The sweep never moves the search, so it cannot drag
# the detection after it.
#
# AND IT IS ROTATION-PROOF, which matters because these clips are portrait video: a world-vertical fin
# appears as a near-HORIZONTAL line in the stored frame. Nothing here assumes an axis. The fin is
# projected as a polyline, its local tangent is measured in the image, and the profile is sampled along
# that tangent's normal.
#
# THE TESTS, stated before it runs. Near against far by camera distance from the wall, which is the split
# that bites on a depth. A null of the same frames split odd against even, which shares the geometry and
# so reports only this instrument's own noise. And the north wall's opening jambs run through the same
# code as a control, because their station is already known.
#   python tools/fin_v.py [south|north|both]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FINS = [18.12, 22.02, 25.92, 29.83, 33.73]
# (label, drawn d, [edge u], sample heights, sweep range)
TARGETS = {
    'south': ('the glazing fins', 15.24,
              [u for uf in FINS for u in (uf, uf + 0.40)], (2.5, 4.5, 6.5, 8.5), (14.44, 16.04)),
    'north': ('the opening jambs, CONTROL', -0.030,
              [4.098, 5.310, 7.697, 8.911, 10.707, 11.920, 15.227, 16.440, 18.917, 20.130],
              (9.4, 10.0, 10.6, 11.2), (-0.83, 0.77)),
}
# THE WINDOW IS FIXED IN METRES OF WALL, NOT IN PIXELS, and the first version of this got that wrong.
# 26 px either side covers about 60 mm of depth from three metres away and about 300 mm from fourteen, so
# a pixel window is a different question asked of every frame, and the far frames were free to grab any
# strong edge within a third of a metre. The north control caught it: pooled d -0.285 against a station
# known to -0.030, with a median residual of 8.6 px, which is a detector locking onto the wrong thing.
# The window is now WINM metres of depth converted to pixels per reading.
import os
WINM = float(os.environ.get('WINM', 0.26))
MINGRAD = float(os.environ.get('MINGRAD', 6.0))
MARGIN = float(os.environ.get('MARGIN', 1.6))   # the winner must beat the best rival outside 5 px by this
# THE SETTINGS ARE ENVIRONMENT VARIABLES BECAUSE THEY HAVE TO BE SWEPT. A near-far split and a null test
# whether the answer is well conditioned; neither notices when the DETECTOR is reading a different feature.
# Running the same solve at several detector settings does notice, and here it is decisive.


def polyline(cam, u, d, levs):
    P = np.array([O + u * HU + d * HD + np.array([0.0, lv, 0.0]) for lv in levs])
    x, y, z = cam.project(P)
    return x, y, z


def sample(im, px, py):
    x0, y0 = int(px), int(py)
    if x0 < 1 or y0 < 1 or x0 > im.shape[1] - 3 or y0 > im.shape[0] - 3:
        return np.nan
    ax, ay = px - x0, py - y0
    return float(im[y0, x0] * (1 - ax) * (1 - ay) + im[y0, x0 + 1] * ax * (1 - ay)
                 + im[y0 + 1, x0] * (1 - ax) * ay + im[y0 + 1, x0 + 1] * ax * ay)


def run(which):
    label, d0, edges, levs, (dlo, dhi) = TARGETS[which]
    obs = []
    for cname in ('walk', 'night', 'day4k'):
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in frames.items():
            q = cam.center - O
            cd, ch = float(q @ HD), float(q[1])
            if ch > 3.0:
                continue
            rng = abs(cd - d0)
            if rng < 3.0:
                continue
            im = None
            for ue in edges:
                for lv in levs:
                    x, y, z = polyline(cam, ue, d0, [lv - 0.35, lv, lv + 0.35])
                    if not np.all(z > 0.5):
                        continue
                    px, py = float(x[1]), float(y[1])
                    if not (4 < px < cam.w - 5 and 4 < py < cam.h - 5):
                        continue
                    tx, ty = float(x[2] - x[0]), float(y[2] - y[0])
                    tn = np.hypot(tx, ty)
                    if tn < 8:
                        continue
                    nx, ny = -ty / tn, tx / tn         # the normal to the fin in this picture
                    if im is None:
                        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                        if im is None:
                            break
                        im = cv2.GaussianBlur(im, (3, 3), 0).astype(np.float64)
                    xa, ya, za = polyline(cam, ue, d0 + WINM, [lv])
                    if za[0] <= 0.5:
                        continue
                    win = abs((float(xa[0]) - px) * nx + (float(ya[0]) - py) * ny)
                    if win < 4 or win > 140:
                        continue
                    step = win / 30.0
                    ts = np.arange(-win, win + 0.5 * step, step)
                    prof = np.array([sample(im, px + t * nx, py + t * ny) for t in ts])
                    if np.any(~np.isfinite(prof)):
                        continue
                    g = np.abs(np.gradient(prof))
                    j = int(np.argmax(g))
                    if g[j] < MINGRAD or j < 3 or j > len(g) - 4:
                        continue
                    # AND IT MUST BE THE DOMINANT EDGE IN ITS WINDOW. Without this the detector reports
                    # the strongest of several edges as if it were the only one, which is how a jamb
                    # reading becomes a reveal reading and the control lands 255 mm out.
                    far = np.array([g[m] for m in range(len(g)) if abs(m - j) > 5])
                    if far.size and g[j] < MARGIN * float(far.max()):
                        continue
                    t = float(ts[j])
                    obs.append({'cam': cam, 'u': ue, 'lev': lv, 'px': px + t * nx, 'py': py + t * ny,
                                'nx': nx, 'ny': ny, 'rng': rng, 'cls': cname, 'k': k})
    print('')
    print('%s (%s): %d edge readings from %d frames, camera %.1f to %.1f m off'
          % (which.upper(), label, len(obs), len(set(o['k'] for o in obs)),
             min(o['rng'] for o in obs) if obs else 0, max(o['rng'] for o in obs) if obs else 0))
    if len(obs) < 20:
        print('   too few to solve')
        return None

    def solve(rows):
        ds = np.arange(dlo, dhi + 1e-9, 0.005)
        best, bd = None, None
        for d in ds:
            res = []
            for o in rows:
                x, y, z = polyline(o['cam'], o['u'], d, [o['lev']])
                if z[0] <= 0.5:
                    continue
                res.append(abs((float(x[0]) - o['px']) * o['nx'] + (float(y[0]) - o['py']) * o['ny']))
            if len(res) < max(8, len(rows) // 3):
                continue
            v = float(np.median(res))
            if best is None or v < best:
                best, bd = v, float(d)
        return bd, best

    allb, allr = solve(obs)
    byr = sorted(obs, key=lambda o: o['rng'])
    half = len(byr) // 2
    nb, _ = solve(byr[:half])
    fb, _ = solve(byr[half:])
    ob, _ = solve(obs[1::2])
    eb, _ = solve(obs[0::2])
    print('   pooled d %+.3f   drawn %+.3f   so %+.0f mm   median residual %.2f px'
          % (allb, d0, 1000 * (allb - d0), allr))
    print('   near half %+.3f   far half %+.3f   they differ by %.3f m' % (nb, fb, abs(nb - fb)))
    print('   null: odd %+.3f   even %+.3f   they differ by %.3f m' % (ob, eb, abs(ob - eb)))
    # THE INTERNAL CONTROL THE FINS THEMSELVES PROVIDE. The north jamb control cannot run: tightened
    # enough to be trustworthy, the detector finds only 13 readings up in those dark openings. But five
    # fins stand at five different places along a wall that is one plane, and each has TWO edges 0.40 m
    # apart in u. If the detector is on the fin faces, all of them return the same d. If it is grabbing
    # whatever mullion is nearby, they scatter. That is a control with no outside knowledge in it.
    if which == 'south':
        print('   per fin, which is the control this run actually has:')
        percent = []
        for uf in FINS:
            rows = [o for o in obs if abs(o['u'] - uf) < 0.01 or abs(o['u'] - uf - 0.40) < 0.01]
            if len(rows) < 12:
                print('      fin u %.2f   %3d readings, too few' % (uf, len(rows)))
                continue
            b, r = solve(rows)
            a1 = [o for o in rows if abs(o['u'] - uf) < 0.01]
            a2 = [o for o in rows if abs(o['u'] - uf - 0.40) < 0.01]
            e1 = solve(a1)[0] if len(a1) >= 8 else None
            e2 = solve(a2)[0] if len(a2) >= 8 else None
            percent.append(b)
            print('      fin u %.2f   %3d readings   d %+.3f   near edge %s   far edge %s'
                  % (uf, len(rows), b,
                     ('%+.3f' % e1) if e1 is not None else '   -  ',
                     ('%+.3f' % e2) if e2 is not None else '   -  '))
        if len(percent) >= 3:
            pa = np.array(percent)
            print('      %d fins agree to %.3f m (%.3f to %.3f), median %+.3f'
                  % (len(pa), float(pa.max() - pa.min()), float(pa.min()), float(pa.max()),
                     float(np.median(pa))))
    ok = abs(nb - fb) < 0.05 and abs(nb - fb) <= max(abs(ob - eb), 0.02)
    print('   %s' % ('the near-far halves agree, so this station is measured'
                     if ok else 'the halves do NOT agree inside the null; this station is NOT measured'))
    return allb, d0, nb, fb, ob, eb, ok


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    for w in (('north', 'south') if which == 'both' else (which,)):
        run(w)
    print('')
    print('the north runs first and on purpose: its station is already known to 1 to 2 mm by tools/')
    print('depth_v.py, so if this code cannot return it, nothing it says about the south is worth having.')
