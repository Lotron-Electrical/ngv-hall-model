# The end galleries' accuracy in numbers: on a posed frame and the sim rendered from its pose
# (tools/pose_pair.py's pair), the brightness profile up the end face at several d stations is
# stepped in both halves, every sim step is matched to the nearest real step, and the residual
# (real minus sim, metres up the wall) is printed per station, then summarised.
#   python tools/end_residual.py <east|west> <d_csv> class:frame:pair.jpg ...
import sys, os, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
side = sys.argv[1]; uF = 48.056 if side == 'east' else 4.194; ds = [float(a) for a in sys.argv[2].split(',')]
hs = np.arange(float(os.environ.get('HMIN', 3.0)), float(os.environ.get('HMAX', 12.0)) + 0.01, 0.05)
def steps(v, n=8):
    sm = np.convolve(np.nan_to_num(v, nan=np.nanmean(v)), np.ones(5) / 5, 'same'); dv = np.diff(sm)
    idx = np.argsort(-np.abs(dv))[:n * 2]; picks = []
    for i in sorted(idx):
        if hs[i] < hs[0] + 0.15 or hs[i] > hs[-1] - 0.15: continue   # the profile's own ends are not edges
        if picks and abs(hs[i] - picks[-1][0]) < 0.3: continue
        picks.append((hs[i], dv[i]))
    return picks[:n]
allres = []
for spec in sys.argv[3:]:
    cname, fr, pairpath = spec.split(':', 2); cam, ipath = U.load_class(cname)[fr]
    real = cv2.imread(ipath, 0).astype(float); pair = cv2.imread(pairpath, 0); sim = pair[:, pair.shape[1] // 2:].astype(float)
    down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0]); rot = None
    if abs(down[1]) < abs(right[1]): rot = 'cw' if right[1] < 0 else 'ccw'
    elif down[1] > 0: rot = '180'
    def px(x, y):
        if rot == 'cw': return cam.h - 1 - y, x
        if rot == 'ccw': return y, cam.w - 1 - x
        if rot == '180': return cam.w - 1 - x, cam.h - 1 - y
        return x, y
    for dd in ds:
        x, y, z = cam.project(np.asarray([world(uF, dd, h) for h in hs]))
        vr = np.full(len(hs), np.nan); vs = np.full(len(hs), np.nan)
        for i in range(len(hs)):
            if z[i] > 0 and 2 <= x[i] < cam.w - 2 and 2 <= y[i] < cam.h - 2:
                xx, yy = int(x[i]), int(y[i]); vr[i] = real[yy - 2:yy + 3, xx - 2:xx + 3].mean()
                sx, sy = px(xx, yy); vs[i] = sim[sy - 2:sy + 3, sx - 2:sx + 3].mean()
        if np.isnan(vr).sum() > len(vr) * 0.5: print(fr, 'd%.1f off frame' % dd); continue
        sr, ss = steps(vr), steps(vs); out = []
        for h, s in ss:
            cand = [(abs(h2 - h), h2) for h2, s2 in sr if (s2 > 0) == (s > 0) and abs(h2 - h) <= 0.45]
            if cand: r = min(cand)[1] - h; out.append((h, r)); allres.append(r)
            else: out.append((h, None))
        print('%s d%.1f: ' % (fr, dd) + '  '.join('sim %.2f%s -> %s' % (h, '+' if s > 0 else '-', ('real %+.2f' % r) if r is not None else 'none') for (h, s), (_, r) in zip(ss, out)))
a = np.array(allres)
if len(a): print('matched %d sim steps: residual mean %+.2f m, median %+.2f, |median| %.2f, 90%% within %.2f m' % (len(a), a.mean(), np.median(a), np.median(np.abs(a)), np.percentile(np.abs(a), 90)))
