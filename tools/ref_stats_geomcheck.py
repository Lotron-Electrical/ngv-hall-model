"""Track C step 5: decide which members of lf02.jpg are bay ridges (crest, constant height)
and which are the 3.7 m cross members (vertex to ridge midpoint, rising 0.86 m).

Physics: a member that stays at one height is a straight 3D line and projects straight.
A cross member V-M-V' is a ^ in elevation (0 -> 0.86 -> 0 m) so, unless the camera sits
in its vertical plane, it projects with a kink at M of about 0.86/12.9 = 6.6 % of its
lateral offset from the principal point. At 470 px offset that is ~30 px, easily seen.

Usage: python tools/ref_stats_geomcheck.py <lf02.jpg> <out_dir>
Writes <out_dir>/geomcheck.json and geomcheck_overlay.jpg
"""
import sys, os, json
import numpy as np
import cv2

src, out = sys.argv[1], sys.argv[2]
img = cv2.imread(src); H, W = img.shape[:2]
V = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32)
dark = 1.0 - V / 255.0
g = json.load(open(os.path.join(out, 'grid.json')))
vx = [m['centre'] for m in g['vertical']]                       # 169, 636.5, 1109
hy = sorted(m['centre'] for m in g['horizontal'] if m['w_p50'] > 20)   # 22, 493.75, 960

def dark_centre(prof, c, half=40, thr=0.72):
    """centre of the dark run around c in a 1-D darkness profile; None if no run"""
    lo = max(0, int(c - half)); hi = min(len(prof), int(c + half))
    seg = prof[lo:hi]
    m = seg >= thr
    if not m.any():
        return None
    # take the run closest to c
    runs = []; i = 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]:
                j += 1
            runs.append((lo + i, lo + j - 1)); i = j
        else:
            i += 1
    a, b = min(runs, key=lambda r: abs(0.5 * (r[0] + r[1]) - c))
    if b - a > 90:
        return None
    return 0.5 * (a + b)

res = {}
ov = img.copy()
def trace(orientation, c, label):
    pts = []
    n = H if orientation == 'v' else W
    for t in range(10, n - 10, 4):
        prof = dark[t, :] if orientation == 'v' else dark[:, t]
        cc = dark_centre(prof, c)
        if cc is not None:
            pts.append((t, cc))
    pts = np.array(pts)
    # fit a straight line through the end thirds, measure the mid third deviation
    t, c_ = pts[:, 0], pts[:, 1]
    ends = (t < n * 0.2) | (t > n * 0.8)
    A = np.vstack([t[ends], np.ones(ends.sum())]).T
    k, b = np.linalg.lstsq(A, c_[ends], rcond=None)[0]
    resid = c_ - (k * t + b)
    mid = (t > n * 0.4) & (t < n * 0.6)
    r = dict(label=label, n=int(len(pts)), slope_px_per_px=float(k),
             end_fit_rms_px=float(np.sqrt((resid[ends] ** 2).mean())),
             mid_deviation_px_median=float(np.median(resid[mid])),
             deviation_p10_p50_p90=[float(np.percentile(resid, q)) for q in (10, 50, 90)],
             samples=[[float(a), float(b_)] for a, b_ in pts[::10]])
    for tt, cc in pts:
        p = (int(cc), int(tt)) if orientation == 'v' else (int(tt), int(cc))
        cv2.circle(ov, p, 2, (0, 255, 0), -1)
    p1 = (int(k * 0 + b), 0) if orientation == 'v' else (0, int(b))
    p2 = (int(k * n + b), n) if orientation == 'v' else (n, int(k * n + b))
    cv2.line(ov, p1, p2, (0, 0, 255), 1)
    return r

for i, x in enumerate(vx):
    res[f'v{i}_x{int(x)}'] = trace('v', x, f'vertical member at x={x:.0f}')
for i, y in enumerate(hy):
    res[f'h{i}_y{int(y)}'] = trace('h', y, f'horizontal member at y={y:.0f}')
for k, r in res.items():
    print(k, 'n', r['n'], 'slope', round(r['slope_px_per_px'], 4), 'mid dev', round(r['mid_deviation_px_median'], 1),
          'dev p10/50/90', [round(v, 1) for v in r['deviation_p10_p50_p90']])

# expected kink for a cross member: 0.86 m rise over a member ~3.7 m from the principal point,
# camera ~12.9 m below the vertex  ->  offset * 0.86/12.9
for k, r in res.items():
    c0 = float(k.split('_')[1][1:])
    off = abs(c0 - (W / 2 if k.startswith('v') else H / 2))
    r['expected_kink_px_if_cross_member'] = float(off * 0.86 / 12.9)
    r['offset_from_image_centre_px'] = off
cv2.imwrite(os.path.join(out, 'geomcheck_overlay.jpg'), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(res, open(os.path.join(out, 'geomcheck.json'), 'w'), indent=1)
