# The tapestries' edges on the wall: colour saturation sampled along the wall plane through posed frames
# (three rows for the u edges, one column for the h edges). Prints per frame; the tapestry is the
# saturated run.   python tools/tapestry_edges.py <north|south> <u0> <u1> <h0> <h1> class:frame ...
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
side = sys.argv[1]; u0, u1, h0, h1 = map(float, sys.argv[2:6]); dw = -0.09 if side == 'north' else 15.364
def run(vals, xs, thr):
    ok = ~np.isnan(vals); idx = np.where(np.logical_and(ok, vals > thr))[0]
    if len(idx) == 0: return None
    runs = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1); r = max(runs, key=len)
    return xs[r[0]], xs[r[-1]], ('FRAME' if r[0] == 0 or not ok[r[0] - 1] else 'edge'), ('FRAME' if r[-1] == len(xs) - 1 or not ok[r[-1] + 1] else 'edge')
for spec in sys.argv[6:]:
    cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]; im = cv2.imread(p); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); S = hsv[:, :, 1].astype(float)
    def sample(pts):
        x, y, z = cam.project(np.asarray(pts)); v = np.full(len(pts), np.nan)
        for i in range(len(pts)):
            if z[i] > 0 and 3 <= x[i] < cam.w - 3 and 3 <= y[i] < cam.h - 3: v[i] = S[int(y[i]) - 3:int(y[i]) + 4, int(x[i]) - 3:int(x[i]) + 4].mean()
        return v
    us = np.arange(u0 - 2, u1 + 2.001, 0.05); out = []
    for hz in (h0 + 0.25 * (h1 - h0), (h0 + h1) / 2, h0 + 0.75 * (h1 - h0)):
        v = sample([world(u, dw, hz) for u in us])
        if np.isnan(v).sum() > len(v) * 0.6: out.append('h%.1f off' % hz); continue
        thr = (np.nanpercentile(v, 15) + np.nanpercentile(v, 90)) / 2; r = run(v, us, thr)
        out.append('h%.1f: u %.2f(%s)..%.2f(%s)' % (hz, r[0], r[2], r[1], r[3]) if r else 'h%.1f: none' % hz)
    hs = np.arange(h0 - 1.5, h1 + 1.501, 0.05); um = (u0 + u1) / 2
    v = sample([world(um, dw, h) for h in hs])
    if np.isnan(v).sum() <= len(v) * 0.6:
        thr = (np.nanpercentile(v, 15) + np.nanpercentile(v, 90)) / 2; r = run(v, hs, thr)
        out.append('u%.1f: h %.2f(%s)..%.2f(%s)' % (um, r[0], r[2], r[1], r[3]) if r else 'u%.1f: none' % um)
    print(cls, k, ' | '.join(out))
