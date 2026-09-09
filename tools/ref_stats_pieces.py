"""Track C step 2: piece statistics from lf02.jpg using the grid from ref_stats_grid.py.

Usage: python tools/ref_stats_pieces.py <lf02.jpg> <out_dir>
Reads  <out_dir>/grid.json
Writes <out_dir>/pieces.json, seg_overlay.jpg, crops
"""
import sys, os, json
import numpy as np
import cv2

src, out = sys.argv[1], sys.argv[2]
img = cv2.imread(src)
H, W = img.shape[:2]
g = json.load(open(os.path.join(out, 'grid.json')))
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
V = hsv[..., 2]

# --- grid model (only the real members; 246/736 rows were motif rows, not beams) ---
vx = sorted(m['centre'] for m in g['vertical'])            # 169, 636.5, 1109
hy = [m['centre'] for m in g['horizontal'] if m['w_p50'] > 20]  # 22, 493.75, 960
hy = sorted(hy)
assert len(vx) == 3 and len(hy) == 3, (vx, hy)
heavy_w = 0.5 * (g['vertical'][1]['w_p50'] + [m for m in g['horizontal'] if m['centre'] > 400 and m['centre'] < 600][0]['w_p50'])
light_w = np.mean([g['vertical'][0]['w_p50'], g['vertical'][2]['w_p50'],
                   [m for m in g['horizontal'] if m['centre'] < 100][0]['w_p50'],
                   [m for m in g['horizontal'] if m['centre'] > 900][0]['w_p50']])
pitch_px = float(np.mean([vx[1] - vx[0], vx[2] - vx[1], hy[1] - hy[0], hy[2] - hy[1]]))
px_per_m = pitch_px / 3.7035   # mean of 7.4285/2 and 7.3855/2
mm_per_px = 1000.0 / px_per_m
print(f"pitch {pitch_px:.1f} px -> {px_per_m:.1f} px/m, {mm_per_px:.2f} mm/px")

# sub-squares: TL, TR, BL, BR (x0,y0,x1,y1)
squares = {
    'TL': (vx[0], hy[0], vx[1], hy[1]), 'TR': (vx[1], hy[0], vx[2], hy[1]),
    'BL': (vx[0], hy[1], vx[1], hy[2]), 'BR': (vx[1], hy[1], vx[2], hy[2]),
}

# --- glass mask ---
thr = int(sys.argv[3]) if len(sys.argv) > 3 else 110
mask = (V > thr).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, connectivity=4)
min_area = 40
keep = np.zeros(n, bool)
keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
mask2 = keep[lab].astype(np.uint8)

# --- rib band mask (measured widths) for the field-area denominator ---
rib = np.zeros((H, W), np.uint8)
for i, x in enumerate(vx):
    w = heavy_w if i == 1 else light_w
    cv2.line(rib, (int(x), 0), (int(x), H), 1, int(round(w)))
for i, y in enumerate(hy):
    w = heavy_w if i == 1 else light_w
    cv2.line(rib, (0, int(y)), (W, int(y)), 1, int(round(w)))
# diagonals: corner-to-corner of each sub-square, width measured locally (dark run across the line)
def run_width_profile(prof, centre, t):
    if prof[centre] < t:
        return None
    a = centre
    while a > 0 and prof[a - 1] >= t:
        a -= 1
    b = centre
    while b < len(prof) - 1 and prof[b + 1] >= t:
        b += 1
    return a, b
dark = 1.0 - V.astype(np.float32) / 255.0
def local_width(p1, p2, t=0.72, search=12):
    x1, y1 = p1; x2, y2 = p2
    L = np.hypot(x2 - x1, y2 - y1); ang = np.arctan2(y2 - y1, x2 - x1)
    nx, ny = -np.sin(ang), np.cos(ang)
    ws = []
    for s_ in np.arange(40, L - 40, 3):
        cx = x1 + s_ * np.cos(ang); cy = y1 + s_ * np.sin(ang)
        s = np.arange(-45, 46)
        xs = (cx + s * nx).astype(np.float32); ys = (cy + s * ny).astype(np.float32)
        oob = (xs < 0) | (ys < 0) | (xs >= W - 1) | (ys >= H - 1)
        if oob[45 - search:46 + search].any():
            continue
        prof = cv2.remap(dark, xs[None], ys[None], cv2.INTER_LINEAR)[0]
        prof[oob] = 0.0   # outside the frame counts as 'not dark' so the run stops there
        best = None
        for c0 in range(45 - search, 46 + search):
            r = run_width_profile(prof, c0, t)
            if r and (best is None or (r[1] - r[0]) < (best[1] - best[0])):
                best = r
        if best and (best[1] - best[0]) < 80:
            ws.append(best[1] - best[0] + 1)
    ws = np.array(ws)
    if len(ws) == 0:
        return dict(n=0, p10=None, p25=None, p50=None, p75=None)
    return dict(n=len(ws), p10=float(np.percentile(ws, 10)), p25=float(np.percentile(ws, 25)),
                p50=float(np.percentile(ws, 50)), p75=float(np.percentile(ws, 75)))
