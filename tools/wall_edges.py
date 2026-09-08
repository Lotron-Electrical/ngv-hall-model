# 2026-09-09: the north wall's twelve openings measured SIDEWAYS against the photographs. The companion to
# tools/end_levels.py, which does the same for horizontal lines at the ends: here each opening's two jambs
# are vertical lines on the wall face (d -0.09, h 8.99 to 11.35), so the search runs across the hall
# instead of up it, and the offset is reported along u. A positive offset means the real jamb stands
# further east than the model draws it.
# The same three protections apply. The search window is in metres and never reaches halfway to the
# opening's other jamb, so one jamb cannot be found twice. Frames are ranked by sharpness, because an
# opening 120 px wide over 20 m of hall gives about 12 px per 0.1 m and a hand-held walking frame carries
# that much blur. And the offsets are split by camera distance: a wall FACE in the wrong place (the model
# puts it on d -0.09) produces a sideways offset that shrinks as the camera backs away, while a jamb in
# the wrong place along the hall does not.
#   python tools/wall_edges.py <class> [max_frames]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098,5.310],[7.697,8.911],[10.785,11.998],[15.154,16.367],[18.646,19.859],[22.357,23.570],
        [26.066,27.279],[29.816,31.028],[33.495,34.706],[37.177,38.383],[40.906,42.118],[44.526,45.739]]
DFACE = -0.09
cls = sys.argv[1]
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 40
JAMBS = []
for i, (a, b) in enumerate(OPEN):
    JAMBS.append(('opening %2d west jamb' % i, i, a))
    JAMBS.append(('opening %2d east jamb' % i, i, b))
ALLU = sorted(u for _, _, u in JAMBS)
def window(uu):
    near = min((abs(uu - o) for o in ALLU if abs(o - uu) > 1e-6), default=1.0)
    return min(0.35, 0.45 * near)
