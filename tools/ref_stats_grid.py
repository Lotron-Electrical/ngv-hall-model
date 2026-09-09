"""Track C step 1: find the rib grid in lf02.jpg (Rory Hyde 2004 straight-up shot).

Finds the heavy horizontal ridge, the vertical 3.7 m cross members and the
panel diagonals by maximising mean darkness along candidate lines, then
measures the dark-run width across each line at many sample points.

Usage: python tools/ref_stats_grid.py <lf02.jpg> <out_dir>
Writes <out_dir>/grid.json and <out_dir>/grid_overlay.jpg
"""
import sys, os, json
import numpy as np
import cv2

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
img = cv2.imread(src)
H, W = img.shape[:2]
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
V = hsv[..., 2].astype(np.float32)
dark = 1.0 - V / 255.0

# ---------- axis-aligned members ----------
col = dark.mean(axis=0)
row = dark.mean(axis=1)

def peaks(prof, min_dist, thr):
    idx = []
    p = prof.copy()
    while True:
        i = int(np.argmax(p))
        if p[i] < thr:
            break
        idx.append(i)
        lo, hi = max(0, i - min_dist), min(len(p), i + min_dist)
        p[lo:hi] = 0
    return sorted(idx)

vx = peaks(col, 200, col.mean() + 0.6 * col.std())
hy = peaks(row, 200, row.mean() + 0.6 * row.std())
print("column-darkness peaks (vertical members) x =", vx)
print("row-darkness peaks (horizontal members) y =", hy)

# refine each axis-aligned member: centre + width from the dark run
def run_width_profile(prof, centre, thr):
    """dark run containing centre in a 1-D profile (thr = darkness threshold)"""
    if prof[centre] < thr:
        return None
    a = centre
    while a > 0 and prof[a - 1] >= thr:
        a -= 1
    b = centre
    while b < len(prof) - 1 and prof[b + 1] >= thr:
        b += 1
    return a, b

def member_stats(orientation, c, thr=0.72):
    widths, centres = [], []
    n = H if orientation == 'v' else W
    for t in range(0, n, 2):
        prof = dark[t, :] if orientation == 'v' else dark[:, t]
        best = None
        for c0 in range(c - 12, c + 13):
            if 0 <= c0 < len(prof):
                r = run_width_profile(prof, c0, thr)
                if r and (best is None or (r[1] - r[0]) < (best[1] - best[0])):
                    best = r
        if best and (best[1] - best[0]) < 80:
            widths.append(best[1] - best[0] + 1)
            centres.append(0.5 * (best[0] + best[1]))
    widths = np.array(widths)
    return dict(centre=float(np.median(centres)), n=len(widths),
                w_p10=float(np.percentile(widths, 10)), w_p25=float(np.percentile(widths, 25)),
                w_p50=float(np.percentile(widths, 50)), w_p75=float(np.percentile(widths, 75)))

vert = [member_stats('v', x) for x in vx]
horz = [member_stats('h', y) for y in hy]
print("vertical members:", vert)
print("horizontal members:", horz)

# ---------- diagonals ----------
# candidate diagonals pass through the intersections of the grid; search angle+offset
def line_darkness(x0, y0, ang, thr=None):
    L = int(np.hypot(W, H))
    t = np.arange(-L, L)
    xs = x0 + t * np.cos(ang)
    ys = y0 + t * np.sin(ang)
    m = (xs >= 0) & (xs < W - 1) & (ys >= 0) & (ys < H - 1)
    xs, ys = xs[m], ys[m]
    vals = cv2.remap(dark, xs.astype(np.float32)[None], ys.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
    return float(vals.mean()), len(vals)

vxs = [m['centre'] for m in vert]
hys = [m['centre'] for m in horz]
sx = np.median(np.diff(vxs)) if len(vxs) > 1 else None
sy = None
print("sub-square pitch px: x", sx)

# intersections of ridge and vertical members are diagonal endpoints
diags = []
for x0 in vxs:
    for y0 in hys:
        for base in (np.pi / 4, -np.pi / 4):
            best = None
            for da in np.linspace(-0.06, 0.06, 25):
                for dx in range(-6, 7):
                    d, n = line_darkness(x0 + dx, y0, base + da)
                    if best is None or d > best[0]:
                        best = (d, x0 + dx, y0, base + da)
            diags.append(dict(darkness=best[0], x0=float(best[1]), y0=float(best[2]), ang=float(best[3])))
# dedupe near-identical lines
uniq = []
for d in sorted(diags, key=lambda d: -d['darkness']):
    dup = False
    for u in uniq:
        if abs(u['ang'] - d['ang']) < 0.02:
            # distance of d's anchor from u's line
            nx, ny = -np.sin(u['ang']), np.cos(u['ang'])
            dist = abs((d['x0'] - u['x0']) * nx + (d['y0'] - u['y0']) * ny)
            if dist < 15:
                dup = True
                break
    if not dup:
        uniq.append(d)
print("diagonals:", len(uniq))

def diag_width(d, thr=0.72):
    """perpendicular dark-run width sampled along the line"""
    ang = d['ang']; nx, ny = -np.sin(ang), np.cos(ang)
    L = int(np.hypot(W, H))
    widths = []
    for t in range(-L, L, 3):
        cx = d['x0'] + t * np.cos(ang); cy = d['y0'] + t * np.sin(ang)
        if not (10 < cx < W - 10 and 10 < cy < H - 10):
            continue
        s = np.arange(-40, 41)
        xs = (cx + s * nx).astype(np.float32); ys = (cy + s * ny).astype(np.float32)
        m = (xs >= 0) & (xs < W - 1) & (ys >= 0) & (ys < H - 1)
        if m.sum() < 60:
            continue
        prof = cv2.remap(dark, xs[None], ys[None], cv2.INTER_LINEAR)[0]
        best = None
        for c0 in range(34, 47):
            r = run_width_profile(prof, c0, thr)
            if r and (best is None or (r[1] - r[0]) < (best[1] - best[0])):
                best = r
        if best and (best[1] - best[0]) < 70:
            widths.append(best[1] - best[0] + 1)
    widths = np.array(widths)
    if len(widths) == 0:
        return {}
    return dict(n=len(widths), w_p10=float(np.percentile(widths, 10)), w_p25=float(np.percentile(widths, 25)),
                w_p50=float(np.percentile(widths, 50)), w_p75=float(np.percentile(widths, 75)))

for d in uniq:
    d.update(diag_width(d))
    print(d)

# overlay
ov = img.copy()
for m in vert:
    cv2.line(ov, (int(m['centre']), 0), (int(m['centre']), H), (0, 255, 255), 2)
for m in horz:
    cv2.line(ov, (0, int(m['centre'])), (W, int(m['centre'])), (0, 255, 255), 2)
for d in uniq:
    L = 3000
    p1 = (int(d['x0'] - L * np.cos(d['ang'])), int(d['y0'] - L * np.sin(d['ang'])))
    p2 = (int(d['x0'] + L * np.cos(d['ang'])), int(d['y0'] + L * np.sin(d['ang'])))
    cv2.line(ov, p1, p2, (255, 0, 255), 1)
cv2.imwrite(os.path.join(out, 'grid_overlay.jpg'), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(dict(W=W, H=H, vertical=vert, horizontal=horz, diagonals=uniq, pitch_px_x=float(sx) if sx else None),
          open(os.path.join(out, 'grid.json'), 'w'), indent=1)
