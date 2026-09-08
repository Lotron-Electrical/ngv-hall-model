# Brightness up an end face plane (u = face) at given d stations, h 3..12 step 0.05, through posed
# frames; prints the profile (every 0.2) and the strongest brightness steps (h, sign, size).
#   python tools/end_profile.py <east|west> <d_csv> class:frame ...
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
side = sys.argv[1]; uF = 48.056 if side == 'east' else 4.194; ds = [float(a) for a in sys.argv[2].split(',')]
hs = np.arange(3.0, 12.01, 0.05)
for spec in sys.argv[3:]:
    cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]; g = cv2.imread(p, 0).astype(float)
    for dd in ds:
        x, y, z = cam.project(np.asarray([world(uF, dd, h) for h in hs]))
        v = np.full(len(hs), np.nan)
        for i in range(len(hs)):
            if z[i] > 0 and 2 <= x[i] < cam.w - 2 and 2 <= y[i] < cam.h - 2: v[i] = g[int(y[i]) - 2:int(y[i]) + 3, int(x[i]) - 2:int(x[i]) + 3].mean()
        if np.isnan(v).sum() > len(v) * 0.5: print(cls, k, 'd%.1f mostly off frame' % dd); continue
        print('%s %s d%.1f:' % (cls, k, dd), ' '.join(('%.0f' % a if not np.isnan(a) else '.') for a in v[::4]))
        sm = np.convolve(np.nan_to_num(v, nan=np.nanmean(v)), np.ones(5) / 5, 'same'); dv = np.diff(sm)
        idx = np.argsort(-np.abs(dv))[:12]; picks = []
        for i in sorted(idx):
            if picks and abs(hs[i] - picks[-1][0]) < 0.3: continue
            picks.append((hs[i], dv[i]))
        print('    steps:', ' '.join('%.2f%s%.0f' % (h, '+' if s > 0 else '-', abs(s)) for h, s in picks))