frames = U.load_class(cls)
# Frames are chosen PER JAMB, not once for the whole wall. Ranking the class as a whole picks the sharpest
# frames anywhere and they all look at the same stretch of wall, which is why the first run measured
# openings 4-6 from 20 frames and openings 0-3 from three. Here every frame's sharpness is read once, every
# frame is asked which jambs it can actually resolve, and each jamb then takes the sharpest frames that see
# IT. An image is still only read once, whatever it ends up measuring.
sharp, sees = {}, {}
for fr, (cam, ip) in frames.items():
    vis = []
    for name, oi, uu in JAMBS:
        pts = np.array([O + uu * HU + DFACE * HD + np.array([0, hv, 0]) for hv in (9.2, 10.2, 11.2)])
        side = np.array([O + (uu + 0.25) * HU + DFACE * HD + np.array([0, hv, 0]) for hv in (9.2, 10.2, 11.2)])
        x, y, z = cam.project(pts); xs, ys, zs = cam.project(side)
        if (z <= 0.5).any() or (zs <= 0.5).any(): continue
        if ((x > 40) * (x < cam.w - 40) * (y > 40) * (y < cam.h - 40)).sum() < 3: continue
        if np.median(np.hypot(xs - x, ys - y)) < 5: continue      # 0.25 m is under 5 px: unresolvable
        vis.append(name)
    if not vis: continue
    small = cv2.imread(ip, cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if small is None: continue
    sharp[fr] = float(cv2.Laplacian(small, cv2.CV_32F).var()); sees[fr] = vis
want = {}
for name, oi, uu in JAMBS:
    got = sorted((f for f in sees if name in sees[f]), key=lambda f: -sharp[f])[:maxf]
    for f in got: want.setdefault(f, []).append(name)
acc = {n: [] for n, _, _ in JAMBS}
used = 0
for fr in sorted(want, key=lambda f: -sharp[f]):
    cam, ip = frames[fr]
    img = None
    for name in want[fr]:
        uu = dict((n, u) for n, _, u in JAMBS)[name]
        win = window(uu)
        hs = np.linspace(9.15, 11.20, 15)
        pts = np.array([O + uu * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        side = np.array([O + (uu + 0.25) * HU + DFACE * HD + np.array([0, hv, 0]) for hv in hs])
        x, y, z = cam.project(pts); xs, ys, zs = cam.project(side)
        ok = (z > 0.5) * (zs > 0.5) * (x > 40) * (x < cam.w - 40) * (y > 40) * (y < cam.h - 40)
        if ok.sum() < 6: continue
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None: break
            img = cv2.GaussianBlur(img, (5, 5), 0)
            used += 1
        offs = []
        for i in np.flatnonzero(ok):
            vx, vy = xs[i] - x[i], ys[i] - y[i]
            L = np.hypot(vx, vy)
            if L < 5: continue
            mpp = 0.25 / L
            R = int(round(win / mpp))
            if R < 4 or R > 90: continue
            t = np.arange(-R, R + 1)
            sx = np.clip(np.round(x[i] + vx / L * t).astype(int), 0, img.shape[1] - 1)
            sy = np.clip(np.round(y[i] + vy / L * t).astype(int), 0, img.shape[0] - 1)
            prof = img[sy, sx].astype(np.float32)
            if prof.max() - prof.min() < 10: continue
            j = int(np.argmax(np.abs(np.gradient(prof))[2:-2])) + 2
            offs.append(float(t[j]) * mpp)
        if len(offs) >= 5:
            q = cam.center - O
            acc[name].append((float(np.median(offs)),
                              float(np.hypot(float(q @ HU) - uu, float(q @ HD) - DFACE)),
                              float(q @ HU) - uu,
                              (float(q @ HU) - uu) / max(float(q @ HD) - DFACE, 0.5)))
cand = list(sharp)
# A capture's own quartiles say how well ITS frames agree with each other, which is not the same as how
# well the measurement is known: consecutive frames of one walking pass share the pass's every systematic.
# So the per-capture medians are written out and tools/wall_pool.py pools them ACROSS captures, where the
# real spread lives. Pass a path as the last argument to write this capture's medians there.
import json, os
if os.environ.get('WALL_JSON'):
    rec = {}
    for nm, oi, uu in JAMBS:
        a = acc[nm]
        if len(a) >= 3:
            v = [x[0] for x in a]
            rec[nm] = {'u': uu, 'opening': oi, 'n': len(v), 'median': float(np.median(v)),
                       'p25': float(np.percentile(v, 25)), 'p75': float(np.percentile(v, 75))}
    json.dump({'class': cls, 'frames': used, 'jambs': rec}, open(os.environ['WALL_JSON'], 'w'), indent=1)
    print('wrote', os.environ['WALL_JSON'])
print('%s: %d frames measured (of %d that see the wall)' % (cls, used, len(cand)))
rows = []
for name, oi, uu in JAMBS:
    a = np.array(acc[name])
    if a.shape[0] < 3: print('  %-22s u %6.3f   only %d frames' % (name, uu, a.shape[0])); continue
    v, dd, sd = a[:, 0], a[:, 1], a[:, 2]
    # A wall FACE in the wrong place along d displaces a jamb toward whichever side the camera stands on,
    # so its offset FLIPS SIGN as the camera crosses the opening. A jamb genuinely in the wrong place along
    # the hall does not flip. West/east here is the camera's side, not the jamb's.
    wv = v[sd < 0]; ev = v[sd > 0]
    ws = '%+.3f(%d)' % (np.median(wv), wv.size) if wv.size >= 3 else '   -    '
    es = '%+.3f(%d)' % (np.median(ev), ev.size) if ev.size >= 3 else '   -    '
    print('  %-22s u %6.3f   n %3d   offset %+.3f m  p25 %+.3f p75 %+.3f   camera west %s  east %s'
          % (name, uu, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75), ws, es))
    rows.append((oi, name, float(np.median(v))))
# the width of each opening follows from its two jambs, and 1.256 is what the model draws
byo = {}
for oi, name, m in rows: byo.setdefault(oi, {})['east' if 'east' in name else 'west'] = m
print('  -- opening widths, measured against what the model now draws')
wd = []
for oi in sorted(byo):
    p = byo[oi]
    if 'west' in p and 'east' in p:
        drawn = OPEN[oi][1] - OPEN[oi][0]
        w = drawn + p['east'] - p['west']; wd.append(w)
        print('     opening %2d   drawn %.3f   measured %.3f m  (%+.3f)' % (oi, drawn, w, w - drawn))
if wd: print('     median %.3f m over %d openings' % (float(np.median(wd)), len(wd)))
# The joint fit. Every jamb's measured offset is modelled as its own true error along the hall PLUS one
# shared term for the wall face sitting at the wrong depth: offset = a_jamb + b * tan(angle off the normal).
# One b for the whole wall, one a per jamb, solved together by least squares. b is minus the face error, so
# a positive b means the real wall face stands SOUTH of the drawn d -0.09, further into the hall.
names = [n for n, _, _ in JAMBS if len(acc[n]) >= 5]
if len(names) >= 4:
    rowsA, rhs, idx = [], [], {n: i for i, n in enumerate(names)}
    for n in names:
        for off, dist, sd, tn in acc[n]:
            r = np.zeros(len(names) + 1); r[idx[n]] = 1.0; r[-1] = tn
            rowsA.append(r); rhs.append(off)
    A = np.array(rowsA); y = np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ sol
    print('  -- joint fit over %d jambs, %d measurements' % (len(names), len(y)))
    print('     wall face depth term b %+.3f m  (residual rms %.3f m; the same fit with b forced to zero: rms %.3f)'
          % (sol[-1], float(np.sqrt((res ** 2).mean())),
             float(np.sqrt(((y - A[:, :-1] @ np.linalg.lstsq(A[:, :-1], y, rcond=None)[0]) ** 2).mean()))))
    for n in names:
        print('     %-22s true offset along the hall %+.3f m' % (n, sol[idx[n]]))