diag_lines = []
centre = (vx[1], hy[1])
for k, (x0, y0, x1, y1) in squares.items():
    corners = dict(TL=((x0, y0), (x1, y1)), TR=((x1, y0), (x0, y1)), BL=((x0, y1), (x1, y0)), BR=((x1, y1), (x0, y0)))[k]
    # main = vertex (outer corner) to bay corner (centre); anti = the other two corners
    vert_c = corners[0]
    main = (vert_c, centre)
    others = [c for c in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)] if c != vert_c and c != centre]
    anti = (others[0], others[1])
    for name, (pa, pb) in (('main', main), ('anti', anti)):
        st = local_width(pa, pb)
        st.update(square=k, kind=name, p1=[float(pa[0]), float(pa[1])], p2=[float(pb[0]), float(pb[1])])
        diag_lines.append(st)
        print(k, name, st)
main_w = float(np.median([d['p50'] for d in diag_lines if d['kind'] == 'main']))
anti_w = float(np.median([d['p50'] for d in diag_lines if d['kind'] == 'anti']))
diag_w = 0.5 * (main_w + anti_w)
for d in diag_lines:
    w = main_w if d['kind'] == 'main' else anti_w
    cv2.line(rib, (int(d['p1'][0]), int(d['p1'][1])), (int(d['p2'][0]), int(d['p2'][1])), 1, int(round(w)))
# also measure the axis members locally the same way (consistency check)
axis_w = {}
for i, x in enumerate(vx):
    axis_w[f'v{i}'] = local_width((x, 0), (x, H))
for i, y in enumerate(hy):
    axis_w[f'h{i}'] = local_width((0, y), (W, y))
print('axis widths', {k: (v['p25'], v['p50']) for k, v in axis_w.items()})
print(f"heavy {heavy_w:.1f}px={heavy_w*mm_per_px:.0f}mm light {light_w:.1f}px={light_w*mm_per_px:.0f}mm diag {diag_w:.1f}px={diag_w*mm_per_px:.0f}mm; {len(diag_lines)} diag lines")

# --- per-square coverage ---
cov = {}
for k, (x0, y0, x1, y1) in squares.items():
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    sq = mask2[y0:y1, x0:x1]; rb = rib[y0:y1, x0:x1]
    A = sq.size; Ar = int(rb.sum()); Ag = int(sq.sum())
    cov[k] = dict(area_px=A, rib_px=Ar, glass_px=Ag,
                  glass_frac_of_square=Ag / A,
                  glass_frac_of_field=Ag / (A - Ar),
                  rib_frac_of_square=Ar / A)
    print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in cov[k].items()})

# --- per-piece stats inside the four squares ---
n, lab, stats, cent = cv2.connectedComponentsWithStats(mask2, connectivity=4)
pieces = []
Lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)
dt = cv2.distanceTransform(mask2, cv2.DIST_L2, 3)
sq_region = np.zeros((H, W), np.uint8)
for k, (x0, y0, x1, y1) in squares.items():
    sq_region[int(y0):int(y1), int(x0):int(x1)] = 1
