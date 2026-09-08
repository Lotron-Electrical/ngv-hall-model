# Brightness along the north wall face at height h, u step 0.1, through posed frames: the lit doorway
# is the bright run. Prints the run's u edges (half-max) per frame, and the h profile at the run's middle.
#   python tools/door_profile.py <h> <u_lo> <u_hi> class:frame ...
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
hz, ulo, uhi = map(float, sys.argv[1:4]); dw = -0.09
for spec in sys.argv[4:]:
    cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]; g = cv2.imread(p, 0).astype(float)
    us = np.arange(ulo, uhi + 0.001, 0.1)
    x, y, z = cam.project(np.asarray([world(u, dw, hz) for u in us]))
    ok = np.logical_and.reduce([z > 0, x >= 1, x < cam.w - 1, y >= 1, y < cam.h - 1])
    v = np.full(len(us), np.nan)
    for i in np.where(ok)[0]: v[i] = g[int(y[i]) - 1:int(y[i]) + 2, int(x[i]) - 1:int(x[i]) + 2].mean()
    good = ~np.isnan(v)
    if good.sum() < 5: print(k, 'off frame'); continue
    lo, hi = np.nanpercentile(v, 10), np.nanmax(v); thr = (lo + hi) / 2
    bright = np.logical_and(good, v > thr)
    idx = np.where(bright)[0]
    if len(idx) == 0: print(k, 'no bright run'); continue
    # the longest contiguous run
    runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1); r = max(runs, key=len)
    ue, uw = us[r[0]], us[r[-1]]
    edge_e = 'edge' if r[0] > 0 and good[r[0] - 1] else 'FRAME'; edge_w = 'edge' if r[-1] < len(us) - 1 and good[r[-1] + 1] else 'FRAME'
    um = (ue + uw) / 2
    hs = np.arange(0, 4.01, 0.1); x2, y2, z2 = cam.project(np.asarray([world(um, dw, h) for h in hs]))
    vh = [g[int(yy) - 1:int(yy) + 2, int(xx) - 1:int(xx) + 2].mean() if (zz > 0 and 1 <= xx < cam.w - 1 and 1 <= yy < cam.h - 1) else np.nan for xx, yy, zz in zip(x2, y2, z2)]
    vh = np.array(vh); bh = np.where(vh > thr)[0]
    head = hs[bh[-1]] if len(bh) else float('nan')
    print('%s %s h%.1f: lit u %.1f (%s) .. %.1f (%s), width %.1f, floor 10%% %.0f max %.0f; head at u %.1f: h %.1f' % (cls, k, hz, ue, edge_e, uw, edge_w, uw - ue, lo, hi, um, head))
    print('   ', ' '.join('%.0f' % a if not np.isnan(a) else '.' for a in v[::2]))