for i in range(1, n):
    x, y, w, h, a = stats[i]
    cx, cy = cent[i]
    if a < min_area or not sq_region[int(cy), int(cx)]:
        continue
    if x <= 0 or y <= 0 or x + w >= W or y + h >= H:
        continue
    comp = (lab[y:y + h, x:x + w] == i)
    cnt, _ = cv2.findContours(comp.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnt, key=cv2.contourArea)
    hull = cv2.convexHull(c)
    hull_a = max(cv2.contourArea(hull), 1)
    (rx, ry), (rw, rh), rang = cv2.minAreaRect(c)
    rect_a = max(rw * rh, 1)
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.06 * peri, True)
    nv = len(approx)
    solidity = a / hull_a
    rect_fill = a / rect_a
    if rect_fill > 0.80 and nv == 4:
        shape = 'rect'
    elif nv == 3 or (rect_fill < 0.62 and solidity > 0.9 and nv <= 4):
        shape = 'tri'
    else:
        shape = 'irregular'
    inner = comp & (dt[y:y + h, x:x + w] >= 2)
    if inner.sum() < 8:
        inner = comp
    px = rgb[y:y + h, x:x + w][inner]
    med = np.median(px, axis=0)
    hsvm = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_RGB2HSV)[0, 0]
    hue = float(hsvm[0]) * 2.0; sat = float(hsvm[1]) / 255.0; val = float(hsvm[2]) / 255.0
    # look stats
    d = dt[y:y + h, x:x + w][comp]; l = Lum[y:y + h, x:x + w][comp]
    prof = {}
    for r in (1, 2, 3):
        m = (d >= r) & (d < r + 1)
        prof[r] = float(l[m].mean()) if m.sum() > 3 else None
    mi = d >= 4
    interior_mean = float(l[mi].mean()) if mi.sum() > 8 else None
    interior_std = float(l[mi].std()) if mi.sum() > 8 else None
    clipped = float((px.max(axis=1) >= 250).mean())
    pieces.append(dict(id=int(i), cx=float(cx), cy=float(cy), area_px=int(a),
                       eq_diam_mm=float(2 * np.sqrt(a / np.pi) * mm_per_px),
                       rect_w_mm=float(max(rw, rh) * mm_per_px), rect_h_mm=float(min(rw, rh) * mm_per_px),
                       aspect=float(max(rw, rh) / max(min(rw, rh), 1)), rect_fill=float(rect_fill),
                       solidity=float(solidity), nverts=int(nv), shape=shape,
                       med_rgb=[int(v) for v in med], hue=hue, sat=sat, val=val, clipped_frac=clipped,
                       edge_prof=prof, interior_mean=interior_mean, interior_std=interior_std))
print("pieces:", len(pieces))

# --- matrix colour (well away from pieces), inside squares, outside rib bands / inside rib bands ---
dt_out = cv2.distanceTransform((1 - mask2).astype(np.uint8), cv2.DIST_L2, 3)
far = (dt_out >= 4) & (sq_region == 1)
mat_field = np.median(rgb[far & (rib == 0)], axis=0)
mat_rib = np.median(rgb[far & (rib == 1)], axis=0)
mat_field_p = np.percentile(Lum[far & (rib == 0)], [10, 50, 90])
print("matrix field rgb", mat_field, "rib rgb", mat_rib, "field lum p10/50/90", mat_field_p)

# --- overlays ---
ov = img.copy()
col = {'rect': (0, 255, 0), 'tri': (0, 200, 255), 'irregular': (255, 0, 255)}
for p in pieces:
    cv2.circle(ov, (int(p['cx']), int(p['cy'])), 2, col[p['shape']], -1)
edges = cv2.morphologyEx(mask2, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
ov[edges > 0] = (0, 255, 255)
ov[(rib > 0) & (mask2 == 0)] = (ov[(rib > 0) & (mask2 == 0)] * 0.5 + np.array([60, 0, 0])).astype(np.uint8)
cv2.imwrite(os.path.join(out, 'seg_overlay.jpg'), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
# crops used for measurement
x0, y0, x1, y1 = [int(v) for v in squares['TL']]
cv2.imwrite(os.path.join(out, 'crop_TL_square.jpg'), img[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 92])
motif = img[360:480, 260:520]
cv2.imwrite(os.path.join(out, 'crop_motifs_x4.jpg'), cv2.resize(motif, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 92])
big = img[40:140, 260:380]
cv2.imwrite(os.path.join(out, 'crop_pieces_x6.jpg'), cv2.resize(big, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 92])
ridge = img[440:550, 560:760]
cv2.imwrite(os.path.join(out, 'crop_ridge_corner_x4.jpg'), cv2.resize(ridge, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 92])

json.dump(dict(pitch_px=pitch_px, px_per_m=px_per_m, mm_per_px=mm_per_px,
               heavy_w_px=heavy_w, light_w_px=light_w, diag_w_px=diag_w, main_diag_w_px=main_w, anti_diag_w_px=anti_w, diag_lines=diag_lines, axis_w=axis_w, thr=thr,
               squares=squares, coverage=cov, pieces=pieces,
               matrix_field_rgb=[float(v) for v in mat_field], matrix_rib_rgb=[float(v) for v in mat_rib],
               matrix_field_lum_p10_50_90=[float(v) for v in mat_field_p]),
          open(os.path.join(out, 'pieces.json'), 'w'), indent=1)
np.save(os.path.join(out, 'mask.npy'), mask2)
